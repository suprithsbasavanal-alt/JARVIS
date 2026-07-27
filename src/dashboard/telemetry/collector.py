"""Abstract Base Class for Telemetry & Trace Collectors (ISP)."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pydantic import BaseModel


class MetricEvent(BaseModel):
    """Normalized telemetry event."""
    event_name: str
    component: str
    duration_ms: float
    metadata: Dict[str, Any] = {}


class BaseTelemetryCollector(ABC):
    """Abstract Interface for System Telemetry and Tracing."""

    @abstractmethod
    async def record_event(self, event: MetricEvent) -> None:
        """Records telemetry event asynchronously."""
        pass
