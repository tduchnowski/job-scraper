import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from services.scraper.src.pipeline import find_new_jobs, get_scraping_scope
from services.shared.infra.redis import create_producer
from services.shared.utils.logger import setup_logger
from services.shared.storage.session import get_session_local, set_session_local


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    set_session_local()

    redis_host = os.getenv("REDIS_HOST", "")
    redis_port = os.getenv("REDIS_PORT", "")
    job_topic = os.getenv("REDIS_NEW_JOBS_TOPIC", "")

    app.state.job_producer = create_producer(redis_host, redis_port, job_topic)
    await app.state.job_producer.connect()

    yield

    if app.state.job_producer:
        await app.state.job_producer.close()


def create_app():
    app = FastAPI(lifespan=lifespan)

    # TODO: add api key
    @app.post("/scrape")
    async def scrape(request: Request):
        sites = ["indeed"]
        session_maker = get_session_local()
        async with session_maker() as session:
            search_scope = await get_scraping_scope(session)
        result = await find_new_jobs(app.state.job_producer, search_scope, sites)
        return result

    @app.get("/health")
    async def health(request: Request):
        """Check redis connection"""
        pass

    return app
