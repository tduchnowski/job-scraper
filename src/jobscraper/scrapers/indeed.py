import asyncio
from bs4 import BeautifulSoup
import aiohttp
from loguru import logger
from jobscraper.config.scraping_config import INDEED_DOMAINS
from jobscraper.models.job import Job


class IndeedScraper:
    def __init__(
        self,
        session: aiohttp.ClientSession | None,
        semaphore: asyncio.Semaphore,
        location: str,
    ):
        domain = INDEED_DOMAINS.get(location, "https://indeed.com")
        self._base_url = f"{domain}/jobs"
        self._jobview_url = f"{domain}/viewjob"
        self._session = session
        self.location = location
        self.sem = semaphore

    async def scrape_job_list(self, query: str) -> list[Job]:
        logger.debug(f"Scraping Indeed, query={query}, location={self.location}")
        resp = await self._fetch_job_list(query)
        if "captcha" in resp.lower():
            logger.warning("CAPTCHA DETECTED")

        if "unusual traffic" in resp.lower():
            logger.warning("BLOCKED BY ANTI-BOT")

        jobs = self._parse_job_list(resp)
        if not jobs:
            logger.warning("Couldn't find any jobs on served html")
        logger.info(
            f"Scraping Indeed completed for query={query}, location={self.location}. Found {len(jobs)} jobs"
        )
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
        async with self.sem:
            async with self._session.get(self._base_url, params=params) as response:
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
        return result
