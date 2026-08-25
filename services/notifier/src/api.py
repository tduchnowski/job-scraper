import os

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from services.shared.storage.session import get_session_local
from services.notifier.src.pipeline import make_notifications
from services.shared.infra.redis import create_producer
from services.shared.utils.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()

    redis_host = os.getenv("REDIS_HOST", "")
    redis_port = os.getenv("REDIS_PORT", "")
    notification_topic = os.getenv("REDIS_NOTIFICATIONS_TOPIC", "")

    app.state.notification_producer = create_producer(
        redis_host, redis_port, notification_topic
    )
    await app.state.notification_producer.connect()

    yield


def create_app():
    app = FastAPI(lifespan=lifespan)

    @app.post("/notify")
    async def notify(request: Request):
        session_maker = get_session_local()
        async with session_maker() as session:
            result = await make_notifications(session, app.state.notification_producer)
            return result

    @app.post("/dispatch")
    async def dispatch(request: Request):
        result = {}
        return result

    @app.get("/health")
    async def health(request: Request):
        """Check redis and db connection"""
        pass

    return app
