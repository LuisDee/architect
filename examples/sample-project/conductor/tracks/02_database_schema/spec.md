<!-- ARCHITECT CONTEXT v2 | Track: 02_database_schema | Wave: 2 | CC: v1 -->

## Constraints (filtered for this track)

- Error Handling: SQLAlchemy exceptions wrapped in domain exceptions using AppError base class
- Health Checks: /readyz includes PostgreSQL connectivity check
- Testing: TDD, 80% coverage, migration tests, schema validation tests
- Config Management: Database URL and pool settings via pydantic-settings
- Connection Pooling: SQLAlchemy async pool — 10 min, 20 max, 30s idle timeout

## Interfaces

### Owns
- SQLAlchemy models: User, Workflow, WorkflowStep, WorkflowRun, RunStepLog, ApiKey
- Alembic migration chain
- Outbox table (for transactional event publishing)
- Database session factory and dependency injection

### Consumes
- Docker Compose PostgreSQL service (Track 01_infra_scaffold)

### Publishes
- None

### Subscribes
- None

## Dependencies

- Track 01_infra_scaffold: Docker Compose with PostgreSQL service must be running

## Full Context (read if needed)

- architect/architecture.md — System architecture and component map
- architect/cross-cutting.md — All versioned constraints
- architect/interfaces.md — All interface contracts
- architect/dependency-graph.md — Full dependency DAG

<!-- END ARCHITECT CONTEXT -->

<!-- ARCHITECT GENERATED -->

<!-- END ARCHITECT GENERATED -->

<!-- USER ADDITIONS — preserved across regenerations -->

<!-- END USER ADDITIONS -->

# Track 02_database_schema: Database Schema & Migrations

## Overview

Defines the PostgreSQL schema for FlowForge: users, workflows, workflow steps, execution runs, and the transactional outbox. Sets up Alembic migrations, connection pooling, seed data, and the database session management layer. Wave 2 — depends on the infrastructure scaffold providing Docker Compose with PostgreSQL.

## Scope

### In Scope
- SQLAlchemy 2.0 async models for all core domain entities
- Alembic migration configuration and initial migration
- Transactional outbox table per cross-cutting constraint
- Connection pooling configuration (async engine)
- Database session factory with FastAPI dependency injection
- Seed data script for development environment
- Index strategy for known query patterns (workflow by owner, runs by workflow, runs by status)
- Rollback migration for every up migration

### Out of Scope
- Application-level caching (Track 06_event_system handles Redis)
- Full-text search indices (deferred, consider CQRS trigger)
- Data archival and retention automation (backlog)
- API endpoints that read/write these models (Track 05_api_layer)
- User authentication logic (Track 03_auth_system — this track only defines the user table schema)

## Technical Approach

SQLAlchemy 2.0 with async engine (`create_async_engine`) and `AsyncSession`. Models use declarative base with type annotations. Alembic configured for async with `run_async` in `env.py`. All tables include `created_at` and `updated_at` timestamp columns with server defaults. The outbox table follows the transactional outbox pattern: events written in the same transaction as state changes, with a `published_at` nullable column for relay tracking. Connection pool uses `pool_size=10`, `max_overflow=10`, `pool_recycle=1800`, `pool_timeout=30`. The session factory provides an `AsyncSession` via FastAPI's `Depends()`.

### Schema Overview

```
users            — id, email, name, password_hash, role, is_active, created_at, updated_at
api_keys         — id, user_id (FK), key_hash, name, scopes, expires_at, created_at
workflows        — id, owner_id (FK→users), name, description, trigger_type, trigger_config, is_active, created_at, updated_at
workflow_steps   — id, workflow_id (FK), position, step_type, config, timeout_seconds, retry_policy, created_at
workflow_runs    — id, workflow_id (FK), triggered_by, status, started_at, completed_at, error_message
run_step_logs    — id, run_id (FK), step_id (FK), status, input_data, output_data, started_at, completed_at, error_message, attempt
outbox           — id, aggregate_type, aggregate_id, event_type, payload (JSONB), created_at, published_at
```

## Acceptance Criteria

1. `alembic upgrade head` runs without error on a fresh PostgreSQL instance
2. `alembic downgrade base` rolls back all migrations cleanly
3. All tables match the schema overview above
4. Seed data populates all tables with representative test data (3 users, 5 workflows, sample steps and runs)
5. Connection pool handles 50 concurrent connections without errors
6. Outbox table exists with required columns (id, aggregate_type, aggregate_id, event_type, payload, created_at, published_at)
7. All tables have appropriate indices verified by EXPLAIN on key query patterns
8. FastAPI dependency `get_db_session` yields an AsyncSession and properly closes it

## Cross-Cutting Compliance

- Error Handling: `backend/app/models/exceptions.py` wraps SQLAlchemy `IntegrityError`, `NoResultFound` in domain exceptions inheriting from `AppError`
- Health Checks: `GET /readyz` PostgreSQL check uses `SELECT 1` through the connection pool
- Testing: Migration tests (upgrade + downgrade cycle), model validation tests, session factory tests, 80% coverage
- Config Management: `DATABASE_URL` and pool settings read from pydantic-settings `Settings` class
- Connection Pooling: Configured on `create_async_engine` per spec (10 min, 20 max, 30s timeout)

<!-- END ARCHITECT GENERATED -->

<!-- USER ADDITIONS — preserved across regenerations -->

<!-- END USER ADDITIONS -->
