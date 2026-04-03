from loguru import logger
import sys
import os

def setup_logger():
    logger.remove()
    env = os.getenv("ENV", "dev")
    is_prod = env == "prod"
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time} | {level} | {message}",
        serialize=is_prod
    )
    # Only log to file in dev
    if not is_prod:
        os.makedirs("logs", exist_ok=True)
        logger.add(
            "logs/app.log",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days"
        )
