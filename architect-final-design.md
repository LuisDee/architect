# Architect: Final Design Specification

> **Version:** 1.0-rc1
> **Status:** Ready for implementation
> **Documents superseded:** architect-plugin-design-v2.md, architecture-research-phase.md, architect-review-response.md

---

## 1. What Architect Is

Architect is an upstream companion to Conductor. It solves two problems:

1. **Architecture advisory** — Proactively identifies patterns, cross-cutting concerns, and design decisions the developer hasn't considered, using signal extraction, a built-in pattern knowledge base, and external research tools (Context7, web search, deep-research skills).

2. **Project decomposition** — Transforms a project vision into a complete, sequenced, dependency-aware set of Conductor tracks with cross-cutting constraints injected into every track.

After initial setup, the developer lives entirely in Conductor. Architect's value is embedded in the files Conductor reads — context headers in specs, validation hooks in the workflow, and a living architecture that evolves through automated discovery.

---

## 2. Design Principles

1. **Conductor-Native.** Reads Conductor's files as input, writes Conductor-compatible tracks as output. Never duplicates what Conductor captures.

2. **Setup-Heavy, Runtime-Light.** Commands run mostly at project start. Ongoing value is delivered through hooks and context headers, not commands the developer must remember.

3. **File-First, Command-Second.** Markdown files and Python scripts are the product. Commands are convenience wrappers. Any agent that reads Markdown can use the artifacts.

4. **Living Architecture.** Cross-cutting concerns, interface contracts, and the dependency graph are versioned and evolve with the project. Discovery is continuous and automatic.

5. **Fail Safe.** Race conditions, stale state, and partial failures are handled explicitly. The system degrades gracefully rather than corrupting silently.

6. **Developer Sovereignty.** The developer can override, waive, force-advance, and manually edit. Quality gates are advisory. The system informs decisions, doesn't block them.

---

## 3. Integration Model

```
CONDUCTOR OWNS                          ARCHITECT ADDS
─────────────────                       ──────────────────
conductor/product.md          ←reads──  architect/architecture.md
conductor/product-guidelines.md         architect/cross-cutting.md
conductor/tech-stack.md       ←reads──  architect/interfaces.md
conductor/workflow.md         ←marker─  architect/dependency-graph.md
conductor/tracks.md           ←writes─  architect/execution-sequence.md
conductor/tracks/<id>/spec.md ←writes─  architect/hooks/*.md
conductor/tracks/<id>/plan.md ←writes─  architect/discovery/
conductor/tracks/<id>/metadata.json     architect/references/*.md
```

**workflow.md integration:** Architect adds a single marker line:
```markdown
<!-- ARCHITECT:HOOKS — Read architect/hooks/*.md for additional workflow steps -->
```

All hook logic lives in `architect/hooks/` as separate files. Conductor can restructure workflow.md freely; the marker survives. If removed, hooks are disabled — graceful degradation.

---

## 4. Directory Structure

