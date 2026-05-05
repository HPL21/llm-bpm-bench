from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class TestSuiteBase(BaseModel):
    """Shared properties for Test Suites."""
    name: str = Field(
        ..., min_length=1, max_length=200, description="Name of the test suite"
    )
    description: str | None = Field(
        None, description="Optional description of what this suite tests"
    )
    system_prompt: str = Field(
        ...,
        min_length=1,
        description=" The system prompt used for all tests in this suite",
    )
    verification_method: str = Field(
        ...,
        description="Method like EXACT_MATCH, JSON_COMPARE, OCR_MATCH"
    )
    parameters: dict[str, Any] | None = Field(None, description="Optional parameter overrides for this suite")
    qdrant_collection: str | None = Field(None, description="Qdrant collection name for RAG mode")
    embedding_model_id: UUID | None = Field(None, description="ID of the embedding model for RAG mode")


class TestSuiteCreate(TestSuiteBase):
    """Properties to receive on item creation."""
    pass


class TestSuiteUpdate(BaseModel):
    """Properties to receive on item update."""
    name: str | None = None
    description: str | None = None
    system_prompt: str | None = None
    verification_method: str | None = None
    parameters: dict[str, Any] | None = None
    qdrant_collection: str | None = None
    embedding_model_id: UUID | None = None


class TestSuiteRead(TestSuiteBase):
    """Properties to return to client."""
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None
    embedding_model_id: UUID | None = None
    model_config = ConfigDict(from_attributes=True)
