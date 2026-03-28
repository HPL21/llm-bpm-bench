from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.file_asset import FileAsset
from app.schemas.file import FileAssetRead, CollectionCreate
from app.services.storage_service import storage_service

router = APIRouter()


@router.post("/upload", summary="Upload multiple files", response_model=List[FileAssetRead])
async def upload_files(
    collection_name: str = Form("default"),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> List[FileAssetRead]:
    uploaded_assets = []
    try:
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
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", summary="List all files", response_model=List[FileAssetRead])
async def list_files(db: AsyncSession = Depends(get_db)) -> List[FileAssetRead]:
    try:
        result = await db.execute(select(FileAsset))
        return list(result.scalars().all())  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{asset_id}", summary="Delete file")
async def delete_file(asset_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FileAsset).where(FileAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        storage_service.delete_file(asset.minio_path)
        await db.delete(asset)
        await db.commit()
        return {"status": "success", "message": "File deleted"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections", summary="Create an empty collection", response_model=FileAssetRead)
async def create_collection(
    collection: CollectionCreate,
    db: AsyncSession = Depends(get_db)
) -> FileAssetRead:
    try:
        minio_filename = storage_service.create_empty_collection(collection.name)
        new_asset = FileAsset(
            filename=".keep",
            collection_name=collection.name,
            minio_path=minio_filename,
            content_type="application/x-empty",
        )
        db.add(new_asset)
        await db.commit()
        await db.refresh(new_asset)
        return new_asset  # type: ignore
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
