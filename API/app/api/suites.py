from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.test_suite import TestSuiteCreate, TestSuiteRead, TestSuiteUpdate
from app.services.suite_service import suite_service

router = APIRouter()


@router.post(
    "/",
    response_model=TestSuiteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Test Suite",
)
async def create_suite(
    suite_in: TestSuiteCreate,
    db: AsyncSession = Depends(get_db),
) -> TestSuiteRead:
    """
    Creates a new Test Suite with a specific System Prompt.
    """
    return await suite_service.create(db, suite_in)  # type: ignore


@router.get("/", response_model=List[TestSuiteRead], summary="List all Test Suites")
async def list_suites(db: AsyncSession = Depends(get_db)) -> List[TestSuiteRead]:
    """
    Retrieve all available Test Suites.
    """
    return list(await suite_service.get_all(db))  # type: ignore


@router.get(
    "/{suite_id}", response_model=TestSuiteRead, summary="Get Test Suite details"
)
async def get_suite(
    suite_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TestSuiteRead:
    """
    Get specific Test Suite by ID.
    """
    suite = await suite_service.get_by_id(db, suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Test Suite not found")
    return suite  # type: ignore


@router.put("/{suite_id}", response_model=TestSuiteRead, summary="Update Test Suite")
async def update_suite(
    suite_id: UUID,
    suite_in: TestSuiteUpdate,
    db: AsyncSession = Depends(get_db),
) -> TestSuiteRead:
    """
    Update a Test Suite.
    """
    suite = await suite_service.get_by_id(db, suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Test Suite not found")

    return await suite_service.update(db, suite, suite_in)  # type: ignore


@router.delete(
    "/{suite_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Test Suite"
)
async def delete_suite(
    suite_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a Test Suite.
    """
    suite = await suite_service.get_by_id(db, suite_id)
    if not suite:
        raise HTTPException(status_code=404, detail="Test Suite not found")

    await suite_service.delete(db, suite)
