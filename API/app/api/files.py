from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.file import FileAssetRead, CollectionCreate
from app.services.file_service import file_service

router = APIRouter()


@router.post("/upload", summary="Upload multiple files", response_model=List[FileAssetRead])
async def upload_files(
    collection_name: str = Form("default"),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
) -> List[FileAssetRead]:
    try:
        return await file_service.create_file_assets(db, files, collection_name)  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", summary="List all files", response_model=List[FileAssetRead])
async def list_files(db: AsyncSession = Depends(get_db)) -> List[FileAssetRead]:
    try:
        return await file_service.get_all_files(db)  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{asset_id}", summary="Delete file")
async def delete_file(asset_id: UUID, db: AsyncSession = Depends(get_db)):
    asset = await file_service.get_file_by_id(db, asset_id)

    if not asset:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        await file_service.delete_file_asset(db, asset)
        return {"status": "success", "message": "File deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collections", summary="Create an empty collection", response_model=FileAssetRead)
async def create_collection(
    collection: CollectionCreate,
    db: AsyncSession = Depends(get_db)
) -> FileAssetRead:
    try:
        return await file_service.create_collection_asset(db, collection.name)  # type: ignore
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
