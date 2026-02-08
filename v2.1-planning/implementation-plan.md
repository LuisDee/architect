# Implementation Plan

> **Date:** 2026-02-08
> **Purpose:** Complete implementation plan for Architect v2.1 with tracks, dependencies, and execution sequence.

---

## 1. Implementation Strategy

### Approach
Architect v2.1 is decomposed into **5 implementation tracks** organized in **3 waves**. This mirrors the plugin's own decomposition model — tracks are dependency-ordered, wave-parallel, and brief-based.

### Guiding Principles
1. **Backward compatibility first** — All v2.0 projects must continue working without migration
2. **Incremental value** — Each wave delivers usable features, not just infrastructure
3. **Reuse over rewrite** — Extend existing scripts and sub-agents rather than creating new ones where possible
4. **Test as you go** — Each track includes contract test extensions
5. **Claude Code first** — New features target Claude Code initially; Gemini CLI follows later

### Complexity Budget
Total estimated complexity: **L + M + M + M + S = 10 points** (scale: S=1, M=2, L=3, XL=4)

---

## 2. Track Definitions

### Track T-FEAT: Intelligent Feature Decomposition
**Complexity:** L (3 points)
**Wave:** 1

**Scope:**
- New `/architect-feature` command with clarification loop
- Scope analyzer decision tree (single vs. multi-track)
- Architecture-aware context preparation
- Incremental dependency graph updates
- Brief generation for feature tracks

**Key Design Decisions:**
- Reuse `brief-generator` sub-agent (unchanged)
- New `scope_analyzer.py` for the single/multi-track decision tree
- New `feature_context.py` for existing-architecture-aware context preparation
- Clarification uses `AskUserQuestion` tool (≤ 3 targeted questions)
- Incremental graph update: read existing `dependency-graph.md`, add new nodes/edges, re-validate with `validate_dag.py`, re-sort with `topological_sort.py`

**Files to Create:**
- `commands/architect-feature.md` (~250 lines)
- `scripts/scope_analyzer.py` (~200 lines)
- `scripts/feature_context.py` (~150 lines)

**Files to Modify:**
- `agents/architect-expert.md` — Add feature decomposition mode
- `scripts/validate_dag.py` — Add incremental node/edge addition
- `skills/architect/SKILL.md` — Document new command
- `tests/test_contracts.py` — Add feature brief contract tests

**Dependencies:** None (Wave 1)

**Acceptance Criteria:**
1. `/architect-feature "description"` generates correct brief(s) for a new feature
2. Scope analyzer correctly chooses single vs. multi-track for test scenarios
3. New tracks integrate into existing dependency graph without cycles
4. Clarification questions fire when description is vague
5. Existing `/architect-decompose` behavior unchanged
6. Contract tests pass for feature-generated briefs

---

### Track T-LIVING: Living Architecture
**Complexity:** M (2 points)
**Wave:** 1

**Scope:**
- Architecture.md auto-update after track completion
- Decision extraction from completed track artifacts
- ADR generation for significant decisions
- Changelog generation per wave
- Drift detection (structural, not just interface)

**Key Design Decisions:**
- Architecture updates are **additive only** — new sections, status updates, confirmed choices; never destructive edits
- ADRs follow Michael Nygard's Context/Decision/Consequences format
- ADR numbering: ADR-NNN-slug format (e.g., ADR-003-jwt-rs256-over-sessions)
- Trigger: `05-wave-sync.md` hook (already fires after track completion)
- Decision extraction: parse spec.md for technology choices, pattern selections, interface definitions using structured search patterns

**Files to Create:**
- `scripts/architecture_updater.py` (~250 lines)
- `scripts/extract_decisions.py` (~150 lines)
- `skills/architect/templates/adr.md` (~30 lines)
- `skills/architect/templates/changelog-entry.md` (~20 lines)

**Files to Modify:**
- `hooks/project-hooks/05-wave-sync.md` — Trigger architecture updates
- `scripts/sync_check.py` — Add structural drift detection
- `skills/architect/SKILL.md` — Document living architecture
- `tests/test_contracts.py` — Add ADR format tests, architecture update tests

