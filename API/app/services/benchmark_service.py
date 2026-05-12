from __future__ import annotations

from uuid import UUID
from typing import List, Optional

from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.benchmark_run import BenchmarkRun, RunStatus
from app.models.benchmark_execution import BenchmarkExecution, ExecutionStatus
from app.models.llm_model import LLMModel
from app.models.test_case import TestCase
from app.models.test_suite import TestSuite
from app.schemas.benchmark import BenchmarkRunCreate


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

        if total > 0 and (completed + failed) == total and run.status != RunStatus.COMPLETED:
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


benchmark_service = BenchmarkService()
