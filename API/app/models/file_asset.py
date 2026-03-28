import uuid
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class FileAsset(Base):
    __tablename__ = "file_assets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    collection_name: Mapped[str] = mapped_column(String, nullable=False, default="default")
    minio_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
