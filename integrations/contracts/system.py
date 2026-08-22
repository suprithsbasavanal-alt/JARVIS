"""Abstract System Integration Contract (macOS & Android)."""

from abc import ABC, abstractmethod
from typing import Any
from integrations.base import BaseIntegration


class SystemContract(BaseIntegration, ABC):
    """Abstract contract for native OS interactions."""

    @abstractmethod
    async def get_system_status(self) -> dict[str, Any]:
        """Fetch battery, network, and memory metrics (NORMAL tier)."""
        pass

    @abstractmethod
    async def show_notification(self, title: str, body: str) -> bool:
        """Post a local desktop/Android system notification (NORMAL tier)."""
        pass

    @abstractmethod
    async def execute_system_action(self, action_name: str, payload: dict[str, Any], approval_token: str) -> bool:
        """Execute gated OS action (SENSITIVE tier - requires approval token)."""
        pass
