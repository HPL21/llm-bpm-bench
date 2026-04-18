from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List, Any
from uuid import UUID
from app.core.database import get_db
from app.models.benchmark_run import BenchmarkRun, RunStatus
from app.models.benchmark_execution import BenchmarkExecution, ExecutionStatus
from app.models.test_case import TestCase
from app.schemas.benchmark import (
    BenchmarkRunCreate,
    BenchmarkRunResponse,
    BenchmarkRunDetailResponse
)

router = APIRouter()


@router.post("/runs", response_model=BenchmarkRunResponse)
async def create_benchmark_run(
    payload: BenchmarkRunCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Tworzy nowe uruchomienie benchmarku.
    Generuje rekordy wykonania (BenchmarkExecution) dla każdego przypadku testowego
    z wybranych zbiorów przeciwko każdemu z wybranych modeli.
    """
    if not payload.model_ids:
        raise HTTPException(status_code=400, detail="Nie wybrano żadnego modelu LLM.")
    if not payload.suite_ids:
        raise HTTPException(status_code=400, detail="Nie wybrano żadnego zbioru testowego.")

    stmt = select(TestCase.id).where(TestCase.suite_id.in_(payload.suite_ids))
    result = await db.execute(stmt)
    test_case_ids = result.scalars().all()

    if not test_case_ids:
        raise HTTPException(
            status_code=400,
            detail="Wybrane zbiory testowe są puste (brak przypadków testowych)."
        )

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

    return BenchmarkRunResponse(
        id=new_run.id,
        name=new_run.name,
        status=new_run.status,
        total_executions=len(executions_to_insert),
        created_at=new_run.created_at
    )


@router.get("/runs", response_model=List[BenchmarkRunResponse])
async def get_benchmark_runs(db: AsyncSession = Depends(get_db)):
    """
    Zwraca listę wszystkich uruchomień benchmarków.
    """
    stmt = select(BenchmarkRun).order_by(BenchmarkRun.created_at.desc())
    result = await db.execute(stmt)
    runs = result.scalars().all()
    return runs


@router.get("/runs/{run_id}", response_model=BenchmarkRunDetailResponse)
async def get_benchmark_run_details(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Zwraca szczegóły uruchomienia, wylicza postęp (statystyki z zadań podrzędnych)
    oraz zwraca listę wszystkich egzekucji.
    """
    stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id).options(
        selectinload(BenchmarkRun.executions)
    )
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Nie znaleziono takiego benchmarku.")

    total = len(run.executions)
    completed = sum(1 for e in run.executions if e.status == ExecutionStatus.COMPLETED)
    failed = sum(1 for e in run.executions if e.status == ExecutionStatus.FAILED)
    pending = sum(1 for e in run.executions if e.status in [ExecutionStatus.PENDING, ExecutionStatus.PROCESSING])

    if total > 0 and (completed + failed) == total and run.status != RunStatus.COMPLETED:
        run.status = RunStatus.COMPLETED
        await db.commit()

    return BenchmarkRunDetailResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        created_at=run.created_at,
        total_executions=total,
        completed_executions=completed,
        failed_executions=failed,
        pending_executions=pending,
        executions=run.executions  # type: ignore
    )


@router.post("/runs/{run_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_benchmark_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Anuluje uruchomienie. Wszystkie zadania, które mają status PENDING
    zostaną zmienione na CANCELLED. Workery po prostu ich nie podejmą.
    """

    stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Nie znaleziono takiego benchmarku.")

    if run.status in [RunStatus.COMPLETED, RunStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Tego benchmarku nie można już anulować.")
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

    return {"message": "Benchmark został pomyślnie anulowany."}
