# Current System Analysis

> **Date:** 2026-02-08
> **Purpose:** Document what Architect can do today, its architecture, and its limitations.

---

## 1. System Overview

Architect is a Claude Code plugin (and Gemini CLI extension) that sits upstream of Conductor. It reads Conductor's project files (`product.md`, `tech-stack.md`, `workflow.md`), performs architecture research, identifies cross-cutting concerns, and generates fully sequenced, dependency-aware implementation tracks as **briefs** (not full specs — Conductor generates those interactively).

After initial setup, the developer lives entirely in Conductor. Architect's value is embedded in context headers, hooks, and a living architecture that evolves through automated discovery.

---

## 2. Current Capabilities

### 2.1 Commands (3 slash commands)

| Command | File | Purpose | Status |
|---------|------|---------|--------|
| `/architect-decompose` | `commands/architect-decompose.md` | Full project decomposition: read Conductor files, architecture research, generate architecture artifacts, generate track briefs, install hooks | **Complete & comprehensive** (~470 lines) |
| `/architect-sync` | `commands/architect-sync.md` | Process pending discoveries, run sync checks, validate wave completion | **Complete** (~160 lines) |
| `/architect-status` | `commands/architect-status.md` | Bird's eye progress report with complexity-weighted metrics | **Complete** (~100 lines) |

Each command also has a Gemini CLI TOML wrapper in `commands/architect/*.toml`.

### 2.2 Agents (4 sub-agents)

| Agent | File | Role | Dispatch Model |
|-------|------|------|----------------|
| `architect-expert` | `agents/architect-expert.md` | Main orchestrator / solo executor | Spawned by Claude Code for decomposition tasks |
| `pattern-matcher` | `agents/pattern-matcher.md` | Reads reference files, matches signals to architecture patterns | Parallel with codebase-analyzer (Step 3) |
| `codebase-analyzer` | `agents/codebase-analyzer.md` | Explores codebase, maps structure and dependencies | Parallel with pattern-matcher (Step 3) |
| `brief-generator` | `agents/brief-generator.md` | Generates one track's brief.md + metadata.json | Batches of 3-5 in parallel (Step 5) |

**Sub-agent optimization:** On Claude Code, the decompose command spawns sub-agents in parallel to keep the orchestrator's context lean (~40-60K token savings on a 15-track project). On Gemini CLI, the same logic runs sequentially.

### 2.3 Scripts (9 Python utilities)

All scripts are Python 3.12+ stdlib only (no pip dependencies), output JSON to stdout:

| Script | Purpose | Maturity |
|--------|---------|----------|
| `validate_dag.py` | Cycle detection in dependency graph (Kahn's algorithm) | Solid, tested |
| `topological_sort.py` | Generate wave-based execution sequence from DAG | Solid, tested |
| `inject_context.py` | Build compressed context headers for briefs (~2000 token budget) | Solid, with fallback to minimal template |
| `merge_discoveries.py` | Process pending discoveries: dedup, conflict detect, urgency validation | Full implementation |
| `sync_check.py` | Drift detection: interface mismatches, CC version drift, orphaned interfaces | Full implementation |
| `validate_wave_completion.py` | Quality gate: phase completion, test runner, blocking discoveries, patches | Full implementation with test runner |
| `check_conductor_compat.py` | Pre-flight Conductor format compatibility check | Solid |
| `progress.py` | Complexity-weighted progress calculation (S=1, M=2, L=3, XL=4) | Full implementation |
| `prepare_brief_context.py` | Prepare filtered context bundle per track for sub-agent dispatch | Full implementation with CLI override for first generation |

### 2.4 Skills

Single skill: `skills/architect/SKILL.md` (~200 lines) — auto-activates when working with conductor/ directories or discussing project decomposition. Contains system overview, integration model, decompose flow, state machine, and design principles.

### 2.5 References (Knowledge Base)

| File | Content | Lines |
|------|---------|-------|
| `architecture-patterns.md` | Signal-to-pattern mapping for ~12 architecture patterns (Saga, Outbox, CQRS, Circuit Breaker, etc.) with signals, trade-offs, when-to-use decision trees | ~400+ lines |
| `cross-cutting-catalog.md` | Always-evaluate checklist: 8 "Always" items, 5 "If multi-service", 3 "If user-facing", 4 "If data-heavy" | ~95 lines |
| `classification-guide.md` | Discovery classification decision tree with 6 types + 3 urgency levels, with examples | ~150+ lines |

### 2.6 Templates (10 templates)

| Template | Purpose |
|----------|---------|
| `context-header.md` | Full compressed context header (~2000 tokens) |
| `context-header-minimal.md` | Emergency fallback header (~500 tokens) |
| `architecture.md` | System architecture document template |
| `cross-cutting.md` | Versioned constraints template |
| `interfaces.md` | Track-to-track API/event contracts template |
| `dependency-graph.md` | Track dependency DAG template |
| `execution-sequence.md` | Wave ordering template |
| `track-brief.md` | Per-track brief (scope, design decisions, constraints) — the handoff to Conductor |
| `track-metadata.json` | Per-track state and configuration template |
| `patch-phase.md` | Retroactive compliance phase template |

### 2.7 Hooks (5 project hooks)

Copied into the project's `architect/hooks/` directory during decompose:

| Hook | When | Purpose |
|------|------|---------|
| `01-constraint-update-check.md` | Before any phase | Detect mid-track CC version changes |
| `02-interface-verification.md` | Before consuming another track's API | Catch contract drift |
| `03-discovery-check.md` | After each task | Identify emergent work |
| `04-phase-validation.md` | Before marking phase complete | Verify CC compliance |
| `05-wave-sync.md` | After track complete | Sync, quality gate, advance |

### 2.8 Testing Infrastructure

- **Contract tests** (`tests/test_contracts.py`) — ~1100 lines, comprehensive Conductor<->Architect integration contract validation covering:
  - tracks.md format (Conductor parser compatibility)
  - metadata.json schema (field names, value enums)
  - brief.md structure (context headers, required sections)
  - Brief pickup detection
  - Context header preservation (brief -> spec)
  - Cross-references (tracks.md <-> filesystem <-> metadata.json)
  - Dependency graph consistency (cycles, forward-wave deps)
  - State machine validity
  - Negative test cases (bad fixtures)
- **Fixture files** — Good architect output, manual tracks, post-spec-gen, and bad fixtures
- **Script unit tests** (`tests/test_prepare_brief_context.py`) — pytest-based
- **Fixture generator** (`tests/generate_fixtures.py`) — generates test fixtures programmatically

### 2.9 Cross-Platform Support

- **Claude Code:** Full plugin format (.claude-plugin/plugin.json, commands/*.md, agents/*.md, skills/*/SKILL.md)
- **Gemini CLI:** Extension format (gemini-extension.json, commands/architect/*.toml, GEMINI.md)
- **Sync script:** `scripts/sync-gemini-commands.sh` keeps TOML commands in sync with Markdown commands

---

## 3. Architecture

### 3.1 Integration Model

```
CONDUCTOR OWNS                          ARCHITECT ADDS
-----------------                       ------------------
conductor/product.md          <-reads-  architect/architecture.md
conductor/product-guidelines.md         architect/cross-cutting.md
conductor/tech-stack.md       <-reads-  architect/interfaces.md
conductor/workflow.md         <-marker- architect/dependency-graph.md
conductor/tracks.md           <-writes- architect/execution-sequence.md
conductor/tracks/<id>/brief.md <-writes- architect/hooks/*.md
conductor/tracks/<id>/spec.md  <-Cond.- architect/discovery/
conductor/tracks/<id>/plan.md  <-Cond.- architect/references/*.md
conductor/tracks/<id>/metadata.json
```

### 3.2 Data Flow

1. Conductor setup creates `product.md`, `tech-stack.md`, `workflow.md`
2. Architect reads these, performs architecture research, generates architecture artifacts
3. Architect generates track briefs (`brief.md` + `metadata.json` per track)
4. Architect installs hooks into the project
5. Conductor picks up briefs, generates interactive specs and plans
6. During implementation, hooks fire to check constraints, discover emergent work, validate compliance
7. At wave boundaries, `/architect-sync` processes discoveries and validates wave completion

### 3.3 Key Design Patterns

- **File-first, command-second:** Markdown files are the product; commands are convenience wrappers
- **Brief-based handoff:** Architect generates briefs (questions), Conductor generates specs (answers)
- **Write-to-disk, summarize-back:** Context optimization — write artifacts to disk, keep only one-line summaries in conversation
- **Per-file discovery system:** No race conditions — each discovery is a separate file with random suffix
- **Append-only cross-cutting:** Versioned constraints never modified, only appended
- **Advisory quality gates:** Developer can override, waive, or force-advance anything

---

## 4. Current Limitations

### 4.1 No Feature-Level Decomposition

Architect only handles **initial project setup** — the full "greenfield" decompose. There is NO mechanism to:
- Add a feature to an existing, mature codebase
- Decide if a new feature request needs 1 track or N tracks
- Handle ambiguous feature requests (ask clarifying questions)
- Decompose a feature that cuts across existing tracks

The only way to add tracks post-setup is through the discovery system (manual discovery logging during implementation).

### 4.2 No Living Architecture Updates

`architect/architecture.md` is generated once during decompose and **never automatically updated**. There is no mechanism to:
- Auto-update architecture.md when tracks are completed
- Track how the system evolves over time
- Generate Architecture Decision Records (ADRs) automatically as implementation decisions are made
- Keep a change log that stays current
- Detect architectural drift between intended design and actual implementation

### 4.3 No Visualization

There are zero visualization capabilities:
- No terminal-based architecture diagrams
- No way to see system structure visually
- No track state visualization beyond text-based status output
- No dependency graph rendering
- The ASCII component map in architecture.md is generated once and becomes stale

### 4.4 No Pattern Detection During Implementation

Pattern detection only happens during initial decompose (architecture research phase). There is no mechanism to:
- Identify when a track introduces a reusable pattern
- Prompt developer to promote local patterns to cross-cutting concerns
- Detect emerging architectural patterns from implementation
- Retroactively check existing tracks for compliance with new patterns

The discovery-check hook (03) mentions "Consider for Later" triggers, but there's no automated pattern recognition — it relies entirely on the implementing agent's judgment.

### 4.5 Limited Test Configuration

- `test_command` and `test_timeout_seconds` are NOT set by Architect (deliberately — Conductor sets these)
- `validate_wave_completion.py` warns (doesn't fail) when no test command exists
- No prerequisite or environment setup for tests
- No cleanup after tests
- Quality gates are entirely advisory

### 4.6 No Re-Decompose Workflow (Incomplete)

The re-run mode section in `architect-decompose.md` describes a classification scheme for pivot handling (FREEZE, REGENERATE, PAUSE, etc.) but this is **specification only** — there's no script or automated tooling to implement it. The agent must manually classify each track.

### 4.7 No Conductor Version Pinning

`check_conductor_compat.py` does basic file existence checks but doesn't:
- Detect Conductor version
- Handle format differences between Conductor versions
- Provide migration guidance
- Validate against a Conductor contract schema

### 4.8 Missing `classification-guide.md` Integration

The classification guide exists as a reference file but is not programmatically integrated. The `merge_discoveries.py` script processes discoveries but doesn't use the classification guide's decision tree — the discovering agent must apply it manually.

### 4.9 No Examples/Sample Project

The `examples/` directory exists but contains no sample project. There's no reference implementation showing what a fully decomposed project looks like.

---

## 5. Code Quality Assessment

### Strengths
- All scripts are clean, well-documented Python with proper error handling
- JSON output from scripts enables programmatic consumption
- Contract tests are thorough with both positive and negative test cases
- Template system is well-designed with clear placeholder instructions
- Sub-agent dispatch pattern is well-implemented with structured outputs
- Cross-platform support (Claude Code + Gemini CLI) from single repo

### Weaknesses
- No script for re-decompose workflow (specification-only)
- `regenerate_specs.py` still has a `.pyc` cache file despite being deleted
- The `how-to-make-conductor-envoke-architect.md` and `example-*.py` files at root level appear to be working documents that should be cleaned up
- No CI/CD pipeline for running contract tests
- Some duplication between `inject_context.py` and `prepare_brief_context.py` in constraint extraction logic

---

## 6. File Inventory Summary

| Category | Count | Total Lines (approx) |
|----------|-------|---------------------|
| Commands | 3 (.md) + 3 (.toml) | ~730 |
| Agents | 4 | ~390 |
| Scripts | 9 (.py) + 1 (.sh) | ~1,800 |
| Skills | 1 SKILL.md | ~200 |
| References | 3 | ~645 |
| Templates | 10 | ~500 |
| Hooks | 6 (incl. README) | ~250 |
| Tests | 3 (.py) + 1 (.sh) + fixtures | ~1,500 |
| Design docs | 6 | ~3,500 |
| Config/meta | 5 | ~50 |
| **Total** | **~55 files** | **~9,500** |
