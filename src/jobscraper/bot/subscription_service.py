from enum import Enum

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.storage.repository import UserSubscriptionRepository


class SubscriptionResult(Enum):
    CREATED = 1
    EXISTS = 2
    FAILED = 3


class RemoveSubscriptionResult(Enum):
    REMOVED = 1
    NOT_EXIST = 2
    FAILED = 3


class SubscriptionService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def subscribe(
        self, user_id: int, category: str, location: str
    ) -> SubscriptionResult:
        res = SubscriptionResult.FAILED
        async with self.session_factory() as session:
            subs_repo = UserSubscriptionRepository(session)
            res = await self.create_subscription(subs_repo, user_id, category, location)
            await session.commit()
            return res

    async def create_subscription(
        self,
        subscription_repo: UserSubscriptionRepository,
        user_id: int,
        category: str,
        location: str,
    ) -> SubscriptionResult:
        try:
            existing = await subscription_repo.find_subscription(
                user_id, category, location
            )
            if existing:
                return SubscriptionResult.EXISTS
            await subscription_repo.create_subscription(user_id, category, location)
            return SubscriptionResult.CREATED
        except SQLAlchemyError as e:
            logger.error(f"DB error while creating subscription: {e}")
            return SubscriptionResult.FAILED

    async def unsubscribe(
        self, user_id: int, category: str, location: str
    ) -> RemoveSubscriptionResult:
        result = RemoveSubscriptionResult.FAILED
        async with self.session_factory() as session:
            repo = UserSubscriptionRepository(session)
            result = await self.delete_subscription(repo, user_id, category, location)
            await session.commit()
        return result

    async def delete_subscription(
        self,
        repo: UserSubscriptionRepository,
        user_id: int,
        category: str,
        location: str,
    ) -> RemoveSubscriptionResult:
        try:
            sub = await repo.find_subscription(user_id, category, location)
            if not sub:
                return RemoveSubscriptionResult.NOT_EXIST
            else:
                sub.is_active = False
                return (
                    RemoveSubscriptionResult.REMOVED
                )  # technically its more like marking as inactive than removing...
        except SQLAlchemyError as e:
            logger.error(f"DB error while creating subscription: {e}")
            return RemoveSubscriptionResult.FAILED
