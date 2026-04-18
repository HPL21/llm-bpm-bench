from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.models.benchmark_execution import ExecutionStatus


class BenchmarkRunCreate(BaseModel):
    name: Optional[str] = Field(None, description="Opcjonalna nazwa uruchomienia, np. 'Test Nocny'")
    model_ids: List[UUID] = Field(..., description="Lista ID modeli LLM do przetestowania")
    suite_ids: List[UUID] = Field(..., description="Lista ID zbiorów testowych (Test Suites)")


class BenchmarkRunResponse(BaseModel):
    id: UUID
    name: Optional[str]
    status: str
    total_executions: int
    created_at: datetime

    class Config:
        from_attributes = True


class BenchmarkExecutionResponse(BaseModel):
    """Pojedynczy rekord z wynikiem ewaluacji"""
    id: UUID
    test_case_id: UUID
    llm_model_id: UUID
    status: ExecutionStatus
    response_text: Optional[str] = None
    score: Optional[float] = None
    error_message: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class BenchmarkRunDetailResponse(BenchmarkRunResponse):
    """Szczegóły uruchomienia z podsumowaniem i listą wszystkich zadań"""
    total_executions: int = 0
    completed_executions: int = 0
    failed_executions: int = 0
    pending_executions: int = 0

    executions: List[BenchmarkExecutionResponse] = []
