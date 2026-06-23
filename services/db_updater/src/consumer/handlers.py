from redisaq import Message
from services.shared.models.queue_message import (
    NotificationUpdate,
    SubscriptionUpdate,
    UserActivity,
)


async def process_user_activity(activity_message: Message):
    user_activity = UserActivity.model_validate(activity_message.payload)
    print(user_activity)


async def process_subscription(subscription_message: Message):
    subscription = SubscriptionUpdate.model_validate(subscription_message.payload)
    print(subscription)


async def process_notification(notification_message: Message):
    notification = NotificationUpdate.model_validate(notification_message.payload)
    print(notification)
