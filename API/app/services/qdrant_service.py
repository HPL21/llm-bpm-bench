from uuid import uuid4
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.models.file_asset import FileAsset
from app.services.embedding_service import embedding_service
from app.services.storage_service import storage_service
import pymupdf4llm
import os
import tempfile


class QdrantService:
    """Service for managing Qdrant collections and vector operations."""

    _client: QdrantClient | None = None
    VECTOR_SIZE: int = 1024

    @classmethod
    def get_client(cls) -> QdrantClient:
        """Get or create Qdrant client."""
        if cls._client is None:
            cls._client = QdrantClient(url=settings.QDRANT_URL)
        return cls._client

    @classmethod
    def create_collection(cls, collection_name: str) -> bool:
        """Create a new collection in Qdrant."""
        client = cls.get_client()
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=cls.VECTOR_SIZE,
                    distance=models.Distance.COSINE
                )
            )
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                return True
            raise

    @classmethod
    def collection_exists(cls, collection_name: str) -> bool:
        """Check if a collection exists in Qdrant."""
        client = cls.get_client()
        try:
            collections = client.get_collections()
            return any(c.name == collection_name for c in collections.collections)
        except Exception:
            return False

    @classmethod
    def delete_collection(cls, collection_name: str) -> bool:
        """Delete a collection from Qdrant."""
        client = cls.get_client()
        try:
            client.delete_collection(collection_name=collection_name)
            return True
        except UnexpectedResponse as e:
            if "not found" in str(e).lower():
                return True
            raise

    @classmethod
    def list_collections(cls) -> list[str]:
        """List all collections in Qdrant."""
        client = cls.get_client()
        collections = client.get_collections()
        return [c.name for c in collections.collections]

    @classmethod
    def _extract_text_from_file(cls, file_asset: FileAsset) -> list[dict]:
        """
        Extract text from file.
        For PDFs: returns list of tuples (page_number, text).
        For text files: returns list with single item (1, text).
        """
        ext = file_asset.filename.lower().split('.')[-1]

        try:
            response = storage_service.client.get_object(
                storage_service.bucket_name,
                file_asset.minio_path
            )
            file_bytes = response.read()

            if ext == 'pdf':
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name

                try:
                    pdf_chunks = pymupdf4llm.to_markdown(tmp_path, page_chunks=True)
                    pages = []
                    for chunk in pdf_chunks:
                        text = chunk.get("text", "").strip()  # type: ignore
                        if text:
                            pages.append(chunk)
                    return pages
                finally:
                    os.remove(tmp_path)
            else:
                raise ValueError("ext not supported")
        except Exception as e:
            raise ValueError(f"Failed to extract text from {file_asset.filename}: {e}")

    @classmethod
    async def index_file(
        cls,
        file_asset: FileAsset,
        collection_name: str,
        model_id: str | None = None
    ) -> int:
        """
        Index a file into Qdrant using simple text extraction.
        """
        pages = cls._extract_text_from_file(file_asset)

        if not pages:
            return 0

        client = cls.get_client()
        indexed_count = 0

        for page in pages:
            page_text = page.get('text')
            embedding = await embedding_service.encode([page_text], model_id=model_id)  # type: ignore

            page['filename'] = file_asset.filename
            page['page_number'] = page.get('metadata', {}).get('page')

            point = models.PointStruct(
                id=str(uuid4()),
                vector=embedding[0],
                payload=page
            )

            client.upsert(
                collection_name=collection_name,
                points=[point]
            )
            indexed_count += 1

        return indexed_count

    @classmethod
    async def search_relevant_chunks(
        cls,
        collection_name: str,
        query: str,
        model_id: str | None = None,
        limit: int = 5
    ) -> list[tuple[str, int | None, str | None]]:
        """
        Search for relevant text chunks in Qdrant.
        """
        client = cls.get_client()

        embeddings = await embedding_service.encode([query], model_id=model_id)
        query_embedding = embeddings[0]

        response = client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=limit,
            with_payload=True
        )

        return [
            (
                (hit.payload or {}).get("text", ""),
                (hit.payload or {}).get("page_number"),
                (hit.payload or {}).get("filename")
            )
            for hit in response.points
        ]


qdrant_service = QdrantService()
