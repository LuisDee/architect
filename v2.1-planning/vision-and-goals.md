# Vision and Goals

> **Date:** 2026-02-08
> **Purpose:** Define refined goals for Architect v2.1 with concrete user workflows, edge cases, and integration details.

---

## 1. Vision Statement

**Architect v2.0** is a project-setup tool — it runs once at the start, generates tracks, and hands off to Conductor forever.

**Architect v2.1** becomes a **living architecture partner** — it runs throughout the project lifecycle, adapts to change, and grows smarter as the codebase evolves. It handles not just "what should we build?" but "how should this new thing fit into what we've already built?"

---

## 2. Goal 1: Intelligent Feature Decomposition

### Problem
Today, Architect only handles greenfield decomposition. Adding features to a mature codebase — the most common real-world scenario — requires manual discovery logging and ad-hoc track creation through Conductor.

### Refined Goal
Add a new command (`/architect-feature`) that takes a feature description, analyzes the existing codebase and architecture, and decides whether it needs 1 track or N tracks — generating the right briefs, updating the dependency graph, and slotting them into the existing execution sequence.

### User Workflow

```
Developer: /architect-feature "Add role-based access control"

Architect:
  1. Reads product.md, architecture.md, existing tracks, codebase
  2. Asks clarifying questions if product.md is underspecified:
     "RBAC: Should roles be hierarchical or flat? How many predefined roles?"
  3. Analyzes scope:
     - Data model changes → needs its own track (depends on auth foundation)
     - API middleware changes → extends existing API track OR new track
     - UI permission gates → extends existing frontend track OR new track
  4. Presents decomposition to developer:
     "I recommend 2 new tracks:
      - T-RBAC-MODEL (Wave 3, depends on T-AUTH): Data model + migration
      - T-RBAC-GATES (Wave 4, depends on T-RBAC-MODEL + T-API): Middleware + UI gates
      Alternatively, this could be a single track if roles are simple (< 3 predefined roles)."
  5. Developer approves/modifies
  6. Architect generates briefs, updates dependency-graph.md, execution-sequence.md, tracks.md
```

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Feature fits entirely within an existing track | Recommend extending that track via discovery (TRACK_EXTENSION) rather than creating new tracks |
| Feature description is vague ("make it faster") | Enter clarification mode — ask targeted questions before decomposing |
| Feature conflicts with existing architecture decisions | Flag the conflict, reference the relevant architecture.md section, ask developer to resolve |
| Feature depends on incomplete tracks | Place new tracks after the dependency's current wave, warn about blocking risk |
| Feature is trivially small | Recommend implementing directly without tracks — not everything needs decomposition |
| Multiple features requested at once | Process sequentially, each building on the state left by the previous |

### Scope Analyzer Decision Tree

```
Input: feature description + existing architecture state

1. Is the feature description clear enough to decompose?
   NO → Enter clarification mode (ask ≤ 3 targeted questions)
   YES → Continue

2. Does the feature require changes to > 1 architectural boundary?
   (boundaries: data model, API layer, UI layer, infrastructure, external integrations)
   NO → Single track. Go to step 5.
   YES → Continue

3. Can the changes be deployed atomically (all-or-nothing)?
   YES → Single track despite crossing boundaries. Go to step 5.
   NO → Multiple tracks needed. Continue.

4. For each boundary touched:
   a. Does an existing in-progress track already cover this boundary?
      YES → Recommend TRACK_EXTENSION discovery
      NO → Create new track
   b. Identify dependencies between new tracks
   c. Identify dependencies between new and existing tracks

5. Place track(s) in execution sequence:
   a. Compute wave based on dependency graph
   b. Validate no cycles introduced (validate_dag.py)
   c. Generate brief(s)
```

### Integration with Existing System
- Reuses `brief-generator` sub-agent for brief creation
- Reuses `validate_dag.py` and `topological_sort.py` for dependency management
- Reuses `inject_context.py` for context headers
- New: `scope_analyzer.py` script for the decision tree
- New: `feature_context.py` to prepare codebase context for feature analysis
- Updates: `architect-expert.md` gains feature decomposition mode

---

## 3. Goal 2: Living Architecture

### Problem
`architecture.md` is a snapshot from project inception that immediately starts drifting. By Wave 3, it may describe components that were renamed, merged, or fundamentally redesigned during implementation.

### Refined Goal
Make architecture documentation a living artifact that automatically updates as tracks complete, captures decisions as immutable ADRs, and detects drift between intended and actual architecture.

### User Workflow

