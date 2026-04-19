from enum import Enum

from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from jobscraper.storage.repository import UserSubscriptionRepository


class SubscriptionResult(Enum):
    """Subscription creation result: CREATED, EXISTS, or FAILED."""

    CREATED = 1
    EXISTS = 2
    FAILED = 3


class RemoveSubscriptionResult(Enum):
    """Subscription removal result: REMOVED, NOT_EXIST, or FAILED."""

    REMOVED = 1
    NOT_EXIST = 2
    FAILED = 3


class SubscriptionService:
    """Manages user job subscriptions."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def subscribe(
        self, user_id: int, category: str, location: str
    ) -> SubscriptionResult:
        """Create a subscription for user. Returns CREATED, EXISTS, or FAILED."""
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
        """Create subscription if not exists. Returns CREATED, EXISTS, or FAILED."""
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
        """Remove subscription (soft delete). Returns REMOVED, NOT_EXIST, or FAILED."""
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
        """Soft delete: mark is_active=False. Returns REMOVED, NOT_EXIST, or FAILED."""
        try:
            sub = await repo.find_subscription(user_id, category, location)
            if not sub:
                return RemoveSubscriptionResult.NOT_EXIST
            sub.is_active = False
            return RemoveSubscriptionResult.REMOVED
        except SQLAlchemyError as e:
            logger.error(f"DB error while deleting subscription: {e}")
            return RemoveSubscriptionResult.FAILED
