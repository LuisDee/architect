<!-- ARCHITECT CONTEXT | Track: 02_auth_system | Wave: 1 | CC: v1.0 -->
## Cross-Cutting Constraints
- CC-01: All services must use structured JSON logging
- CC-04: JWT-based authentication for all API endpoints
## Interfaces
Owns: IAuth (login, register, token refresh)
Consumes: None
## Dependencies
None
<!-- END ARCHITECT CONTEXT -->

# Track 02: Authentication System

## What This Track Delivers
Implements JWT-based authentication with login, registration, and token management.

## Scope
IN:
- User model and password hashing
- JWT token generation and validation
- Login and registration endpoints

OUT:
- Role-based authorization (future track)
- OAuth2 social login (future track)

## Key Design Decisions
1. **Token storage:** Stateless JWT vs server-side sessions?
   Trade-off: Scalability vs revocation.
2. **Password hashing:** bcrypt vs argon2?
   Trade-off: Compatibility vs security margin.
3. **Refresh token strategy:** Rotating vs long-lived?
   Trade-off: Security vs complexity.

## Architectural Notes
- All downstream tracks consume IAuth for protected endpoints

## Complexity: L
## Estimated Phases: ~4
