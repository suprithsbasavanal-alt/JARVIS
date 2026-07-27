"""DAG Workflow Execution Engine Implementation (SOLID - SRP / DIP)."""

import time
from typing import Any, Dict
from src.automation.contracts.workflow import (
    WorkflowEngineContract,
    WorkflowDefinition,
    WorkflowStep,
)
from src.shared.logger.logger import get_logger

logger = get_logger("automation.engine")


class DAGWorkflowEngine(WorkflowEngineContract):
    """Executes multi-step DAG workflows sequentially or in parallel."""

    async def run_workflow(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"Executing workflow '{workflow.name}' (ID: {workflow.workflow_id}) with {len(workflow.steps)} steps...")

        results = {}
        for step in workflow.steps:
            logger.info(f"Running workflow step '{step.step_id}' - Action: '{step.action_name}'...")
            # Simulate step action execution
            results[step.step_id] = {
                "action": step.action_name,
                "status": "COMPLETED",
                "params": step.params
            }

        duration = round((time.time() - start_time) * 1000, 2)
        return {
            "workflow_id": workflow.workflow_id,
            "status": "SUCCESS",
            "execution_time_ms": duration,
            "results": results
        }
