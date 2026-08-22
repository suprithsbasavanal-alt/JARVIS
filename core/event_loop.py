"""Core Asynchronous Event Loop Coordinator for JARVIS."""

import asyncio
from collections.abc import Coroutine
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4
from core.compat import BaseModel, Field
from core.events import EventBus
from core.types import BaseDomainEvent


class LoopStatus(str, Enum):
    """Lifecycle state of the core event loop."""
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"


class EventLoopTask(BaseModel):
    """Queued async task container."""
    task_id: UUID = Field(default_factory=uuid4)
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_completed: bool = False


class JarvisEventLoop:
    """Asynchronous runtime event loop orchestrating background tasks, queues, and event streams."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self.status = LoopStatus.INITIALIZING
        self._queue: asyncio.Queue[tuple[str, Coroutine[Any, Any, Any]]] = asyncio.Queue()
        self._running_task: asyncio.Task[None] | None = None
        self._active_tasks: dict[UUID, EventLoopTask] = {}

    async def start(self) -> None:
        """Start background event processing worker."""
        if self.status == LoopStatus.RUNNING:
            return
        self.status = LoopStatus.RUNNING
        await self.event_bus.publish(
            BaseDomainEvent(
                event_name="EVENT_LOOP_STARTED",
                payload={"timestamp": datetime.now(timezone.utc).isoformat()},
            )
        )
        self._running_task = asyncio.create_task(self._process_queue())

    async def stop(self) -> None:
        """Gracefully stop background event loop."""
        self.status = LoopStatus.STOPPING
        if self._running_task:
            self._running_task.cancel()
            try:
                await self._running_task
            except asyncio.CancelledError:
                pass
        self.status = LoopStatus.STOPPED
        await self.event_bus.publish(
            BaseDomainEvent(
                event_name="EVENT_LOOP_STOPPED",
                payload={"timestamp": datetime.now(timezone.utc).isoformat()},
            )
        )

    async def enqueue_task(self, name: str, coro: Coroutine[Any, Any, Any]) -> UUID:
        """Enqueue an asynchronous task to be processed by the event loop."""
        task_info = EventLoopTask(name=name)
        self._active_tasks[task_info.task_id] = task_info
        await self._queue.put((name, coro))
        return task_info.task_id

    async def _process_queue(self) -> None:
        """Worker loop draining the task queue."""
        while self.status == LoopStatus.RUNNING:
            try:
                name, coro = await self._queue.get()
                try:
                    await coro
                except Exception as err:
                    await self.event_bus.publish(
                        BaseDomainEvent(
                            event_name="TASK_EXECUTION_ERROR",
                            payload={"task_name": name, "error": str(err)},
                        )
                    )
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
