import pytest
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from jobscraper.models.job import JobCategory
from jobscraper.services.scraping_service import get_scraping_scope


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "db_data,expected",
    [
        # Empty result
        ([], {}),
        # Single location, single category
        ([("Seattle", JobCategory.PYTHON)], {"Seattle": [JobCategory.PYTHON]}),
        # Single location, multiple categories
        (
            [
                ("Austin", JobCategory.PYTHON),
                ("Austin", JobCategory.JAVASCRIPT),
                ("Austin", JobCategory.DATA),
            ],
            {"Austin": [JobCategory.PYTHON, JobCategory.JAVASCRIPT, JobCategory.DATA]},
        ),
        # Multiple locations, various categories
        (
            [
                ("NYC", JobCategory.BACKEND),
                ("LA", JobCategory.FRONTEND),
                ("NYC", JobCategory.DEVOPS),
                ("LA", JobCategory.CLOUD),
                ("NYC", JobCategory.PYTHON),
                ("LA", JobCategory.FULLSTACK),
            ],
            {
                "NYC": [JobCategory.BACKEND, JobCategory.DEVOPS, JobCategory.PYTHON],
                "LA": [JobCategory.FRONTEND, JobCategory.CLOUD, JobCategory.FULLSTACK],
            },
        ),
        # Test all major category groups
        (
            [
                ("Boston", JobCategory.PYTHON),
                ("Boston", JobCategory.JAVA),
                ("Boston", JobCategory.GO),
                ("Boston", JobCategory.RUST),
            ],
            {
                "Boston": [
                    JobCategory.PYTHON,
                    JobCategory.JAVA,
                    JobCategory.GO,
                    JobCategory.RUST,
                ]
            },
        ),
    ],
)
async def test_get_scraping_scope(db_data, expected):
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.execute.return_value = db_data

    res = await get_scraping_scope(mock_session)
    assert res == expected
