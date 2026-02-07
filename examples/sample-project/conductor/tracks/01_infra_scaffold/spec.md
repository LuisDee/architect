<!-- ARCHITECT CONTEXT v2 | Track: 01_infra_scaffold | Wave: 1 | CC: v1 -->

## Constraints (filtered for this track)

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

### Publishes
- None

### Subscribes
- None

## Dependencies

- None (Wave 1 — no prior tracks)

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

# Track 01_infra_scaffold: Infrastructure Scaffold

## Overview

Sets up the project foundation: Docker Compose for local development, CI/CD pipelines, Python backend structure, React frontend scaffold, and shared configuration. Every other track depends on this infrastructure being in place. Wave 1 — no dependencies.

## Scope

### In Scope
- Docker Compose configuration with PostgreSQL 16, Redis 7, backend (FastAPI), and frontend (React) services
- GitHub Actions CI/CD pipeline (lint, test, build stages)
- Python backend project structure: `backend/` with `app/`, `common/`, `tests/` directories
- React frontend project scaffold: `frontend/` with Vite, TypeScript, React Router
- Makefile with targets: dev, test, lint, format, migrate, build
- Environment configuration via pydantic-settings with `.env` and `.env.example`
- Pre-commit hook configuration (ruff, mypy, eslint, prettier)
- Health check endpoint scaffolds (/healthz, /readyz)

### Out of Scope
- Database schema and migrations (Track 02_database_schema)
- Authentication middleware (Track 03_auth_system)
- OTel collector and Grafana dashboards (Track 08_observability)
- Production Kubernetes manifests (deferred)
- Nginx reverse proxy configuration (deferred)

## Technical Approach

Using Docker Compose for local orchestration with hot-reload for both backend and frontend. Backend follows a modular package structure under `backend/app/` with routers, services, and models directories. Frontend bootstrapped with Vite + React + TypeScript. Shared configuration pattern: pydantic-settings `Settings` class reads from environment variables with `.env` fallback. CI pipeline runs in GitHub Actions with parallel lint and test stages, then a build stage for Docker images. Makefile wraps docker compose commands for ergonomic local development.

## Acceptance Criteria

1. `make dev` starts all services (PostgreSQL, Redis, backend, frontend) and they become healthy
2. Backend responds to `GET /healthz` with `200 OK`
3. Frontend loads in browser at `http://localhost:5173`
4. `make test` runs both backend (pytest) and frontend (Vitest) test suites
5. `make lint` runs ruff + mypy (backend) and eslint + prettier (frontend) with zero errors on scaffold code
6. GitHub Actions workflow runs successfully on push to any branch
7. `.env.example` documents all required environment variables
8. Pre-commit hooks catch formatting issues before commit

## Cross-Cutting Compliance

- Observability: OTel SDK imported in base FastAPI app, structlog configured as default logger
- Error Handling: `backend/common/errors.py` defines base exception classes and RFC 7807 error response model
- Health Checks: `/healthz` returns 200 (liveness), `/readyz` checks PostgreSQL and Redis connectivity
- Testing: pytest and Vitest configured with coverage reporting, CI enforces 80% gate
- Config Management: pydantic-settings `Settings` class with validation, `.env` for local dev

<!-- END ARCHITECT GENERATED -->

<!-- USER ADDITIONS — preserved across regenerations -->

<!-- END USER ADDITIONS -->
