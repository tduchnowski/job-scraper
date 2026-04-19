from aiogram.types import Message


"""Help text for /help command."""
RESPONSE = (
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


async def help_cmd(message: Message):
    await message.answer(RESPONSE, parse_mode="markdown")
