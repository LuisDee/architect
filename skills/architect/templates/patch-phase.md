# Patch Phase Template
#
# Appended to an existing track's plan.md when a cross-cutting change
# requires retroactive compliance on a COMPLETE track.
#
# Placeholders: {{PATCH_ID}}, {{CC_VERSION}}, {{CONCERN_NAME}},
# {{DATE}}, {{BLOCKS_WAVE}}, {{DEPENDS_ON}}, {{TASKS}}, {{TEST_COMMAND}}
#
# When this phase is injected:
# - Track state changes from COMPLETE to NEEDS_PATCH
# - metadata.json patches[] array gets a new entry
# - Wave completion gate checks this patch before advancing

---

## Phase {{PATCH_ID}}: Retroactive Compliance — {{CONCERN_NAME}} (CC {{CC_VERSION}})

**Added by:** `/architect-sync` on {{DATE}}
**Source:** Cross-cutting version {{CC_VERSION}}
**Blocks:** Wave {{BLOCKS_WAVE}} cannot start until this phase is complete
**Depends on:** {{DEPENDS_ON}}

<!-- DEPENDS_ON: other patches that must complete first (within same CC version).
     Usually empty — patches are ordered by CC version. Only needed when
     multiple patches in the same CC version have internal ordering.
     Example: "Phase P1 (caching must be available before cache invalidation)" -->

### Tasks

{{TASKS}}

<!-- Example:

- [ ] Task {{PATCH_ID}}.1: Add Redis cache-aside to GET /v1/resources
  - Done when: GET /v1/resources returns cached response on second call, cache TTL = 5min
- [ ] Task {{PATCH_ID}}.2: Add Redis cache-aside to GET /v1/resources/{id}
  - Done when: GET /v1/resources/{id} returns cached response on second call
- [ ] Task {{PATCH_ID}}.3: Add cache invalidation on write operations
  - Done when: POST/PUT/DELETE invalidate relevant cache keys
- [ ] Task {{PATCH_ID}}.4: Integration tests for cache behavior
  - Done when: Tests verify cache hit, cache miss, and cache invalidation

-->

### Patch Validation
- [ ] Cross-cutting compliance verified for CC {{CC_VERSION}}
- [ ] Tests passing: `{{TEST_COMMAND}}`
- [ ] Conductor — User Manual Verification 'Phase {{PATCH_ID}}'

<!-- metadata.json patch entry format:
{
  "id": "{{CC_VERSION}}-{{CONCERN_NAME_SLUG}}",
  "cc_version": "{{CC_VERSION}}",
  "status": "PENDING",
  "blocks_wave": {{BLOCKS_WAVE_NUMBER}},
  "depends_on": [],
  "phase_id": "{{PATCH_ID}}"
}
-->