```
project/
├── architect/
│   ├── architecture.md                    # System architecture, component map, ADRs
│   ├── cross-cutting.md                   # Versioned behavioral constraints (append-only)
│   ├── interfaces.md                      # Track-to-track API/event contracts
│   ├── dependency-graph.md                # Track dependency DAG
│   ├── execution-sequence.md              # Wave ordering + completion criteria
│   │
│   ├── hooks/                             # Workflow hooks (agent reads at specified points)
│   │   ├── README.md                      # Hook activation docs + when to read each hook
│   │   ├── 01-constraint-update-check.md  # Before each phase: check CC version
│   │   ├── 02-interface-verification.md   # Before consuming another track's API
│   │   ├── 03-discovery-check.md          # After each task: check for emergent work
│   │   ├── 04-phase-validation.md         # Before marking phase complete: CC compliance
│   │   └── 05-wave-sync.md               # After track complete: sync + quality gate
│   │
│   ├── discovery/                         # Per-file discovery system (no race conditions)
│   │   ├── pending/                       # One file per discovery entry
│   │   ├── processed/                     # Archive after sync processes them
│   │   └── discovery-log.md              # Canonical merged log (read-only, for reference)
│   │
│   ├── references/                        # Built-in knowledge (ships with plugin)
│   │   ├── architecture-patterns.md       # Signal → pattern mapping + trade-offs
│   │   ├── cross-cutting-catalog.md       # Always-evaluate checklist
│   │   └── classification-guide.md        # Discovery classification decision tree
│   │
│   └── templates/                         # Track generation templates
│       ├── context-header.md              # Compressed context header (~<2000 tokens)
│       ├── context-header-minimal.md      # Emergency fallback (<500 tokens)
│       ├── architecture.md                # architect/architecture.md template
│       ├── cross-cutting.md               # architect/cross-cutting.md template
│       ├── interfaces.md                  # architect/interfaces.md template
│       ├── dependency-graph.md            # architect/dependency-graph.md template
│       ├── execution-sequence.md          # architect/execution-sequence.md template
│       ├── track-spec.md
│       ├── track-plan.md
│       ├── track-metadata.json            # Per-track metadata template
│       └── patch-phase.md                # Template for retroactive compliance phases
│
├── conductor/                             # Conductor's artifacts
│   ├── product.md                         # ← Conductor setup
│   ├── product-guidelines.md              # ← Conductor setup
│   ├── tech-stack.md                      # ← Conductor setup
│   ├── workflow.md                        # ← Conductor setup + one ARCHITECT:HOOKS marker
│   ├── tracks.md                          # ← Architect writes track registry
│   └── tracks/
│       └── <track_id>/
│           ├── spec.md                    # ← Architect generates (with context header)
│           ├── plan.md                    # ← Architect generates (with validation steps)
│           └── metadata.json              # ← Architect generates (track state + config)
│
└── .claude/skills/architect/              # Claude Code skill packaging
    ├── SKILL.md
    ├── references/                        # → symlink or copy of architect/references/
    ├── templates/                         # → symlink or copy of architect/templates/
    └── scripts/
        ├── validate_dag.py                # Cycle detection + edge simulation
        ├── topological_sort.py            # Wave generation from DAG
        ├── inject_context.py              # Compressed context header generation
        ├── merge_discoveries.py           # Pending → canonical log (dedup + conflict check)
        ├── sync_check.py                  # Drift detection between tracks and architecture
        ├── validate_wave_completion.py    # Quality gate with test runner
        ├── check_conductor_compat.py      # Version compatibility check
        └── progress.py                    # Complexity-weighted progress
```

For Gemini CLI, equivalent lives in `commands/architect/*.toml`.

---

## 5. Commands

### `/architect:decompose` — Setup (Primary Command)

**When:** Once after `/conductor:setup`. Re-run after major pivots.

**Flow:**

```
Step 1: Read Conductor files
  → conductor/product.md, tech-stack.md, workflow.md, product-guidelines.md
  → Run check_conductor_compat.py (warn if format unrecognized)

Step 2: Ask for gaps
  → Key user workflows (if not in product.md)
  → Scale/performance constraints
  → Existing systems to integrate with

Step 3: Architecture research (signal-driven)
  → Extract architectural signals from all inputs
  → Match signals to pattern candidates (references/architecture-patterns.md)
  → Research top candidates (Context7, web search, deep-research if available)
  → Present recommendations with trade-offs (3 tiers: strongly recommended,
    recommended, consider for later)
  → Developer accepts/rejects/modifies
  → Check awesome-agent-skills for existing solutions before building tracks

Step 4: Generate architecture (enriched with accepted patterns)
  → architect/architecture.md (component map, ADRs)
  → architect/cross-cutting.md v1 (behavioral constraints)
  → architect/interfaces.md (track-to-track contracts)
  → architect/dependency-graph.md (DAG)
  → architect/execution-sequence.md (waves + completion criteria)
  → REVIEW GATE: developer approves architecture + track list

Step 5: Generate all tracks
  → For each track in sequence:
    - conductor/tracks/<id>/spec.md (with compressed context header)
    - conductor/tracks/<id>/plan.md (with phases, tasks, validation steps)
    - conductor/tracks/<id>/metadata.json (state, complexity, config)
  → Update conductor/tracks.md (track registry)
  → REVIEW GATE: developer approves track specs/plans

Step 6: Install hooks
  → Generate architect/hooks/*.md
  → Add <!-- ARCHITECT:HOOKS --> marker to conductor/workflow.md
  → Initialize architect/discovery/ directory
  → "Consider for later" patterns become measurable triggers in hooks
```