**Dependencies:** None (Wave 1)

**Acceptance Criteria:**
1. After track completion, architecture.md is updated with confirmed decisions
2. ADR generated for each significant technology/pattern decision
3. CHANGELOG.md updated per wave with summary of completed tracks
4. Structural drift detected when implementation diverges from architecture.md
5. Manual edits to architecture.md are preserved (additive-only updates)
6. Contract tests pass for ADR format and architecture update patches

---

### Track T-VIZ: Visualization
**Complexity:** M (2 points)
**Wave:** 2

**Scope:**
- Mermaid dependency graph generation with status coloring
- Mermaid component map generation
- Mermaid wave timeline (Gantt) generation
- Terminal progress bars for `/architect-status`
- Diagram update on sync/status commands

**Key Design Decisions:**
- Mermaid chosen over Structurizr for GitHub/GitLab native rendering
- Diagrams stored in `architect/diagrams/` directory
- Status coloring: green=complete, blue=in-progress, gray=pending, red=blocked (from metadata.json)
- Terminal progress: ASCII bars, no external dependencies
- `/architect-status --visual` flag for diagram generation (default: text-only, preserving current behavior)

**Files to Create:**
- `scripts/generate_diagrams.py` (~200 lines)
- `scripts/terminal_progress.py` (~100 lines)
- `skills/architect/templates/dependency-graph.mmd` (~20 lines)
- `skills/architect/templates/component-map.mmd` (~20 lines)

**Files to Modify:**
- `commands/architect-status.md` — Add `--visual` flag, integrate terminal progress
- `commands/architect-sync.md` — Update diagrams after sync
- `skills/architect/SKILL.md` — Document visualization
- `tests/test_contracts.py` — Add Mermaid format validation tests

**Dependencies:** T-LIVING (needs architecture.md updates for component map accuracy)

**Acceptance Criteria:**
1. `dependency-graph.mmd` renders correctly on GitHub with proper track status colors
2. `component-map.mmd` reflects current architecture.md content
3. `wave-timeline.mmd` shows correct wave ordering
4. Terminal progress bars display per-wave and overall completion
5. `/architect-status --visual` generates all diagram files
6. Diagrams update correctly after `/architect-sync`
7. Mermaid syntax validates (no rendering errors)

---

### Track T-PATTERN: Pattern Detection
**Complexity:** M (2 points)
**Wave:** 2

**Scope:**
- Pattern detection during implementation (via enhanced discovery hook)
- Fan-in analysis for cross-cutting concern identification
- Repetition detection across modules
- Pattern promotion workflow in `/architect-sync`
- Updated pattern-matcher for mid-project analysis

**Key Design Decisions:**
- **Role-based detection** over template-based (research shows 38.81% accuracy for GoF is too low)
- Detection is **hint-based**: enhanced discovery hook provides detection hints to the implementing agent, who then logs actual discoveries
- Fan-in analysis counts import frequency and call-site distribution from codebase-analyzer output
- Pattern promotion requires explicit developer approval (never auto-promoted)
- Promoted patterns become new CC version entries in cross-cutting.md

**Files to Create:**
- `scripts/detect_patterns.py` (~200 lines)

**Files to Modify:**
- `hooks/project-hooks/03-discovery-check.md` — Add pattern detection hints
- `commands/architect-sync.md` — Add pattern promotion workflow
- `agents/pattern-matcher.md` — Support mid-project pattern matching
- `agents/codebase-analyzer.md` — Add fan-in analysis to output
- `scripts/merge_discoveries.py` — Add pattern-aware processing
- `skills/architect/references/architecture-patterns.md` — Add pattern promotion examples
- `skills/architect/SKILL.md` — Document pattern detection
- `tests/test_contracts.py` — Add pattern discovery format tests

**Dependencies:** T-LIVING (pattern promotion updates cross-cutting.md, which T-LIVING manages)

**Acceptance Criteria:**
1. Enhanced discovery hook provides actionable pattern detection hints
2. Fan-in analysis identifies modules with high cross-boundary usage
3. Repetition detection flags structures appearing 3+ times across modules
4. `/architect-sync` presents pattern promotion proposals to developer
5. Promoted patterns correctly added as new CC version in cross-cutting.md
6. Pattern-matcher can run mid-project (not just during initial decompose)
7. Contract tests pass for pattern discovery format

