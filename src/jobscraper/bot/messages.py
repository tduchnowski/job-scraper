from typing import Sequence
from aiogram import Bot

from jobscraper.config.scraping_config import LOCATIONS, SEARCH_QUERIES
from jobscraper.storage.models import NotificationORM, UserORM, UserSubscriptionORM


GENERAL_FAIL_MSG = "Something went wrong. Try again later"


def get_start_text() -> str:
    return (
        "🎯 *Welcome to IT Jobs Worldwide Bot!*\n\n"
        "I'll help you stay updated with the latest job opportunities matching your preferences.\n\n"
        "📌 *Quick Start*\n\n"
        "1️⃣  Subscribe to job catgories and locations\n"
        "2️⃣  I'll notify you when new jobs are posted\n"
        "3️⃣  Never miss an opportunity!\n\n"
        "📋 *Available Commands*\n\n"
        "`/subscribe <CATEGORY> <LOCATION>`\n"
        "Add a subscription\n\n"
        "`/unsubscribe <CATEGORY> <LOCATION>`\n"
        "Remove a subscription\n\n"
        "`/categories`\n"
        "See all job categories\n\n"
        "`/mysubscriptions`\n"
        "View your current subscriptions\n\n"
        "`/help`\n"
        "Show all commands\n\n\n"
        "🚀 Ready to find your next job?"
    )


def get_job_notification_text(batch: list[NotificationORM]) -> str:
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


def get_help_text() -> str:
    return (
        "🤖 *IT Jobs Worldwide Bot– Help*\n\n"
        "Here’s how you can use the bot:\n\n"
        "*/subscribe <category> <location>*\n"
        "Subscribe to job notifications for a given category and location.\n"
        "Example:\n"
        "`/subscribe GO GERMANY`\n\n"
        "*/unsubscribe <category> <location>*\n"
        "Stop receiving notifications for a specific subscription.\n"
        "Example:\n"
        "`/unsubscribe GO GERMANY`\n\n"
        "*/categories*\n"
        "View the list of all supported job categories you can subscribe to.\n\n"
        "*/mysubscriptions*\n"
        "See all your current subscriptions.\n\n"
        "You’ll receive notifications whenever new jobs matching your subscriptions are found 🚀"
    )


def get_categories_text(categories: list[str]):
    if not categories:
        return "*No categories available at the moment.*\n\nPlease check back later."
    sorted_cats = sorted(categories)
    categories_list = "\n".join([f"• `{cat}`" for cat in sorted_cats])
    return (
        "*Available Job Categories*\n\n"
        f"{categories_list}\n\n"
        "💡 *How to subscribe:*\n"
        "Use `/subscribe <CATEGORY> <LOCATION>`\n"
    )


def get_subscriptions_text(subscriptions: Sequence[UserSubscriptionORM]) -> str:
    if not subscriptions:
        return (
            "📋 *You have no active subscriptions*\n\n"
            "💡 *Get started:*\n"
            "Use `/subscribe <CATEGORY> <LOCATION>` to start receiving job notifications\n\n"
            "Use `/categories` to see all available categories"
        )

    sorted_subs = sorted(subscriptions, key=lambda s: (s.category, s.location))
    subscription_lines = []
    for i, sub in enumerate(sorted_subs, 1):
        subscription_lines.append(f"{i}. {sub.category.value} → {sub.location}")

    subscriptions_list = "\n".join(subscription_lines)
    return (
        "📋 *Your Active Subscriptions*\n\n"
        f"{subscriptions_list}\n\n"
        "❌ *Remove a subscription:*\n"
        "Use `/unsubscribe <CATEGORY> <LOCATION>`\n\n"
    )


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
        return False, ("❌ Please provide a valid country as a location.\n\n")
    return True, ""


async def send_batch_notification(
    bot: Bot,
    user: UserORM,
    batch: list[NotificationORM],
):
    # Send to Telegram
    await bot.send_message(
        chat_id=user.chat_id,
        text=get_job_notification_text(batch),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )
