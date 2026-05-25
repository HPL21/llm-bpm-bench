from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
from uuid import UUID
from fastapi.responses import StreamingResponse
from app.core.database import get_db
from app.schemas.benchmark import (
    BenchmarkRunCreate,
    BenchmarkRunResponse,
    BenchmarkRunDetailResponse
)
from app.services.benchmark_service import benchmark_service

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

    try:
        new_run, total_executions = await benchmark_service.create_run(db, payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return BenchmarkRunResponse(
        id=new_run.id,
        name=new_run.name,
        status=new_run.status,
        total_executions=total_executions,
        created_at=new_run.created_at
    )


@router.get("/runs", response_model=List[BenchmarkRunResponse])
async def get_benchmark_runs(db: AsyncSession = Depends(get_db)):
    """
    Zwraca listę wszystkich uruchomień benchmarków (pomija usunięte).
    """
    runs_with_counts = await benchmark_service.get_all_runs(db)

    return [
        BenchmarkRunResponse(
            id=row.BenchmarkRun.id,
            name=row.BenchmarkRun.name,
            status=row.BenchmarkRun.status,
            total_executions=row.total_executions,
            created_at=row.BenchmarkRun.created_at
        )
        for row in runs_with_counts
    ]


@router.post("/executions/{execution_id}/repeat", status_code=status.HTTP_200_OK)
async def repeat_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Powtarza pojedyncze wykonanie benchmarku: ustawia status na PENDING
    i czyści pola wynikowe (response_text, score, error_message,
    prompt_tokens, completion_tokens, latency_ms).
    """
    execution = await benchmark_service.repeat_execution(db, execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail="Nie znaleziono wykonania o podanym ID.")

    return {
        "id": execution.id,
        "status": execution.status,
        "response_text": execution.response_text,
        "score": execution.score,
        "error_message": execution.error_message,
        "prompt_tokens": execution.prompt_tokens,
        "completion_tokens": execution.completion_tokens,
        "latency_ms": execution.latency_ms,
    }


@router.post("/runs/delete", status_code=status.HTTP_200_OK)
async def delete_benchmark_runs(
    run_ids: List[UUID],
    db: AsyncSession = Depends(get_db)
):
    """
    Soft delete - ustawia is_deleted na True dla podanych uruchomień benchmarków.
    """
    count = await benchmark_service.delete_runs(db, run_ids)
    return {"message": f"Usunięto {count} uruchomień benchmarków."}


@router.get("/runs/{run_id}", response_model=BenchmarkRunDetailResponse)
async def get_benchmark_run_details(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Zwraca szczegóły uruchomienia, wylicza postęp (statystyki z zadań podrzędnych)
    oraz zwraca listę wszystkich egzekucji.
    """
    result = await benchmark_service.get_run_details(db, run_id)

    if not result:
        raise HTTPException(status_code=404, detail="Nie znaleziono takiego benchmarku.")

    run, stats = result

    return BenchmarkRunDetailResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        created_at=run.created_at,
        total_executions=stats["total"],
        completed_executions=stats["completed"],
        failed_executions=stats["failed"],
        pending_executions=stats["pending"],
        executions=run.executions  # type: ignore
    )


@router.post("/runs/{run_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_benchmark_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Anuluje uruchomienie. Wszystkie zadania, które mają status PENDING
    zostaną zmienione na CANCELLED. Workery po prostu ich nie podejmą.
    """
    success = await benchmark_service.cancel_run(db, run_id)

    if not success:
        raise HTTPException(status_code=404, detail="Nie znaleziono takiego benchmarku lub nie można go anulować.")

    return {"message": "Benchmark został pomyślnie anulowany."}


@router.post("/runs/{run_id}/repeat-failed", response_model=BenchmarkRunDetailResponse)
async def repeat_failed_executions(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Powtarza wszystkie nieudane wykonania w danym uruchomieniu benchmarku:
    ustawia status na PENDING i czyści pola wynikowe dla każdego nieudanego wykonania.
    """
    result = await benchmark_service.repeat_failed_executions(db, run_id)

    if not result:
        raise HTTPException(status_code=404, detail="Nie znaleziono takiego benchmarku.")

    run, stats = result

    return BenchmarkRunDetailResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        created_at=run.created_at,
        total_executions=stats["total"],
        completed_executions=stats["completed"],
        failed_executions=stats["failed"],
        pending_executions=stats["pending"],
        executions=run.executions  # type: ignore
    )


@router.get("/runs/{run_id}/summary")
async def get_benchmark_summary(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Zwraca zagregowane podsumowanie dla danego uruchomienia benchmarku:
    średnią poprawność, czas i zużycie tokenów pogrupowane po modelu i zbiorze testowym.
    """
    summary = await benchmark_service.get_runs_summary(db, [run_id])
    return summary


@router.post("/runs/export-excel")
async def export_benchmark_runs_to_excel(
    run_ids: List[UUID],
    db: AsyncSession = Depends(get_db)
):
    """
    Eksportuje wybrane uruchomienia benchmarków do pliku Excel.
    """
    import io
    excel_data = await benchmark_service.export_to_excel(db, run_ids)

    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=benchmark_results.xlsx"}
    )


@router.post("/runs/export-executions-csv")
async def export_benchmark_executions_to_csv(
    run_ids: List[UUID],
    db: AsyncSession = Depends(get_db)
):
    """
    Eksportuje pojedyncze wykonania benchmarków z wybranych uruchomień do pliku CSV.
    """
    import io
    csv_data = await benchmark_service.export_executions_to_csv(db, run_ids)

    return StreamingResponse(
        io.BytesIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=benchmark_executions.csv"}
    )
