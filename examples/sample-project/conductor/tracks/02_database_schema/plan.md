# Track 02_database_schema: Database Schema & Migrations — Implementation Plan

> **Complexity:** M
> **Wave:** 2
> **Dependencies:** 01_infra_scaffold
> **CC Version at generation:** v1

---

## Phase 1: Alembic Setup & Core Tables

**Goal:** Alembic is configured for async, core SQLAlchemy models exist, and the initial migration creates all tables.

### Tasks

- [ ] Task 1.1: Configure Alembic for async SQLAlchemy
  - Done when: `alembic.ini` and `backend/app/migrations/env.py` are set up with `run_async`, `alembic revision --autogenerate -m "initial"` generates a migration
- [ ] Task 1.2: Define SQLAlchemy base and mixins
  - Done when: `backend/app/models/base.py` defines declarative base with `id` (UUID, server default), `created_at`, `updated_at` timestamp mixin
- [ ] Task 1.3: Create User and ApiKey models
  - Done when: `backend/app/models/user.py` defines `User` and `ApiKey` models matching schema spec, with proper relationships and constraints (unique email, cascade delete on API keys)
- [ ] Task 1.4: Create Workflow and WorkflowStep models
  - Done when: `backend/app/models/workflow.py` defines both models, `workflow_steps` has position ordering, `trigger_type` is an enum, `retry_policy` is JSONB
- [ ] Task 1.5: Create WorkflowRun and RunStepLog models
  - Done when: `backend/app/models/run.py` defines both models, `status` is an enum (pending, running, completed, failed, cancelled), `attempt` tracks retry count
- [ ] Task 1.6: Create Outbox model
  - Done when: `backend/app/models/outbox.py` defines outbox table with aggregate_type, aggregate_id, event_type, payload (JSONB), created_at, published_at (nullable)
- [ ] Task 1.7: Generate and verify initial migration
  - Done when: `alembic upgrade head` creates all tables, `alembic downgrade base` removes them cleanly

### Phase 1 Validation
- [ ] Cross-cutting compliance check (read architect/cross-cutting.md, verify applicable constraints)
- [ ] Tests passing: `pytest backend/tests/track_02/ -v -k "phase1"`
- [ ] Conductor — User Manual Verification 'Phase 1'

---

## Phase 2: Connection Pool & Session Management

**Goal:** Async engine with connection pooling is configured, FastAPI dependency injection provides database sessions.

### Tasks

- [ ] Task 2.1: Configure async engine with connection pooling
  - Done when: `backend/app/database.py` creates `AsyncEngine` with pool_size=10, max_overflow=10, pool_recycle=1800, pool_timeout=30, reads DATABASE_URL from Settings
- [ ] Task 2.2: Create session factory and FastAPI dependency
  - Done when: `get_db_session` async generator yields `AsyncSession`, properly commits on success and rolls back on exception, registered as FastAPI dependency
- [ ] Task 2.3: Update /readyz health check with real PostgreSQL check
  - Done when: `/readyz` executes `SELECT 1` through the pool and reports `"postgres": "ok"` or `"postgres": "error: <message>"`
- [ ] Task 2.4: Create domain exception wrappers
  - Done when: `backend/app/models/exceptions.py` catches `IntegrityError` → `ConflictError`, `NoResultFound` → `NotFoundError`, both extend `AppError` from common/errors.py

### Phase 2 Validation
- [ ] Cross-cutting compliance check
- [ ] Tests passing: `pytest backend/tests/track_02/ -v -k "phase2"`
- [ ] Conductor — User Manual Verification 'Phase 2'

---

## Phase 3: Indices, Seeds & Integration Tests

**Goal:** Query-pattern indices are in place, seed data script works, and integration tests verify the full stack.

### Tasks

- [ ] Task 3.1: Add indices for known query patterns
  - Done when: Indices exist on `workflows.owner_id`, `workflow_runs.workflow_id`, `workflow_runs.status`, `run_step_logs.run_id`, `outbox.published_at` (partial index WHERE NULL), new migration generated
- [ ] Task 3.2: Create seed data script
  - Done when: `backend/scripts/seed.py` creates 3 users (admin, developer, viewer), 5 workflows with steps, 10 sample runs with step logs, script is idempotent (truncate + reseed)
- [ ] Task 3.3: Write migration cycle integration tests
  - Done when: Test applies all migrations, verifies table existence, rolls back to base, reapplies — all clean
- [ ] Task 3.4: Write model and session integration tests
  - Done when: Tests create/read/update/delete for each model through AsyncSession, verify cascades work (delete user → delete API keys), verify outbox insert in same transaction as workflow create
- [ ] Task 3.5: Verify EXPLAIN output on indexed queries
  - Done when: Test runs EXPLAIN on key queries and asserts index scans (not seq scans) for filtered queries on indexed columns

### Phase 3 Validation
- [ ] Cross-cutting compliance check
- [ ] Tests passing: `pytest backend/tests/track_02/ -v`
- [ ] Coverage: `pytest backend/tests/track_02/ --cov=backend/app/models --cov-report=term-missing` shows >= 80%
- [ ] Conductor — User Manual Verification 'Phase 3'

---

## Final Validation

- [ ] All phases complete
- [ ] Full test suite passing: `pytest backend/tests/track_02/ -v`
- [ ] Cross-cutting compliance verified for CC version v1
- [ ] No BLOCKING discoveries in pending/
- [ ] Conductor — User Manual Verification 'Track 02_database_schema'

<!-- PATCH PHASES APPENDED BELOW
     When cross-cutting changes require retroactive compliance on a completed track,
     patch phases are appended here by /architect-sync.
     See templates/patch-phase.md for the format.
-->