---

### Track T-TEST: Enhanced Testing Integration
**Complexity:** S (1 point)
**Wave:** 3

**Scope:**
- Test Strategy section in track briefs
- Test environment prerequisites in metadata.json
- Quality thresholds per track
- Override audit trail
- Enhanced wave validation with prerequisites

**Key Design Decisions:**
- Test strategy **inferred** from tech-stack.md (framework choices → test approach recommendations)
- Quality thresholds are **advisory** (consistent with existing gate philosophy)
- Override audit: append to `metadata.json` override_log array
- Prerequisites: list of track IDs whose completion is needed for integration tests
- Brief-generator derives test strategy, Conductor overrides during spec generation

**Files to Create:**
None (all modifications to existing files)

**Files to Modify:**
- `skills/architect/templates/track-brief.md` — Add "Test Strategy" section
- `skills/architect/templates/track-metadata.json` — Add test_prerequisites, quality_threshold, override_log fields
- `agents/brief-generator.md` — Add test strategy derivation instructions
- `scripts/validate_wave_completion.py` — Check prerequisites, thresholds, log overrides
- `tests/test_contracts.py` — Add test strategy contract tests, metadata schema updates

**Dependencies:** T-FEAT, T-LIVING (test strategy references architecture decisions; prerequisites reference dependency graph)

**Acceptance Criteria:**
1. Generated briefs include Test Strategy section derived from tech-stack.md
2. metadata.json includes test_prerequisites and quality_threshold fields
3. Wave validation checks prerequisites are met before running tests
4. Quality threshold warnings appear when coverage/pass-rate below target
5. Overrides logged in metadata.json override_log
6. Backward compatible: existing briefs without test strategy still work
7. Contract tests pass for updated metadata.json schema

---

## 3. Dependency Graph

```
T-FEAT ──────────────────────────────┐
                                     ├──→ T-TEST
T-LIVING ──┬──→ T-VIZ               │
           └──→ T-PATTERN ───────────┘
```

**Explicit dependencies:**
- T-VIZ depends on T-LIVING (component map needs architecture.md updates)
- T-PATTERN depends on T-LIVING (pattern promotion writes to cross-cutting.md)
- T-TEST depends on T-FEAT (test prerequisites reference dependency graph)
- T-TEST depends on T-LIVING (test strategy references architecture decisions)

---

## 4. Execution Sequence

### Wave 1: Foundation (T-FEAT + T-LIVING)
**Parallelism:** Full — these tracks are independent
**Estimated effort:** L + M = 5 points

| Track | What Gets Delivered |
|-------|-------------------|
| T-FEAT | `/architect-feature` command working end-to-end with scope analysis and clarification |
| T-LIVING | Architecture auto-updates, ADR generation, changelog, enhanced drift detection |

**Wave 1 Exit Criteria:**
- Both commands work with sample project
- Contract tests pass for new artifact formats
- Existing `/architect-decompose` behavior unchanged (regression test)

### Wave 2: Intelligence (T-VIZ + T-PATTERN)
**Parallelism:** Full — these tracks are independent (both depend on T-LIVING, resolved in Wave 1)
**Estimated effort:** M + M = 4 points

| Track | What Gets Delivered |
|-------|-------------------|
| T-VIZ | Mermaid diagrams, terminal progress bars, `/architect-status --visual` |
| T-PATTERN | Pattern detection hints, fan-in analysis, pattern promotion workflow |

**Wave 2 Exit Criteria:**
- Diagrams render correctly on GitHub
- Pattern detection fires and produces actionable discoveries
- Contract tests pass for new formats

### Wave 3: Polish (T-TEST)
**Parallelism:** N/A — single track
**Estimated effort:** S = 1 point

| Track | What Gets Delivered |
|-------|-------------------|
| T-TEST | Test strategy in briefs, prerequisites, quality thresholds, override audit |

