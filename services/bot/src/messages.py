from aiogram import Bot

from shared.config.scraping import LOCATIONS, SEARCH_QUERIES
from shared.models.notification import Notification
from shared.models.user import User


def are_args_valid(text: str) -> tuple[bool, str]:
    # Parse arguments
    args = text.split()
    if len(args) != 3:
        return False, (
            "❌ Wrong arguments\n\n"
            "Usage: /subscribe <category> <location>\n\n"
            "Example: `/subscribe PYTHON Poland`"
        )

    _, category, location = args
    category = category.upper()
    location = location.upper()

    # Validate category
    if category not in SEARCH_QUERIES:
        return False, (
            f"❌ Invalid category: {category}\n\n"
            "✅ To see supported categories: /categories\n"
        )

    # Validate location
    if location not in LOCATIONS:
        return False, ("❌ Please provide a supported country as a location.\n\n")
    return True, ""


async def send_batch_notification(
    bot: Bot,
    user: User,
    batch: list[Notification],
):
    # Send to Telegram
    await bot.send_message(
        chat_id=user.chat_id,
        text=get_job_notification_text(batch),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


def get_job_notification_text(batch: list[Notification]) -> str:
    jobs_text = "\n\n---\n\n".join(
        [
            f"📌 *{n.job.title}*\n"
            f"🏢 {n.job.company}\n"
            f"📍 {n.job.location}\n"
            f"🔗 [View]({n.job.url})"
            for n in batch
        ]
    )

    return f"🎉 *New job alert!*\n\n{jobs_text}\n\n"
