import os

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

from services.shared.storage.session import get_session_local, set_session_local
from services.notifier.src.pipeline import make_messages, make_notifications
from services.shared.infra.redis import create_producer
from services.shared.utils.logger import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_session_local()
    setup_logger()

    redis_url = os.getenv("REDIS_URL", "")
    notification_topic = os.getenv("REDIS_NOTIFICATIONS_TOPIC", "")
    job_status_topic = os.getenv("REDIS_JOB_STATUS_TOPIC", "")
    user_messages_topic = os.getenv("REDIS_USER_MESSAGES_TOPIC", "")
    if not all(
        (
            redis_url,
            notification_topic,
            job_status_topic,
            user_messages_topic,
        )
    ):
        raise ValueError(
            f"Not all env variables are set: REDIS_URL={redis_url}, REDIS_NOTIFICATIONS_TOPIC={notification_topic}, REDIS_JOB_STATUS_TOPIC={job_status_topic}"
        )

    app.state.notification_producer = create_producer(redis_url, notification_topic)
    await app.state.notification_producer.connect()

    app.state.job_status_producer = create_producer(redis_url, job_status_topic)
    await app.state.job_status_producer.connect()

    app.state.user_messages_producer = create_producer(redis_url, user_messages_topic)
    await app.state.user_messages_producer.connect()

    yield


def create_app():
    app = FastAPI(lifespan=lifespan)

    @app.post("/notify")
    async def notify(request: Request):
        session_maker = get_session_local()
        async with session_maker() as session:
            result = await make_notifications(
                session, app.state.notification_producer, app.state.job_status_producer
            )
            return result

    @app.post("/dispatch")
    async def dispatch(request: Request):
        session_maker = get_session_local()
        async with session_maker() as session:
            result = await make_messages(session, app.state.user_messages_producer)
            return result

    @app.get("/health")
    async def health(request: Request):
        """Check redis and db connection"""
        pass

    return app
