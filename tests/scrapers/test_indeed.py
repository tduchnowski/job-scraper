import pytest
from jobscraper.scrapers.indeed import IndeedScraper


@pytest.fixture
def scraper_poland():
    # session is not used in parsing, so can be None
    return IndeedScraper(session=None, location="POLAND")


def test_parse_job_list_basic(scraper_poland):
    html = """
    <html>
        <body>
            <div class="job_seen_beacon">
                <h2 class="jobTitle">Python Developer</h2>
                <a data-jk="abc123" href="/rc/clk?jk=abc123"></a>
                <span data-testid="company-name">Acme Corp</span>
            </div>
        </body>
    </html>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "abc123"
    assert job.title == "Python Developer"
    assert job.company == "Acme Corp"
    assert "jk=abc123" in job.url


def test_title_nested_in_span(scraper_poland):
    html = """
    <div class="job_seen_beacon">
        <a data-jk="abc123" href="/rc/clk?jk=abc123">
            <h2 class="jobTitle">
                <span>Python Developer</span>
            </h2>
        </a>
        <span data-testid="company-name">Acme</span>
    </div>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert len(jobs) == 1
    assert jobs[0].title == "Python Developer"


def test_title_with_noise(scraper_poland):
    html = """
    <div class="job_seen_beacon">
        <a data-jk="abc123" href="/rc/clk?jk=abc123">
            <h2 class="jobTitle">
                <span>Python Developer</span>
                <span class="new">new</span>
            </h2>
        </a>
        <span data-testid="company-name">Acme</span>
    </div>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert len(jobs) == 1
    assert "Python Developer" in jobs[0].title


def test_parse_skips_missing_title(scraper_poland):
    html = """
    <div class="job_seen_beacon">
        <a data-jk="abc123" href="/rc/clk?jk=abc123"></a>
        <span data-testid="company-name">Acme Corp</span>
    </div>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert jobs == []


def test_parse_skips_missing_jk(scraper_poland):
    html = """
    <div class="job_seen_beacon">
        <a href="/rc/clk"></a>
        <h2 class="jobTitle">Python Dev</h2>
        <span data-testid="company-name">Acme</span>
    </div>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert jobs == []


def test_parse_multiple_jobs(scraper_poland):
    html = """
    <div class="job_seen_beacon">
        <h2 class="jobTitle">Python Dev</h2>
        <a data-jk="1" href="/rc/clk?jk=1"></a>
        <span data-testid="company-name">Acme Corp</span>
    </div>
    <div class="job_seen_beacon">
        <h2 class="jobTitle">Python Developer</h2>
        <a data-jk="2" href="/rc/clk?jk=2"></a>
        <span data-testid="company-name">Acme Corp</span>
    </div>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert len(jobs) == 2
    assert {job.id for job in jobs} == {"1", "2"}


def test_jk_extraction(scraper_poland):
    html = """
    <div class="job_seen_beacon">
        <a data-jk="xyz789" href="/rc/clk?jk=xyz789"></a>
        <h2 class="jobTitle">Dev</h2>
        <span data-testid="company-name">A</span>
    </div>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert jobs[0].id == "xyz789"


def test_duplicate_jobs(scraper_poland):
    html = """
    <div class="job_seen_beacon">
        <a data-jk="same" href="/rc/clk?jk=same"><h2 class="jobTitle">Dev</h2></a>
        <span data-testid="company-name">A</span>
    </div>
    <div class="job_seen_beacon">
        <a data-jk="same" href="/rc/clk?jk=same"><h2 class="jobTitle">Dev</h2></a>
        <span data-testid="company-name">A</span>
    </div>
    <div class="job_seen_beacon">
        <a data-jk="diff" href="/rc/clk?jk=diff"><h2 class="jobTitle">Dev</h2></a>
        <span data-testid="company-name">A</span>
    </div>
    """
    jobs = scraper_poland._parse_job_list(html)
    assert len(jobs) == 2
