<!-- ARCHITECT CONTEXT | Track: 03_auth_system | Wave: 3 | CC: v1 -->

# Track 03: Authentication & Authorization

## What This Track Delivers

Implements the complete authentication and authorization layer for FlowForge: JWT-based token authentication (access + refresh), password hashing, role-based access control with a three-tier hierarchy (admin/developer/viewer), API key authentication for programmatic access, and the FastAPI auth middleware that all protected endpoints consume. This track is the security gateway for every user-facing and API interaction.

## Scope

### IN
- JWT token generation and validation (access + refresh tokens)
- Password hashing and verification
- Login, register, refresh, and password reset endpoints
- RBAC middleware with role hierarchy (admin > developer > viewer)
- API key authentication as alternative auth path
- Auth FastAPI dependency (`get_current_user`)
- User-related event publishing (user.created, user.deleted)

### OUT
- OAuth/SSO providers (backlog)
- Multi-factor authentication (backlog)
- User management UI (Track 07_react_frontend)
- User table schema definition (Track 02_database_schema -- this track uses it)
- Rate limiting on auth endpoints (Track 05_api_layer)

## Key Design Decisions

These should be resolved with the developer during spec generation:

1. Token storage: httpOnly cookies vs Authorization header with localStorage/memory?
   Trade-off: XSS protection (cookies) vs simpler client implementation and API key compatibility (header)
2. Refresh token rotation: rotate on every use vs fixed expiry with long TTL?
   Trade-off: security against leaked tokens vs implementation simplicity
3. RBAC granularity: role-based (admin/developer/viewer) vs permission-based (can_edit, can_delete)?
   Trade-off: simplicity for MVP vs flexibility for future fine-grained permissions
4. JWT library: python-jose vs PyJWT vs authlib?
   Trade-off: feature set vs maintenance status vs dependency weight
5. API key scope: global access vs per-endpoint scoped keys?
   Trade-off: simplicity vs principle of least privilege for webhook/integration use cases

## Architectural Notes

- Auth middleware (`get_current_user`) will be imported by every API track as a FastAPI dependency. Design the interface so tracks can require authentication without coupling to auth internals (token format, storage mechanism).
- Track 07_react_frontend needs token refresh to be transparent to API calls (interceptor pattern). Keep the refresh endpoint contract simple and stateless.
- The API key auth path must work for webhook triggers (Track 05_api_layer) where JWT auth is not practical.

## Complexity: M
## Estimated Phases: ~3