**Re-run mode (after pivot):**
```
Classify each existing track:
  COMPLETE + unaffected    → FREEZE
  COMPLETE + affected      → generate patch phase in plan.md
  IN_PROGRESS + unaffected → FREEZE_AFTER_COMPLETION
  IN_PROGRESS + affected   → PAUSE, present options to developer
  NOT_STARTED + affected   → REGENERATE
  NOT_STARTED + new        → GENERATE

Rebuild dependency graph around frozen tracks.
Re-sequence waves.
```

### `/architect:sync` — Validate & Process Discoveries

**When:** Automatically at wave boundaries (via hook). Manually any time.

**Flow:**

```
Step 1: Process pending discoveries
  → Read architect/discovery/pending/*.md
  → Sort chronologically
  → Deduplicate (word-overlap similarity > 0.7 on suggested scope)
  → Check for constraint conflicts (contradictory "must"/"must not")
  → Validate urgency (auto-escalate if blocks in-progress track)
  → Validate DAG (cycle check before adding edges)

Step 2: Execute actions (ordered: tracks first, then meta-files)
  → NEW_TRACK: generate spec + plan + metadata, insert into DAG
  → TRACK_EXTENSION: append patch phase to existing plan.md
  → NEW_DEPENDENCY: add edge to DAG, flag for developer review
  → CROSS_CUTTING_CHANGE: version-append to cross-cutting.md
  → ARCHITECTURE_CHANGE: present to developer, do not auto-apply
  → INTERFACE_MISMATCH: present to developer with specifics

Step 3: Propagate changes
  → Regenerate context headers for NOT_STARTED tracks
  → Generate patch phases for COMPLETE tracks (retroactive compliance)
  → IN_PROGRESS tracks pick up changes via constraint-update-check hook
  → Re-sequence execution waves if DAG changed

Step 4: Move processed discoveries to processed/
  → Only after all actions succeed
  → If any action fails: leave in pending/, log error, continue with next

Step 5: Validate wave completion (if triggered by wave boundary)
  → Run validate_wave_completion.py
  → Present results to developer (advisory, not blocking)
```

### `/architect:status` — Bird's Eye Progress

**When:** Any time.

**Output:** Complexity-weighted progress per wave and overall. Pending discoveries, drift warnings, blocked tracks, unapplied patches.

---

## 6. Track State Machine

```
                    ┌────────────────────┐
                    │    NOT_STARTED      │
                    │ (regenerate header) │
                    └────────┬───────────┘
                             │ /conductor:implement
                             ▼
                    ┌────────────────────┐
              ┌────▶│    IN_PROGRESS      │◀────┐
              │     │ (pick up new CC     │     │
              │     │  via phase hook)    │     │
              │     └────────┬───────────┘     │
              │              │                  │
              │    ┌─────────┴──────────┐       │
              │    │                    │       │
              │    ▼                    ▼       │
         ┌─────────────┐    ┌──────────────┐   │
         │   PAUSED     │    │   COMPLETE    │   │
         │ (pivot/blocker)│   │              │   │
         └──────┬──────┘    └──────┬───────┘   │
                │                   │           │
                │ resume            │ new CC    │
                └───────────────────┤ version   │
                                    ▼           │
                           ┌───────────────┐    │
                           │ NEEDS_PATCH   │────┘
                           │ (retroactive  │ (patch phase
                           │  compliance)  │  injected,
                           └───────────────┘  re-enters
                                              IN_PROGRESS)
```

---

## 7. metadata.json per Track

```json
{
  "track_id": "04_api_core",
  "state": "COMPLETE",
  "complexity": "XL",
  "wave": 4,

  "cc_version_at_start": "v1.0",
  "cc_version_current": "v1.1",

  "dependencies": ["01_infra_scaffold", "02_database_schema", "03_auth_system"],
  "interfaces_owned": ["/v1/resources", "/v1/workflows"],
  "interfaces_consumed": ["/v1/auth/me"],

  "test_command": "pytest backend/tests/track_04/ -v",
  "test_timeout_seconds": 300,

  "patches": [
    {
      "id": "v1.1-caching",
      "cc_version": "v1.1",
      "status": "PENDING",
      "blocks_wave": 5,
      "depends_on": [],
      "phase_id": "P1"
    }
  ],

  "started_at": "2026-02-07T09:00:00Z",
  "completed_at": "2026-02-07T14:30:00Z"
}
```

