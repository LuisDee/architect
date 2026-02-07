# Track 01_infra_scaffold: Infrastructure Scaffold — Implementation Plan

> **Complexity:** M
> **Wave:** 1
> **Dependencies:** None
> **CC Version at generation:** v1

---

## Phase 1: Backend Scaffold

**Goal:** Python backend project structure exists with FastAPI app, configuration, and health check endpoints.

### Tasks

- [ ] Task 1.1: Create backend directory structure
  - Done when: `backend/app/`, `backend/app/routers/`, `backend/app/services/`, `backend/app/models/`, `backend/common/`, and `backend/tests/` directories exist with `__init__.py` files
- [ ] Task 1.2: Set up FastAPI application with configuration
  - Done when: `backend/app/main.py` creates FastAPI app, `backend/app/config.py` uses pydantic-settings to load from environment, `.env.example` lists all variables
- [ ] Task 1.3: Implement health check endpoints
  - Done when: `GET /healthz` returns `{"status": "ok"}`, `GET /readyz` returns `{"status": "ok", "checks": {"postgres": "...", "redis": "..."}}` (stubs for now, real checks in later tracks)
- [ ] Task 1.4: Set up structlog and base error handling
  - Done when: `backend/common/logging.py` configures structlog with JSON output, `backend/common/errors.py` defines `AppError` base class and RFC 7807 `ProblemDetail` Pydantic model, exception handler registered on FastAPI app
- [ ] Task 1.5: Configure pytest with async support
  - Done when: `backend/tests/conftest.py` sets up async test client (httpx), `pytest.ini` or `pyproject.toml` configures pytest-asyncio, `backend/tests/test_health.py` tests both endpoints

### Phase 1 Validation
- [ ] Cross-cutting compliance check (read architect/cross-cutting.md, verify applicable constraints)
- [ ] Tests passing: `pytest backend/tests/ -v`
- [ ] Conductor — User Manual Verification 'Phase 1'

---

## Phase 2: Frontend Scaffold

**Goal:** React frontend project exists with routing, dev server, and basic page structure.

### Tasks

- [ ] Task 2.1: Scaffold React project with Vite
  - Done when: `frontend/` directory has Vite + React + TypeScript config, `npm install` succeeds, `npm run dev` starts dev server on port 5173
- [ ] Task 2.2: Set up React Router with placeholder pages
  - Done when: Routes defined for `/` (dashboard), `/workflows` (list), `/workflows/:id` (detail), `/settings`, pages render placeholder text
- [ ] Task 2.3: Configure Zustand store scaffold
  - Done when: `frontend/src/stores/` directory exists with an empty auth store and workflow store stub
- [ ] Task 2.4: Set up Axios with base configuration
  - Done when: `frontend/src/api/client.ts` creates Axios instance with base URL from env, request/response interceptors for auth token injection and error handling
- [ ] Task 2.5: Configure Vitest with React Testing Library
  - Done when: `vitest.config.ts` configured, `frontend/src/__tests__/App.test.tsx` passes, `npm run test` works

### Phase 2 Validation
- [ ] Cross-cutting compliance check
- [ ] Tests passing: `cd frontend && npm run test`
- [ ] Conductor — User Manual Verification 'Phase 2'

---

## Phase 3: Docker & CI/CD

**Goal:** Docker Compose starts all services, CI pipeline runs lint and test stages, Makefile provides ergonomic commands.

### Tasks

- [ ] Task 3.1: Create Docker Compose configuration
  - Done when: `docker-compose.yml` defines services: postgres (port 5432), redis (port 6379), backend (port 8000, hot-reload), frontend (port 5173, hot-reload), with health checks on all services
- [ ] Task 3.2: Write Dockerfiles for backend and frontend
  - Done when: `backend/Dockerfile` builds Python app with multi-stage build, `frontend/Dockerfile` builds React app, both use non-root users
- [ ] Task 3.3: Create Makefile
  - Done when: Targets exist for `dev` (compose up), `down` (compose down), `test` (run all tests), `lint` (run all linters), `format` (auto-fix formatting), `migrate` (run alembic — stub for now), `build` (build images), `clean` (remove volumes)
- [ ] Task 3.4: Set up GitHub Actions CI pipeline
  - Done when: `.github/workflows/ci.yml` runs on push/PR with parallel jobs: lint (ruff + mypy + eslint), test-backend (pytest), test-frontend (Vitest), build (Docker build)
- [ ] Task 3.5: Configure pre-commit hooks
  - Done when: `.pre-commit-config.yaml` runs ruff, mypy, eslint, prettier on staged files, `pre-commit install` works

### Phase 3 Validation
- [ ] Cross-cutting compliance check
- [ ] Tests passing: `make test`
- [ ] `make dev` starts all services and they pass health checks
- [ ] Conductor — User Manual Verification 'Phase 3'

---

## Final Validation

- [ ] All phases complete
- [ ] Full test suite passing: `make test`
- [ ] Cross-cutting compliance verified for CC version v1
- [ ] No BLOCKING discoveries in pending/
- [ ] Conductor — User Manual Verification 'Track 01_infra_scaffold'

<!-- PATCH PHASES APPENDED BELOW
     When cross-cutting changes require retroactive compliance on a completed track,
     patch phases are appended here by /architect-sync.
     See templates/patch-phase.md for the format.
-->
