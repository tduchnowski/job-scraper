import os
from sqlalchemy import text
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
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=5,
    )

    _session_local = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def get_db_url():
    host = os.getenv("POSTGRES_HOST")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    if not all([host, user, password, db]):
        raise ValueError("Missing environment variables for database setup")

    if os.getenv("ENVIRONMENT") == "deploy":
        return f"postgresql+asyncpg://{user}:{password}@{host}/{db}?ssl=require"
    else:
        return f"postgresql+asyncpg://{user}:{password}@{host}/{db}"


async def check_db_health():
    session_factory = get_session_local()
    async with session_factory() as session:
        try:
            await session.execute(text("SELECT 1"))
            await session.commit()  # Explicit commit for safety
        finally:
            await session.close()  # Ensure connection returns to pool
