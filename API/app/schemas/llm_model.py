from datetime import datetime
from uuid import UUID
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class LLMModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: str
    api_base_url: str
    model_identifier: str
    api_key: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict, description="Custom LLM parameters")
    is_active: bool = True


class LLMModelCreate(LLMModelBase):
    pass


class LLMModelUpdate(BaseModel):
    name: str | None = None
    provider: str | None = None
    api_base_url: str | None = None
    model_identifier: str | None = None
    api_key: str | None = None
    parameters: dict[str, Any] | None = None
    is_active: bool | None = None


class LLMModelRead(LLMModelBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
