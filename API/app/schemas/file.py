from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FileAssetRead(BaseModel):
    """
    Schema for reading file asset data (Output DTO).
    """

    id: UUID
    filename: str
    minio_path: str
    content_type: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
