"""Unit Test Suite for Automation Component."""

import pytest
from src.automation import (
    DAGWorkflowEngine,
    CronSchedulerService,
    WorkflowDefinition,
    WorkflowStep,
)


@pytest.mark.asyncio
async def test_dag_workflow_engine():
    """Verifies DAG Workflow Engine step execution."""
    engine = DAGWorkflowEngine()
    step1 = WorkflowStep(step_id="step_1", action_name="download_dataset", params={"url": "https://example.com/data"})
    step2 = WorkflowStep(step_id="step_2", action_name="process_dataset", params={"mode": "clean"}, depends_on=["step_1"])

    workflow = WorkflowDefinition(
        workflow_id="wf_001",
        name="Data Pipeline Workflow",
        steps=[step1, step2]
    )

    result = await engine.run_workflow(workflow)
    assert result["status"] == "SUCCESS"
    assert "step_1" in result["results"]
    assert "step_2" in result["results"]


def test_cron_scheduler_service():
    """Verifies Cron Scheduler job scheduling and cancellation."""
    scheduler = CronSchedulerService()

    async def dummy_task():
        pass

    scheduler.schedule_job("job_1", "0 * * * *", dummy_task)
    assert "job_1" in scheduler._jobs

    cancelled = scheduler.cancel_job("job_1")
    assert cancelled is True
    assert "job_1" not in scheduler._jobs
