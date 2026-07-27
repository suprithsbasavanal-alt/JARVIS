# Automation Module (`src/automation`)

## Purpose
Executes scheduled jobs, cron tasks, background multi-step workflow DAGs, and event-driven automation triggers.

## Architectural Layer
**Use Case & Orchestration Layer**. Coordinates system processes, background tools, and agent actions without coupling to specific scheduling drivers.

## Subdirectories
- `contracts/`: Abstract Base Classes (`WorkflowEngineContract`, `BaseTrigger`, `SchedulerContract`).
- `engine/`: DAG workflow execution state machine.
- `schedulers/`: Cron expression evaluator and interval job scheduler.
