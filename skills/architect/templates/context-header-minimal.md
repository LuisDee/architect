# Context Header Minimal Template (~500 token budget)
#
# Emergency fallback when the full context header exceeds 2000 tokens.
# Includes only: top 5 constraints, interface summary, direct dependencies.
#
# Placeholders: {{TRACK_ID}}, {{WAVE}}, {{CC_VERSION}},
# {{TOP_CONSTRAINTS}}, {{INTERFACES_SUMMARY}}, {{DEPENDENCIES_SHORT}}

<!-- ARCHITECT CONTEXT v2-minimal | Track: {{TRACK_ID}} | Wave: {{WAVE}} | CC: {{CC_VERSION}} -->

## Constraints
{{TOP_CONSTRAINTS}}

<!-- Top 5 most relevant constraints for this track. Example:
- OTel on all endpoints
- RFC 7807 errors
- Events via outbox table
- Redis cache-aside on reads (v1.1)
- TDD, 80% coverage
-->

## Interfaces
{{INTERFACES_SUMMARY}}

<!-- One-line summary per category. Example:
- OWNS: CRUD /v1/resources (5 endpoints)
- CONSUMES: /v1/auth/me (Track 03), Redis queue (Track 06)
- PUBLISHES: resource.created, resource.updated, resource.deleted
-->

## Dependencies
{{DEPENDENCIES_SHORT}}

<!-- Direct dependencies only, one line each. Example:
- Track 01_infra_scaffold
- Track 03_auth
- Track 06_redis_queue
-->

Full context: architect/cross-cutting.md | architect/interfaces.md | architect/dependency-graph.md

<!-- END ARCHITECT CONTEXT -->
