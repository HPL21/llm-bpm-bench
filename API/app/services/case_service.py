from uuid import UUID
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_case import TestCase
from app.models.file_asset import FileAsset
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate


class CaseService:
    """
    Service responsible for CRUD operations on Test Cases (including file linking).
    """

    async def get_by_suite_id(
        self, db: AsyncSession, suite_id: UUID
    ) -> Sequence[TestCase]:
        """Fetch all test cases belonging to a specific suite."""
        result = await db.execute(
            select(TestCase)
            .where(TestCase.suite_id == suite_id)
            .order_by(TestCase.created_at)
        )
        return result.scalars().all()

    async def create(self, db: AsyncSession, schema: TestCaseCreate) -> TestCase:
        """Create a test case and link provided files."""
        db_case = TestCase(
            suite_id=schema.suite_id,
            input_text=schema.input_text,
            expected_output=schema.expected_output,
        )

        if schema.file_ids:
            files_result = await db.execute(
                select(FileAsset).where(FileAsset.id.in_(schema.file_ids))
            )
            files = files_result.scalars().all()
            db_case.files = list(files)

        db.add(db_case)
        await db.commit()
        await db.refresh(db_case)
        return db_case

    async def bulk_create(self, db: AsyncSession, cases: Sequence[TestCaseCreate]) -> list[TestCase]:
        """Bulk create test cases."""
        db_cases = []
        for schema in cases:
            db_case = TestCase(
                suite_id=schema.suite_id,
                input_text=schema.input_text,
                expected_output=schema.expected_output,
            )

            if schema.file_ids:
                files_result = await db.execute(
                    select(FileAsset).where(FileAsset.id.in_(schema.file_ids))
                )
                files = files_result.scalars().all()
                db_case.files = list(files)

            db_cases.append(db_case)

        db.add_all(db_cases)
        await db.commit()
        for db_case in db_cases:
            await db.refresh(db_case)
        return db_cases

    async def delete(self, db: AsyncSession, case_id: UUID) -> None:
        """Delete a test case."""
        result = await db.execute(select(TestCase).where(TestCase.id == case_id))
        case = result.scalars().first()
        if case:
            await db.delete(case)
            await db.commit()

    async def update(
        self, db: AsyncSession, case_id: UUID, schema: TestCaseUpdate
    ) -> TestCase | None:
        result = await db.execute(select(TestCase).where(TestCase.id == case_id))
        case = result.scalars().first()
        if not case:
            return None

        update_data = schema.model_dump(exclude_unset=True, exclude={"file_ids"})
        for field, value in update_data.items():
            setattr(case, field, value)

        if schema.file_ids is not None:
            files_result = await db.execute(
                select(FileAsset).where(FileAsset.id.in_(schema.file_ids))
            )
            case.files = list(files_result.scalars().all())

        db.add(case)
        await db.commit()
        await db.refresh(case)
        return case

    async def get_files_by_filenames(
        self, db: AsyncSession, collection_name: str, filenames: set
    ) -> tuple[list, set]:
        """
        Fetch files from a collection matching the given filenames.
        Returns a tuple of (found_files, missing_filenames).
        """
        result = await db.execute(
            select(FileAsset)
            .where(FileAsset.collection_name == collection_name)
            .where(FileAsset.filename.in_(filenames))
        )
        found_files = result.scalars().all()
        found_filenames = {f.filename for f in found_files}
        missing_files = filenames - found_filenames
        return list(found_files), missing_files


case_service = CaseService()
