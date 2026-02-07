# Architect Plugin: Packaging & Delivery

## What the Plugin Actually Is

It's a **git repo** containing Markdown files and Python scripts. That's it.
No compiled code, no npm packages, no Docker images. Just files that an
AI agent reads to become smarter about project decomposition.

---

## Installation Methods

### Claude Code (Primary)

```bash
# Option A: Plugin command (recommended)
claude /plugin add https://github.com/<org>/architect-plugin

# Option B: Git clone into project
git clone https://github.com/<org>/architect-plugin.git .claude/skills/architect

# Option C: Git clone global (available in all projects)
git clone https://github.com/<org>/architect-plugin.git ~/.claude/skills/architect
```

After installation, the user types `/architect:decompose` and Claude Code
reads the SKILL.md, loads the references, and follows the instructions.

### Gemini CLI (Conductor's Environment)

```bash
# Clone into project
git clone https://github.com/<org>/architect-plugin.git

# Or add as git submodule
git submodule add https://github.com/<org>/architect-plugin.git tools/architect
```

Gemini CLI reads the TOML command files and the shared skill content.

### Any Other Agent (OpenCode, Codex, etc.)

```bash
# Just clone it. The agent reads the Markdown files.
git clone https://github.com/<org>/architect-plugin.git .claude/skills/architect
```

---

## Repository Structure: Every File

```
architect-plugin/
│
├── README.md                              # Installation + quickstart
├── LICENSE                                # MIT or Apache 2.0
│
├── ── CLAUDE CODE INTEGRATION ──────────
│
├── SKILL.md                               # 🔑 THE entry point.
│                                          # Claude Code reads this first.
│                                          # Contains: what Architect is,
│                                          # when to activate, command list,
│                                          # and pointers to all other files.
│
├── commands/                              # Slash command definitions
│   ├── architect-decompose.md             # /architect:decompose prompt
│   ├── architect-sync.md                  # /architect:sync prompt
│   └── architect-status.md                # /architect:status prompt
│
├── ── GEMINI CLI INTEGRATION ───────────
│
├── gemini/                                # Gemini CLI command wrappers
│   ├── architect-decompose.toml           # TOML command definition
│   ├── architect-sync.toml
│   └── architect-status.toml
│
├── ── SHARED CONTENT (agent-agnostic) ──
│
├── references/                            # Built-in knowledge base
│   ├── architecture-patterns.md           # Signal → pattern mapping
│   ├── cross-cutting-catalog.md           # Always-evaluate checklist
│   └── classification-guide.md            # Discovery classification decision tree
│
├── templates/                             # Templates for generated artifacts
│   ├── context-header.md                  # Compressed context header (~2000 tok)
│   ├── context-header-minimal.md          # Fallback header (~500 tok)
│   ├── architecture.md                    # architect/architecture.md template
│   ├── cross-cutting.md                   # architect/cross-cutting.md template
│   ├── interfaces.md                      # architect/interfaces.md template
│   ├── dependency-graph.md                # architect/dependency-graph.md template
│   ├── execution-sequence.md              # architect/execution-sequence.md template
│   ├── track-spec.md                      # Per-track spec template
│   ├── track-plan.md                      # Per-track plan template
│   ├── track-metadata.json                # Per-track metadata template
│   └── patch-phase.md                     # Retroactive compliance phase template
│
├── hooks/                                 # Workflow hooks (copied into project)
│   ├── README.md                          # Hook activation reference
│   ├── constraint-update-check.md         # Before each phase
│   ├── interface-verification.md          # Before consuming another track's API
│   ├── discovery-check.md                 # After each task
│   ├── phase-validation.md                # Before marking phase complete
│   └── wave-sync.md                       # After track complete
│
├── scripts/                               # Python utilities
│   ├── requirements.txt                   # Dependencies (minimal: pyyaml, pathlib)
│   ├── validate_dag.py                    # Cycle detection + edge simulation
│   ├── topological_sort.py                # DAG → wave-based execution sequence
│   ├── inject_context.py                  # Generate compressed context headers
│   ├── merge_discoveries.py              # Pending → canonical log (dedup, conflicts)
│   ├── sync_check.py                      # Drift detection between tracks & arch
│   ├── validate_wave_completion.py        # Quality gate with test runner
│   ├── check_conductor_compat.py          # Conductor version check
│   ├── progress.py                        # Complexity-weighted progress calculation
│   └── regenerate_specs.py               # Regenerate specs preserving USER zones
│
└── examples/                              # Reference implementation
    ├── sample-project/                    # Complete worked example
    │   ├── architect/                     # What architect/ looks like after decompose
    │   │   ├── architecture.md
    │   │   ├── cross-cutting.md
    │   │   ├── interfaces.md
    │   │   ├── dependency-graph.md
    │   │   ├── execution-sequence.md
    │   │   ├── hooks/                     # Copied from plugin hooks/
    │   │   ├── discovery/
    │   │   │   ├── pending/
    │   │   │   ├── processed/
    │   │   │   └── discovery-log.md
    │   │   └── references/               # Copied from plugin references/
    │   │
    │   └── conductor/                     # What conductor/ looks like after decompose
    │       ├── product.md                 # (from /conductor:setup)
    │       ├── tech-stack.md              # (from /conductor:setup)
    │       ├── workflow.md                # (with ARCHITECT:HOOKS marker)
    │       ├── tracks.md                  # (generated by Architect)
    │       └── tracks/
    │           ├── 01_infra_scaffold/
    │           │   ├── spec.md
    │           │   ├── plan.md
    │           │   └── metadata.json
    │           └── ...
    │
    └── discovery-walkthrough.md           # Shows a discovery happening end-to-end
```

