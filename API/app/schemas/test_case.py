from datetime import datetime
from uuid import UUID
from typing import List

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.file import FileAssetRead


class TestCaseBase(BaseModel):
    """Shared properties."""

    input_text: str = Field(
        ..., description="Specific instructions or input for this test case"
    )
    expected_output: str | None = Field(
        None, description="The expected answer (ground truth)"
    )


class TestCaseCreate(TestCaseBase):
    """
    Properties to receive on creation.
    We receive the ID of the suite and a list of File IDs to attach.
    """

    suite_id: UUID
    file_ids: List[UUID] = Field(
        default_factory=list, description="List of FileAsset IDs to attach"
    )


class TestCaseUpdate(BaseModel):
    """Properties for updating."""

    input_text: str | None = None
    expected_output: str | None = None
    file_ids: List[UUID] | None = Field(
        None, description="If provided, replaces the current list of files"
    )


class TestCaseRead(TestCaseBase):
    """Properties to return to client."""

    id: UUID
    suite_id: UUID
    files: List[FileAssetRead]
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