**Wave 3 Exit Criteria:**
- Briefs include test strategy derived from tech-stack.md
- Wave validation checks prerequisites and thresholds
- All contract tests pass (including backward compatibility)

---

## 5. File Change Summary

### New Files (8)
| File | Track | Lines (est.) |
|------|-------|-------------|
| `commands/architect-feature.md` | T-FEAT | 250 |
| `scripts/scope_analyzer.py` | T-FEAT | 200 |
| `scripts/feature_context.py` | T-FEAT | 150 |
| `scripts/architecture_updater.py` | T-LIVING | 250 |
| `scripts/extract_decisions.py` | T-LIVING | 150 |
| `scripts/generate_diagrams.py` | T-VIZ | 200 |
| `scripts/terminal_progress.py` | T-VIZ | 100 |
| `scripts/detect_patterns.py` | T-PATTERN | 200 |
| **Total new** | | **~1,500** |

### New Templates (4)
| File | Track |
|------|-------|
| `skills/architect/templates/adr.md` | T-LIVING |
| `skills/architect/templates/changelog-entry.md` | T-LIVING |
| `skills/architect/templates/dependency-graph.mmd` | T-VIZ |
| `skills/architect/templates/component-map.mmd` | T-VIZ |

### Modified Files (18)
| File | Tracks | Nature of Change |
|------|--------|-----------------|
| `agents/architect-expert.md` | T-FEAT | Add feature decomposition mode |
| `agents/pattern-matcher.md` | T-PATTERN | Support mid-project analysis |
| `agents/codebase-analyzer.md` | T-PATTERN | Add fan-in analysis output |
| `agents/brief-generator.md` | T-TEST | Add test strategy derivation |
| `commands/architect-status.md` | T-VIZ | Add --visual flag, terminal progress |
| `commands/architect-sync.md` | T-VIZ, T-PATTERN | Update diagrams, pattern promotion |
| `hooks/project-hooks/03-discovery-check.md` | T-PATTERN | Pattern detection hints |
| `hooks/project-hooks/05-wave-sync.md` | T-LIVING | Trigger architecture updates |
| `scripts/validate_dag.py` | T-FEAT | Incremental node/edge addition |
| `scripts/sync_check.py` | T-LIVING | Structural drift detection |
| `scripts/merge_discoveries.py` | T-PATTERN | Pattern-aware processing |
| `scripts/validate_wave_completion.py` | T-TEST | Prerequisites, thresholds, audit |
| `skills/architect/SKILL.md` | ALL | Document all new features |
| `skills/architect/templates/track-brief.md` | T-TEST | Test Strategy section |
| `skills/architect/templates/track-metadata.json` | T-TEST | New test fields |
| `skills/architect/references/architecture-patterns.md` | T-PATTERN | Pattern promotion examples |
| `tests/test_contracts.py` | ALL | Contract tests for all new formats |
| `README.md` | ALL | Updated documentation |

---

## 6. Testing Strategy

### Unit Tests (per script)
Each new Python script includes unit tests following the existing pattern in `tests/`:
- `test_scope_analyzer.py` — Decision tree scenarios (single track, multi track, vague input, trivial input)
- `test_feature_context.py` — Context bundle generation from existing architecture
- `test_architecture_updater.py` — Additive update generation, manual edit preservation
- `test_extract_decisions.py` — Decision extraction from sample spec.md/plan.md files
- `test_generate_diagrams.py` — Mermaid syntax validation, status color mapping
- `test_detect_patterns.py` — Fan-in calculation, repetition detection

### Contract Tests (extensions to test_contracts.py)
| Test Category | What's Validated |
|--------------|-----------------|
| Feature brief format | Same brief.md structure as decompose-generated briefs |
| ADR format | Context/Decision/Consequences sections present, ADR-NNN-slug naming |
| Mermaid diagram format | Valid Mermaid syntax, correct track references |
| Updated metadata.json | New fields present, backward compatible with old schema |
| Architecture update patches | Additive-only (no deletions), valid Markdown |
| Pattern discovery format | CROSS_CUTTING_CHANGE type, pattern structure included |

