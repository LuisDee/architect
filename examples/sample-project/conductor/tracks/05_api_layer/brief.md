<!-- ARCHITECT CONTEXT | Track: 05_api_layer | Wave: 4 | CC: v1 -->

## Cross-Cutting Constraints
- API Conventions: RESTful, envelope responses, cursor pagination, snake_case JSON
- Error Handling: RFC 7807 Problem Details format
- Observability: OTel traces on all HTTP requests
## Interfaces
Owns: /v1/workflows, /v1/runs, /v1/webhooks endpoints
Consumes: Auth middleware (Track 03), Workflow engine (Track 04), Database session (Track 02), Event publisher (Track 06)
## Dependencies
02_database_schema, 03_auth_system, 04_workflow_engine, 06_event_system

<!-- END ARCHITECT CONTEXT -->

# Track 05: REST API Layer

## What This Track Delivers

The FastAPI REST endpoints that expose all FlowForge resources to consumers: workflow CRUD and triggering, workflow run management, webhook ingestion, and template management. This track wires together auth middleware, database models, the workflow engine, and the event system into a cohesive, well-documented API surface with envelope responses and cursor pagination.

## Scope

### IN
- Workflow CRUD: create, read, update, delete, list (cursor pagination)
- Workflow triggers: manual trigger, webhook endpoint, schedule registration
- Run management: list runs by workflow, get run detail with step logs, cancel run
- Template CRUD for reusable step templates
- OpenAPI schema auto-generation with proper descriptions
- Request validation via Pydantic v2 models
- Envelope response format: `{ "data": ..., "meta": { "cursor": ..., "has_more": ... } }`

### OUT
- Frontend application (Track 07_react_frontend)
- Workflow execution logic (Track 04_workflow_engine -- this track only calls it)
- Admin/team management endpoints (backlog)
- Rate limiting and API throttling (backlog)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. Router organization: one router per resource vs feature-based grouping vs single large router?
   Trade-off: granularity of imports vs navigation simplicity vs co-location of related endpoints
2. Pagination: cursor-based vs offset-based? Opaque cursor vs encoded timestamp/ID?
   Trade-off: performance on large datasets (cursor) vs simplicity and random page access (offset)
3. Webhook validation: HMAC signature verification vs API key only vs both?
   Trade-off: security against replay attacks (HMAC) vs implementation simplicity (API key)
4. Response serialization: Pydantic response_model vs manual dict construction?
   Trade-off: automatic validation + OpenAPI accuracy (Pydantic) vs flexibility + performance (manual)
5. Error handling: per-router exception handlers vs global middleware?
   Trade-off: fine-grained control vs consistency and less boilerplate

## Architectural Notes

- All endpoint contracts are defined in `architect/interfaces.md`. The implementation must match those contracts exactly -- mismatches will be flagged as INTERFACE_MISMATCH discoveries.
- This track is the primary consumer of Track 03_auth_system's middleware, Track 02's session factory, and Track 04's engine. Integration testing here validates the full request lifecycle.
- The webhook endpoint must support API key auth (not JWT) since external systems cannot obtain JWT tokens.

## Complexity: L
## Estimated Phases: ~3
