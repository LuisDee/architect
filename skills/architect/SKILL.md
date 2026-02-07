---
name: architect
description: >
  Architecture decomposition knowledge for Conductor projects.
  Auto-activates when: working with conductor/ directories, discussing
  project decomposition, identifying cross-cutting concerns, processing
  architectural discoveries, or generating implementation tracks.
---

# Architect: Project Decomposition for Conductor

Architect sits upstream of Conductor. It reads Conductor's product/tech-stack files, performs architecture research, identifies cross-cutting concerns, and generates fully sequenced, dependency-aware implementation tracks.

After Architect runs, the developer lives entirely in Conductor. Architect's value is embedded in context headers, hooks, and a living architecture that evolves through automated discovery.

## When This Skill Applies

- Project has a `conductor/` directory and needs track generation
- User asks to break down a project into tracks or implementation phases
- User mentions cross-cutting concerns, architectural patterns, or dependencies
- Discovery files exist in `architect/discovery/`
- User invokes `/architect-decompose`, `/architect-sync`, or `/architect-status`

## Commands

| Command | When | Purpose |
|---------|------|---------|
| `/architect-decompose` | Once after `/conductor:setup` | Full project decomposition into tracks |
| `/architect-sync` | At wave boundaries or manually | Validate + process pending discoveries |
| `/architect-status` | Any time | Bird's eye complexity-weighted progress |

Command definitions live in `commands/architect-decompose.md`, `commands/architect-sync.md`, and `commands/architect-status.md`.

## References (Read Before Generating Architecture)

These files contain the built-in knowledge base. Read them before making architectural decisions.

| File | Purpose |
|------|---------|
| `references/architecture-patterns.md` | Signal-to-pattern mapping with trade-offs and tiers |
| `references/cross-cutting-catalog.md` | Always-evaluate checklist (always / multi-service / user-facing / data-heavy) |
| `references/classification-guide.md` | Discovery classification decision tree with 6 types + urgency levels |

## Templates (Use When Generating Files)

Use these templates when generating project artifacts. Each template contains placeholder markers and instructions for filling them.

| Template | Generates |
|----------|-----------|
| `templates/context-header.md` | Compressed context header for spec.md (~2000 tokens) |
| `templates/context-header-minimal.md` | Emergency fallback header (~500 tokens) |
| `templates/architecture.md` | `architect/architecture.md` — component map + ADRs |
| `templates/cross-cutting.md` | `architect/cross-cutting.md` — versioned behavioral constraints |
| `templates/interfaces.md` | `architect/interfaces.md` — track-to-track API/event contracts |
| `templates/dependency-graph.md` | `architect/dependency-graph.md` — track dependency DAG |
| `templates/execution-sequence.md` | `architect/execution-sequence.md` — wave ordering |
| `templates/track-spec.md` | `conductor/tracks/<id>/spec.md` per track |
| `templates/track-plan.md` | `conductor/tracks/<id>/plan.md` per track |
| `templates/track-metadata.json` | `conductor/tracks/<id>/metadata.json` per track |
| `templates/patch-phase.md` | Retroactive compliance phase (injected into existing plans) |

## Scripts (Run Via Bash)

Python utilities (stdlib only, no pip dependencies). Run from the project root.

| Script | Purpose | When |
|--------|---------|------|
| `scripts/validate_dag.py` | Cycle detection in dependency graph | After adding tracks/dependencies |
| `scripts/topological_sort.py` | Generate wave sequence from DAG | During decompose |
| `scripts/inject_context.py` | Build compressed context headers | During track generation |
| `scripts/merge_discoveries.py` | Process pending discoveries (dedup + conflict check) | During sync |
| `scripts/sync_check.py` | Drift detection between tracks and architecture | During sync |
| `scripts/validate_wave_completion.py` | Quality gate with test runner | At wave boundaries |
| `scripts/check_conductor_compat.py` | Conductor format compatibility check | Before decompose |
| `scripts/progress.py` | Complexity-weighted progress calculation | During status |
| `scripts/regenerate_specs.py` | Regenerate spec files preserving USER ADDITIONS | During sync (CC changes) |

## System Overview

### Integration Model

```
CONDUCTOR OWNS                          ARCHITECT ADDS
-----------------                       ------------------
conductor/product.md          <-reads-  architect/architecture.md
conductor/product-guidelines.md         architect/cross-cutting.md
conductor/tech-stack.md       <-reads-  architect/interfaces.md
conductor/workflow.md         <-marker- architect/dependency-graph.md
conductor/tracks.md           <-writes- architect/execution-sequence.md
conductor/tracks/<id>/spec.md <-writes- architect/hooks/*.md
conductor/tracks/<id>/plan.md <-writes- architect/discovery/
conductor/tracks/<id>/metadata.json     architect/references/*.md
```

