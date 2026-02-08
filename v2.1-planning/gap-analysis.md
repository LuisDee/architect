# Gap Analysis

> **Date:** 2026-02-08
> **Purpose:** Map current capabilities against v2.1 vision, identifying specific gaps and their resolution strategies.

---

## 1. Goal: Intelligent Feature Decomposition

### What Exists Today
- `/architect-decompose` handles full greenfield decomposition only
- Discovery system allows manual logging of emergent work during implementation
- `/architect-sync` processes discoveries with classification (NEW_TRACK, TRACK_EXTENSION, etc.)
- `validate_dag.py` and `topological_sort.py` handle dependency management
- `brief-generator` sub-agent generates per-track briefs
- `prepare_brief_context.py` creates filtered context bundles

### What's Missing

| Gap | Severity | Description |
|-----|----------|-------------|
| **No `/architect-feature` command** | Critical | No way to add features to an existing project. The only entry point is full decompose. |
| **No scope analysis logic** | Critical | No decision tree for "does this feature need 1 track or N tracks?" — all decompositions produce N tracks. |
| **No clarification mechanism** | High | Agent cannot ask targeted questions when product.md or feature description is underspecified. Currently makes assumptions that cascade through all briefs. |
| **No existing-architecture awareness** | High | `codebase-analyzer` explores raw codebase but doesn't read existing `architecture.md`, `cross-cutting.md`, or completed track specs. Feature decomposition must be architecture-aware. |
| **No incremental dependency graph updates** | Medium | `validate_dag.py` validates a complete graph; no mechanism to add nodes/edges to an existing graph and re-validate. |
| **No "too small to track" detection** | Medium | Everything gets decomposed into tracks. No heuristic to say "this is a 30-minute task, just do it directly." |
| **No feature context preparation** | Medium | `prepare_brief_context.py` prepares context for initial decompose. Feature decomposition needs context about existing architecture state, not just product.md. |

### Reusable Components
- `brief-generator` sub-agent (unchanged — generates briefs from context bundles)
- `validate_dag.py` (extend to support incremental node/edge addition)
- `topological_sort.py` (unchanged — recomputes waves from updated graph)
- `inject_context.py` (unchanged — generates context headers for new briefs)
- Discovery classification system (directly applicable — features that extend existing tracks use TRACK_EXTENSION)

### New Components Needed
1. **`/architect-feature` command** (~200-300 lines) — New command with feature description input, clarification loop, scope analysis, brief generation, graph update
2. **`scope_analyzer.py` script** (~200 lines) — Decision tree: single vs. multi-track, boundary detection, atomicity analysis
3. **`feature_context.py` script** (~150 lines) — Prepare context bundle for feature analysis (existing architecture + codebase state + completed track summaries)
4. **Clarification protocol** in architect-expert.md — Pre-decomposition question-answer loop using `AskUserQuestion`

---

## 2. Goal: Living Architecture

### What Exists Today
- `architecture.md` generated once during decompose via `architecture.md` template
- `cross-cutting.md` is append-only versioned (CC v1.0, v1.1, etc.)
- `interfaces.md` tracks inter-track API/event contracts
- `sync_check.py` detects interface mismatches and CC version drift
- `05-wave-sync.md` hook fires after track completion
- Discovery system captures emergent architectural changes (ARCHITECTURE_CHANGE type)

### What's Missing

| Gap | Severity | Description |
|-----|----------|-------------|
| **No architecture.md auto-update** | Critical | architecture.md is write-once. No mechanism to update component status, confirmed technology choices, or structural changes after initial generation. |
| **No ADR generation** | High | No Architecture Decision Records. Decisions are implicit in briefs/specs but never captured as standalone documents. |
| **No change log** | Medium | No CHANGELOG.md or equivalent tracking project evolution over time. |
| **No drift detection beyond interfaces** | Medium | `sync_check.py` checks interface mismatches but not structural drift (component renamed, module merged, pattern changed). |
| **No decision extraction from completed tracks** | High | When a track completes, the decisions made during spec/plan generation (technology choices, pattern selections) are locked inside that track's files, not propagated to architecture-level docs. |
| **No architecture versioning** | Low | architecture.md has no version history. Changes are destructive edits, not versioned updates. |

### Reusable Components
- `05-wave-sync.md` hook (extend as trigger point for architecture updates)
- `sync_check.py` (extend with structural drift checks)
- `cross-cutting.md` versioning pattern (same append-only principle could apply to architecture sections)
- `merge_discoveries.py` (ARCHITECTURE_CHANGE discoveries can feed into auto-updates)
- Template system (add ADR template, changelog template)

