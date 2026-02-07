<!-- ARCHITECT CONTEXT v2 | Track: 03_auth_system | Wave: 3 | CC: v1 -->
<!-- Full context header omitted for brevity — see tracks 01/02 for full examples -->

# Track 03_auth_system: Authentication & Authorization

## Overview

Implements JWT-based authentication (access + refresh tokens), bcrypt password hashing, role-based access control (admin/developer/viewer), and FastAPI middleware for route protection. Provides the auth endpoints and middleware consumed by all API tracks. Wave 3 — depends on infrastructure scaffold and database schema (user/api_key tables).

## Scope

### In Scope
- JWT token generation (access: 15min, refresh: 7 days) and validation
- Password hashing with bcrypt, login/register/refresh endpoints
- RBAC middleware with role hierarchy: admin > developer > viewer
- API key authentication for programmatic access
- Auth FastAPI dependency (`get_current_user`)
- Password reset flow (token-based)

### Out of Scope
- OAuth/SSO providers (backlog)
- Multi-factor authentication (backlog)
- User management UI (Track 07_react_frontend)

## Technical Approach

python-jose for JWT, passlib[bcrypt] for hashing. Middleware checks `Authorization: Bearer <token>` header, decodes JWT, loads user from DB. RBAC uses a `require_role(minimum_role)` dependency. API keys hashed with SHA-256, looked up on each request as alternative auth path.

## Acceptance Criteria

1. `POST /v1/auth/register` creates user, returns tokens
2. `POST /v1/auth/login` validates credentials, returns tokens
3. `POST /v1/auth/refresh` issues new access token from valid refresh token
4. `GET /v1/auth/me` returns current user (requires auth)
5. Protected endpoints return 401 without valid token
6. Role-restricted endpoints return 403 for insufficient role
7. API key auth works as alternative to JWT
