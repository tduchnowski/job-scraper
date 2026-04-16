from aiogram.types import Message


RESPONSE = (
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


async def start_cmd(message: Message):
    await message.answer(RESPONSE, parse_mode="markdown")
