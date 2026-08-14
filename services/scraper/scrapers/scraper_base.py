from abc import ABC, abstractmethod
import asyncio

import aiohttp

from services.shared.models.job import Job


class Scraper(ABC):
    def __init__(
        self,
        session: aiohttp.ClientSession,
        semaphore: asyncio.Semaphore,
        location: str,
    ):
        self._session = session
        self.location = location
        self.sem = semaphore

    @abstractmethod
    async def scrape_job_list(self, query: str) -> list[Job]:
        pass
