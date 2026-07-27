"""Telemetry Metrics & OpenTelemetry Trace Collector (SOLID - SRP / LSP)."""

from typing import List
from src.dashboard.telemetry.collector import BaseTelemetryCollector, MetricEvent
from src.shared.logger.logger import get_logger

logger = get_logger("dashboard.telemetry")


class TelemetryCollector(BaseTelemetryCollector):
    """OpenTelemetry metrics collector accumulating runtime execution traces."""

    def __init__(self) -> None:
        self._events: List[MetricEvent] = []

    async def record_event(self, event: MetricEvent) -> None:
        """Records metric event asynchronously."""
        self._events.append(event)
        logger.debug(f"Recorded telemetry event '{event.event_name}' ({event.duration_ms}ms) for component '{event.component}'.")

    def get_events(self) -> List[MetricEvent]:
        """Retrieves accumulated metric events."""
        return list(self._events)
