"""Background Cron & Event Scheduler Service."""

from typing import Callable, Coroutine, Dict, Any
from src.shared.logger.logger import get_logger

logger = get_logger("automation.scheduler")


class CronSchedulerService:
    """Manages scheduled background automation triggers."""

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def schedule_job(self, job_id: str, cron_expression: str, task_fn: Callable[[], Coroutine[Any, Any, None]]) -> None:
        """Schedules recurring background job."""
        self._jobs[job_id] = {
            "cron": cron_expression,
            "fn": task_fn,
            "status": "SCHEDULED"
        }
        logger.info(f"Scheduled cron job '{job_id}' with schedule '{cron_expression}'.")

    def cancel_job(self, job_id: str) -> bool:
        """Cancels background job by ID."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Cancelled cron job '{job_id}'.")
            return True
        return False
