from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.file_asset import FileAsset
from app.schemas.file import FileAssetRead
from app.services.storage_service import storage_service

router = APIRouter()


@router.post(
    "/upload", summary="Upload a file to storage and DB", response_model=FileAssetRead
)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> FileAssetRead:
    """
    Uploads a file to MinIO and registers it in the PostgreSQL database.
    """
    try:
        minio_filename = storage_service.upload_file(file)
        new_asset = FileAsset(
            filename=str(file.filename),
            minio_path=minio_filename,
            content_type=file.content_type or "application/octet-stream",
        )
        db.add(new_asset)
        await db.commit()
        await db.refresh(new_asset)
        return new_asset  # type: ignore

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", summary="List all files from DB", response_model=List[FileAssetRead])
async def list_files(db: AsyncSession = Depends(get_db)) -> List[FileAssetRead]:
    """
    Lists all file assets registered in the database.
    """
    try:
        result = await db.execute(select(FileAsset))
        files = result.scalars().all()
        return list(files)  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
