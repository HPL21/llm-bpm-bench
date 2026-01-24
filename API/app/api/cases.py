from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.test_case import TestCaseCreate, TestCaseRead, TestCaseUpdate
from app.services.case_service import case_service

router = APIRouter()


@router.post(
    "/",
    response_model=TestCaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a Test Case",
)
async def create_test_case(
    case_in: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
) -> TestCaseRead:
    """
    Create a new test case within a suite.
    Optionally links to existing file assets via `file_ids`.
    """
    return await case_service.create(db, case_in)  # type: ignore


@router.get(
    "/suite/{suite_id}",
    response_model=List[TestCaseRead],
    summary="List cases in a Suite",
)
async def list_cases_by_suite(
    suite_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> List[TestCaseRead]:
    """
    Get all test cases belonging to a specific Test Suite.
    """
    return list(await case_service.get_by_suite_id(db, suite_id))  # type: ignore


@router.delete(
    "/{case_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Test Case"
)
async def delete_test_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    await case_service.delete(db, case_id)


@router.patch("/{case_id}", response_model=TestCaseRead, summary="Update Test Case")
async def update_test_case(
    case_id: UUID,
    case_in: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
) -> TestCaseRead:
    updated_case = await case_service.update(db, case_id, case_in)
    if not updated_case:
        raise HTTPException(status_code=404, detail="Test case not found")
    return updated_case  # type: ignore
