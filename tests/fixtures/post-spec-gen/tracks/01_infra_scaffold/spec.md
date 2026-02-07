<!-- ARCHITECT CONTEXT | Track: 01_infra_scaffold | Wave: 1 | CC: v1.0 -->
## Cross-Cutting Constraints
- CC-01: All services must use structured JSON logging
- CC-03: Environment configuration via .env files, never hardcoded
## Interfaces
Owns: IInfraConfig (database connection, redis connection, env vars)
Consumes: None (Wave 1, no upstream dependencies)
## Dependencies
None
<!-- END ARCHITECT CONTEXT -->

# Track 01: Infrastructure Scaffold -- Specification

## Design Decisions (Resolved)
1. Migration framework: **Alembic**
2. Docker strategy: **Multi-stage**

## Functional Requirements
- FR-1: Docker Compose with PostgreSQL 16, Redis 7, app service
- FR-2: Alembic migration framework