### Integration Tests
| Test | What's Validated |
|------|-----------------|
| Feature → existing graph | New tracks integrate without cycles |
| Track completion → architecture update | architecture.md updated correctly |
| Pattern detection → promotion → CC update | End-to-end pattern promotion flow |
| Wave validation with prerequisites | Prerequisites checked before test execution |

### Regression Tests
- All existing contract tests pass without modification
- `/architect-decompose` produces identical output for same input
- Existing hooks fire at same trigger points
- metadata.json backward compatible (old projects still work)

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Scope analyzer makes wrong single/multi-track decision | Medium | Medium | Advisory output — developer always reviews. Include confidence score. Few-shot examples calibrate. |
| Architecture auto-updates corrupt architecture.md | Low | High | Additive-only constraint. Generate as patch proposal, don't auto-apply in v2.1. |
| Pattern detection produces too many false positives | Medium | Medium | High threshold (3+ occurrences). All promotions require developer approval. Start conservative. |
| Mermaid diagrams don't render in all environments | Low | Low | Text-based fallback always available. Mermaid syntax is standard. |
| New features break existing contract tests | Low | High | Run full contract suite after each track. Backward compatibility tests explicit. |
| Context window bloat from architecture awareness | Medium | Medium | Budget context carefully. feature_context.py filters aggressively (same pattern as prepare_brief_context.py). |
| Feature decomposition takes too long (multiple LLM round-trips) | Medium | Low | Timeout after 3 clarification rounds. Scope analyzer is a script, not LLM-dependent. |

---

## 8. Migration Guide

### For Existing v2.0 Projects
No migration required. All changes are additive:
- New fields in metadata.json have defaults
- New template sections are optional
- New scripts don't affect existing workflows
- Hooks are backward compatible (new trigger points are additive)

### For New v2.1 Projects
Full features available automatically when using updated plugin:
- `/architect-decompose` works as before (no changes to interface)
- `/architect-feature` available for adding features post-setup
- `/architect-sync` processes pattern discoveries and triggers architecture updates
- `/architect-status --visual` generates diagrams

---

## 9. Implementation Order Within Tracks

### T-FEAT Implementation Order
1. `scripts/feature_context.py` (context preparation — needed by everything else)
2. `scripts/scope_analyzer.py` (decision tree — core logic)
3. `scripts/validate_dag.py` updates (incremental graph support)
4. `commands/architect-feature.md` (command that ties it together)
5. `agents/architect-expert.md` updates (feature mode)
6. Contract tests
7. SKILL.md documentation

### T-LIVING Implementation Order
1. `scripts/extract_decisions.py` (decision extraction — needed by updater)
2. `scripts/architecture_updater.py` (the core update engine)
3. Templates: `adr.md`, `changelog-entry.md`
4. `hooks/project-hooks/05-wave-sync.md` updates (trigger)
5. `scripts/sync_check.py` updates (structural drift)
6. Contract tests
7. SKILL.md documentation

### T-VIZ Implementation Order
1. `scripts/generate_diagrams.py` (Mermaid generation)
2. `scripts/terminal_progress.py` (ASCII progress bars)
3. Templates: `dependency-graph.mmd`, `component-map.mmd`
4. `commands/architect-status.md` updates (--visual flag)
5. `commands/architect-sync.md` updates (diagram refresh)
6. Contract tests
7. SKILL.md documentation

### T-PATTERN Implementation Order
1. `scripts/detect_patterns.py` (detection logic)
2. `agents/codebase-analyzer.md` updates (fan-in output)
3. `agents/pattern-matcher.md` updates (mid-project mode)
4. `hooks/project-hooks/03-discovery-check.md` updates (detection hints)
5. `commands/architect-sync.md` updates (promotion workflow)
6. `scripts/merge_discoveries.py` updates (pattern awareness)
7. Contract tests
8. SKILL.md documentation

### T-TEST Implementation Order
1. `skills/architect/templates/track-brief.md` updates (Test Strategy section)
2. `skills/architect/templates/track-metadata.json` updates (new fields)
3. `agents/brief-generator.md` updates (test strategy derivation)
4. `scripts/validate_wave_completion.py` updates (prerequisites, thresholds, audit)
5. Contract tests
6. SKILL.md documentation