```
[After Track T-AUTH completes]

Conductor: ✅ Track T-AUTH complete. Running wave-sync hook.

Architect (automated via hook):
  1. Reads completed track's spec.md and plan.md for implementation decisions
  2. Updates architecture.md:
     - Component map: Auth service confirmed, endpoint paths updated
     - Technology choices: "JWT with RS256" (was "JWT or session-based TBD")
  3. Generates ADR:
     decisions/ADR-003-jwt-rs256-over-sessions.md
     - Context: Auth track needed token strategy
     - Decision: JWT with RS256 for stateless verification
     - Consequences: No server-side session store needed; token revocation requires blocklist
  4. Updates change log:
     CHANGELOG.md: "Wave 1 complete: Auth foundation, database schema established"
  5. Checks for drift:
     - interfaces.md says T-API exposes /api/v1/auth/*
     - T-AUTH implementation uses /auth/v2/*
     - ⚠️ DRIFT DETECTED: Interface path mismatch
```

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Track completed but no architectural decisions made | Skip ADR generation, still update component map status |
| Implementation contradicts architecture.md | Flag as drift warning in sync output, developer decides resolution |
| Multiple tracks complete simultaneously (same wave) | Process each independently, merge architecture updates, detect conflicts |
| Developer manually edits architecture.md | Respect manual edits — auto-updates are additive (append sections, update status), never destructive |
| Architecture.md becomes too large | Split into sub-documents (architecture/components.md, architecture/decisions.md) with index |

### Architecture Doc Updater Workflow
1. **Trigger:** Track completion (via 05-wave-sync hook)
2. **Input:** Completed track's spec.md, plan.md, metadata.json
3. **Process:**
   a. Extract decisions (technology choices, patterns used, interfaces defined)
   b. Diff against current architecture.md sections
   c. Generate patch (additive only — new sections, status updates, confirmed choices)
   d. Generate ADR if significant decision detected
   e. Append to CHANGELOG.md
4. **Output:** Updated architecture.md, optional ADR, changelog entry
5. **Review:** Changes are written to disk; developer reviews at next sync

---

## 4. Goal 3: Visualization

### Problem
Understanding a 15-track project with wave dependencies is impossible from text files alone. Developers need visual representations to validate decomposition decisions and track progress.

### Refined Goal
Generate Mermaid-based diagrams that render on GitHub/GitLab and can be exported for other contexts. Provide both static decomposition diagrams and dynamic progress overlays.

### User Workflow

```
Developer: /architect-status --visual

Architect generates/updates:
  1. architect/diagrams/dependency-graph.mmd
     - Mermaid flowchart showing track dependencies
     - Color-coded by status: green=complete, blue=in-progress, gray=pending, red=blocked

  2. architect/diagrams/component-map.mmd
     - Mermaid architecture diagram showing system components
     - Grouped by service/module boundary

  3. architect/diagrams/wave-timeline.mmd
     - Gantt-style chart showing wave execution with track placement

  Terminal output:
  ┌─────────────────────────────────────┐
  │ Wave 1: ████████████ 100% (3/3)     │
  │ Wave 2: ████████░░░░  67% (2/3)     │
  │ Wave 3: ░░░░░░░░░░░░   0% (0/4)     │
  │ Wave 4: ░░░░░░░░░░░░   0% (0/2)     │
  │ Overall: ████████░░░░  42% weighted  │
  └─────────────────────────────────────┘

  📄 Diagrams updated: architect/diagrams/
  View on GitHub or run: mmdc -i dependency-graph.mmd -o dependency-graph.svg
```

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Project has > 20 tracks | Group tracks by wave; collapse completed waves into summary nodes |
| Circular dependency detected | Highlight cycle in red with error annotation |
| No Mermaid renderer available | Fall back to ASCII representation in terminal |
| Diagram too wide for terminal | Truncate with "... N more tracks" and reference full .mmd file |

### Diagram Types

1. **Dependency Graph** (generated during decompose, updated during sync)
   - Mermaid flowchart with track nodes and dependency edges
   - Status coloring overlay from metadata.json

2. **Component Map** (generated during decompose, updated after track completion)
   - Mermaid architecture diagram showing system topology
   - Service boundaries, data stores, external integrations

3. **Wave Timeline** (generated from execution-sequence.md)
   - Mermaid Gantt chart showing wave ordering and parallelism

4. **Terminal Progress Bar** (generated during status command)
   - ASCII progress bars per wave with percentage completion
   - Complexity-weighted totals

---

## 5. Goal 4: Pattern Detection During Implementation

### Problem
Pattern detection only occurs during initial decompose. When a developer establishes a useful pattern in Track A (e.g., error handling approach, API response format), Tracks B-N don't automatically learn about it.

### Refined Goal
Detect emerging patterns during implementation and offer to promote them to cross-cutting concerns, ensuring consistency across tracks without manual intervention.

### User Workflow

