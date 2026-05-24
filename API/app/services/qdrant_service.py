import logging
from uuid import uuid4
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.file_asset import FileAsset
from app.models.llm_model import LLMModel
from app.services.embedding_service import embedding_service
from app.services.storage_service import storage_service
import pymupdf4llm
import os
import tempfile

logger = logging.getLogger("BenchmarkWorker")


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
        model_id: str | None = None,
        batch_size: int = 4
    ) -> int:
        """
        Index a file into Qdrant using simple text extraction with batching.
        """
        pages = cls._extract_text_from_file(file_asset)

        if not pages:
            return 0

        async with AsyncSessionLocal() as db:
            stmt = select(LLMModel).where(LLMModel.id == model_id)
            result = await db.execute(stmt)
            model_config = result.scalar_one_or_none()

        client = cls.get_client()
        indexed_count = 0

        for i in range(0, len(pages), batch_size):
            batch_pages = pages[i:i + batch_size]
            batch_texts = [page.get('text', '') for page in batch_pages]
            embeddings = await embedding_service.encode(batch_texts, model_config=model_config)
            points = []
            for j, page in enumerate(batch_pages):
                metadata = page.get('metadata', {})
                cleaned_payload = {
                    "title": metadata.get("title", ""),
                    "page_count": metadata.get("page_count"),
                    "page_number": metadata.get("page_number"),
                    "text": batch_texts[j]
                }
                points.append(
                    models.PointStruct(
                        id=str(uuid4()),
                        vector=embeddings[j],
                        payload=cleaned_payload
                    )
                )
            client.upsert(
                collection_name=collection_name,
                points=points
            )
            indexed_count += len(points)

        return indexed_count

    @classmethod
    async def search_relevant_chunks(
        cls,
        collection_name: str,
        query: str,
        model_id: str | None = None,
        limit: int = 10
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
                (hit.payload or {}).get("title")
            )
            for hit in response.points
        ]

    @classmethod
    async def search_relevant_chunks_multiquery(
        cls,
        collection_name: str,
        queries: list[str],
        model_id: str | None = None,
        limit: int = 10
    ) -> list[tuple[str, int | None, str | None]]:
        """
        Search for relevant text chunks in Qdrant using multiple queries (Multi-Query RAG).
        Deduplicates results based on point ID and returns the highest scoring chunks.
        """
        client = cls.get_client()

        embeddings = await embedding_service.encode(queries, model_id=model_id)

        all_hits = []
        for query_embedding in embeddings:
            response = client.query_points(
                collection_name=collection_name,
                query=query_embedding,
                limit=limit,
                with_payload=True
            )
            all_hits.extend(response.points)

        unique_hits = {}
        for hit in all_hits:
            if hit.id not in unique_hits or hit.score > unique_hits[hit.id].score:
                unique_hits[hit.id] = hit

        top_hits = sorted(unique_hits.values(), key=lambda x: x.score, reverse=True)[:limit]

        return [
            (
                (hit.payload or {}).get("text", ""),
                (hit.payload or {}).get("page_number"),
                (hit.payload or {}).get("title")
            )
            for hit in top_hits
        ]


qdrant_service = QdrantService()
