from aiogram.types import ErrorEvent
from loguru import logger


async def error_handler(event: ErrorEvent):
    """global error handler for errors triggered by handlers and not caught before"""
    logger.critical(f"Exception caught: {event.exception}", exc_info=True)
    if event.update.message:
        await event.update.message.answer(
            "Something went wrong. Please try again later"
        )
