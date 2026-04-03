import pytest
from jobscraper.scrapers.indeed import IndeedScraper


@pytest.fixture
def scraper():
    # session is not used in parsing, so can be None
    return IndeedScraper(session=None)


def test_parse_job_list_basic(scraper):
    html = """
    <html>
        <body>
            <div class="job_seen_beacon">
                <a data-jk="abc123" href="/rc/clk?jk=abc123">
                    <h2 class="jobTitle">Python Developer</h2>
                </a>
                <span data-testid="company-name">Acme Corp</span>
            </div>
        </body>
    </html>
    """

    jobs = scraper._parse_job_list(html)

    assert len(jobs) == 1

    job = jobs[0]
    assert job.id == "abc123"
    assert job.title == "Python Developer"
    assert job.company == "Acme Corp"
    assert "jk=abc123" in job.url

def test_parse_skips_missing_title(scraper):
    html = """
    <div class="job_seen_beacon">
        <a data-jk="abc123" href="/rc/clk?jk=abc123"></a>
        <span data-testid="company-name">Acme Corp</span>
    </div>
    """

    jobs = scraper._parse_job_list(html)

    assert jobs == []
