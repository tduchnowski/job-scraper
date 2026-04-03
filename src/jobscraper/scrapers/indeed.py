from bs4 import BeautifulSoup
import aiohttp
from loguru import logger
from jobscraper.models.job import Job


class IndeedScraper:
    def __init__(self, session: aiohttp.ClientSession | None):
        self._base_url = "https://pl.indeed.com/jobs"
        self._jobview_url = "https://pl.indeed.com/viewjob"
        self._session = session

    async def scrape_job_list(self, query: str, location: str) -> list[Job]:
        logger.info(f"Scraping Indeed, query={query}, location={location}")
        resp = await self._fetch_job_list(query, location)
        return self._parse_job_list(resp)

    async def _fetch_job_list(self, query: str, location: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        }
        params = {
            "q": query,
            "l": location,
            "radius": 25,
            "sort": "date",
        }
        if self._session is None:
            logger.warning("Session is None, so can't fetch job postings")
            return ""
        async with self._session.get(
            self._base_url, params=params, headers=headers
        ) as response:
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

            result.append(Job(id=str(jk), title=title, company=company, url=job_url))
        logger.info(f"Scraped {len(result)} jobs")
        return result

    def scrape_job_details(self, job_id: str):
        pass
