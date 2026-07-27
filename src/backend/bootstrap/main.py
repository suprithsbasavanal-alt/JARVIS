"""Main Application Entry Point & Lifecycle Bootstrap."""

import asyncio
from src.shared.logger.logger import get_logger
from config.settings import settings

logger = get_logger("bootstrap")


async def bootstrap_application() -> None:
    """Initializes system containers, validates config, and starts services."""
    logger.info(f"Starting {settings.APP_NAME} in '{settings.ENVIRONMENT}' mode...")
    # Infrastructure dependency registration will occur here at application boot.
    logger.info("Jarvis architecture contracts and configuration loaded successfully.")


if __name__ == "__main__":
    asyncio.run(bootstrap_application())
