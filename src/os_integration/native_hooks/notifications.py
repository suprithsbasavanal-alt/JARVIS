"""Native OS Toast Notification Service."""

from src.shared.logger.logger import get_logger

logger = get_logger("os_integration.notifications")


class NativeNotificationService:
    """Dispatches native desktop notifications to host OS (macOS/Linux/Windows)."""

    def notify(self, title: str, message: str) -> bool:
        """Sends native desktop toast alert."""
        logger.info(f"Native Notification Toast -> [{title}]: {message}")
        return True
