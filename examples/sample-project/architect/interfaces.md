# Interface Contracts

> Track-to-track API and event contracts. Each interface has exactly one owner.
> Consumers implement against this specification. Mismatches are INTERFACE_MISMATCH discoveries.
>
> Updated by: `/architect-decompose` (initial), `/architect-sync` (discovery-driven changes)

---

## REST Endpoints

### 03_auth_system: Authentication API

**Base path:** `/v1/auth`

| Method | Path | Description | Request Body | Response | Auth |
|--------|------|-------------|-------------|----------|------|
| POST | /v1/auth/register | Register new user | `{ email, name, password }` | `{ data: { user, tokens } }` | None |
| POST | /v1/auth/login | Login | `{ email, password }` | `{ data: { user, tokens } }` | None |
| POST | /v1/auth/refresh | Refresh access token | `{ refresh_token }` | `{ data: { access_token } }` | None |
| GET | /v1/auth/me | Get current user | — | `{ data: User }` | Bearer |
| POST | /v1/auth/password-reset | Request password reset | `{ email }` | `204 No Content` | None |
| POST | /v1/auth/password-reset/confirm | Confirm reset | `{ token, new_password }` | `204 No Content` | None |

**Consumed by:** Track 05_api_layer (middleware), Track 07_react_frontend (login/register pages)

### 05_api_layer: Workflow API

**Base path:** `/v1/workflows`

| Method | Path | Description | Request Body | Response | Auth |
|--------|------|-------------|-------------|----------|------|
| POST | /v1/workflows | Create workflow | `{ name, description, trigger_type, trigger_config, steps[] }` | `{ data: Workflow }` | Bearer |
| GET | /v1/workflows | List workflows | — | `{ data: Workflow[], meta: { cursor, has_more } }` | Bearer |
| GET | /v1/workflows/{id} | Get workflow | — | `{ data: Workflow }` | Bearer |
| PUT | /v1/workflows/{id} | Update workflow | `{ name?, description?, steps[]? }` | `{ data: Workflow }` | Bearer |
| DELETE | /v1/workflows/{id} | Delete workflow | — | `204 No Content` | Bearer (admin/owner) |
| POST | /v1/workflows/{id}/trigger | Trigger execution | `{ input_data? }` | `{ data: WorkflowRun }` | Bearer |

**Consumed by:** Track 07_react_frontend

### 05_api_layer: Workflow Run API

**Base path:** `/v1/runs`

| Method | Path | Description | Request Body | Response | Auth |
|--------|------|-------------|-------------|----------|------|
| GET | /v1/workflows/{id}/runs | List runs for workflow | — | `{ data: Run[], meta: { cursor, has_more } }` | Bearer |
| GET | /v1/runs/{id} | Get run detail | — | `{ data: Run (with step_logs) }` | Bearer |
| POST | /v1/runs/{id}/cancel | Cancel running execution | — | `{ data: Run }` | Bearer |

**Consumed by:** Track 07_react_frontend

### 05_api_layer: Webhook Ingestion

**Base path:** `/v1/webhooks`

| Method | Path | Description | Request Body | Response | Auth |
|--------|------|-------------|-------------|----------|------|
| POST | /v1/webhooks/{webhook_id} | Receive webhook trigger | Any JSON | `202 Accepted` | API Key (query param or header) |

**Consumed by:** External systems

---

## Event Contracts

### 04_workflow_engine: workflow.*

| Event | Payload | Published When |
|-------|---------|---------------|
| workflow.started | `{ run_id, workflow_id, triggered_by, timestamp }` | Workflow execution begins |
| workflow.completed | `{ run_id, workflow_id, duration_ms, timestamp }` | All steps completed successfully |
| workflow.failed | `{ run_id, workflow_id, failed_step_id, error, timestamp }` | Step exhausted retries or unrecoverable error |

**Published via:** Transactional outbox
**Consumed by:** Track 08_observability (metrics), Track 07_react_frontend (polling for status)

### 04_workflow_engine: step.*

| Event | Payload | Published When |
|-------|---------|---------------|
| step.started | `{ run_id, step_id, attempt, timestamp }` | Step execution begins (including retries) |
| step.completed | `{ run_id, step_id, attempt, duration_ms, output_summary, timestamp }` | Step finishes successfully |
| step.failed | `{ run_id, step_id, attempt, error, will_retry, timestamp }` | Step fails (may retry) |

**Published via:** Transactional outbox
**Consumed by:** Track 08_observability (metrics), Track 07_react_frontend (run detail polling)

### 03_auth_system: user.*

| Event | Payload | Published When |
|-------|---------|---------------|
| user.created | `{ user_id, email, role, timestamp }` | New user registered |
| user.deleted | `{ user_id, email, timestamp }` | User account deleted |

**Published via:** Transactional outbox
**Consumed by:** Track 04_workflow_engine (cascade-cancel active runs on user delete)

---

## Shared Data Schemas

### User (read schema)

```json
{
  "id": "uuid — Unique identifier",
  "email": "string — Email address",
  "name": "string — Display name",
  "role": "enum(admin|developer|viewer) — RBAC role",
  "is_active": "boolean — Account active flag",
  "created_at": "datetime — ISO 8601"
}
```

**Owned by:** Track 03_auth_system
**Used by:** Track 05_api_layer (response serialization), Track 07_react_frontend (display)

### Workflow (read schema)

```json
{
  "id": "uuid — Unique identifier",
  "name": "string — Workflow name (1-255 chars)",
  "description": "string|null — Optional description",
  "trigger_type": "enum(manual|webhook|schedule) — How this workflow is triggered",
  "trigger_config": "object|null — Trigger-specific config (cron expression, webhook secret)",
  "is_active": "boolean — Whether workflow accepts triggers",
  "steps": "WorkflowStep[] — Ordered list of steps",
  "owner_id": "uuid — User who created it",
  "created_at": "datetime — ISO 8601",
  "updated_at": "datetime — ISO 8601"
}
```

**Owned by:** Track 05_api_layer
**Used by:** Track 07_react_frontend (builder + list), Track 04_workflow_engine (execution)

### WorkflowRun (read schema)

```json
{
  "id": "uuid — Unique identifier",
  "workflow_id": "uuid — Parent workflow",
  "triggered_by": "string — user:{id} or webhook:{id} or schedule",
  "status": "enum(pending|running|completed|failed|cancelled) — Current state",
  "started_at": "datetime|null — When execution began",
  "completed_at": "datetime|null — When execution finished",
  "error_message": "string|null — Error details if failed",
  "step_logs": "RunStepLog[] — Per-step execution logs (included in detail view)"
}
```

**Owned by:** Track 05_api_layer
**Used by:** Track 07_react_frontend (run monitor)

### Pagination Meta

```json
{
  "cursor": "string|null — Opaque cursor for next page",
  "has_more": "boolean — Whether more results exist"
}
```

**Owned by:** Convention (cross-cutting)
**Used by:** All tracks with list endpoints

---

## Contract Change Protocol

When an interface needs to change:

1. Owner proposes change in interfaces.md
2. All consumers listed under the interface are checked:
   - new: auto-inherit via header regeneration
   - in_progress: flag for developer review
   - completed: INTERFACE_MISMATCH discovery → patch phase if needed
3. Breaking changes require developer approval before applying