**Notes:**
- `test_command`: Explicit. Falls back to convention detection if absent.
- `patches`: Each patch becomes a phase in plan.md. `blocks_wave` enforced by `validate_wave_completion.py`.
- `patches[].depends_on`: Patches applied in CC version order. Dependencies only needed if within the same CC version.
- `cc_version_at_start` vs `cc_version_current`: Enables the constraint-update-check hook to detect mid-track changes.

---

## 8. Cross-Cutting Concerns: Versioned, Append-Only

```markdown
# Cross-Cutting Concerns

## v1 — Initial (Wave 1)

### Observability
- OpenTelemetry SDK for traces, metrics, logs
- structlog for Python, pino for Node
- Health checks: /healthz (liveness), /readyz (readiness)
- Source: Architecture research (always-recommend pattern)

### Error Handling
- RFC 7807 Problem Details format
- Errors logged with trace ID
- No stack traces in production responses

### Transactional Outbox
- All event publishing through outbox table
- Events and state changes atomic (same DB transaction)
- Source: Architecture research (accepted by developer)

### API Conventions
- RESTful, envelope responses, cursor pagination

### Testing
- TDD, 80% coverage, integration tests

---

## v1.1 — Discovery (Wave 4, Track 04_api_core)

### Caching (NEW)
- Redis cache-aside on all read-heavy endpoints
- Cache keys: {service}:{resource}:{id}, TTL: 5min default

### Retroactive Compliance
| Track | State | Action |
|-------|-------|--------|
| 04 | COMPLETE | PATCH_REQUIRED → Phase P1 in plan.md |
| 07 | IN_PROGRESS | MID_TRACK_ADOPTION via constraint-update-check hook |
| 08-15 | NOT_STARTED | AUTO_INHERIT via context header regeneration |
```

**Conflict detection:** When adding new constraints, `merge_discoveries.py` checks for contradictions with existing constraints (e.g., "must include X" vs "must not include X" on the same subject). Conflicts become ARCHITECTURE_CHANGE discoveries requiring developer review.

---

## 9. Compressed Context Headers

Every `spec.md` starts with a compressed context header filtered to only what THIS track needs:

```markdown
<!-- ARCHITECT CONTEXT v2 | Track: 09_api_workflows | Wave: 5 | CC: v1.1 -->

## Constraints (filtered for this track)
- Observability: OTel on all endpoints
- Errors: RFC 7807
- Outbox: All events through outbox table
- Caching: Redis cache-aside on read endpoints (v1.1)
- Testing: TDD, 80% coverage

## Interfaces
- OWNS: POST/GET/PUT/DELETE /v1/workflows, POST /v1/workflows/{id}/execute
- CONSUMES: Auth middleware (Track 03), Redis queue (Track 06)
- PUBLISHES: workflow.created, workflow.executed, run.completed, run.failed

## Dependencies
- Track 04 (api_core): middleware stack must be running
- Track 06 (redis_queue): queue abstraction must be available

## Full Context (read if needed)
- architect/cross-cutting.md | architect/interfaces.md | architect/dependency-graph.md
<!-- END ARCHITECT CONTEXT -->
```

**Generation rules (`inject_context.py`):**
- Filter constraints to those applying to this track
- Include only interfaces this track owns/consumes
- Include only direct dependencies
- Hard cap: 2000 tokens. If exceeded, drop to `context-header-minimal.md` template (top 5 constraints, interfaces, deps only, ~500 tokens)

**Manual override zones:**
```markdown
<!-- END ARCHITECT CONTEXT -->

# Spec: Track 09 — Workflow API

<!-- ARCHITECT GENERATED -->
[generated spec content — regenerated on decompose]
<!-- END ARCHITECT GENERATED -->

<!-- USER ADDITIONS — preserved across regenerations -->
[developer's manual additions survive regeneration]
<!-- END USER ADDITIONS -->
```

---

## 10. Hooks: The Runtime Integration Layer

Hooks are the mechanism through which Architect's intelligence runs during Conductor's implementation without requiring separate commands.

### Hook Activation

The `<!-- ARCHITECT:HOOKS -->` marker in `workflow.md` tells the agent to read `architect/hooks/README.md`, which specifies when each hook fires:

```markdown
# architect/hooks/README.md

| Hook | When | Purpose |
|------|------|---------|
| 01-constraint-update-check.md | Before starting any phase | Detect mid-track CC version changes |
| 02-interface-verification.md | Before consuming another track's API | Catch contract drift early |
| 03-discovery-check.md | After completing each task | Identify emergent work |
| 04-phase-validation.md | Before marking a phase complete | Verify CC compliance |
| 05-wave-sync.md | After marking a track complete | Sync, quality gate, advance |
```

### Hook 01: Constraint Update Check

```markdown
Before starting ANY new phase:

1. Read your track's metadata.json → cc_version_at_start
2. Read architect/cross-cutting.md → current version
3. If versions differ:
   - Read new constraints added since your version
   - Apply applicable ones to REMAINING phases only
   - Update metadata.json cc_version_current
   - Do NOT rework completed phases
   - If rework IS needed, log TRACK_EXTENSION discovery
     with patch tasks for completed phases
```

### Hook 02: Interface Verification

```markdown
Before implementing code that consumes another track's API/events:

1. Read architect/interfaces.md for the expected contract.

2. Check producer track state (from metadata.json):

   COMPLETE:
   a. Check if producer has passing integration tests
      → Read conductor/tracks/{producer}/ for test files
      → If tests exist and pass: trust the contract
   b. If no tests, verify implementation matches interfaces.md
      → Read the producer's actual code/API definition
      → If mismatch: log INTERFACE_MISMATCH discovery (BLOCKING)

   IN_PROGRESS or NOT_STARTED:
   → Implement against interfaces.md contract using mocks
   → Add TODO: "Validate against real endpoint"
```

### Hook 03: Discovery Check

```markdown
After completing each task:

1. Assess:
   - Did this reveal assumptions that don't hold?
   - Is functionality missing from any planned track?
   - Are there uncaptured dependencies?
   - Should a cross-cutting concern change?

2. If YES: write discovery file to architect/discovery/pending/
   Filename: {track_id}-{ISO-timestamp}-{6-char-random}.md

3. Classification (use decision tree):

   Q: Does this affect multiple tracks or the whole system?
     YES → Behavioral pattern? → CROSS_CUTTING_CHANGE
           Structural change?  → ARCHITECTURE_CHANGE
     NO  →
       Q: Does this belong in an existing track?
         <5 tasks, same tech → TRACK_EXTENSION
         5+ tasks or different tech → NEW_TRACK
         Need another track's output → NEW_DEPENDENCY

   Q: Can we continue without this?
     No → BLOCKING
     Yes, but needed for downstream → NEXT_WAVE
     Nice to have → BACKLOG

4. If BLOCKING: also notify developer immediately.
5. Continue with current work. Don't scope-creep.

6. "Consider for later" triggers (from architecture research):
   [Specific measurable thresholds injected here by decompose]
   e.g., "If query latency > 500ms → log CQRS discovery"
```

### Hook 04: Phase Validation

```markdown
Before marking a phase complete:

1. Read architect/cross-cutting.md (current version)
2. Verify each applicable constraint:
   - [ ] OTel instrumentation on new endpoints
   - [ ] Error responses follow defined format
   - [ ] Auth middleware on protected routes
   - [ ] Events published through outbox
   - [ ] Code coverage meets threshold
3. If any check fails: fix before marking complete.
4. If a constraint itself needs changing: log CROSS_CUTTING_CHANGE.
```

### Hook 05: Wave Sync

```markdown
When a track is marked complete:

1. Update metadata.json: state → COMPLETE, completed_at → now
2. Check execution-sequence.md: are ALL tracks in this wave complete?

   If NOT all complete → continue to next track in wave.

   If ALL complete → run wave sync:
   a. Run: python scripts/merge_discoveries.py
   b. Run: python scripts/sync_check.py
   c. Run: python scripts/validate_wave_completion.py

   validate_wave_completion.py checks:
   - All phases marked complete
   - Tests passing (uses metadata.json test_command)
   - No BLOCKING discoveries in pending/
   - All patches with blocks_wave == next_wave are COMPLETE
   - Cross-cutting validation passed

   Results presented to developer (advisory):
   → Fix issues, waive specific checks, or force-advance

3. If wave validated → present next wave preview + advance.
```

---

## 11. Discovery System

### File-Based (No Race Conditions)

Each discovery is a separate file in `architect/discovery/pending/`:

