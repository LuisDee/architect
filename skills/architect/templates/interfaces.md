# Interface Contracts

> Track-to-track API and event contracts. Each interface has exactly one owner.
> Consumers implement against this specification. Mismatches are INTERFACE_MISMATCH discoveries.
>
> Updated by: `/architect-decompose` (initial), `/architect-sync` (discovery-driven changes)

---

## REST Endpoints

### {{TRACK_ID}}: {{TRACK_NAME}}

**Base path:** `/v1/{{resource}}`

| Method | Path | Description | Request Body | Response | Auth |
|--------|------|-------------|-------------|----------|------|
| {{METHOD}} | {{PATH}} | {{DESC}} | {{REQ}} | {{RES}} | {{AUTH}} |

<!-- Example:

### 04_api_core: Core Resource API

**Base path:** `/v1/resources`

| Method | Path | Description | Request Body | Response | Auth |
|--------|------|-------------|-------------|----------|------|
| POST | /v1/resources | Create resource | `{ name, type, config }` | `{ data: Resource }` | Bearer |
| GET | /v1/resources | List resources | — | `{ data: Resource[], meta: { cursor, has_more } }` | Bearer |
| GET | /v1/resources/{id} | Get by ID | — | `{ data: Resource }` | Bearer |
| PUT | /v1/resources/{id} | Update resource | `{ name?, config? }` | `{ data: Resource }` | Bearer |
| DELETE | /v1/resources/{id} | Delete resource | — | `204 No Content` | Bearer |

**Consumed by:** Track 05_frontend, Track 09_workflows

-->

---

## Event Contracts

### {{TRACK_ID}}: {{EVENT_NAMESPACE}}

| Event | Payload | Published When |
|-------|---------|---------------|
| {{EVENT_NAME}} | `{ {{FIELDS}} }` | {{TRIGGER}} |

<!-- Example:

### 04_api_core: resource.*

| Event | Payload | Published When |
|-------|---------|---------------|
| resource.created | `{ resource_id, type, created_by, timestamp }` | After successful POST /v1/resources |
| resource.updated | `{ resource_id, changed_fields[], updated_by, timestamp }` | After successful PUT /v1/resources/{id} |
| resource.deleted | `{ resource_id, deleted_by, timestamp }` | After successful DELETE /v1/resources/{id} |

**Published via:** Transactional outbox
**Consumed by:** Track 09_workflows (resource.created), Track 13_notifications (resource.*)

-->

---

## Shared Data Schemas

### {{SCHEMA_NAME}}

```json
{
  "{{field_1}}": "{{type}} — {{description}}",
  "{{field_2}}": "{{type}} — {{description}}"
}
```

<!-- Example:

### Resource (shared read schema)

```json
{
  "id": "uuid — Unique identifier",
  "name": "string — Display name (1-255 chars)",
  "type": "enum(compute|storage|network) — Resource category",
  "config": "object — Type-specific configuration",
  "status": "enum(active|inactive|error) — Current state",
  "created_by": "uuid — User ID of creator",
  "created_at": "datetime — ISO 8601",
  "updated_at": "datetime — ISO 8601"
}
```

**Owned by:** Track 04_api_core
**Used by:** Track 05_frontend (display), Track 09_workflows (execution context)

### Pagination Meta

```json
{
  "cursor": "string|null — Opaque cursor for next page",
  "has_more": "boolean — Whether more results exist",
  "total_count": "integer|null — Total count (only if requested via ?count=true)"
}
```

**Owned by:** Convention (cross-cutting)
**Used by:** All tracks with list endpoints

-->

---

## Contract Change Protocol

When an interface needs to change:

1. Owner proposes change in interfaces.md
2. All consumers listed under the interface are checked:
   - new: auto-inherit via header regeneration
   - in_progress: flag for developer review
   - completed: INTERFACE_MISMATCH discovery → patch phase if needed
3. Breaking changes require developer approval before applying
