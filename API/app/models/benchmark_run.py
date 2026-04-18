import uuid
import enum
from typing import TYPE_CHECKING
from sqlalchemy import String, Enum, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.benchmark_execution import BenchmarkExecution


class RunStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class BenchmarkRun(Base):
    """
    Reprezentuje nadrzędne uruchomienie benchmarku dla wybranych modeli i zbiorów testowych.
    """
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), default=RunStatus.PENDING, nullable=False
    )
    executions: Mapped[list["BenchmarkExecution"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BenchmarkRun(id={self.id}, name='{self.name}', status='{self.status}')>"
