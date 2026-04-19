from aiogram.types import Message

from jobscraper.config.scraping_config import SEARCH_QUERIES


async def categories_cmd(message: Message):
    await message.answer(
        get_categories_text(list(SEARCH_QUERIES.keys())), parse_mode="markdown"
    )


def get_categories_text(categories: list[str]):
    """Generate markdown list of categories with subscription instructions."""
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