```
architect/discovery/pending/
  track-02-2026-02-07T10-00-01Z-a3f2b8.md
  track-05-2026-02-07T10-00-01Z-c7d9e1.md
  track-10-2026-02-07T10-00-02Z-f4a2b3.md
```

Filename format: `{track_id}-{ISO-timestamp}-{6-char-random-hex}.md`

The random suffix eliminates collision risk even for sub-second task completions.

### Discovery Entry Format

```markdown
## Discovery
- **Source:** Track 04_api_core, Phase 2, Task 2.2
- **Timestamp:** 2026-02-07T14:45:00Z
- **Discovery:** Real-time workflow monitoring requires WebSocket support.
- **Classification:** NEW_TRACK
- **Suggested scope:** realtime_websockets — WebSocket infrastructure, Redis pub/sub, frontend hooks
- **Dependencies:** Depends on 04_api_core, 06_redis_queue. Partially blocks 08, 11.
- **Urgency:** NEXT_WAVE
```

### Merge Process (`merge_discoveries.py`)

```
1. Load all files from pending/
2. Sort by timestamp
3. For each entry:
   a. DEDUP: Check word-overlap similarity with existing entries (>0.7 = duplicate)
      → Duplicate: append "also discovered by" note, move to processed/
   b. CONFLICT: Check for contradictory constraints
      → Conflict: reclassify both as ARCHITECTURE_CHANGE, flag for developer
   c. CYCLE: If NEW_TRACK or NEW_DEPENDENCY, run validate_dag.py --check-edge
      → Cycle: reclassify as ARCHITECTURE_CHANGE
   d. URGENCY: Validate urgency (auto-escalate if blocks in-progress or next-wave track)
   e. EXECUTE: Generate tracks, patch plans, update cross-cutting, update DAG
   f. COMMIT: Append to discovery-log.md, move file to processed/

Failure handling:
- If track generation fails → leave discovery in pending/, log error, continue
- Never move to processed/ until action is complete
- Developer sees "N unprocessed discoveries" on next sync/status
```

### Patches Become Plan Phases

When a cross-cutting change requires retroactive compliance on a completed track, the patch is injected as a new phase in the track's `plan.md`:

```markdown
## Phase P1: Retroactive Compliance — Caching (CC v1.1)
**Added by:** architect sync, 2026-02-07
**Blocks:** Wave 5 cannot start until this phase is complete

- [ ] Task P1.1: Add Redis cache-aside to GET /v1/resources
- [ ] Task P1.2: Add Redis cache-aside to GET /v1/workflows
- [ ] Task P1.3: Add cache invalidation on write operations
- [ ] Task P1.4: Integration tests for cache behavior
- [ ] Cross-cutting validation (v1.1)
- [ ] Conductor — User Manual Verification 'Phase P1'
```

This is tracked in metadata.json patches array with `status: PENDING|IN_PROGRESS|COMPLETE`. The wave completion quality gate checks `patches[].status == COMPLETE` for any patch where `blocks_wave` matches the next wave.

---

## 12. Architecture Research Phase

### When It Runs

Primarily during `/architect:decompose` Step 3. Also runs during discovery processing when a deferred pattern's trigger threshold is hit.

### Signal Extraction

The agent reads all project inputs and extracts architectural signals — characteristics that imply specific patterns:

```
"workflows span multiple services" + "rollback on failure"
  → Saga pattern (orchestration)

"events published after DB writes"
  → Transactional outbox

"monitor progress in real-time"
  → WebSocket/SSE infrastructure

"multiple services" + "debugging production issues"
  → Distributed tracing (OpenTelemetry)

"external API calls" + "unreliable dependencies"
  → Circuit breaker
```

Full signal→pattern mapping lives in `references/architecture-patterns.md`.

### Research Tool Priority

```
1. Built-in knowledge (references/*.md)
   → Always available, zero cost, zero latency
   → Pattern descriptions, trade-offs, when-to-use decision trees

2. Context7 MCP (if configured)
   → Up-to-date library docs for implementation specifics
   → "How to implement outbox in SQLAlchemy 2.0?"

3. Web search
   → Current best practices, comparisons
   → "Redis vs RabbitMQ for job queues 2025"

4. Deep Research skill (if configured, $2-5 per query)
   → Complex decisions with many viable options
   → "Temporal vs custom saga orchestrator for Python/FastAPI"

5. Existing skills/plugins catalog
   → Check before building: obra/defense-in-depth, etc.
   → Install what exists, generate what doesn't
```

