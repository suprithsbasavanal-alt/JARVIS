"""Autonomous Agent Reasoning Orchestrator (SOLID - SRP / DIP)."""

import time
from typing import Optional
from src.ai_engine.contracts.orchestrator import (
    BaseAgentOrchestrator,
    AgentTask,
    AgentExecutionResult,
)
from src.ai_engine.contracts.provider import BaseLLMProvider, LLMRequest
from src.ai_engine.providers.factory import LLMProviderFactory
from src.ai_engine.prompts.template_manager import SystemPromptTemplateManager
from src.shared.logger.logger import get_logger
from config.settings import settings

logger = get_logger("ai_engine.agent_orchestrator")


class AgentOrchestrator(BaseAgentOrchestrator):
    """Autonomous ReAct Agent Orchestrator managing multi-step execution loop."""

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        prompt_manager: Optional[SystemPromptTemplateManager] = None,
    ) -> None:
        self.llm_provider = llm_provider or LLMProviderFactory.get_provider()
        self.prompt_manager = prompt_manager or SystemPromptTemplateManager()

    async def execute_task(self, task: AgentTask) -> AgentExecutionResult:
        """Executes task reasoning loop autonomously."""
        start_time = time.time()
        logger.info(f"Starting agent task '{task.task_id}' for session '{task.session_id}'...")

        steps_taken = []

        # Step 1: Render System Directive
        system_instruction = self.prompt_manager.render(
            "default",
            environment=settings.environment.value,
            app_name=settings.app_name,
            app_version=settings.app_version
        )
        steps_taken.append({"step": "system_prompt_render", "instruction": system_instruction[:80] + "..."})

        # Step 2: Formulate LLM Inference Request
        llm_request = LLMRequest(
            prompt=task.user_query,
            system_instruction=system_instruction,
            temperature=settings.model.temperature,
            max_tokens=settings.model.max_tokens,
        )
        steps_taken.append({"step": "llm_request_prepared", "provider": self.llm_provider.provider_name})

        # Step 3: Execute Model Inference
        response = await self.llm_provider.generate(llm_request)
        steps_taken.append({
            "step": "llm_response_received",
            "tokens": response.prompt_tokens + response.completion_tokens,
            "latency_ms": round((time.time() - start_time) * 1000, 2)
        })

        logger.info(f"Completed task '{task.task_id}' successfully.")
        return AgentExecutionResult(
            task_id=task.task_id,
            final_output=response.content,
            steps_taken=steps_taken,
            success=True,
        )