### New Components Needed
1. **`architecture_updater.py` script** (~250 lines) — Read completed track artifacts, extract decisions, generate architecture.md patches
2. **`extract_decisions.py` script** (~150 lines) — Parse spec.md/plan.md for technology choices, pattern selections, interface definitions
3. **ADR template** (`templates/adr.md`) — Lightweight Context/Decision/Consequences format
4. **Changelog template** (`templates/changelog-entry.md`) — Per-wave changelog entry
5. **Updated `05-wave-sync.md` hook** — Trigger architecture updates after track completion
6. **Architecture diff logic** — Compare intended (architecture.md) vs. actual (completed track artifacts) to detect drift

---

## 3. Goal: Visualization

### What Exists Today
- `dependency-graph.md` template produces a text-based Markdown table
- `execution-sequence.md` template produces a numbered wave list
- `/architect-status` outputs text-based progress report
- `progress.py` calculates complexity-weighted progress numbers
- ASCII component map in architecture.md (generated once, becomes stale)

### What's Missing

| Gap | Severity | Description |
|-----|----------|-------------|
| **No Mermaid diagrams** | High | No machine-readable diagram format. Everything is prose/tables. |
| **No status-colored dependency graph** | High | dependency-graph.md shows structure but not status (which tracks are complete, in-progress, blocked). |
| **No terminal progress visualization** | Medium | `/architect-status` outputs numbers but no visual bars or charts. |
| **No component topology diagram** | Medium | No visual representation of system architecture beyond the static ASCII map. |
| **No wave timeline visualization** | Low | No Gantt-style view showing wave ordering with time/parallelism. |
| **No diagram generation infrastructure** | Medium | No tooling to create, update, or render diagrams from existing data. |

### Reusable Components
- `progress.py` (provides all data needed for progress bars)
- `dependency-graph.md` content (data exists, just needs Mermaid formatting)
- `execution-sequence.md` content (wave ordering data for timeline)
- metadata.json per track (provides status for color coding)

### New Components Needed
1. **`generate_diagrams.py` script** (~200 lines) — Generate Mermaid .mmd files from dependency-graph.md and metadata.json
2. **`terminal_progress.py` script** (~100 lines) — ASCII progress bars for terminal output
3. **Mermaid templates** — dependency-graph.mmd, component-map.mmd, wave-timeline.mmd templates
4. **Updated `/architect-status` command** — `--visual` flag for diagram generation + terminal progress
5. **Diagram directory** (`architect/diagrams/`) — Convention for storing generated diagrams

---

## 4. Goal: Pattern Detection During Implementation

### What Exists Today
- `pattern-matcher` sub-agent runs during initial decompose only
- `architecture-patterns.md` reference with ~12 signal-to-pattern mappings
- `cross-cutting-catalog.md` with Always/If-Multi-Service/If-User-Facing/If-Data-Heavy checklist
- `03-discovery-check.md` hook fires after each task, mentions "Consider for Later" triggers
- Discovery system with CROSS_CUTTING_CHANGE classification type
- `merge_discoveries.py` processes discoveries but doesn't use classification guide programmatically

### What's Missing

| Gap | Severity | Description |
|-----|----------|-------------|
| **No runtime pattern detection** | Critical | Pattern detection is a one-time activity during decompose. No mechanism to detect patterns as they emerge during implementation. |
| **No pattern promotion workflow** | High | Even when a developer manually logs a pattern as a discovery, there's no structured flow to promote it to a cross-cutting concern. |
| **No repetition detection** | High | No automated detection of code structures appearing in 3+ locations across modules. |
| **No fan-in analysis** | Medium | codebase-analyzer doesn't count import frequency or call-site distribution. |
| **No convention detection** | Medium | No detection of naming conventions, response formats, or error handling approaches that are becoming consistent. |
| **No pattern-to-constraint mapping** | Medium | When a pattern is detected, there's no automated translation to a cross-cutting constraint format. |
| **classification-guide.md not programmatically integrated** | Low | The classification guide exists but merge_discoveries.py doesn't use its decision tree. |

### Reusable Components
- `pattern-matcher` sub-agent (extend to run during implementation, not just decompose)
- `architecture-patterns.md` reference (signal-to-pattern catalog already exists)
- `cross-cutting-catalog.md` (checklist for categorizing detected patterns)
- Discovery system (pattern discoveries use existing CROSS_CUTTING_CHANGE type)
- `03-discovery-check.md` hook (extend with pattern detection hints)
- `merge_discoveries.py` (already processes discoveries, extend with pattern awareness)

### New Components Needed
1. **`detect_patterns.py` script** (~200 lines) — Fan-in analysis, repetition detection, convention detection from codebase-analyzer output
2. **Pattern promotion protocol** in `/architect-sync` — When processing CROSS_CUTTING_CHANGE discoveries, structured promotion workflow with developer approval
3. **Updated `03-discovery-check.md` hook** — Enhanced hints for pattern detection during implementation
4. **Updated `pattern-matcher` sub-agent** — Support for mid-project pattern matching (not just initial analysis)
5. **Pattern examples in references** — 2-3 canonical examples of promoted patterns for few-shot learning

---

## 5. Goal: Enhanced Testing Integration

