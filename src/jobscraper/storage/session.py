import os
from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

_session_local = None


def get_session_local():
    if _session_local is None:
        raise RuntimeError("SessionLocal not initialized")
    return _session_local


def set_session_local():
    global _session_local
    db_url = get_db_url()

    engine = create_async_engine(
        db_url,
        echo=False,  # set True for debugging
    )

    _session_local = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info(f"Engine set up for DB_URL={db_url}")


def get_db_url():
    host = os.getenv("POSTGRES_HOST")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    if not all([host, user, password, db]):
        raise ValueError("Missing environment variables for database setup")

    if os.getenv("ENVIRONMENT") == "prod":
        return f"postgresql+asyncpg://{user}:{password}@{host}/{db}?sslmode=require&channel_binding=require"
    else:
        return f"postgresql+asyncpg://{user}:{password}@{host}/{db}"
