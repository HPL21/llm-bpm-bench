import uuid
from typing import List

from sqlalchemy import Column, ForeignKey, Table, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.file_asset import FileAsset

case_files_link = Table(
    "case_files_link",
    Base.metadata,
    Column(
        "test_case_id",
        Uuid(as_uuid=True),
        ForeignKey("test_cases.id"),
        primary_key=True,
    ),
    Column(
        "file_asset_id",
        Uuid(as_uuid=True),
        ForeignKey("file_assets.id"),
        primary_key=True,
    ),
)


class TestCase(Base):
    """
    Represents a specific test scenario within a Test Suite.
    Can be linked to multiple file assets.
    """

    __tablename__ = "test_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    suite_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("test_suites.id"),
        nullable=False,
    )
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    files: Mapped[List[FileAsset]] = relationship(
        "FileAsset",
        secondary=case_files_link,
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TestCase(id={self.id}, suite_id={self.suite_id})>"
