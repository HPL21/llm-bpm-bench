import uuid
from typing import Sequence
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.llm_model import LLMModel
from app.schemas.llm_model import LLMModelCreate, LLMModelUpdate


class LLMModelService:
    @staticmethod
    async def get_models(db: AsyncSession) -> Sequence[LLMModel]:
        result = await db.execute(select(LLMModel).order_by(LLMModel.name))
        return result.scalars().all()

    @staticmethod
    async def get_model(db: AsyncSession, model_id: uuid.UUID) -> LLMModel | None:
        result = await db.execute(select(LLMModel).where(LLMModel.id == model_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_model(db: AsyncSession, model_in: LLMModelCreate) -> LLMModel:
        db_model = LLMModel(**model_in.model_dump())
        db.add(db_model)
        await db.commit()
        await db.refresh(db_model)
        return db_model

    @staticmethod
    async def update_model(
        db: AsyncSession, db_model: LLMModel, model_in: LLMModelUpdate
    ) -> LLMModel:
        update_data = model_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_model, field, value)

        await db.commit()
        await db.refresh(db_model)
        return db_model

    @staticmethod
    async def delete_model(db: AsyncSession, model_id: uuid.UUID) -> bool:
        result = await db.execute(delete(LLMModel).where(LLMModel.id == model_id))
        await db.commit()
        return result.rowcount > 0  # type: ignore
