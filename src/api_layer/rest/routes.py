"""FastAPI REST Router & Controller Handlers (SOLID - SRP)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Dict
from src.api_layer.rest.base_controller import APIResponse
from src.ai_engine.contracts.orchestrator import AgentTask
from src.ai_engine.orchestrator.agent_orchestrator import AgentOrchestrator
from config.settings import settings

router = APIRouter()
agent_orchestrator = AgentOrchestrator()


class AgentExecuteRequest(BaseModel):
    user_query: str
    session_id: str = "default_session"


@router.get("/health", response_model=APIResponse[Dict[str, str]])
async def health_check() -> APIResponse[Dict[str, str]]:
    """Health check endpoint returning system status."""
    return APIResponse[Dict[str, str]](
        success=True,
        data={
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment.value
        }
    )


@router.get("/api/v1/system/status", response_model=APIResponse[Dict[str, Any]])
async def get_system_status() -> APIResponse[Dict[str, Any]]:
    """Returns detailed status of active modules and feature flags."""
    return APIResponse[Dict[str, Any]](
        success=True,
        data={
            "app_name": settings.app_name,
            "features": settings.features.model_dump(),
            "default_model": settings.model.default_model_name,
            "provider": settings.model.default_provider,
        }
    )


@router.post("/api/v1/agent/execute", response_model=APIResponse[Dict[str, Any]])
async def execute_agent_task(payload: AgentExecuteRequest) -> APIResponse[Dict[str, Any]]:
    """Submits a user query for execution by the AI Agent Orchestrator."""
    task = AgentTask(
        task_id=f"task_{settings.app_name.lower()}",
        user_query=payload.user_query,
        session_id=payload.session_id
    )

    result = await agent_orchestrator.execute_task(task)
    return APIResponse[Dict[str, Any]](
        success=result.success,
        data={
            "task_id": result.task_id,
            "output": result.final_output,
            "steps": result.steps_taken
        }
    )
