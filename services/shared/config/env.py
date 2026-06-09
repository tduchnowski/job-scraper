import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv


def setup_env(dotenv_file_path: str | None = None):
    env = os.getenv("ENVIRONMENT", "dev")
    if env == "deploy":
        logger.info("Environment configured for deployment")
        return

    if not dotenv_file_path:
        raise ValueError(
            "The environment is not deploy but the dotenv file was not specified"
        )

    env_file = Path(dotenv_file_path)
    if not env_file.exists():
        raise FileNotFoundError(f"Missing env file for env={env}")
    load_dotenv(env_file, override=True)
    logger.info(f"Environment set for env={env}")
