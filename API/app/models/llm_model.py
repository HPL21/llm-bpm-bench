import uuid
from typing import Any
from sqlalchemy import String, JSON, Uuid, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class LLMModel(Base):
    """
    Reprezentuje zarejestrowany endpoint LLM.
    """
    __tablename__ = "llm_models"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    api_base_url: Mapped[str] = mapped_column(String, nullable=False)
    model_identifier: Mapped[str] = mapped_column(String, nullable=False)
    api_key: Mapped[str | None] = mapped_column(String, nullable=True)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<LLMModel(id={self.id}, name='{self.name}')>"
