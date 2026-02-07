<!-- ARCHITECT CONTEXT | Track: 02_database_schema | Wave: 2 | CC: v1 -->

## Cross-Cutting Constraints

- Error Handling: SQLAlchemy exceptions wrapped in domain exceptions using AppError base class
- Health Checks: /readyz includes PostgreSQL connectivity check
- Testing: TDD, 80% coverage, migration tests, schema validation tests
- Config Management: Database URL and pool settings via pydantic-settings
- Connection Pooling: SQLAlchemy async pool -- configurable pool_size, max_overflow, idle timeout

## Interfaces

### Owns
- SQLAlchemy models: User, Workflow, WorkflowStep, WorkflowRun, RunStepLog, ApiKey
- Alembic migration chain
- Outbox table (for transactional event publishing)
- Database session factory and dependency injection

### Consumes
- Docker Compose PostgreSQL service (Track 01_infra_scaffold)

## Dependencies

- Track 01_infra_scaffold: Docker Compose with PostgreSQL service must be running

<!-- END ARCHITECT CONTEXT -->

# Track 02: Database Schema & Migrations

## What This Track Delivers

Defines the complete PostgreSQL schema for FlowForge -- users, workflows, workflow steps, execution runs, API keys, and the transactional outbox -- along with Alembic migrations, connection pooling, a database session management layer, seed data, and query-pattern indices. This is the data foundation that every API and engine track imports from.

## Scope

### IN
- SQLAlchemy models for all core domain entities (User, Workflow, WorkflowStep, WorkflowRun, RunStepLog, ApiKey)
- Alembic migration configuration and initial migration (with rollback)
- Transactional outbox table for domain event publishing
- Connection pool configuration for the async engine
- Database session factory with FastAPI dependency injection
- Seed data script for development environment
- Indices for known query patterns (workflow by owner, runs by workflow, runs by status)

### OUT
- Application-level caching with Redis (Track 06_event_system)
- Full-text search indices (deferred -- consider later CQRS trigger)
- API endpoints that read/write these models (Track 05_api_layer)
- User authentication logic (Track 03_auth_system -- this track only defines the user table schema)
- Data archival and retention automation (backlog)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. ORM approach: SQLAlchemy sync vs async engine? Declarative mapping vs imperative mapping?
   Trade-off: async (better concurrency) vs sync (simpler debugging, wider library support)
2. Migration strategy: Alembic autogenerate vs hand-written migrations?
   Trade-off: speed of development (autogenerate) vs explicit control and reviewability (hand-written)
3. UUID generation: server-side (`gen_random_uuid()` in PostgreSQL) vs client-side (Python `uuid4()`)?
   Trade-off: database consistency + no round-trip vs application-level control + testability
4. Outbox polling: dedicated background service vs in-process background thread?
   Trade-off: operational complexity (separate process) vs coupling + failure isolation (in-process)
5. Seed data approach: factory_boy fixtures vs raw SQL scripts vs Python seed script?
   Trade-off: composability + test reuse (factory_boy) vs simplicity (SQL) vs flexibility (Python script)
6. Connection pool sizing: fixed pool vs auto-scaling? What pool_size and max_overflow for MVP?
   Trade-off: predictable resource usage (fixed) vs elasticity under load (auto-scaling)

## Architectural Notes

- The outbox table is critical infrastructure for Track 06_event_system's relay process. The schema must include `aggregate_type`, `aggregate_id`, `event_type`, `payload` (JSONB), `created_at`, and a nullable `published_at` column that the relay uses to track delivery state.
- The session factory (`get_db_session`) will be imported by every API track (03, 04, 05) as a FastAPI dependency. Design it so consumers don't need to know about engine configuration or pool internals.
- The schema must support Track 04_workflow_engine's state machine: `workflow_runs.status` needs an enum with at least `pending`, `running`, `completed`, `failed`, `cancelled` -- and `run_step_logs` needs an `attempt` counter for retry tracking.
- All models should include `created_at` and `updated_at` timestamp columns with server defaults to support consistent auditing across the system.

## Complexity: M
## Estimated Phases: ~3
