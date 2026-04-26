import pytest
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from jobscraper.models.job import Job, JobCategory, JobLocation
from jobscraper.services.scraping_service import get_scraping_scope, scrape_one


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "location,category,query,mock_jobs,expected_jobs_count",
    [
        # Test 1: Single job
        (
            JobLocation.POLAND,
            JobCategory.PYTHON,
            "python developer",
            [
                Job(
                    id="job_1",
                    url="https://indeed.com/job1",
                    title="Python Developer",
                    company="Tech Corp",
                    description="Python dev needed",
                    salary="$100k",
                    job_type="full-time",
                    skills=["Python", "Django"],
                    seniority="senior",
                )
            ],
            1,
        ),
        # Test 2: Multiple jobs from same location/category
        (
            JobLocation.GERMANY,
            JobCategory.JAVASCRIPT,
            "frontend developer",
            [
                Job(
                    id="job_2",
                    url="https://indeed.com/job2",
                    title="Frontend Developer",
                    company="Startup Inc",
                    description="React developer needed",
                    salary="$120k",
                    job_type="full-time",
                    skills=["React", "TypeScript"],
                    seniority="mid",
                ),
                Job(
                    id="job_3",
                    url="https://indeed.com/job3",
                    title="UI Developer",
                    company="Design Co",
                    description="UI/UX developer",
                    salary="$110k",
                    job_type="contract",
                    skills=["CSS", "HTML"],
                    seniority="junior",
                ),
            ],
            2,
        ),
        # Test 3: No jobs found
        (JobLocation.POLAND, JobCategory.GO, "golang backend", [], 0),
        # Test 4: Job with minimal fields (only required ones)
        (
            JobLocation.UKRAINE,
            JobCategory.DATA,
            "data engineer",
            [
                Job(
                    id="job_4",
                    url="https://indeed.com/job4",
                    title="Data Engineer",
                    company="Data Corp",
                )
            ],
            1,
        ),
        # Test 5: Different location with edge characters
        (
            JobLocation.SPAIN,
            JobCategory.RUST,
            "systems programmer",
            [
                Job(
                    id="job_5",
                    url="https://indeed.com/job5",
                    title="Systems Engineer",
                    company="Systems Inc",
                    description="Systems programming in Rust",
                    skills=["Rust", "C"],
                    seniority="senior",
                )
            ],
            1,
        ),
        # Test 6: Multiple jobs with various optional fields
        (
            JobLocation.REMOTE,
            JobCategory.CLOUD,
            "cloud architect",
            [
                Job(
                    id="job_6",
                    url="https://indeed.com/job6",
                    title="Cloud Architect",
                    company="AWS",
                    description="Design cloud solutions",
                    salary="$150k",
                    job_type="full-time",
                    skills=["AWS", "Terraform", "Kubernetes"],
                    seniority="lead",
                    summary="Senior cloud position",
                ),
                Job(
                    id="job_7",
                    url="https://indeed.com/job7",
                    title="DevOps Engineer",
                    company="Cloud Inc",
                    description="CI/CD pipelines",
                    salary="$140k",
                    job_type="full-time",
                    skills=["Docker", "Jenkins"],
                    seniority="senior",
                ),
            ],
            2,
        ),
        # Test 7: Category with multiple words/values
        (
            JobLocation.FRANCE,
            JobCategory.DATA_SCIENCE,
            "data scientist",
            [
                Job(
                    id="job_8",
                    url="https://indeed.com/job8",
                    title="Data Scientist",
                    company="Analytics Co",
                    description="Machine learning models",
                    skills=["Python", "TensorFlow"],
                    seniority="mid",
                )
            ],
            1,
        ),
        # Test 8: Remote location with mobile category
        (
            JobLocation.REMOTE,
            JobCategory.MOBILE,
            "mobile developer",
            [
                Job(
                    id="job_9",
                    url="https://indeed.com/job9",
                    title="iOS Developer",
                    company="Mobile Inc",
                    description="Swift development",
                    salary="$130k",
                    job_type="full-time",
                    skills=["Swift", "iOS"],
                    seniority="senior",
                )
            ],
            1,
        ),
        # Test 9: Asian location
        (
            JobLocation.JAPAN,
            JobCategory.BACKEND,
            "backend engineer",
            [
                Job(
                    id="job_10",
                    url="https://indeed.com/job10",
                    title="Backend Engineer",
                    company="Tech Japan",
                    description="Go microservices",
                    salary="¥8M",
                    job_type="full-time",
                    skills=["Go", "gRPC"],
                    seniority="mid",
                )
            ],
            1,
        ),
        # Test 10: South American location
        (
            JobLocation.BRAZIL,
            JobCategory.FRONTEND,
            "react developer",
            [
                Job(
                    id="job_11",
                    url="https://indeed.com/job11",
                    title="React Developer",
                    company="Brazil Tech",
                    description="Frontend development",
                    salary="R$120k",
                    job_type="full-time",
                    skills=["React", "Next.js"],
                    seniority="junior",
                )
            ],
            1,
        ),
    ],
)
async def test_scrape_one(location, category, query, mock_jobs, expected_jobs_count):
    mock_indeed = AsyncMock()
    mock_indeed.scrape_job_list.return_value = mock_jobs

    res = await scrape_one(mock_indeed, location, category, query)

    assert len(res) == expected_jobs_count
    for job in res:
        assert job.category == category
        assert job.location == location
