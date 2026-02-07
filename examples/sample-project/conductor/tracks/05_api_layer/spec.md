<!-- ARCHITECT CONTEXT v2 | Track: 05_api_layer | Wave: 4 | CC: v1 -->
<!-- Full context header omitted for brevity — see tracks 01/02 for full examples -->

# Track 05_api_layer: REST API Layer

## Overview

FastAPI REST endpoints for all FlowForge resources: workflows (CRUD + trigger), workflow runs (list + detail + cancel), templates, and team management. Wires together auth middleware, database models, workflow engine, and event system into a cohesive API surface. Wave 4 — depends on database schema, auth, workflow engine, and event system.

## Scope

### In Scope
- Workflow CRUD: create, read, update, delete, list (cursor pagination)
- Workflow triggers: manual trigger, webhook endpoint, schedule registration
- Run management: list runs by workflow, get run detail with step logs, cancel run
- Template CRUD: reusable step templates
- OpenAPI schema auto-generation with proper descriptions
- Request validation via Pydantic v2 models
- Envelope responses: `{ "data": ..., "meta": { "cursor": ..., "has_more": ... } }`

### Out of Scope
- Frontend (Track 07_react_frontend)
- Workflow execution logic (Track 04_workflow_engine — this track only calls it)
- Admin/team management endpoints (backlog)

## Acceptance Criteria

1. All CRUD endpoints return correct status codes and envelope responses
2. Cursor pagination works on list endpoints
3. `POST /v1/workflows/{id}/trigger` starts a workflow execution
4. `POST /v1/webhooks/{webhook_id}` triggers associated workflow
5. Auth required on all endpoints, RBAC enforced per route
6. OpenAPI spec matches all endpoint contracts in interfaces.md
