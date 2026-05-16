from __future__ import annotations

import io
from uuid import UUID
from typing import List, Optional, Dict, Tuple

from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark_run import BenchmarkRun, RunStatus
from app.models.benchmark_execution import BenchmarkExecution, ExecutionStatus
from app.models.llm_model import LLMModel
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.schemas.benchmark import BenchmarkRunCreate

try:
    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from openpyxl.styles import Font, Border, Side
except ImportError:  # pragma: no cover
    Workbook = None  # type: ignore


class BenchmarkService:
    """
    Service responsible for benchmark run operations.
    """

    async def create_run(self, db: AsyncSession, payload: BenchmarkRunCreate) -> BenchmarkRun:
        """
        Create a new benchmark run with executions for each test case and model combination.
        """
        stmt = select(TestCase.id).where(TestCase.suite_id.in_(payload.suite_ids))
        result = await db.execute(stmt)
        test_case_ids = result.scalars().all()

        if not test_case_ids:
            raise ValueError("Wybrane zbiory testowe są puste (brak przypadków testowych).")

        default_name = f"Benchmark: {len(payload.model_ids)} modeli, {len(payload.suite_ids)} zbiorów"
        new_run = BenchmarkRun(
            name=payload.name or default_name,
            status=RunStatus.PENDING
        )

        db.add(new_run)
        await db.flush()

        executions_to_insert = []
        for model_id in payload.model_ids:
            for tc_id in test_case_ids:
                execution = BenchmarkExecution(
                    run_id=new_run.id,
                    test_case_id=tc_id,
                    llm_model_id=model_id,
                    status=ExecutionStatus.PENDING
                )
                executions_to_insert.append(execution)

        db.add_all(executions_to_insert)
        await db.commit()

        stmt = (
            select(BenchmarkRun)
            .where(BenchmarkRun.id == new_run.id)
            .options(selectinload(BenchmarkRun.executions))
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    async def get_all_runs(self, db: AsyncSession) -> List[BenchmarkRun]:
        """
        Fetch all benchmark runs excluding deleted ones.
        """
        stmt = (
            select(BenchmarkRun)
            .where(BenchmarkRun.is_deleted.is_(False))
            .options(selectinload(BenchmarkRun.executions))
            .order_by(BenchmarkRun.created_at.desc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_run_details(self, db: AsyncSession, run_id: UUID) -> Optional[BenchmarkRun]:
        """
        Fetch benchmark run details with executions, models and test cases.
        Updates status to COMPLETED if all executions are done.
        """
        stmt = (
            select(BenchmarkRun)
            .where(BenchmarkRun.id == run_id)
            .options(
                selectinload(BenchmarkRun.executions).joinedload(BenchmarkExecution.llm_model),
                selectinload(BenchmarkRun.executions).joinedload(BenchmarkExecution.test_case)
            )
        )
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            return None

        run.executions.sort(key=lambda e: (e.created_at, e.id))

        total = len(run.executions)
        completed = sum(1 for e in run.executions if e.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for e in run.executions if e.status == ExecutionStatus.FAILED)
        processing = sum(1 for e in run.executions if e.status == ExecutionStatus.PROCESSING)

        if processing > 0 and run.status != RunStatus.RUNNING:
            run.status = RunStatus.RUNNING
            await db.commit()
        elif total > 0 and (completed + failed) == total and run.status != RunStatus.COMPLETED:
            run.status = RunStatus.COMPLETED
            await db.commit()

        return run

    async def delete_runs(self, db: AsyncSession, run_ids: List[UUID]) -> int:
        """
        Soft delete benchmark runs by setting is_deleted to True.
        Returns the number of runs marked as deleted.
        """
        stmt = (
            update(BenchmarkRun)
            .where(BenchmarkRun.id.in_(run_ids))
            .values(is_deleted=True)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount  # type: ignore

    async def cancel_run(self, db: AsyncSession, run_id: UUID) -> Optional[BenchmarkRun]:
        """
        Cancel a benchmark run and all pending executions.
        Returns the updated run or None if not found/cannot be cancelled.
        """
        stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id)
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            return None

        if run.status in [RunStatus.COMPLETED, RunStatus.CANCELLED]:
            return None

        run.status = RunStatus.CANCELLED
        cancel_exec_stmt = (
            update(BenchmarkExecution)
            .where(
                BenchmarkExecution.run_id == run_id,
                BenchmarkExecution.status == ExecutionStatus.PENDING
            )
            .values(status=ExecutionStatus.CANCELLED)
        )
        await db.execute(cancel_exec_stmt)
        await db.commit()
        return run

    async def get_run_summary(self, db: AsyncSession, run_id: UUID) -> list:
        """
        Get aggregated summary for a benchmark run:
        average correctness, time and token usage grouped by model and test suite.
        """
        stmt = (
            select(
                LLMModel.name.label("model_name"),
                TestSuite.name.label("suite_name"),
                func.avg(BenchmarkExecution.score).label("avg_score"),
                (func.avg(BenchmarkExecution.latency_ms) / 1000.0).label("avg_time"),
                func.avg(
                    func.coalesce(BenchmarkExecution.prompt_tokens, 0) +
                    func.coalesce(BenchmarkExecution.completion_tokens, 0)
                ).label("avg_tokens")
            )
            .join(LLMModel, BenchmarkExecution.llm_model_id == LLMModel.id)
            .join(TestCase, BenchmarkExecution.test_case_id == TestCase.id)
            .join(TestSuite, TestCase.suite_id == TestSuite.id)
            .where(BenchmarkExecution.run_id == run_id)
            .where(BenchmarkExecution.status.in_([ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]))
            .group_by(LLMModel.name, TestSuite.name)
        )
        result = await db.execute(stmt)
        summary = result.all()

        if not summary:
            return []

        return [
            {
                "model": row.model_name,
                "test_suite": row.suite_name,
                "avg_correctness": round((row.avg_score or 0) * 100, 2),
                "avg_time": round(row.avg_time or 0, 2),
                "avg_tokens": round(row.avg_tokens or 0, 0)
            }
            for row in summary
        ]

    async def export_to_excel(self, db: AsyncSession, run_ids: List[UUID]) -> bytes:
        """
        Export multiple benchmark runs to an Excel file.
        Aggregates data across runs by model and test suite.
        """
        if Workbook is None:  # pragma: no cover
            raise RuntimeError("openpyxl is not installed. Please install it to use Excel export.")

        aggregated_data: Dict[Tuple[str, str], List[Tuple[float, float, float]]] = {}

        for run_id in run_ids:
            summary = await self.get_run_summary(db, run_id)
            for item in summary:
                key = (item["model"], item["test_suite"])
                values = (
                    item["avg_correctness"],
                    item["avg_time"],
                    item["avg_tokens"]
                )
                if key not in aggregated_data:
                    aggregated_data[key] = []
                aggregated_data[key].append(values)

        rows = []
        for (model, suite), values_list in aggregated_data.items():
            avg_correctness = sum(v[0] for v in values_list) / len(values_list)
            avg_time = sum(v[1] for v in values_list) / len(values_list)
            avg_tokens = sum(v[2] for v in values_list) / len(values_list)
            rows.append([
                model,
                suite,
                round(avg_correctness, 2),
                round(avg_time, 2),
                round(avg_tokens, 0)
            ])

        rows.sort(key=lambda x: (x[0], x[1]))

        wb = Workbook()
        ws = wb.active
        ws.title = "Benchmark Results"  # type: ignore

        headers = ["Model", "Zbiór testowy", "Średnia poprawność", "Średni czas procesowania", "Średnie zużycie tokenów"]
        ws.append(headers)  # type: ignore

        for row in rows:
            ws.append(row)  # type: ignore

        header_font = Font(bold=True)
        for cell in ws[1]:  # type: ignore
            cell.font = header_font

        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):  # type: ignore
            for cell in row:
                cell.border = thin_border

        for idx, column_cells in enumerate(ws.columns, 1):  # type: ignore
            length = max(len(str(cell.value)) for cell in column_cells)
            adjusted_width = min(length + 2, 50)
            ws.column_dimensions[get_column_letter(idx)].width = adjusted_width  # type: ignore

        excel_bytes = io.BytesIO()
        wb.save(excel_bytes)
        excel_bytes.seek(0)
        return excel_bytes.read()

    async def repeat_execution(self, db: AsyncSession, execution_id: UUID) -> Optional[BenchmarkExecution]:
        """
        Reset an execution to PENDING status and clear all result fields so it can be processed again.
        """
        stmt = (
            select(BenchmarkExecution)
            .where(BenchmarkExecution.id == execution_id)
            .options(
                selectinload(BenchmarkExecution.llm_model),
                selectinload(BenchmarkExecution.test_case),
            )
        )
        result = await db.execute(stmt)
        execution = result.scalar_one_or_none()

        if not execution:
            return None

        self._reset_execution(execution)
        await db.commit()
        await db.refresh(execution)

        return execution

    def _reset_execution(self, execution: BenchmarkExecution) -> None:
        """
        Reset an execution to PENDING status and clear all result fields.
        """
        execution.status = ExecutionStatus.PENDING
        execution.response_text = None
        execution.score = None
        execution.error_message = None
        execution.prompt_tokens = None
        execution.completion_tokens = None
        execution.latency_ms = None

    async def repeat_failed_executions(self, db: AsyncSession, run_id: UUID) -> Optional[BenchmarkRun]:
        """
        Reset all failed executions in a run to PENDING status and clear their result fields.
        Updates the run status after resetting the executions.
        """
        stmt = (
            select(BenchmarkRun)
            .where(BenchmarkRun.id == run_id)
            .options(
                selectinload(BenchmarkRun.executions).joinedload(BenchmarkExecution.llm_model),
                selectinload(BenchmarkRun.executions).joinedload(BenchmarkExecution.test_case)
            )
        )
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            return None

        any_reset = False
        for execution in run.executions:
            if execution.status == ExecutionStatus.FAILED:
                self._reset_execution(execution)
                any_reset = True

        if any_reset:
            run.status = RunStatus.PENDING

        await db.commit()
        await db.refresh(run)

        return run


benchmark_service = BenchmarkService()
