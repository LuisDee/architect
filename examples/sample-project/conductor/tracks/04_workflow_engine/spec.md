<!-- ARCHITECT CONTEXT v2 | Track: 04_workflow_engine | Wave: 3 | CC: v1 -->
<!-- Full context header omitted for brevity — see tracks 01/02 for full examples -->

# Track 04_workflow_engine: Workflow Execution Engine

## Overview

The core engine that executes workflows: resolves step ordering, manages execution state machine (pending → running → completed/failed), handles retries with backoff, parallel step execution, conditional branching, and timeout enforcement. Publishes events via the transactional outbox. Wave 3 — depends on database schema and event system.

## Scope

### In Scope
- Workflow execution state machine with transitions and persistence
- Step runner: dispatches steps to Celery workers by step_type
- Built-in step types: HTTP request, delay, conditional (if/else), parallel fork/join
- Retry policy enforcement (max_retries, backoff_factor, retry_on errors)
- Per-step timeout enforcement (default 5 minutes)
- Workflow-level concurrency limit (100 concurrent executions)
- Event publishing: workflow.started, workflow.completed, workflow.failed, step.completed, step.failed
- Execution context passing (output of step N available as input to step N+1)

### Out of Scope
- REST API endpoints for triggering workflows (Track 05_api_layer)
- Webhook ingestion and schedule triggers (Track 05_api_layer)
- UI for workflow monitoring (Track 07_react_frontend)
- Custom step type plugin system (backlog)

## Technical Approach

Celery with Redis broker for distributed step execution. Each workflow run creates a chain/group of Celery tasks based on step topology. State machine persisted to `workflow_runs` and `run_step_logs` tables. Retry uses Celery's built-in retry with exponential backoff. Events written to outbox table in the same transaction as state updates. Execution context stored as JSONB, passed between steps.

## Acceptance Criteria

1. Linear workflow (A → B → C) executes steps in order and completes
2. Parallel workflow (A → [B, C] → D) runs B and C concurrently, waits for both before D
3. Conditional step evaluates expression and takes correct branch
4. Failed step retries according to policy, marks run as failed after max retries
5. Step timeout kills execution after configured duration
6. Concurrent execution limit enforced (101st workflow queued, not started)
7. All state transitions persisted to database before proceeding
8. Events published via outbox for every state transition