### Presentation to Developer

Three tiers:
- 🔴 **Strongly recommended** — system needs these (multiple strong signal matches)
- 🟡 **Recommended** — will save pain later (single strong signal match)
- 🟢 **Consider for later** — may emerge during implementation (inferred signals)

"Consider for later" patterns become measurable triggers in the discovery-check hook:
```markdown
## Deferred Pattern Triggers
- CQRS: If dashboard queries > 500ms → log discovery
- Circuit breaker: If external API failure rate > 5% → log discovery
- Event sourcing: If audit/compliance requirements emerge → log discovery
```

### Tool Detection

Architect detects available MCP servers and adjusts:
- Context7 available → use for implementation-specific docs
- Deep Research available → use for complex architectural decisions
- Neither → fall back to built-in knowledge + web search

The built-in knowledge base is always sufficient for solid recommendations. External tools enhance with current, specific information.

---

## 13. Cross-Cutting Catalog (Always Evaluated)

Regardless of what the developer mentions, Architect evaluates these during decompose:

**Always:**
- Structured logging strategy
- Error handling convention
- Health checks (liveness + readiness)
- Configuration management (env vars, secrets)
- Graceful shutdown
- Input validation approach
- Database connection pooling
- Timeout policies on external calls

**If multi-service:**
- Distributed tracing
- Service discovery
- API versioning
- Event schema versioning
- Idempotency for message handlers

**If user-facing:**
- Authentication + authorization
- CORS policy
- Session management

**If data-heavy:**
- Backup and recovery
- Data retention policy
- PII handling
- Migration strategy

---

## 14. Wave Execution & Quality Gates

### Execution Sequence Format

```markdown
## Wave 1 — Foundation
  [01] infra_scaffold
  [13] observability

## Wave 1 Completion Criteria
- All phases complete, tests passing
- Docker Compose starts all services
- OTel collector receiving traces

## Wave 2 — Core Services (parallel)
  [02] database_schema
  [05] frontend_shell
  [06] redis_queue

## Wave 2 Completion Criteria
- All phases complete, tests passing
- Migrations applied successfully
- React app renders, Redis responds to PING
- No BLOCKING discoveries in pending/
```

### Quality Gate (`validate_wave_completion.py`)

```python
def validate_wave(wave_number):
    tracks = get_tracks_in_wave(wave_number)
    results = []

    for track in tracks:
        track_ok = True

        # 1. All phases complete
        if not all_phases_complete(track):
            results.append(("FAIL", track.id, "Incomplete phases"))
            track_ok = False

        # 2. Tests passing
        if track.metadata.get("test_command"):
            test_result = run_command(
                track.metadata["test_command"],
                timeout=track.metadata.get("test_timeout_seconds", 300)
            )
            if test_result.returncode != 0:
                results.append(("FAIL", track.id, f"Tests failing"))
                track_ok = False
        else:
            results.append(("WARN", track.id, "No test_command in metadata"))

        # 3. No blocking discoveries
        blocking = [d for d in pending_discoveries()
                    if d.source_track == track.id and d.urgency == "BLOCKING"]
        if blocking:
            results.append(("FAIL", track.id, f"{len(blocking)} blocking discoveries"))
            track_ok = False

        # 4. Patches complete (for patches blocking next wave)
        next_wave = wave_number + 1
        pending_patches = [p for p in track.metadata.get("patches", [])
                          if p["blocks_wave"] == next_wave and p["status"] != "COMPLETE"]
        if pending_patches:
            results.append(("FAIL", track.id, f"{len(pending_patches)} unapplied patches"))
            track_ok = False

        if track_ok:
            results.append(("PASS", track.id, "All checks passed"))

    # Present results (advisory)
    print_results(results)
    if any(r[0] == "FAIL" for r in results):
        print("\nOptions: fix issues | waive checks (with reason) | force-advance")
        return False
    return True
```

### Complexity-Weighted Progress (`progress.py`)

```python
WEIGHTS = {"S": 1, "M": 2, "L": 3, "XL": 4}

def calculate_progress():
    tracks = load_all_tracks()
    total = sum(WEIGHTS[t.complexity] for t in tracks)
    done = sum(WEIGHTS[t.complexity] * t.completion_pct() for t in tracks)
    return done / total

def completion_pct(track):
    if track.state == "COMPLETE" and not track.pending_patches:
        return 1.0
    phases = parse_plan(track)
    completed = sum(1 for p in phases if p.complete)
    return completed / len(phases) if phases else 0.0
```

