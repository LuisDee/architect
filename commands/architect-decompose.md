---
description: Decompose project into Conductor tracks with architecture research, cross-cutting constraints, and dependency-aware sequencing
---

# /architect-decompose

You are performing full project decomposition for Conductor. This is the primary Architect command. It reads Conductor's project files, performs architecture research, identifies cross-cutting concerns, generates a complete system architecture, and produces fully sequenced implementation tracks.

Run this once after `/conductor:setup`. Re-run after major pivots.

---

## Step 1: Pre-Flight Checks

1. **Check for Conductor directory:**
   ```
   ls conductor/
   ```
   If `conductor/` does not exist, stop and tell the user:
   "Run /conductor:setup first. Architect reads Conductor's product.md and tech-stack.md as input."

2. **Run compatibility check:**
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/check_conductor_compat.py
   ```
   - If it reports missing required files, stop and tell the user which files are needed.
   - If it reports warnings, note them but continue.
   - If it detects an existing ARCHITECT:HOOKS marker, warn: "Architect hooks already installed. This will regenerate architecture and tracks. Existing USER ADDITIONS zones in specs will be preserved."

3. **Read Conductor files:**
   - `conductor/product.md` (required)
   - `conductor/tech-stack.md` (required)
   - `conductor/workflow.md` (required)
   - `conductor/product-guidelines.md` (if exists)

4. **Check for existing architect/ directory:**
   - If `architect/` exists, this is a re-run. Notify the user and ask whether to regenerate from scratch or do an incremental update. For incremental: read existing architecture.md, cross-cutting.md, and track states to preserve completed work.

---

## Step 2: Gap Analysis

Review all Conductor files and identify what you know vs. what is missing. Ask the developer ONLY for information that is genuinely missing and necessary for decomposition.

**Ask about (if not already covered in product.md / tech-stack.md):**

1. **Key user workflows** — "What are the 3-5 most important things a user does in this system?" (Only ask if product.md lacks clear user flows)
2. **Scale and performance constraints** — "Any specific throughput, latency, or data volume requirements?" (Only ask if not mentioned)
3. **Existing system integrations** — "Does this integrate with any existing systems, APIs, or databases?" (Only ask if not mentioned)
4. **Deployment environment** — "Where will this run? (cloud provider, Kubernetes, bare metal, etc.)" (Only ask if tech-stack.md is silent on deployment)

Do NOT ask about things already covered in the Conductor files. Summarize what you learned from the files to confirm understanding before proceeding.

---

## Step 3: Architecture Research

This is where Architect adds unique value. You identify patterns the developer may not have considered.

### 3a. Read the Knowledge Base

Read the built-in references:
- `${CLAUDE_PLUGIN_ROOT}/skills/architect/references/architecture-patterns.md`
- `${CLAUDE_PLUGIN_ROOT}/skills/architect/references/cross-cutting-catalog.md`

### 3b. Extract Architectural Signals

Read ALL project inputs (product.md, tech-stack.md, developer answers, product-guidelines.md) and extract architectural signals — phrases, requirements, or characteristics that imply specific patterns.

List the signals you found. Example:
```
Signals extracted:
- "workflows span multiple services" + "rollback on failure" → Saga pattern
- "events published after DB writes" → Transactional Outbox
- "multiple services" + "debugging production" → Distributed Tracing
- "external API calls" to payment provider → Circuit Breaker
```

### 3c. Match Signals to Patterns

For each signal, look up the matching pattern in architecture-patterns.md. Verify:
- Do the signals genuinely match? (Avoid false positives)
- Is the "when NOT to use" applicable here?
- What tier does it fall into given signal strength?

### 3d. Research (if tools available)

Check which research tools are available and use them to enrich recommendations:

1. **Context7 MCP** (if configured) — Look up implementation specifics for the project's tech stack. Example: "How to implement outbox pattern in SQLAlchemy 2.0?"
2. **Web search** (if available) — Compare current best practices. Example: "Redis Streams vs RabbitMQ for job queues 2026"
3. **Deep Research skill** (if configured) — For complex decisions with many viable options.
4. **Existing skills/plugins** — Check if relevant skills already exist before planning to build.

If no external tools are available, the built-in knowledge base is sufficient for solid recommendations.

### 3e. Present Recommendations

Present pattern recommendations to the developer in three tiers:

**Strongly Recommended** (system needs these — multiple strong signal matches):
For each: pattern name, why it matches (cite specific signals), trade-offs summary, implementation approach for this tech stack.

**Recommended** (will save pain later — single strong signal match):
For each: pattern name, why it matches, trade-offs, what happens if you skip it.

**Consider for Later** (may emerge during implementation — inferred signals):
For each: pattern name, the signal that suggests it, the measurable trigger that would confirm it's needed.

### 3f. Developer Accepts/Rejects/Modifies

For each recommendation, the developer can:
- **Accept** — Pattern becomes part of the architecture
- **Reject** — Note the rejection reason in an ADR
- **Modify** — Adjust the approach (e.g., "use Redis Streams instead of Kafka")
- **Defer** — Move to "Consider for Later" with a trigger condition

Wait for developer input before proceeding.

### REVIEW GATE 1: Architecture Research Approval
Confirm: "These are the accepted patterns and cross-cutting concerns. Ready to generate the architecture?"

---

## Step 4: Generate Architecture

Read templates from `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/` and generate the architecture artifacts.

### 4a. Create architect/ directory structure
```
mkdir -p architect/hooks architect/discovery/pending architect/discovery/processed architect/references
```

### 4b. Generate architect/architecture.md
Using template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/architecture.md`

