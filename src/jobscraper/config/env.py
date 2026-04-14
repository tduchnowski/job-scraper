import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv


def setup_env():
    env = os.getenv("ENVIRONMENT", "dev")
    if env == "deploy":
        logger.info("Environment configured for deployment")
        return

    env_file = Path(f".env.{env}")
    if not env_file.exists():
        raise FileNotFoundError(f"Missing env file for env={env}")
    load_dotenv(env_file, override=True)
    logger.info(f"Environment set for env={env}")
