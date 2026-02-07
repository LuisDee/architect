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
Sets up the foundational project structure, Docker Compose environment,
database initialization, and CI/CD pipeline.

## Scope
IN:
- Docker Compose with PostgreSQL 16, Redis 7, and app service
- Database initialization scripts and migration framework
- Environment configuration (.env template + validation)
- CI/CD pipeline (GitHub Actions: lint, test, build)

OUT:
- Application code (handled by downstream tracks)
- Authentication (Track 02)

## Key Design Decisions
1. **Migration framework:** Alembic vs raw SQL migrations?
   Trade-off: ORM coupling vs explicit control.
2. **Docker strategy:** Single Dockerfile vs multi-stage?
   Trade-off: Build speed vs image size.
3. **CI provider:** GitHub Actions vs GitLab CI?
   Trade-off: Ecosystem integration vs self-hosting.
4. **Database pooling:** PgBouncer vs SQLAlchemy pool?
   Trade-off: External dependency vs simpler stack.

## Architectural Notes
- Track 03 depends on the database configuration this track establishes
- CI pipeline must be extensible for downstream tracks

## Complexity: M
## Estimated Phases: ~3
