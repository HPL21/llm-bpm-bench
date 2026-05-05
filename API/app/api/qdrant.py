from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.file_asset import FileAsset
from app.services.qdrant_service import qdrant_service

router = APIRouter()


class CollectionCreate(BaseModel):
    collection_name: str


class IndexCollectionRequest(BaseModel):
    collection_name: str
    model_id: str | None = None
    minio_catalog: str | None = None


@router.get("/collections")
async def list_collections():
    """List all Qdrant collections."""
    try:
        collections = qdrant_service.list_collections()
        return {"collections": collections}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list collections: {str(e)}"
        )


@router.post("/collections")
async def create_collection(request: CollectionCreate):
    """Create a new Qdrant collection."""
    try:
        qdrant_service.create_collection(request.collection_name)
        return {"message": f"Collection '{request.collection_name}' created successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create collection: {str(e)}"
        )


@router.delete("/collections/{collection_name}")
async def delete_collection(collection_name: str):
    """Delete a Qdrant collection."""
    try:
        qdrant_service.delete_collection(collection_name)
        return {"message": f"Collection '{collection_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete collection: {str(e)}"
        )


@router.post("/index-collection")
async def index_collection(request: IndexCollectionRequest):
    """Index all files from a MinIO collection into Qdrant."""
    async with AsyncSessionLocal() as db:
        try:
            if not qdrant_service.collection_exists(request.collection_name):
                qdrant_service.create_collection(request.collection_name)

            if request.minio_catalog:
                stmt = select(FileAsset).where(
                    FileAsset.collection_name == request.minio_catalog,
                    FileAsset.filename != '.keep'
                )
            else:
                stmt = select(FileAsset)
            result = await db.execute(stmt)
            files = result.scalars().all()

            if not files:
                return {
                    "message": f"No files found in MinIO catalog '{request.minio_catalog}'",
                    "files": []
                }

            total_chunks = 0
            indexed_files = []

            for file_asset in files:
                chunks_count = await qdrant_service.index_file(
                    file_asset, request.collection_name, model_id=request.model_id
                )
                total_chunks += chunks_count
                indexed_files.append({
                    "file_id": str(file_asset.id),
                    "filename": file_asset.filename,
                    "chunks_indexed": chunks_count
                })

            return {
                "message": f"Indexed {len(indexed_files)} files with {total_chunks} total chunks",
                "files": indexed_files
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to index collection: {str(e)}"
            )
