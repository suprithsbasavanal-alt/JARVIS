"""Asynchronous Runtime EventBus Bridge and Listener for Phase 6.4."""

from collections import defaultdict
from core.events import EventBus
from core.exceptions import ProactiveCooldownActiveError
from core.types import BaseDomainEvent
from intelligence.coordinator import (
    ProactiveCoordinator,
    ProactiveEvaluationResult,
    ProactiveTrigger,
    TriggerType,
)
from intelligence.dialogue_advisor import ProactiveDialogueAdvisor


class ProactiveRuntimeBridge:
    """Subscribes to domain events on EventBus, evaluates proactive triggers, and caches advisories."""

    _EVENT_TRIGGER_MAP = {
        "SESSION_STARTED": TriggerType.SESSION_START,
        "PROJECT_OPENED": TriggerType.PROJECT_OPENED,
        "PROJECT_LOADED": TriggerType.PROJECT_OPENED,
        "USER_PROPOSITION_SUBMITTED": TriggerType.PROPOSITION_SUBMITTED,
        "TASK_CREATED": TriggerType.TASK_CREATED,
        "STUDY_REQUESTED": TriggerType.STUDY_REQUESTED,
        "PERIODIC_HEALTH_CHECK": TriggerType.PERIODIC_CHECK,
    }

    def __init__(
        self,
        coordinator: ProactiveCoordinator,
        event_bus: EventBus | None = None,
    ) -> None:
        self.coordinator = coordinator
        self.event_bus = event_bus
        self._latest_evaluations: dict[str, ProactiveEvaluationResult] = {}
        self._evaluation_history: list[ProactiveEvaluationResult] = []

        if self.event_bus:
            self.attach_to_event_bus(self.event_bus)

    def attach_to_event_bus(self, event_bus: EventBus) -> None:
        """Register asynchronous event listeners for proactive domain events."""
        self.event_bus = event_bus
        for event_name in self._EVENT_TRIGGER_MAP:
            event_bus.subscribe(event_name, self._handle_domain_event)

    async def _handle_domain_event(self, event: BaseDomainEvent) -> None:
        """Process incoming domain event, convert to ProactiveTrigger, and evaluate safely."""
        trigger_type = self._EVENT_TRIGGER_MAP.get(event.event_name)
        if not trigger_type:
            return

        payload = event.payload or {}
        session_id = str(payload.get("session_id", "default_session"))
        project_path = payload.get("project_path", payload.get("path"))
        proposition = payload.get("proposition")
        topic = payload.get("topic")
        goal = payload.get("goal")
        context_summary = payload.get("summary", payload.get("context_summary", ""))

        trigger = ProactiveTrigger(
            trigger_type=trigger_type,
            context_summary=str(context_summary),
            project_path=str(project_path) if project_path else None,
            proposition=str(proposition) if proposition else None,
            topic=str(topic) if topic else None,
            goal=str(goal) if goal else None,
        )

        try:
            result = self.coordinator.evaluate_trigger(trigger)
            self._latest_evaluations[session_id] = result
            self._evaluation_history.append(result)

            # Publish notification that an informational advisory is ready
            if self.event_bus:
                await self.event_bus.publish(
                    BaseDomainEvent(
                        event_name="PROACTIVE_ADVISORY_READY",
                        payload={
                            "session_id": session_id,
                            "evaluation_id": str(result.evaluation_id),
                            "suggestions_count": len(result.suggestions),
                            "disagreements_count": len(result.disagreements),
                            "plans_count": len(result.generated_plans),
                            "is_informational_only": True,
                        },
                    )
                )
        except ProactiveCooldownActiveError:
            # Cooldown is an expected rate-limit condition; safely suppress without crashing event bus
            pass
        except Exception:
            # Fail closed safely on unexpected runtime exceptions
            pass

    def get_latest_evaluation(self, session_id: str = "default_session") -> ProactiveEvaluationResult | None:
        """Retrieve the most recent evaluation result for a session."""
        return self._latest_evaluations.get(session_id)

    def get_formatted_advisory(self, session_id: str = "default_session") -> str | None:
        """Retrieve the latest proactive advisory formatted as an inert XML data block."""
        eval_res = self.get_latest_evaluation(session_id)
        if not eval_res:
            return None
        return ProactiveDialogueAdvisor.format_system_context(eval_res)

    def clear_history(self) -> None:
        """Clear cached evaluations (useful for test isolation)."""
        self._latest_evaluations.clear()
        self._evaluation_history.clear()


# Alias for backwards compatibility / alternate naming
ProactiveRuntimeListener = ProactiveRuntimeBridge
