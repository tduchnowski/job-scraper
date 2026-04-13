from aiogram import Bot

from jobscraper.storage.models import NotificationORM, UserORM


async def send_batch_notification(
    bot: Bot,
    user: UserORM,
    batch: list[NotificationORM],
):
    jobs_text = "\n\n---\n\n".join(
        [
            f"📌 *{n.job.title}*\n"
            f"🏢 {n.job.company}\n"
            # f"💰 {n.job.salary or 'Not specified'}\n"
            f"📍 {n.job.location}\n"
            f"🔗 [View]({n.job.url})"
            for n in batch
        ]
    )

    message = f"🎉 *New job alert!*\n\n{jobs_text}\n\n"

    # Send to Telegram
    await bot.send_message(
        chat_id=user.chat_id,
        text=message,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
