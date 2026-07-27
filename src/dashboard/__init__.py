"""Dashboard Package."""

from .telemetry.collector import BaseTelemetryCollector, MetricEvent

__all__ = [
    "BaseTelemetryCollector",
    "MetricEvent",
]
