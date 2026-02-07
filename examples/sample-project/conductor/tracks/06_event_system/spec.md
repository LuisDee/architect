<!-- ARCHITECT CONTEXT v2 | Track: 06_event_system | Wave: 2 | CC: v1 -->
<!-- Full context header omitted for brevity — see tracks 01/02 for full examples -->

# Track 06_event_system: Event System & Task Queue

## Overview

Sets up Redis as message broker and cache layer: Celery worker configuration, outbox relay (polls outbox table, publishes to Redis), Redis pub/sub for real-time notifications, and cache-aside pattern utilities. Wave 2 — depends on infrastructure scaffold providing Docker Compose with Redis.

## Scope

### In Scope
- Celery worker configuration with Redis broker and result backend
- Outbox relay: background process polling outbox table, publishing events to Redis channels
- Redis pub/sub abstraction for event publishing/subscribing
- Cache-aside helper with configurable TTL (default 5 minutes)
- Dead letter queue (DLQ) for failed event deliveries
- Celery beat for scheduled tasks (cron-based workflow triggers)

### Out of Scope
- Workflow step execution logic (Track 04_workflow_engine uses Celery but defines its own tasks)
- Database models for outbox (Track 02_database_schema)
- WebSocket push to frontend (backlog)

## Acceptance Criteria

1. Celery worker starts and processes tasks from Redis broker
2. Outbox relay picks up unpublished events within 1 second
3. Redis pub/sub delivers events to subscribers
4. Cache-aside returns cached value on hit, fetches and caches on miss
5. Failed deliveries land in DLQ with error context
6. Celery beat triggers scheduled tasks at configured intervals
