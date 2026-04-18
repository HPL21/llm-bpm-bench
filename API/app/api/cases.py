import csv
import io
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.file_asset import FileAsset
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


@router.post(
    "/suite/{suite_id}/import-csv",
    status_code=status.HTTP_201_CREATED,
    summary="Import test cases from CSV"
)
async def import_cases_from_csv(
    suite_id: UUID,
    collection_name: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Importuje przypadki testowe z pliku CSV.
    Plik CSV musi zawierać kolumny: 'filenames' (oddzielone średnikami) i 'expected_response'.
    Opcjonalnie może zawierać 'input_text' (domyślnie przyjmuje nazwy plików, jeśli brak).
    Zwraca błąd 400 z listą brakujących plików, jeśli nie istnieją w podanej kolekcji.
    """
    if not file.filename or file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Wymagany jest plik .csv")

    content = await file.read()
    try:
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
    except Exception:
        raise HTTPException(status_code=400, detail="Nie udało się zdekodować pliku CSV.")

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="Plik CSV jest pusty.")

    if not reader.fieldnames or 'filenames' not in reader.fieldnames or 'expected_response' not in reader.fieldnames:
        raise HTTPException(
            status_code=400,
            detail="Plik CSV musi zawierać nagłówki: 'filenames' oraz 'expected_response'."
        )

    required_filenames = set()
    for row in rows:
        if row.get('filenames'):
            files = [f.strip() for f in row['filenames'].split('###') if f.strip()]
            required_filenames.update(files)

    file_map = {}
    if required_filenames:
        result = await db.execute(
            select(FileAsset)
            .where(FileAsset.collection_name == collection_name)
            .where(FileAsset.filename.in_(required_filenames))
        )
        found_files = result.scalars().all()
        found_filenames = {f.filename for f in found_files}

        missing_files = required_filenames - found_filenames

        if missing_files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Niektóre pliki nie istnieją w wybranej kolekcji.",
                    "missing_files": list(missing_files)
                }
            )
        file_map = {f.filename: f.id for f in found_files}

    created_cases = []
    for row in rows:
        file_ids = []
        if row.get('filenames'):
            files = [f.strip() for f in row['filenames'].split(';') if f.strip()]
            file_ids = [file_map[f] for f in files if f in file_map]

        input_text = row.get('input_text') or f"Przetwórz pliki: {row.get('filenames', '')}"

        case_in = TestCaseCreate(
            suite_id=suite_id,
            input_text=input_text,
            expected_output=row['expected_response'],
            file_ids=file_ids
        )
        created = await case_service.create(db, case_in)
        created_cases.append(created)

    return {"message": "Pomyślnie zaimportowano", "count": len(created_cases)}
