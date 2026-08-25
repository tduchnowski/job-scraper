from typing import AsyncGenerator
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from services.shared.models.queue_message import NewNotification
from services.shared.storage.models import (
    JobORM,
    UserORM,
    UserSubscriptionORM,
)


class NotificationsGenerator:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_stream_for_job(
        self, job: JobORM
    ) -> AsyncGenerator[NewNotification, None]:
        """Create notifications for all users matching a job and insert it in a session. Return the number of notifications found"""
        # TODO: query could be optimized
        query = (
            select(UserORM.id, UserSubscriptionORM.id)
            .join(UserSubscriptionORM, UserSubscriptionORM.user_id == UserORM.id)
            .where(
                and_(
                    UserSubscriptionORM.is_active,
                    UserSubscriptionORM.category == job.category,
                    UserSubscriptionORM.location == job.location,
                    UserSubscriptionORM.last_notified_at < job.created_at,
                )
            )
        )
        # user_and_subscription_ids = (await self.session.execute(query)).all()
        user_and_subscription_ids = await self.session.stream(query)
        async for user_id, sub_id in user_and_subscription_ids:
            yield NewNotification(
                job_id=job.id, user_id=user_id, subscription_id=sub_id
            )
