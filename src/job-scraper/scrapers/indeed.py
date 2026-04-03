from bs4 import BeautifulSoup
import aiohttp
from loguru import logger

class IndeedScraper:
    def __init__(self, session: aiohttp.ClientSession):
        self._base_url = "https://pl.indeed.com/jobs"
        self._jobview_url = "https://pl.indeed.com/viewjob"
        self._session = session

    async def scrape_job_list(self, query: str, location: str):
        logger.info(f"Scraping Indeed, query={query}, location={location}")
        resp = await self._fetch_job_list(query, location)
        self._parse_job_list(resp)

    async def _fetch_job_list(self, query: str, location: str) -> str:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        params = {
            'q': query,
            'l': location,
            'radius': 25,
            'sort': 'date',
        }
        async with self._session.get(self._base_url, params=params, headers=headers) as response:
            return await response.text()

    def _parse_job_list(self, html: str):
        soup = BeautifulSoup(html, "lxml")
        jobs = soup.find_all("div", {"class": "job_seen_beacon"})
        for job in jobs:
            title = job.find("h2", {"class": "jobTitle"})
            title = title.get_text(strip=True) if title else "N/A"
            company = job.find("span", {"data-testid": "company-name"})
            company = company.get_text(strip=True) if company else "N/A"
            link = job.find("a", href=True)
            jk = ""
            job_url = ""
            if link:
                jk = link.get('data-jk', "")
                job_url = f"{self._jobview_url}?jk={jk}" if jk else ""
            logger.info(f"Job -- {title}, {company}, {jk}, {job_url}")

    def scrape_job_details(self, job_id: str):
        pass
