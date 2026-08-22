"""Asynchronous In-Memory Event Bus for JARVIS Subsystem Coordination."""

import asyncio
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any
from core.types import BaseDomainEvent

EventHandler = Callable[[BaseDomainEvent], Coroutine[Any, Any, None]]


class EventBus:
    """Decoupled asynchronous event broker."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: list[BaseDomainEvent] = []

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register an event listener for a given event name."""
        self._subscribers[event_name].append(handler)

    async def publish(self, event: BaseDomainEvent) -> None:
        """Dispatch an event to all registered subscribers."""
        self._history.append(event)
        handlers = self._subscribers.get(event.event_name, [])
        if handlers:
            await asyncio.gather(*(handler(event) for handler in handlers), return_exceptions=True)

    def get_history(self) -> list[BaseDomainEvent]:
        """Retrieve historical event trail."""
        return list(self._history)
