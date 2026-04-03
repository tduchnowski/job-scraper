import asyncio
import aiohttp
from utils.logger import setup_logger 
from loguru import logger
from scrapers.indeed import IndeedScraper

async def main():
    setup_logger()
    logger.info("Pipeline started")
    async with aiohttp.ClientSession() as session:
        indeed = IndeedScraper(session)
        await indeed.scrape_job_list("python developer", "Polska")

if __name__ == "__main__":
    asyncio.run(main())
    
