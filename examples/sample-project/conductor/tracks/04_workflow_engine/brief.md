<!-- ARCHITECT CONTEXT | Track: 04_workflow_engine | Wave: 3 | CC: v1 -->

## Cross-Cutting Constraints
- Transactional Outbox: All domain events through outbox table
- Observability: OTel traces on all execution steps
- Testing: TDD, 80% coverage minimum
## Interfaces
Owns: Workflow execution engine, step runner, lifecycle events
Consumes: Database session (Track 02), Celery worker config (Track 06), Outbox table (Track 02)
## Dependencies
02_database_schema, 06_event_system

<!-- END ARCHITECT CONTEXT -->

# Track 04: Workflow Execution Engine

## What This Track Delivers

The core execution engine that powers FlowForge: resolves step ordering, manages the workflow run state machine (pending/running/completed/failed/cancelled), dispatches steps to workers, handles retries with configurable backoff, supports parallel step execution and conditional branching, enforces timeouts, and publishes lifecycle events through the transactional outbox. This is the computational heart of the platform.

## Scope

### IN
- Workflow execution state machine with persisted transitions
- Step runner: dispatches steps to Celery workers by step_type
- Built-in step types: HTTP request, delay, conditional (if/else), parallel fork/join
- Retry policy enforcement (max_retries, backoff_factor, retry_on errors)
- Per-step timeout enforcement
- Workflow-level concurrency limiting
- Event publishing via outbox: workflow.started, workflow.completed, workflow.failed, step.*
- Execution context passing (output of step N as input to step N+1)

### OUT
- REST API endpoints for triggering workflows (Track 05_api_layer)
- Webhook ingestion and schedule triggers (Track 05_api_layer)
- UI for workflow monitoring (Track 07_react_frontend)
- Custom step type plugin system (backlog)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. Task queue: Celery vs arq vs Dramatiq vs custom asyncio-based runner?
   Trade-off: maturity + ecosystem (Celery) vs async-native + lightweight (arq/Dramatiq)
2. State machine persistence: update-in-place vs event-sourced state transitions?
   Trade-off: query simplicity (update) vs full audit trail and replay capability (event-sourced)
3. Parallel execution: Celery group/chord vs custom orchestrator tracking parallel branches?
   Trade-off: leveraging existing primitives vs full control over fork/join semantics
4. Step context passing: JSONB column in DB vs Redis-cached context vs in-memory (single-process)?
   Trade-off: durability (DB) vs speed (Redis) vs simplicity (in-memory, limits scaling)
5. Concurrency limiting: database semaphore (SELECT FOR UPDATE) vs Redis-based distributed lock?
   Trade-off: transactional consistency (DB) vs performance at scale (Redis)

## Architectural Notes

- The state machine must write state transitions and outbox events in the same database transaction to guarantee consistency. This is a hard requirement from the transactional outbox cross-cutting constraint.
- Track 06_event_system provides the Celery worker configuration and outbox relay -- this track defines the Celery tasks but does not configure the broker or relay.
- The execution context (step inputs/outputs) must be serializable and bounded in size -- consider enforcing a max payload size to prevent memory issues with large workflow chains.

## Complexity: L
## Estimated Phases: ~4
