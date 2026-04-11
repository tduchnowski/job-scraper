from bs4 import BeautifulSoup
import aiohttp
from loguru import logger
from jobscraper.config.scraping_config import INDEED_DOMAINS
from jobscraper.models.job import Job


class IndeedScraper:
    _HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    def __init__(self, session: aiohttp.ClientSession | None, location: str):
        domain = INDEED_DOMAINS.get(location, "https://indeed.com")
        self._base_url = f"{domain}/jobs"
        self._jobview_url = f"{domain}/viewjob"
        self._session = session
        self.location = location

    async def scrape_job_list(self, query: str) -> list[Job]:
        logger.info(f"Scraping Indeed, query={query}, location={self.location}")
        resp = await self._fetch_job_list(query)
        if "captcha" in resp.lower():
            print("CAPTCHA detected")

        if "unusual traffic" in resp.lower():
            print("Blocked by anti-bot")

        if "jobsearch-SerpJobCard" not in resp:
            print("Expected job cards missing")
        jobs = self._parse_job_list(resp)
        if not jobs:
            logger.warning("Couldn't find any jobs on served html")
        return jobs

    async def _fetch_job_list(self, query: str, radius=25) -> str:
        if self._session is None:
            logger.warning("Session is None, so can't fetch job postings")
            return ""
        params = {
            "q": query,
            "l": self.location,
            "radius": radius,
            "sort": "date",
        }
        async with self._session.get(
            self._base_url, params=params, headers=self._HEADERS
        ) as response:
            print(
                {
                    "status": response.status,
                    "url": str(response.url),
                    "final_url": str(response.real_url),
                    "length": len(await response.text()),
                    "headers": dict(response.headers),
                }
            )
            return await response.text()

    def _parse_job_list(self, html: str) -> list[Job]:
        soup = BeautifulSoup(html, "lxml")
        jobs = soup.find_all("div", {"class": "job_seen_beacon"})
        result: list[Job] = []
        job_ids = set()

        for job in jobs:
            title = job.find("h2", {"class": "jobTitle"})
            title = title.get_text(strip=True) if title else None
            company = job.find("span", {"data-testid": "company-name"})
            company = company.get_text(strip=True) if company else None
            if not title or not company:
                logger.warning("Missing title or company, skipping")
                continue
            link = job.find("a", href=True)
            if not link:
                logger.warning("Couldn't extract link information, skipping")
                continue
            jk = link.get("data-jk")
            if not jk:
                logger.warning("Couldn't extract job id")
                continue
            if jk in job_ids:
                logger.warning(f"job id {jk} already seen, skipping")
                continue

            job_ids.add(jk)
            job_url = f"{self._jobview_url}?jk={jk}"

            result.append(
                Job(
                    id=str(jk),
                    title=title,
                    company=company,
                    url=job_url,
                )
            )
        logger.info(f"Scraped {len(result)} jobs")
        return result

    # async def scrape_job_details(self, job_url: str) -> Dict[str, str]:
    #     if self._session is None:
    #         logger.warning("Session is None, so can't fetch job details")
    #         return {}
    #     async with self._session.get(job_url, headers=self._HEADERS) as response:
    #         return self._parse_job_details(await response.text())
    #
    # def _parse_job_details(self, html: str) -> Dict[str, str]:
    #     return {"description": "test description", "location": "Warszawa"}
    #
    # def _parse_description(self, html) -> str:
    #     return ""