---

## 15. Agent Teams Integration

For projects with parallelizable waves, Architect's execution sequence maps directly to Agent Teams:

```
Lead Agent reads architect/execution-sequence.md:
  "Wave 2 has 3 independent tracks: 02, 05, 06"

Lead Agent spawns teammates:
  Teammate A → /conductor:implement Track 02
  Teammate B → /conductor:implement Track 05
  Teammate C → /conductor:implement Track 06

Each teammate:
  - Reads spec.md (with context header)
  - Follows plan.md tasks
  - Writes discoveries to own files in discovery/pending/ (no contention)
  - Runs hooks at specified points

When all teammates complete:
  Lead Agent runs wave sync (merge discoveries, quality gate)
  Lead Agent advances to next wave
```

The wave structure provides natural synchronization barriers. Per-file discoveries eliminate contention. Agents within a wave are independent.

---

## 16. Cross-Agent Compatibility

**File-first design** means the artifacts work identically across:

| Agent | Skill Format | Command Format | Notes |
|-------|-------------|----------------|-------|
| Claude Code | SKILL.md in `.claude/skills/` | Slash commands | Full MCP support for Context7 |
| Gemini CLI | SKILL.md in `skills/` | TOML in `commands/` | Conductor's native environment |
| OpenCode | SKILL.md | AGENTS.md integration | Context7 MCP supported |
| Any agent | Read the Markdown files | Run the Python scripts | Minimum viable integration |

The hooks, context headers, and discovery files are plain Markdown. Any agent that reads files can follow them. The Python scripts run via bash in any environment.

---

## 17. What Architect Does NOT Do

- Does not replace Conductor's setup, implement, status, review, or revert
- Does not generate code — only specs, plans, and architectural artifacts
- Does not enforce constraints at runtime — embeds them for the executing agent
- Does not manage git — Conductor handles commits and checkpoints
- Does not block the developer — all gates are advisory with override options
- Does not require specific MCP servers — degrades gracefully without them

---

## 18. Implementation Roadmap

### Phase 1: Core (MVP)
- SKILL.md entry point
- `references/architecture-patterns.md` and `cross-cutting-catalog.md`
- `references/classification-guide.md` (decision tree)
- Templates: context headers, spec, plan, patch phase
- Scripts: `validate_dag.py`, `topological_sort.py`, `inject_context.py`
- Commands: `/architect:decompose` (without research phase), `/architect:status`
- Hook files (all 5)
- Discovery system (per-file, merge script)

### Phase 2: Intelligence
- Architecture research phase (signal extraction + built-in knowledge)
- Context7 integration for implementation-specific docs
- Web search integration for pattern comparison
- "Consider for later" → deferred trigger injection into hooks
- Deep research skill integration (optional)

### Phase 3: Resilience
- `validate_wave_completion.py` with test runner
- `merge_discoveries.py` with dedup + conflict detection + urgency validation
- `check_conductor_compat.py`
- `progress.py` with complexity weighting
- Manual override zone preservation in regeneration
- Patch ordering and dependency tracking
- Re-decompose pivot workflow

### Phase 4: Polish
- Gemini CLI TOML command wrappers
- Sample project (reference implementation)
- End-to-end test of discovery loop
- Documentation and README

---

## 19. Open Questions (Remaining)

1. **Track granularity for very large projects.** The design assumes 10-20 tracks. For 50+ tracks, decompose itself may need to be hierarchical — subsystems first, then tracks per subsystem. Not urgent until someone tries a 50-track project.

2. **Agent Teams automatic spawning.** Should `/architect:decompose` directly configure Agent Teams for parallel waves, or remain manual? Leaning manual for v1 — let the developer control parallelism.

3. **Conductor contribution.** Should the hook system (architect/hooks/ + marker line) be proposed upstream to Conductor as a native extension mechanism? If Conductor adopts it, Architect's integration becomes even cleaner.

4. **MCP server for Architect itself.** Could Architect's pattern knowledge base be exposed as an MCP server that other tools can query? "What architecture patterns apply to a system with these characteristics?" This is a stretch goal.
