import uuid
from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class TestSuite(Base):
    """
    Represents a collection of test cases with a shared configuration (System Prompt).
    """

    __tablename__ = "test_suites"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    verification_method: Mapped[str] = mapped_column(String, nullable=False, default="EXACT_MATCH")

    def __repr__(self) -> str:
        return f"<TestSuite(id={self.id}, name='{self.name}')>"
