<!-- ARCHITECT CONTEXT | Track: 01_infra_scaffold | Wave: 1 | CC: v1 -->

## Cross-Cutting Constraints

- Observability: OTel SDK configured in base Docker images, structlog for Python services
- Error Handling: Standardize error response format in shared library (consumed by all API tracks)
- Health Checks: /healthz (liveness) and /readyz (readiness) endpoints on all services
- Testing: pytest + Vitest configured in CI, 80% coverage gate
- Config Management: Environment-based config via pydantic-settings, .env files for dev

## Interfaces

### Owns
- Docker Compose service definitions (PostgreSQL, Redis, backend, frontend)
- CI/CD pipeline (GitHub Actions workflows)
- Makefile targets (dev, test, lint, migrate, build)
- Shared Python package structure (`backend/common/`)

### Consumes
- None (foundation track)

## Dependencies

- None (Wave 1 -- no prior tracks)

<!-- END ARCHITECT CONTEXT -->

# Track 01: Infrastructure Scaffold

## What This Track Delivers

Sets up the entire project foundation: Docker Compose for local development, CI/CD pipelines, the Python backend directory structure with a shared `backend/common/` package, the React frontend scaffold, environment configuration, and developer-experience tooling (Makefile, pre-commit hooks). Every subsequent track builds on top of this infrastructure, making it the critical path for the entire project.

## Scope

### IN
- Docker Compose configuration with PostgreSQL, Redis, backend (FastAPI), and frontend (React) services
- CI/CD pipeline with lint, test, and build stages
- Python backend project structure: `backend/` with `app/`, `common/`, `tests/` directories
- React frontend project scaffold with TypeScript and routing
- Makefile with targets: dev, test, lint, format, migrate, build
- Environment configuration with `.env` and `.env.example`
- Pre-commit hook configuration (ruff, mypy, eslint, prettier)
- Health check endpoint scaffolds (/healthz, /readyz)

### OUT
- Database schema and migrations (Track 02_database_schema)
- Authentication middleware (Track 03_auth_system)
- OTel collector and Grafana dashboards (Track 08_observability)
- Production Kubernetes manifests (deferred)
- Nginx reverse proxy configuration (deferred)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. Backend structure: flat modules (`app/routers.py`, `app/services.py`) vs layered packages (`app/routers/`, `app/services/`, `app/models/`)?
   Trade-off: simplicity for small projects vs scalability as tracks add modules
2. Frontend build tool: Vite vs Next.js vs Create React App?
   Trade-off: Vite (fast, lightweight) vs Next.js (SSR, routing built-in) vs CRA (familiar but slow)
3. Docker strategy: multi-stage builds for dev and prod vs dev-only Dockerfiles with separate prod config later?
   Trade-off: upfront complexity vs deferred production readiness
4. CI pipeline: GitHub Actions vs GitLab CI? Parallel stages vs sequential?
   Trade-off: ecosystem integration vs pipeline speed vs simplicity
5. Config management: pydantic-settings vs python-dotenv vs raw `os.environ`?
   Trade-off: validation + type safety (pydantic) vs simplicity (dotenv) vs zero dependencies (os.environ)
6. Monorepo structure: single root with `backend/` and `frontend/` vs workspace-based (npm/poetry workspaces)?
   Trade-off: simplicity vs dependency isolation and independent versioning

## Architectural Notes

- `backend/common/` is the shared library imported by all subsequent tracks -- its error classes, logging config, and utilities become project-wide conventions. Design it for stability since changes here ripple everywhere.
- The frontend scaffold (routing, Axios client, store stubs) is consumed and extended by Track 07_react_frontend. Keep it minimal but structurally complete so Track 07 can add pages without restructuring.
- The CI pipeline defined here will be extended by every track that adds new test suites or lint rules. Design the workflow YAML for easy addition of parallel jobs.
- The Makefile and Docker Compose configuration are the primary developer interface for the entire project. Prioritize ergonomics and fast feedback loops (hot-reload, quick test runs).

## Complexity: M
## Estimated Phases: ~3
