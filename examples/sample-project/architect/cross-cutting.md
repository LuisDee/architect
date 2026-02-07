# Cross-Cutting Concerns

> This file is **append-only**. New versions are added below existing ones.
> Never modify a published version — add a new version section instead.
> Each version is tagged to the wave where it was introduced.

---

## v1 — Initial (Wave 1)

### Observability
- OpenTelemetry SDK for traces and metrics on all services
- structlog for Python backend with JSON output, trace_id/span_id injection
- Health checks: `/healthz` (liveness, no dependency checks), `/readyz` (readiness, includes PostgreSQL + Redis)
- Grafana + Loki for log aggregation, base dashboards for latency/errors/health
- Applies to: ALL
- Source: Architecture research (strongly recommended) + tech-stack.md

### Error Handling
- RFC 7807 Problem Details format for all API error responses
- Errors logged with trace_id for correlation
- No stack traces in production responses
- Domain exceptions extend `AppError` base class with error codes
- Applies to: ALL services with HTTP endpoints
- Source: Cross-cutting catalog (always evaluate)

### Transactional Outbox
- All domain event publishing through outbox table
- Events and state changes written in the same database transaction
- Outbox relay polls every 500ms and publishes to Redis pub/sub
- Dead letter queue for failed deliveries
- Applies to: ALL services that publish domain events (Tracks 04, 05, 06)
- Source: Architecture research (accepted by developer, ADR-002)

### API Conventions
- RESTful endpoints with envelope responses: `{ "data": ..., "meta": { "cursor": ..., "has_more": ... } }`
- Cursor-based pagination for all list endpoints
- snake_case for JSON fields
- ISO 8601 for all timestamps
- API versioning via URL path prefix (`/v1/`)
- Applies to: ALL HTTP APIs
- Source: Architecture research

### Testing
- TDD approach: write tests before implementation
- 80% code coverage minimum, enforced in CI
- Integration tests for API boundaries, database operations, and event handlers
- Test fixtures use factory pattern (factory_boy)
- Applies to: ALL
- Source: Cross-cutting catalog (always evaluate)

### Connection Pooling
- SQLAlchemy async connection pool: pool_size=10, max_overflow=10, pool_recycle=1800, pool_timeout=30
- Redis connection pool: max_connections=20
- All connections health-checked before use
- Applies to: ALL services accessing PostgreSQL or Redis
- Source: Cross-cutting catalog (always evaluate)

---

<!-- NEW VERSIONS APPENDED BELOW
     Format for additions:

## v1.1 — Discovery (Wave N, Track TRACK_ID)

### Concern Name (NEW)
Description
- Applies to: SCOPE
- Source: Discovery DISCOVERY_ID from Track TRACK_ID

### Existing Concern (MODIFIED)
What changed
- Applies to: SCOPE
- Source: Discovery DISCOVERY_ID

### Retroactive Compliance
| Track | State at time of change | Action |
|-------|-------------------------|--------|
| TRACK | completed | PATCH_REQUIRED — Phase P_ID added to plan.md |
| TRACK | in_progress | MID_TRACK_ADOPTION via constraint-update-check hook |
| TRACK | new | AUTO_INHERIT via context header regeneration |

-->
