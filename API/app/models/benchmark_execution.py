import uuid
import enum
from typing import TYPE_CHECKING
from sqlalchemy import Enum, Uuid, ForeignKey, Text, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.benchmark_run import BenchmarkRun
    from app.models.llm_model import LLMModel
    from app.models.test_case import TestCase


class ExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class BenchmarkExecution(Base):
    """
    Reprezentuje pojedyncze wykonanie: Konkretny przypadek testowy na konkretnym modelu LLM.
    """
    __tablename__ = "benchmark_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("benchmark_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    llm_model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus, name="execution_status"), default=ExecutionStatus.PENDING, nullable=False, index=True
    )
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run: Mapped["BenchmarkRun"] = relationship(back_populates="executions")
    llm_model: Mapped["LLMModel"] = relationship("LLMModel")
    test_case: Mapped["TestCase"] = relationship("TestCase")

    @property
    def llm_model_name(self) -> str:
        return self.llm_model.name if self.llm_model else "Nieznany model"

    @property
    def expected_output(self) -> str | None:
        return self.test_case.expected_output if self.test_case else None

    def __repr__(self) -> str:
        return f"<BenchmarkExecution(id={self.id}, status='{self.status}')>"