### What Exists Today
- `test_command` and `test_timeout_seconds` fields in metadata.json (set by Conductor, not Architect)
- `validate_wave_completion.py` checks test command exists and runs it (warns if missing)
- `04-phase-validation.md` hook verifies CC compliance before marking phase complete
- Quality gates are entirely advisory (developer can override anything)
- No test prerequisites, environment setup, or cleanup

### What's Missing

| Gap | Severity | Description |
|-----|----------|-------------|
| **No test strategy in briefs** | High | Briefs don't include testing guidance. Conductor gets no architecture-level testing direction. |
| **No test environment prerequisites** | Medium | No way to specify "this track needs a running PostgreSQL instance for integration tests." |
| **No quality thresholds** | Medium | No target coverage or pass rate per track based on criticality. |
| **No test dependency tracking** | Medium | No tracking of which tracks' tests depend on other tracks being complete (integration test prerequisites). |
| **No override audit trail** | Low | When developer overrides a quality gate, no record is kept. |

### Reusable Components
- `validate_wave_completion.py` (extend with prerequisites and thresholds)
- `track-brief.md` template (add Test Strategy section)
- metadata.json schema (add test configuration fields)
- Advisory quality gate pattern (preserve opt-out behavior, add audit logging)

### New Components Needed
1. **Updated `track-brief.md` template** — New "Test Strategy" section with test approach, environment, prerequisites, thresholds
2. **Updated `validate_wave_completion.py`** — Check prerequisites, quality thresholds, log overrides
3. **Updated metadata.json schema** — Fields for test_prerequisites, quality_threshold, override_log
4. **Test strategy inference logic** in brief-generator — Derive test approach from tech-stack.md framework choices

---

## 6. Gap Priority Matrix

Combining severity, implementation effort, and user impact:

| # | Gap | Goal | Severity | Effort | Priority |
|---|-----|------|----------|--------|----------|
| 1 | No `/architect-feature` command | Feature Decomp | Critical | Large | **P0** |
| 2 | No scope analysis logic | Feature Decomp | Critical | Medium | **P0** |
| 3 | No architecture.md auto-update | Living Arch | Critical | Medium | **P0** |
| 4 | No runtime pattern detection | Pattern Detect | Critical | Large | **P1** |
| 5 | No clarification mechanism | Feature Decomp | High | Small | **P1** |
| 6 | No ADR generation | Living Arch | High | Small | **P1** |
| 7 | No Mermaid diagrams | Visualization | High | Small | **P1** |
| 8 | No status-colored dependency graph | Visualization | High | Small | **P1** |
| 9 | No decision extraction from tracks | Living Arch | High | Medium | **P1** |
| 10 | No pattern promotion workflow | Pattern Detect | High | Medium | **P1** |
| 11 | No test strategy in briefs | Testing | High | Small | **P1** |
| 12 | No existing-architecture awareness | Feature Decomp | High | Medium | **P2** |
| 13 | No repetition detection | Pattern Detect | High | Medium | **P2** |
| 14 | No terminal progress visualization | Visualization | Medium | Small | **P2** |
| 15 | No change log | Living Arch | Medium | Small | **P2** |
| 16 | No incremental graph updates | Feature Decomp | Medium | Small | **P2** |
| 17 | No test environment prerequisites | Testing | Medium | Small | **P2** |
| 18 | No quality thresholds | Testing | Medium | Small | **P2** |
| 19 | No "too small to track" detection | Feature Decomp | Medium | Small | **P3** |
| 20 | No fan-in analysis | Pattern Detect | Medium | Medium | **P3** |
| 21 | No wave timeline visualization | Visualization | Low | Small | **P3** |
| 22 | classification-guide.md not integrated | Pattern Detect | Low | Small | **P3** |
| 23 | No architecture versioning | Living Arch | Low | Medium | **P3** |
| 24 | No override audit trail | Testing | Low | Small | **P3** |

---

## 7. Cross-Cutting Gaps

These gaps affect multiple goals and should be addressed as shared infrastructure:

| Gap | Affected Goals | Resolution |
|-----|---------------|------------|
| **No architecture-aware context preparation** | Feature Decomp, Living Arch, Pattern Detect | New `feature_context.py` that reads existing architecture state (architecture.md, cross-cutting.md, completed tracks, interfaces.md) |
| **No incremental artifact updates** | Feature Decomp, Living Arch, Visualization | Scripts that update existing files rather than regenerating from scratch (dependency-graph.md, execution-sequence.md, tracks.md) |
| **No Mermaid generation** | Visualization, Living Arch | Shared Mermaid generation utility used by both diagram commands and architecture updates |
| **Contract test coverage for new features** | All goals | Extend test_contracts.py to cover new artifact types (ADRs, diagrams, feature briefs) |
| **Gemini CLI compatibility** | All goals | New commands need TOML wrappers; sync-gemini-commands.sh may need updates |