Architect reads Conductor's files as input, writes Conductor-compatible tracks as output. The single integration point in `workflow.md` is a marker line:

```
<!-- ARCHITECT:HOOKS -- Read architect/hooks/*.md for additional workflow steps -->
```

### Decompose Flow (Primary Command)

1. **Read Conductor files** — product.md, tech-stack.md, workflow.md, product-guidelines.md
2. **Ask for gaps** — key workflows, scale constraints, existing integrations
3. **Architecture research** — extract signals, match to patterns (references/architecture-patterns.md), present 3-tier recommendations (strongly recommended / recommended / consider for later), developer accepts/rejects/modifies
4. **Generate architecture** — architecture.md, cross-cutting.md v1, interfaces.md, dependency-graph.md, execution-sequence.md. REVIEW GATE: developer approves.
5. **Generate all tracks** — for each track: spec.md (with context header), plan.md (with phases + validation), metadata.json. Update tracks.md. REVIEW GATE: developer approves.
6. **Install hooks** — copy hooks to `architect/hooks/`, add marker to workflow.md, initialize `architect/discovery/`

### Track State Machine

```
NOT_STARTED --> IN_PROGRESS --> COMPLETE
                    |               |
                    v               v
                  PAUSED      NEEDS_PATCH --> IN_PROGRESS
```

- NOT_STARTED: context header regenerated on CC changes
- IN_PROGRESS: picks up new cross-cutting constraints via phase hooks
- COMPLETE: frozen unless new CC version triggers NEEDS_PATCH
- PAUSED: pivot or blocker; resumes to IN_PROGRESS
- NEEDS_PATCH: retroactive compliance phase injected, re-enters IN_PROGRESS

### Cross-Cutting Concerns

Versioned, append-only. Each version tagged to a wave. Tracks started before a new version pick up changes via the constraint-update-check hook. Completed tracks get patch phases for retroactive compliance. Not-started tracks get regenerated context headers.

### Discovery System

File-based, no race conditions. Each discovery is a separate file in `architect/discovery/pending/`:
- Filename: `{track_id}-{ISO-timestamp}-{6-char-random-hex}.md`
- Contains: source, timestamp, description, classification, suggested scope, dependencies, urgency
- Processed during `/architect-sync` by `merge_discoveries.py`

Six classifications: NEW_TRACK, TRACK_EXTENSION, NEW_DEPENDENCY, CROSS_CUTTING_CHANGE, ARCHITECTURE_CHANGE, INTERFACE_MISMATCH.

Three urgency levels: BLOCKING (stop and notify), NEXT_WAVE (needed for downstream), BACKLOG (nice to have).

### Hooks (Runtime Integration)

Hooks fire at specific points during Conductor's `/conductor:implement`:

| Hook | When | Purpose |
|------|------|---------|
| constraint-update-check | Before any phase | Detect mid-track CC version changes |
| interface-verification | Before consuming another track's API | Catch contract drift |
| discovery-check | After each task | Identify emergent work |
| phase-validation | Before marking phase complete | Verify CC compliance |
| wave-sync | After track complete | Sync, quality gate, advance |

### Context Headers

Every `spec.md` starts with a compressed context header filtered to what THIS track needs:
- Applicable cross-cutting constraints
- Interfaces owned/consumed
- Direct dependencies
- Hard cap: 2000 tokens (falls back to minimal template at 500 tokens)

Manual additions in `<!-- USER ADDITIONS -->` zones survive regeneration.

### Architecture Research Tiers

When presenting pattern recommendations to the developer:

- **Strongly recommended** — multiple strong signal matches; system needs these
- **Recommended** — single strong signal match; will save pain later
- **Consider for later** — inferred signals; may emerge during implementation. These become measurable triggers in the discovery-check hook.

### Research Tool Priority

1. Built-in knowledge (references/*.md) — always available
2. Context7 MCP (if configured) — up-to-date library docs
3. Web search — current best practices
4. Deep Research skill (if configured) — complex multi-option decisions
5. Existing skills/plugins catalog — check before building

### Design Principles

1. **Conductor-Native** — reads Conductor files, writes Conductor-compatible tracks
2. **Setup-Heavy, Runtime-Light** — commands run at project start; ongoing via hooks
3. **File-First, Command-Second** — Markdown files are the product
4. **Living Architecture** — cross-cutting, interfaces, and DAG evolve with the project
5. **Fail Safe** — race conditions, stale state, and partial failures handled explicitly
6. **Developer Sovereignty** — all gates advisory; developer can override everything
