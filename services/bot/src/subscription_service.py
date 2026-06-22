from loguru import logger
from redisaq import Producer

from services.shared.models.queue_message import SubscriptionUpdate, SubscribeOperation


class SubscriptionService:
    def __init__(self, subscription_producer: Producer):
        self.subscription_producer = subscription_producer

    async def update(
        self, user_id: int, category: str, location: str, operation: SubscribeOperation
    ) -> bool:
        subscription_update = SubscriptionUpdate(
            user_id=user_id, operation=operation, category=category, location=location
        )
        try:
            await self.subscription_producer.enqueue(subscription_update.model_dump())
        except Exception:  # TODO: catch more specific exceptions
            logger.exception("Failed to enqueue subscription update")
            return False
        return True
