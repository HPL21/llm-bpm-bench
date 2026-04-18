import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.llm_model import LLMModelRead, LLMModelCreate, LLMModelUpdate
from app.services.llm_service import LLMModelService

router = APIRouter()


@router.get("/", response_model=List[LLMModelRead])
async def list_models(db: AsyncSession = Depends(get_db)):
    return await LLMModelService.get_models(db)


@router.post("/", response_model=LLMModelRead, status_code=status.HTTP_201_CREATED)
async def create_model(model_in: LLMModelCreate, db: AsyncSession = Depends(get_db)):
    return await LLMModelService.create_model(db, model_in)


@router.get("/{model_id}", response_model=LLMModelRead)
async def get_model(model_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    model = await LLMModelService.get_model(db, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.patch("/{model_id}", response_model=LLMModelRead)
async def update_model(
    model_id: uuid.UUID, model_in: LLMModelUpdate, db: AsyncSession = Depends(get_db)
):
    db_model = await LLMModelService.get_model(db, model_id)
    if not db_model:
        raise HTTPException(status_code=404, detail="Model not found")
    return await LLMModelService.update_model(db, db_model, model_in)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model(model_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    success = await LLMModelService.delete_model(db, model_id)
    if not success:
        raise HTTPException(status_code=404, detail="Model not found")
