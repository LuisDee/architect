# Track Brief Template
#
# Usage: Architect generates one brief.md per track during /architect-decompose.
# The brief is the handoff artifact from Architect to Conductor. When the developer
# runs /conductor:implement, Conductor reads brief.md and uses it to drive interactive
# spec and plan generation — asking better design questions because it has
# architectural context.
#
# Architect DOES NOT generate spec.md or plan.md. Conductor does that interactively
# with developer input.
#
# Placeholders: {track_id}, {track_number}, {track_name}, {wave}, {cc_version},
# {filtered_constraints}, {interfaces_owned}, {interfaces_consumed},
# {direct_dependencies}, {one_paragraph_description}, {scope_in}, {scope_out},
# {design_decisions}, {architectural_notes}, {complexity}, {estimated_phases}
#
# ---
# CRITICAL: Brief vs Spec — Guidance for the Generating Agent
#
# You are generating a BRIEF, not a spec. A brief tells Conductor what the track
# is about and what to ask the developer. It does NOT make design decisions.
#
# WRONG (making decisions):
#   "Use SQLAlchemy 2.0 async with Alembic for migrations"
#   "Spawn the user's default shell by reading $SHELL"
#   "FR-1: Dedicated reader thread performs blocking read()..."
#
# RIGHT (identifying the decision):
#   "ORM/migration strategy: SQLAlchemy sync vs async? Alembic vs raw SQL migrations?"
#   "Shell spawning: $SHELL vs hardcoded path? Fallback behavior on missing shell?"
#   "Threading model: dedicated reader thread vs async I/O? Reader-only vs reader+writer?"
#
# The developer will make these choices when Conductor asks them during spec generation.
# Your job is to identify WHAT needs deciding, not to decide it.
#
# Rules:
# - Scope IN/OUT: concrete boundaries, not implementation details
# - Design Decisions: genuine forks where reasonable people would disagree
# - Architectural Notes: things the implementing agent MUST know from the architecture
#   (integration points, cross-track dependencies, gotchas)
# - Do NOT include functional requirements, task lists, or phase breakdowns
# ---

<!-- ARCHITECT CONTEXT | Track: {track_id} | Wave: {wave} | CC: {cc_version} -->

## Cross-Cutting Constraints
{filtered_constraints}

<!-- Only constraints relevant to this track. Example:
- Observability: OTel SDK on all endpoints, structlog for Python
- Errors: RFC 7807 Problem Details, errors logged with trace ID
- Testing: TDD, 80% coverage, integration tests for API boundaries
-->

## Interfaces

### Owns
{interfaces_owned}

<!-- Endpoints/events this track produces. Example:
- POST /v1/workflows — Create workflow
- GET /v1/workflows — List workflows (cursor pagination)
- workflow.created { workflow_id, owner_id, timestamp }
-->

### Consumes
{interfaces_consumed}

<!-- Endpoints/events from other tracks this track depends on. Example:
- GET /v1/auth/me (Track 03_auth) — Current user context
- user.deleted (Track 03_auth) — Cascade-delete user's workflows
-->

## Dependencies
{direct_dependencies}

<!-- What this track needs from other tracks. Example:
- Track 01_infra_scaffold: Docker Compose + base images must be available
- Track 02_database_schema: User and Workflow models must be importable
-->

<!-- END ARCHITECT CONTEXT -->

# Track {track_number}: {track_name}

## What This Track Delivers

{one_paragraph_description}

<!-- One paragraph: what this track delivers, why it matters, and where it sits
     in the overall system. Keep it to 2-4 sentences. -->

## Scope

### IN
{scope_in}

<!-- Bulleted list of what this track covers. Be specific about boundaries.
     Example:
     - JWT token generation and validation (access + refresh)
     - Password hashing and verification
     - RBAC middleware with role hierarchy
     - API key authentication as alternative auth path
     - Auth-related database queries (user lookup, token storage)
-->

### OUT
{scope_out}

<!-- Bulleted list of what this track explicitly does NOT cover, with pointers.
     Example:
     - OAuth/SSO providers (backlog — not needed for MVP)
     - User management UI (Track 07_react_frontend)
     - User table schema definition (Track 02_database_schema — this track uses it)
     - Rate limiting on auth endpoints (Track 05_api_layer)
-->

## Key Design Decisions

These should be resolved with the developer during spec generation:

{design_decisions}

<!-- Numbered list of genuine design forks. Each decision should name the area,
     present the options, and note the trade-off. Conductor will ask the developer
     about each one.

     Example:
     1. Token storage: httpOnly cookies vs localStorage?
        Trade-off: XSS protection vs simpler client implementation
     2. Refresh token rotation: rotate on every use vs fixed expiry?
        Trade-off: security (leaked tokens expire faster) vs simplicity
     3. RBAC granularity: role-based (admin/user) vs permission-based (can_edit, can_delete)?
        Trade-off: simplicity vs flexibility for future permission needs
     4. Password policy: enforce complexity rules vs minimum length only?
        Trade-off: security vs user friction at MVP stage
     5. API key scope: global access vs per-endpoint scopes?
        Trade-off: simplicity vs principle of least privilege

     Aim for 3-7 decisions per track. If you can't find at least 3,
     the track may be too small or too well-constrained to need decisions.
-->

## Architectural Notes

{architectural_notes}

<!-- 2-5 bullets of things the implementing agent needs to know from the
     architecture. Focus on integration points, cross-track impacts, and gotchas.

     Example:
     - Auth middleware will be consumed by every API track — design the
       dependency injection so tracks can import `get_current_user` without
       coupling to auth internals
     - Track 07_react_frontend needs token refresh to be transparent to API calls
       (Axios interceptor pattern) — keep the refresh endpoint contract simple
     - If OAuth/SSO is added later (backlog), the auth module must support
       multiple identity providers — consider this in the user model design
       even if only password auth is implemented now
     - The API key auth path must work for webhook triggers (Track 05_api_layer)
       where JWT auth isn't practical
-->

## Test Strategy

{test_strategy}

<!-- Inferred from tech-stack.md. The brief-generator derives this based on
     the project's framework choices. Conductor may override during spec generation.

     Example:
     - **Test framework:** pytest (Python) + Vitest (TypeScript)
     - **Unit tests:** Business logic, utility functions, data transformations
     - **Integration tests:** API endpoint testing with test database
     - **Prerequisites:** Track 01_infra_scaffold (test database), Track 02_database_schema (models)
     - **Quality threshold:** 80% line coverage (advisory)
     - **Key test scenarios:**
       1. Happy path for each endpoint
       2. Authentication/authorization boundaries
       3. Input validation edge cases
       4. Error response format compliance

     This section is advisory — the developer makes final test strategy decisions
     during spec generation with Conductor.
-->

## Complexity: {complexity}
## Estimated Phases: ~{estimated_phases}

<!-- Complexity: S (1-2 days), M (3-5 days), L (1-2 weeks), XL (2+ weeks)
     Estimated Phases: how many implementation phases Conductor should plan for.
     Typical: S=2, M=3, L=3-4, XL=4-5. This is advisory — Conductor may adjust. -->