**Total files: ~40**
**Total lines of meaningful content: ~3000-4000**
(Most of the volume is in references/*.md and templates/*.md)

---

## What Each Key File Does

### SKILL.md — The Brain

This is what Claude Code reads to "become" the Architect. It contains:

```markdown
# Architect: Project Decomposition for Conductor

## When to Activate
Activate this skill when the user:
- Says "/architect:decompose", "/architect:sync", or "/architect:status"
- Asks to "break down this project into tracks"
- Asks to "decompose this into implementation tasks"
- Has a Conductor project (conductor/ directory exists) and needs tracks

## Commands
- /architect:decompose — [read commands/architect-decompose.md]
- /architect:sync — [read commands/architect-sync.md]
- /architect:status — [read commands/architect-status.md]

## Key References
Before generating architecture, read:
- references/architecture-patterns.md (signal → pattern mapping)
- references/cross-cutting-catalog.md (always-evaluate checklist)

Before generating tracks, read:
- templates/track-spec.md (spec template)
- templates/track-plan.md (plan template)

Before processing discoveries, read:
- references/classification-guide.md (decision tree)

## Scripts Available
All scripts in scripts/ directory. Run via bash:
  python scripts/validate_dag.py
  python scripts/topological_sort.py
  ...

## What Gets Generated
After /architect:decompose, the project will have:
  architect/           ← planning artifacts
  conductor/tracks/    ← track specs, plans, metadata
  conductor/tracks.md  ← track registry
  conductor/workflow.md ← one marker line added
```

### commands/architect-decompose.md — The Detailed Prompt

This is the full step-by-step instruction set for the decompose command.
It's essentially Section 5 from the design spec, written as agent-executable
instructions rather than documentation.

```markdown
# /architect:decompose

## Pre-flight
1. Check for conductor/ directory. If missing: "Run /conductor:setup first."
2. Run: python scripts/check_conductor_compat.py
3. Read: conductor/product.md, conductor/tech-stack.md, conductor/workflow.md

## Step 1: Gap Analysis
Read the Conductor files. Identify what you know vs what's missing.
Ask the developer ONLY for:
- Key user workflows (if not in product.md)
- Cross-cutting behavioral patterns
- Scale/performance constraints
- Existing system integrations

## Step 2: Architecture Research
Read references/architecture-patterns.md.
Extract architectural signals from ALL inputs.
[...full research protocol...]

## Step 3: Generate Architecture
[...templates to use, review gate, etc...]

## Step 4: Generate Tracks
For each track:
1. Read templates/track-spec.md
2. Generate spec with context header (run: python scripts/inject_context.py)
3. Read templates/track-plan.md
4. Generate plan with phases, tasks, validation steps
5. Create metadata.json from templates/track-metadata.json
[...etc...]

## Step 5: Install Hooks
1. Copy hooks/ directory to architect/hooks/
2. Add marker to conductor/workflow.md:
   <!-- ARCHITECT:HOOKS — Read architect/hooks/*.md -->
3. Initialize architect/discovery/pending/ and architect/discovery/processed/
4. Copy references/ to architect/references/
```

### scripts/validate_dag.py — A Real Script

Unlike the Markdown files which are prompts for the agent, the Python
scripts are actual executable code:

```python
#!/usr/bin/env python3
"""Validate the dependency graph for cycles and generate execution sequence."""

import json
import sys
from pathlib import Path
from collections import defaultdict, deque


def load_dependency_graph(path="architect/dependency-graph.md"):
    """Parse dependency graph from Markdown into adjacency list."""
    # Parse the Markdown table/list format
    ...


def detect_cycles(graph):
    """Kahn's algorithm — returns True if cycle exists."""
    in_degree = defaultdict(int)
    for node in graph:
        for dep in graph[node]:
            in_degree[node]  # ensure exists
            in_degree[dep] += 1

    queue = deque(n for n in graph if in_degree[n] == 0)
    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return visited != len(graph)  # True = cycle exists


def check_edge(graph, source, target):
    """Would adding source→target create a cycle?"""
    temp = {k: list(v) for k, v in graph.items()}
    temp.setdefault(source, []).append(target)
    return detect_cycles(temp)


if __name__ == "__main__":
    if "--check-edge" in sys.argv:
        source = sys.argv[sys.argv.index("--from") + 1]
        target = sys.argv[sys.argv.index("--to") + 1]
        graph = load_dependency_graph()
        if check_edge(graph, source, target):
            print(json.dumps({"cycle": True, "source": source, "target": target}))
            sys.exit(1)
        else:
            print(json.dumps({"cycle": False}))
            sys.exit(0)
    else:
        graph = load_dependency_graph()
        if detect_cycles(graph):
            print("❌ Cycle detected in dependency graph")
            sys.exit(1)
        else:
            print("✅ No cycles")
            sys.exit(0)
```

---

## What Happens at Runtime

### Install → Decompose → Implement Flow

```
DEVELOPER                           WHAT HAPPENS ON DISK
────────────────────────────────────────────────────────────

$ claude /plugin add .../architect
                                    .claude/skills/architect/
                                      SKILL.md
                                      commands/*.md
                                      references/*.md
                                      templates/*.md
                                      hooks/*.md
                                      scripts/*.py

$ claude
> /conductor:setup                  conductor/
  [describes project]                 product.md
                                      tech-stack.md
                                      workflow.md

> /architect:decompose              Claude reads SKILL.md
                                    → reads commands/architect-decompose.md
                                    → reads conductor/*.md
                                    → reads references/architecture-patterns.md
                                    → asks developer gap questions
                                    → presents architecture recommendations
                                    → generates:
                                       architect/
                                         architecture.md
                                         cross-cutting.md
                                         interfaces.md
                                         dependency-graph.md
                                         execution-sequence.md
                                         hooks/ (copied from plugin)
                                         references/ (copied from plugin)
                                         discovery/pending/
                                         discovery/processed/
                                         discovery/discovery-log.md
                                       conductor/
                                         tracks.md (registry)
                                         tracks/01_.../spec.md, plan.md, metadata.json
                                         tracks/02_.../spec.md, plan.md, metadata.json
                                         ...
                                         workflow.md (marker line added)

> /conductor:implement              Conductor reads tracks.md
                                    Picks next track from sequence
                                    Agent reads spec.md (context header)
                                    Agent follows plan.md tasks
                                    Agent reads architect/hooks/README.md
                                    → runs discovery check after each task
                                    → runs phase validation per phase
                                    → runs wave sync at track completion
                                    → discoveries written to discovery/pending/
```

### File Ownership

```
FILES THAT SHIP WITH THE PLUGIN (read-only reference):
  .claude/skills/architect/SKILL.md
  .claude/skills/architect/commands/*.md
  .claude/skills/architect/references/*.md
  .claude/skills/architect/templates/*.md
  .claude/skills/architect/hooks/*.md
  .claude/skills/architect/scripts/*.py

FILES GENERATED IN THE PROJECT (read-write, committed to git):
  architect/architecture.md
  architect/cross-cutting.md
  architect/interfaces.md
  architect/dependency-graph.md
  architect/execution-sequence.md
  architect/hooks/*.md              ← copies of plugin hooks
  architect/references/*.md         ← copies of plugin references
  architect/discovery/pending/*.md
  architect/discovery/processed/*.md
  architect/discovery/discovery-log.md
  conductor/tracks.md
  conductor/tracks/*/spec.md
  conductor/tracks/*/plan.md
  conductor/tracks/*/metadata.json
  conductor/workflow.md             ← one marker line added

FILES THE AGENT RUNS (via bash):
  .claude/skills/architect/scripts/*.py
```

---

## Moving to Local Implementation

### Yes — Move to Claude Code on a Branch

```bash
# Create the repo
mkdir architect-plugin && cd architect-plugin
git init
git checkout -b main

# Start with structure
mkdir -p commands references templates hooks scripts examples/sample-project

# Open Claude Code
claude

# Prompt:
> Read .claude/skills/architect/SKILL.md and implement Phase 1 of the
  Architect plugin. The design spec is in architect-final-design.md.
  Start with SKILL.md, then references, then templates, then scripts,
  then commands, then hooks. Generate the sample project last.
```

### Implementation Order (Phase 1 MVP)

```
File                              Priority  Est. Lines
─────────────────────────────────────────────────────────
SKILL.md                          P0        80-120
references/architecture-patterns.md P0      300-400
references/cross-cutting-catalog.md P0      80-100
references/classification-guide.md P0       60-80
templates/context-header.md       P0        30-40
templates/context-header-minimal.md P0      15-20
templates/track-spec.md           P0        40-60
templates/track-plan.md           P0        40-60
templates/track-metadata.json     P0        25-30
templates/patch-phase.md          P0        30-40
templates/architecture.md         P0        40-60
templates/cross-cutting.md        P0        30-40
templates/interfaces.md           P0        30-40
templates/dependency-graph.md     P0        20-30
templates/execution-sequence.md   P0        30-40
hooks/README.md                   P0        30-40
hooks/constraint-update-check.md  P0        40-50
hooks/interface-verification.md   P0        50-60
hooks/discovery-check.md          P0        80-100
hooks/phase-validation.md         P0        40-50
hooks/wave-sync.md                P0        60-80
commands/architect-decompose.md   P0        200-300
commands/architect-sync.md        P0        100-150
commands/architect-status.md      P0        60-80
scripts/validate_dag.py           P0        80-100
scripts/topological_sort.py       P0        60-80
scripts/inject_context.py         P1        100-130
scripts/merge_discoveries.py      P1        120-150
scripts/validate_wave_completion.py P1      80-100
scripts/sync_check.py             P1        80-100
scripts/check_conductor_compat.py P2        40-50
scripts/progress.py               P2        50-60
scripts/regenerate_specs.py       P2        60-80
README.md                         P1        100-150
examples/sample-project/          P2        500-800

TOTAL: ~35 files, ~2500-3500 lines
```

### What Claude Code Will Need

Feed it:
1. **architect-final-design.md** — the spec
2. **architect-workflow-walkthrough.md** — to understand the UX
3. **architect-review-response.md** — for edge case handling

Then let it generate file by file. The Markdown files are the bulk
of the work. The Python scripts are small utilities (~100 lines each).

### Testing Strategy

```bash
# After generating the plugin:

# 1. Create a test project
mkdir test-project && cd test-project
git init

# 2. Install the plugin
ln -s ../architect-plugin .claude/skills/architect

# 3. Run conductor setup (manually create conductor files)
mkdir conductor
# Create minimal product.md, tech-stack.md, workflow.md

# 4. Run decompose
claude
> /architect:decompose

# 5. Verify output
ls architect/          # Should have architecture.md, cross-cutting.md, etc.
ls conductor/tracks/   # Should have track directories with spec.md, plan.md
cat conductor/workflow.md  # Should have ARCHITECT:HOOKS marker

# 6. Simulate a discovery
echo "## Discovery..." > architect/discovery/pending/test-discovery.md

# 7. Run sync
> /architect:sync

# 8. Check discovery was processed
ls architect/discovery/processed/  # Discovery moved here
```

---

## Gemini CLI Packaging (Secondary)

For Conductor's native environment, add TOML command wrappers:

```toml
# gemini/architect-decompose.toml
[command]
name = "architect:decompose"
description = "Decompose project into Conductor tracks"
skill_path = "../"  # Points to SKILL.md at repo root

[command.prompt]
text = """
Read the skill file at SKILL.md, then read commands/architect-decompose.md.
Follow the instructions to decompose this project into tracks.
"""
```

The TOML files are thin wrappers. The actual logic is in the shared
Markdown files that both Claude Code and Gemini CLI read.

---

## Publishing

```bash
# Once tested:
git add .
git commit -m "feat: Architect plugin v1.0 - project decomposition for Conductor"
git remote add origin https://github.com/<org>/architect-plugin.git
git push -u origin main

# Tag release
git tag v1.0.0
git push --tags

# Users install with:
claude /plugin add https://github.com/<org>/architect-plugin
```

Optional: Submit to awesome-agent-skills catalog for discoverability.