Include:
- System overview (from product.md + gap analysis)
- Component map (ASCII diagram showing all components and connections)
- Technology decisions table (key choices with rationale)
- ADRs for each significant decision (accepted AND rejected patterns)
- Accepted patterns table with tiers
- Deferred pattern triggers (for "Consider for Later" patterns)

### 4c. Generate architect/cross-cutting.md
Using template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/cross-cutting.md`

Walk through the cross-cutting catalog (`${CLAUDE_PLUGIN_ROOT}/skills/architect/references/cross-cutting-catalog.md`):
- Evaluate EVERY item in the "Always" section
- Evaluate "If multi-service" items if the architecture has 2+ services
- Evaluate "If user-facing" items if end users interact with the system
- Evaluate "If data-heavy" items if significant data persistence is involved

For each applicable item, write a concrete constraint (not generic). Example:
- Good: "structlog for Python, JSON format, trace_id in every log line"
- Bad: "use structured logging"

Tag as v1 (Wave 1).

### 4d. Generate architect/interfaces.md
Using template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/interfaces.md`

Define track-to-track contracts:
- REST endpoints: method, path, request/response schemas, auth requirements
- Event contracts: event name, payload schema, when published
- Shared data schemas: field names, types, owned-by

### 4e. Generate architect/dependency-graph.md
Using template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/dependency-graph.md`

Build the DAG from the track list. Validate with:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_dag.py --tracks-dir conductor/tracks
```

If cycles detected, restructure until the graph is acyclic.

### 4f. Generate architect/execution-sequence.md
Using template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/execution-sequence.md`

Run topological sort:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/topological_sort.py --tracks-dir conductor/tracks
```

Write wave-by-wave sequence with completion criteria per wave.

### REVIEW GATE 2: Architecture Approval
Present the complete architecture to the developer:
- Component map
- Cross-cutting constraints (v1)
- Interface contracts
- Track list with wave assignments
- Dependency graph

Ask: "Does this architecture look right? Any changes before I generate detailed track specs and plans?"

Wait for developer approval before proceeding.

---

## Step 5: Generate All Tracks

For each track in execution sequence order:

### 5a. Generate conductor/tracks/<track_id>/spec.md

1. Generate context header:
   ```bash
   python ${CLAUDE_PLUGIN_ROOT}/scripts/inject_context.py --track <track_id> --tracks-dir conductor/tracks --architect-dir architect
   ```
