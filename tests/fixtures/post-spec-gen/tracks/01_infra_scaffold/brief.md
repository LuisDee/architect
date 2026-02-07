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

# Track 01: Infrastructure Scaffold

## What This Track Delivers
Sets up the foundational project structure.

## Scope
IN:
- Docker Compose setup

OUT:
- Application code

## Key Design Decisions
1. **Migration framework:** Alembic vs raw SQL?

## Complexity: M
## Estimated Phases: ~3
