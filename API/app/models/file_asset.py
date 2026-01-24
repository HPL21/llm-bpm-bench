import uuid
from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class FileAsset(Base):
    """
    Represents a file asset stored in the object storage (MinIO).
    """

    __tablename__ = "file_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    minio_path: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self):
        return f"<FileAsset(id={self.id}, filename='{self.filename}')>"
