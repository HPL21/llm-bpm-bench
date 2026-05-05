from app.core.llm_clients import LLMClientFactory
from app.models.llm_model import LLMModel
from app.core.database import AsyncSessionLocal
from sqlalchemy import select


class EmbeddingService:
    """Service for generating text embeddings using LLM client system."""

    @classmethod
    async def encode(
        cls, texts: list[str], model_id: str | None = None, model_config: LLMModel | None = None
    ) -> list[list[float]]:
        """
        Generate embeddings using the specified model.

        Args:
            texts: List of texts to embed
            model_id: ID of the model in database (optional if model_config provided)
            model_config: LLMModel object (optional if model_id provided)

        Returns:
            List of embedding vectors
        """
        if model_config is None:
            if model_id is None:
                raise ValueError("Either model_id or model_config must be provided")
            async with AsyncSessionLocal() as db:
                stmt = select(LLMModel).where(LLMModel.id == model_id)
                result = await db.execute(stmt)
                model_config = result.scalar_one_or_none()
                if not model_config:
                    raise ValueError(f"Model with ID {model_id} not found")

        client = LLMClientFactory.get_client(model_config)
        return await client.embed(texts)


embedding_service = EmbeddingService()