```
[During Track T-API implementation, discovery hook fires]

Hook (03-discovery-check):
  Detected: Error handling pattern used in 3+ endpoints:
    { status: "error", code: "ERR_xxx", message: "...", details: {...} }

Discovery logged: architect/discovery/pending/pattern-api-error-format-a7b3.md
  type: CROSS_CUTTING_CHANGE
  urgency: normal
  description: "Consistent API error response format emerging in T-API"
  pattern: { ... extracted structure ... }

[Developer runs /architect-sync]

Architect:
  1. Processes pattern discovery
  2. Validates pattern against existing cross-cutting.md
  3. Proposes promotion:
     "Detected emerging pattern: API Error Response Format
      Used in: T-API (3 endpoints so far)
      Affected tracks: T-ADMIN, T-FRONTEND, T-WEBHOOKS

      Promote to cross-cutting constraint?
      This would add CC v1.x: 'All API error responses MUST use format:
      {status, code, message, details}'"
  4. Developer approves → cross-cutting.md updated, affected track briefs flagged
```

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| Pattern detected but only in 1 location | Log as observation, don't propose promotion until seen 2+ times |
| Pattern conflicts with existing cross-cutting concern | Flag conflict, present both options to developer |
| Pattern is track-specific (not truly cross-cutting) | Classify as local pattern, don't promote |
| Multiple conflicting patterns detected | Present all variants, ask developer to choose canonical version |
| Pattern detected in completed tracks | Note that completed tracks won't be retroactively updated; new tracks will follow the pattern |

### Detection Strategy

Given that LLMs achieve only ~39% accuracy at precise GoF pattern classification, the approach should be **role-based** rather than **template-based**:

1. **Structural role detection** — Identify what role modules/classes play (factory, observer, middleware) rather than matching exact patterns
2. **Repetition detection** — Flag code structures that appear in 3+ locations across different modules
3. **Convention detection** — Identify naming conventions, response formats, error handling approaches that are consistent
4. **Fan-in analysis** — Identify modules with high fan-in (called from many places) as cross-cutting candidates

---

## 6. Goal 5: Enhanced Testing Integration

### Problem
Test configuration is deliberately left to Conductor, but the quality gates are entirely advisory with no test prerequisites or environment setup. The wave validation warns but doesn't block.

### Refined Goal
Provide test infrastructure configuration at the architecture level — test strategy, environment requirements, and quality thresholds — while keeping test execution under Conductor's control.

### User Workflow

```
[During decompose, for each track brief]

Brief includes new "Test Strategy" section:
  ## Test Strategy
  - Unit test approach: [based on tech-stack.md framework choices]
  - Integration test dependencies: [other tracks/services needed]
  - Test environment: [what must be running — DB, auth service, etc.]
  - Quality threshold: [coverage target based on track criticality]
  - Prerequisite tracks for integration tests: [T-AUTH must be complete]

[During wave validation]

validate_wave_completion.py enhanced:
  1. Check test_command exists (existing)
  2. NEW: Check test environment prerequisites are met
  3. NEW: Check quality threshold met (if configured)
  4. NEW: Report test coverage delta (if tool configured)
  5. Still advisory — developer can override
```

### Edge Cases

| Edge Case | Handling |
|-----------|----------|
| No test framework specified in tech-stack.md | Brief says "Test framework: TBD — decide during spec generation" |
| Track has no testable behavior (config-only) | Brief says "Test strategy: Validate configuration loads correctly" |
| Integration tests need services from incomplete tracks | Flag in brief as "Integration tests available after Wave N completion" |
| Developer overrides quality gate | Log the override in metadata.json for audit trail |

---

## 7. Non-Goals for v2.1

To maintain focus, the following are explicitly **out of scope**:

1. **Runtime monitoring** — Architect operates at design-time only
2. **CI/CD integration** — No automated pipeline management beyond quality gates
3. **Multi-repo support** — Single repository per project
4. **Real-time collaboration** — Single developer workflow (developer + AI agents)
5. **Code generation** — Architect generates briefs and architecture docs, not implementation code
6. **Conductor modifications** — v2.1 changes are entirely within the Architect plugin; no Conductor changes required
7. **Gemini CLI parity for new features** — New v2.1 features are Claude Code only initially; Gemini CLI can follow later

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Feature decomposition accuracy | Developer accepts decomposition without modification > 70% of the time | Track modification rate after generation |
| Architecture freshness | architecture.md reflects actual state within 1 wave lag | Manual review at wave boundaries |
| Visualization utility | Developers reference diagrams when making decisions | Usage of /architect-status --visual |
| Pattern promotion rate | ≥ 1 cross-cutting concern promoted per 5-track project | Discovery type distribution |
| Quality gate adoption | Developers override quality gates < 20% of the time | Override rate in metadata.json |
| Context efficiency | Sub-agent token usage stays within budget (< 40K per agent) | Token usage instrumentation |
| Backward compatibility | All existing v2.0 projects work without migration | Contract test suite passes |
