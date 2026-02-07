<!-- ARCHITECT CONTEXT | Track: 06_event_system | Wave: 2 | CC: v1 -->

## Cross-Cutting Constraints
- Transactional Outbox: Outbox relay polls and publishes to Redis
- Connection Pooling: Redis max_connections=20
- Testing: TDD, 80% coverage minimum
## Interfaces
Owns: Celery worker config, outbox relay, Redis pub/sub, cache-aside utilities
Consumes: Docker Compose Redis (Track 01)
## Dependencies
01_infra_scaffold

<!-- END ARCHITECT CONTEXT -->

# Track 06: Event System & Task Queue

## What This Track Delivers

Sets up the asynchronous messaging backbone of FlowForge: Celery worker configuration with Redis as broker, the outbox relay that polls the database outbox table and publishes events to Redis channels, Redis pub/sub abstractions for event-driven communication, cache-aside utilities, dead letter queue handling, and Celery beat for scheduled task execution.

## Scope

### IN
- Celery worker configuration with Redis broker and result backend
- Outbox relay: background process polling outbox table, publishing events to Redis channels
- Redis pub/sub abstraction for event publishing/subscribing
- Cache-aside helper with configurable TTL
- Dead letter queue (DLQ) for failed event deliveries
- Celery beat for scheduled tasks (cron-based workflow triggers)

### OUT
- Workflow step execution logic (Track 04_workflow_engine defines its own Celery tasks)
- Database models for the outbox table (Track 02_database_schema)
- WebSocket push to frontend (backlog -- polling for MVP)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. Outbox relay pattern: polling loop vs database LISTEN/NOTIFY vs CDC (change data capture)?
   Trade-off: simplicity (polling) vs lower latency (LISTEN/NOTIFY) vs scalability (CDC)
2. Event serialization: JSON vs MessagePack vs Protobuf?
   Trade-off: human-readability + debugging (JSON) vs size + speed (binary formats)
3. Celery result backend: Redis vs database vs disabled (fire-and-forget)?
   Trade-off: result inspection + chaining (Redis/DB) vs simplicity + less storage (disabled)
4. DLQ strategy: separate Redis list vs database table vs dedicated DLQ service?
   Trade-off: operational visibility (DB) vs speed (Redis) vs decoupled processing (service)

## Architectural Notes

- The outbox relay is the critical bridge between database transactions and async events. Track 04_workflow_engine and Track 05_api_layer both write to the outbox; this track's relay is responsible for publishing those events reliably.
- Celery worker configuration defined here is shared by Track 04's step execution tasks. The broker URL, concurrency settings, and serialization format must be consistent.
- Cache-aside utilities will be consumed by Track 05_api_layer for response caching. Design the TTL and invalidation interface to be reusable across different resource types.

## Complexity: M
## Estimated Phases: ~3