2. Read template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/track-spec.md`
3. Fill in: overview, scope (in/out), technical approach, acceptance criteria, CC compliance mapping
4. Write to `conductor/tracks/<track_id>/spec.md`

### 5b. Generate conductor/tracks/<track_id>/plan.md

1. Read template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/track-plan.md`
2. Design phases (typically 2-5 per track):
   - Phase 1 is usually setup/scaffold
   - Middle phases are core functionality
   - Final phase is integration + polish
3. Each phase has:
   - Tasks with concrete done criteria
   - Validation step (CC compliance check + tests)
   - Conductor manual verification checkpoint
4. Write to `conductor/tracks/<track_id>/plan.md`

### 5c. Generate conductor/tracks/<track_id>/metadata.json

1. Read template: `${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/track-metadata.json`
2. Fill in: track_id, state (NOT_STARTED), complexity (S/M/L/XL), wave, cc_version_current (v1), dependencies, interfaces_owned, interfaces_consumed, events_published, events_consumed, test_command, test_timeout_seconds
3. Write to `conductor/tracks/<track_id>/metadata.json`

### 5d. Update conductor/tracks.md

After generating all tracks, update (or create) `conductor/tracks.md` as the track registry. Format:
```markdown
# Tracks

| ID | Name | Wave | Complexity | Status | Dependencies |
|----|------|------|------------|--------|-------------|
| 01_infra_scaffold | Infrastructure Scaffold | 1 | M | not started | — |
| ... | ... | ... | ... | ... | ... |
```

### REVIEW GATE 3: Track Approval
Present the track list summary to the developer:
- Total track count and complexity distribution
- Wave assignments
- Key dependencies
- Estimated effort shape (which waves are heaviest)

Ask: "These are the tracks I'll generate. Any adjustments before I finalize?"

Wait for approval. Then generate all track files.

---

## Step 6: Install Hooks

### 6a. Copy hook files to project
Copy all files from `${CLAUDE_PLUGIN_ROOT}/hooks/project-hooks/` to `architect/hooks/`:
```
architect/hooks/README.md
architect/hooks/01-constraint-update-check.md
architect/hooks/02-interface-verification.md
architect/hooks/03-discovery-check.md
architect/hooks/04-phase-validation.md
architect/hooks/05-wave-sync.md
```

### 6b. Inject deferred pattern triggers
In `architect/hooks/03-discovery-check.md`, append the "Consider for Later" patterns and their measurable trigger thresholds from Step 3.

### 6c. Add workflow marker
Add this marker line to `conductor/workflow.md` (at the end, before any closing markers):
```markdown
<!-- ARCHITECT:HOOKS — Read architect/hooks/*.md for additional workflow steps -->
```

### 6d. Copy references to project
Copy `${CLAUDE_PLUGIN_ROOT}/skills/architect/references/` to `architect/references/` so the implementing agent has the knowledge base available without the plugin installed.

### 6e. Initialize discovery directory
Create:
```
architect/discovery/pending/     (empty)
architect/discovery/processed/   (empty)
architect/discovery/discovery-log.md  (header only)
```

---

## Step 7: Final Summary

Present a complete summary:
- Number of tracks generated, grouped by wave
- Total complexity weight
- Architecture patterns adopted
- Cross-cutting constraints (v1)
- Number of interfaces defined
- Hook installation status

Tell the developer: "Architecture and tracks are ready. Start implementation with `/conductor:implement` on Wave 1 tracks. The hooks in architect/hooks/ will guide cross-cutting compliance and discovery during implementation."

---

## Re-Run Mode (After Pivot)

If `architect/` already exists and tracks are in various states, classify each:

| Track State | Affected by Pivot? | Action |
|-------------|-------------------|--------|
| COMPLETE | No | FREEZE — no changes |
| COMPLETE | Yes | Generate patch phase in plan.md |
| IN_PROGRESS | No | FREEZE_AFTER_COMPLETION — let it finish |
| IN_PROGRESS | Yes | PAUSE — present options to developer |
| NOT_STARTED | Affected | REGENERATE — new spec/plan |
| (new) | — | GENERATE — create from scratch |

Rebuild dependency graph around frozen tracks. Re-sequence waves.
