from uuid import UUID
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.test_suite import TestSuite
from app.schemas.test_suite import TestSuiteCreate, TestSuiteUpdate


class SuiteService:
    """
    Service responsible for CRUD operations on Test Suites.
    """

    async def get_all(self, db: AsyncSession) -> Sequence[TestSuite]:
        """Fetch all test suites."""
        result = await db.execute(
            select(TestSuite).order_by(TestSuite.created_at.desc())
        )
        return result.scalars().all()

    async def get_by_id(self, db: AsyncSession, suite_id: UUID) -> TestSuite | None:
        """Fetch a single test suite by ID."""
        result = await db.execute(select(TestSuite).where(TestSuite.id == suite_id))
        return result.scalars().first()

    async def create(self, db: AsyncSession, schema: TestSuiteCreate) -> TestSuite:
        """Create a new test suite."""
        db_obj = TestSuite(
            name=schema.name,
            description=schema.description,
            system_prompt=schema.system_prompt,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, suite: TestSuite, schema: TestSuiteUpdate
    ) -> TestSuite:
        """Update an existing test suite."""
        update_data = schema.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(suite, field, value)

        db.add(suite)
        await db.commit()
        await db.refresh(suite)
        return suite

    async def delete(self, db: AsyncSession, suite: TestSuite) -> None:
        """Delete a test suite."""
        await db.delete(suite)
        await db.commit()


suite_service = SuiteService()
