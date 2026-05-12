from uuid import UUID
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_asset import FileAsset
from app.services.storage_service import storage_service


class FileService:
    """
    Service responsible for file asset operations.
    """

    async def create_file_assets(
        self, db: AsyncSession, files: list, collection_name: str = "default"
    ) -> List[FileAsset]:
        """
        Create multiple FileAsset records from uploaded files.
        Uploads files to MinIO and creates corresponding DB records.
        """
        uploaded_assets = []
        for file in files:
            minio_filename = storage_service.upload_file(file, collection_name)
            new_asset = FileAsset(
                filename=str(file.filename),
                collection_name=collection_name,
                minio_path=minio_filename,
                content_type=file.content_type or "application/octet-stream",
            )
            db.add(new_asset)
            uploaded_assets.append(new_asset)

        await db.commit()
        for asset in uploaded_assets:
            await db.refresh(asset)

        return uploaded_assets

    async def get_all_files(self, db: AsyncSession) -> List[FileAsset]:
        """
        Fetch all file assets.
        """
        result = await db.execute(select(FileAsset))
        return list(result.scalars().all())

    async def get_file_by_id(self, db: AsyncSession, asset_id: UUID) -> FileAsset | None:
        """
        Fetch a single file asset by ID.
        """
        result = await db.execute(select(FileAsset).where(FileAsset.id == asset_id))
        return result.scalar_one_or_none()

    async def delete_file_asset(self, db: AsyncSession, asset: FileAsset) -> None:
        """
        Delete a file asset from both MinIO and database.
        """
        storage_service.delete_file(asset.minio_path)
        await db.delete(asset)
        await db.commit()

    async def get_files_by_collection(
        self, db: AsyncSession, collection_name: str, exclude_keep: bool = False
    ) -> List[FileAsset]:
        """
        Fetch all files belonging to a specific collection.
        If exclude_keep is True, excludes .keep files.
        """
        stmt = select(FileAsset).where(FileAsset.collection_name == collection_name)
        if exclude_keep:
            stmt = stmt.where(FileAsset.filename != '.keep')
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_files_by_filenames(
        self, db: AsyncSession, collection_name: str, filenames: set
    ) -> List[FileAsset]:
        """
        Fetch files from a collection matching the given filenames.
        Returns found files and a set of missing filenames.
        """
        result = await db.execute(
            select(FileAsset)
            .where(FileAsset.collection_name == collection_name)
            .where(FileAsset.filename.in_(filenames))
        )
        found_files = result.scalars().all()
        return list(found_files)

    async def create_collection_asset(self, db: AsyncSession, collection_name: str) -> FileAsset:
        """
        Create an empty collection (.keep file) in MinIO and database.
        """
        minio_filename = storage_service.create_empty_collection(collection_name)
        new_asset = FileAsset(
            filename=".keep",
            collection_name=collection_name,
            minio_path=minio_filename,
            content_type="application/x-empty",
        )
        db.add(new_asset)
        await db.commit()
        await db.refresh(new_asset)
        return new_asset


file_service = FileService()
