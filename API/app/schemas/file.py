from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FileAssetRead(BaseModel):
    id: UUID
    filename: str
    collection_name: str
    minio_path: str
    content_type: str
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CollectionCreate(BaseModel):
    name: str
