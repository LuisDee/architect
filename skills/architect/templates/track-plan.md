# Track {{TRACK_ID}}: {{TRACK_NAME}} — Implementation Plan

> **Complexity:** {{COMPLEXITY}}
> **Wave:** {{WAVE}}
> **Dependencies:** {{DEPENDENCY_LIST}}
> **CC Version at generation:** {{CC_VERSION}}

---

## Phase 1: {{PHASE_1_NAME}}

**Goal:** {{PHASE_1_GOAL}}

<!-- One sentence describing what's true when this phase is complete. -->

### Tasks

- [ ] Task 1.1: {{TASK_DESCRIPTION}}
  - Done when: {{DONE_CRITERIA}}
- [ ] Task 1.2: {{TASK_DESCRIPTION}}
  - Done when: {{DONE_CRITERIA}}
- [ ] Task 1.3: {{TASK_DESCRIPTION}}
  - Done when: {{DONE_CRITERIA}}

### Phase 1 Validation
- [ ] Cross-cutting compliance check (read architect/cross-cutting.md, verify applicable constraints)
- [ ] Tests passing: `{{TEST_COMMAND_PHASE_1}}`
- [ ] Conductor — User Manual Verification 'Phase 1'

<!-- Example filled phase:

## Phase 1: Database Setup

**Goal:** PostgreSQL schema exists with all core tables, migrations work, and connection pooling is configured.

### Tasks

- [ ] Task 1.1: Create Alembic configuration and initial migration
  - Done when: `alembic upgrade head` runs without error on fresh database
- [ ] Task 1.2: Define SQLAlchemy models for users, resources, and workflows
  - Done when: Models match the schema in architecture.md, all relationships defined
- [ ] Task 1.3: Create seed data script
  - Done when: `python scripts/seed.py` populates all tables with representative data
- [ ] Task 1.4: Configure connection pooling
  - Done when: Pool settings match cross-cutting spec (10 min, 20 max, 30s idle)

### Phase 1 Validation
- [ ] Cross-cutting compliance check
- [ ] Tests passing: `pytest backend/tests/track_02/test_schema.py -v`
- [ ] Conductor — User Manual Verification 'Phase 1'

-->

---

## Phase 2: {{PHASE_2_NAME}}

**Goal:** {{PHASE_2_GOAL}}

### Tasks

- [ ] Task 2.1: {{TASK_DESCRIPTION}}
  - Done when: {{DONE_CRITERIA}}
- [ ] Task 2.2: {{TASK_DESCRIPTION}}
  - Done when: {{DONE_CRITERIA}}

### Phase 2 Validation
- [ ] Cross-cutting compliance check
- [ ] Tests passing: `{{TEST_COMMAND_PHASE_2}}`
- [ ] Conductor — User Manual Verification 'Phase 2'

---

<!-- Add more phases as needed. Typical tracks have 2-5 phases.
     Each phase should be a coherent deliverable — something you could demo.

     Phase ordering guidelines:
     - Foundation/setup first (config, schema, scaffold)
     - Core functionality second (main features)
     - Integration third (connecting to other tracks)
     - Polish last (error handling edge cases, performance)

     HOOK REMINDERS (from architect/hooks/):
     - Before each phase: run constraint-update-check (Hook 01)
     - Before consuming another track's API: run interface-verification (Hook 02)
     - After each task: run discovery-check (Hook 03)
     - Before marking phase complete: run phase-validation (Hook 04)
     - After track complete: run wave-sync (Hook 05)
-->

## Final Validation

- [ ] All phases complete
- [ ] Full test suite passing: `{{TEST_COMMAND_FULL}}`
- [ ] Cross-cutting compliance verified for CC version {{CC_VERSION}}
- [ ] No BLOCKING discoveries in pending/
- [ ] Conductor — User Manual Verification 'Track {{TRACK_ID}}'

<!-- PATCH PHASES APPENDED BELOW
     When cross-cutting changes require retroactive compliance on a completed track,
     patch phases are appended here by /architect-sync.
     See templates/patch-phase.md for the format.
-->
