# Architect Plugin: What You're Actually Building

## TL;DR

It's a **Claude Code plugin** — a git repo with a specific directory structure that Claude Code auto-discovers. You install it with one command. It gives you 3 slash commands, 1 specialist agent, reference knowledge, templates, and Python scripts.

**Yes, move to local Claude Code on a repo branch.** This is the right call. Everything below is what Claude Code needs to generate.

---

## How Claude Code Plugins Work

A plugin is a folder with this structure:

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json        # Metadata (only "name" is required)
├── commands/              # Slash commands (auto-discovered .md files)
├── agents/                # Subagents (auto-discovered .md files)
├── skills/                # Agent Skills (subdirs with SKILL.md)
├── hooks/                 # Event handlers (hooks.json)
├── scripts/               # Helper scripts and utilities
├── .mcp.json              # MCP server config (optional)
└── README.md
```

**Auto-discovery:** Claude Code finds commands, agents, and skills automatically from their directories. You don't register them in plugin.json.

**Installation:**
```bash
# From GitHub (via marketplace)
claude plugin install architect@your-marketplace

# From local path (during development)
claude plugin install --path ./architect-plugin

# Or just symlink into your project
ln -s /path/to/architect-plugin .claude/plugins/architect
```

---

## Exact File Tree for Architect

```
architect-plugin/
│
├── .claude-plugin/
│   └── plugin.json                         # Plugin manifest
│
├── commands/                               # 3 slash commands
│   ├── architect-decompose.md              # /architect-decompose
│   ├── architect-sync.md                   # /architect-sync
│   └── architect-status.md                 # /architect-status
│
├── agents/                                 # 1 specialist subagent
│   └── architect-expert.md                 # The decomposition brain
│
├── skills/                                 # 1 skill (knowledge base)
│   └── architect/
│       ├── SKILL.md                        # Skill entry point
│       │
│       ├── references/                     # Built-in knowledge
│       │   ├── architecture-patterns.md    # Signal → pattern mapping
│       │   ├── cross-cutting-catalog.md    # Always-evaluate checklist
│       │   └── classification-guide.md     # Discovery decision tree
│       │
│       └── templates/                      # Generation templates
│           ├── context-header.md
│           ├── context-header-minimal.md
│           ├── architecture.md
│           ├── cross-cutting.md
│           ├── interfaces.md
│           ├── dependency-graph.md
│           ├── execution-sequence.md
│           ├── track-spec.md
│           ├── track-plan.md
│           ├── track-metadata.json
│           └── patch-phase.md
│
├── hooks/                                  # Workflow hooks (copied into project)
│   ├── project-hooks/                      # These get copied to architect/hooks/
│   │   ├── README.md                       # Hook activation reference
│   │   ├── constraint-update-check.md
│   │   ├── interface-verification.md
│   │   ├── discovery-check.md
│   │   ├── phase-validation.md
│   │   └── wave-sync.md
│   └── hooks.json                          # Plugin event handlers (if any)
│
├── scripts/                                # Python utilities
│   ├── validate_dag.py
│   ├── topological_sort.py
│   ├── inject_context.py
│   ├── merge_discoveries.py
│   ├── sync_check.py
│   ├── validate_wave_completion.py
│   ├── check_conductor_compat.py
│   ├── progress.py
│   └── regenerate_specs.py
│
├── .mcp.json                               # Optional: Context7 MCP config
├── README.md                               # Installation + quickstart
├── LICENSE                                 # MIT
│
└── examples/                               # Reference implementation
    └── sample-project/
        ├── architect/                      # What architect/ looks like after decompose
        └── conductor/                      # What conductor/ looks like after decompose
```

**Total: ~45 files, ~3500-4500 lines of content**

---

## What Each Component Does

### `.claude-plugin/plugin.json` — The Manifest

Minimal. Claude Code auto-discovers everything else.

```json
{
  "name": "architect",
  "version": "1.0.0",
  "description": "Project decomposition and architecture advisory for Conductor. Transforms project vision into fully sequenced, dependency-aware implementation tracks with cross-cutting constraints. Use when: (1) breaking down a project into tracks, (2) running /architect-decompose, /architect-sync, /architect-status, (3) a conductor/ directory exists and needs track generation.",
  "author": {
    "name": "Your Name"
  },
  "keywords": ["conductor", "architecture", "decomposition", "tracks", "planning"],
  "license": "MIT"
}
```

### `commands/architect-decompose.md` — The Main Slash Command

This is the full step-by-step instruction set. When the user types `/architect-decompose`, Claude reads this file and follows it.

```markdown
---
description: Decompose project into Conductor tracks with architecture research
---

# /architect-decompose

You are performing project decomposition for Conductor.

## Pre-flight Checks

1. Verify conductor/ directory exists. If not: tell user to run Conductor setup first.
2. Run: `python ${CLAUDE_PLUGIN_ROOT}/scripts/check_conductor_compat.py`
3. Read these Conductor files:
   - conductor/product.md
   - conductor/tech-stack.md
   - conductor/workflow.md
   - conductor/product-guidelines.md (if exists)

## Step 1: Gap Analysis
[... full protocol from design spec ...]

## Step 2: Architecture Research
Read ${CLAUDE_PLUGIN_ROOT}/skills/architect/references/architecture-patterns.md
[... signal extraction, pattern matching, research tools ...]

## Step 3: Generate Architecture
[... using templates from ${CLAUDE_PLUGIN_ROOT}/skills/architect/templates/ ...]

## Step 4: Generate Tracks
[... spec, plan, metadata per track ...]

## Step 5: Install Hooks
Copy ${CLAUDE_PLUGIN_ROOT}/hooks/project-hooks/ to architect/hooks/
[... marker line, discovery dirs ...]
```

**Key detail:** Commands reference plugin files via `${CLAUDE_PLUGIN_ROOT}` — Claude Code resolves this to the plugin's install path.

### `agents/architect-expert.md` — The Specialist Subagent

For Agent Teams scenarios where the lead spawns an architect specialist:

```markdown
---
name: architect-expert
description: >
  Architecture decomposition specialist. Invoke when the project needs
  to be broken down into implementation tracks, when architecture
  research is needed, or when cross-cutting patterns need identification.
  Works with Conductor's track system.
tools: Read, Grep, Glob, Bash, Write
skills: architect
---

You are an expert software architect specializing in project decomposition.

Your role:
- Analyze project requirements and identify architectural patterns
- Decompose systems into dependency-ordered implementation tracks
- Identify cross-cutting concerns developers haven't considered
- Generate Conductor-compatible track specs, plans, and metadata

Key references (read before acting):
- ${CLAUDE_PLUGIN_ROOT}/skills/architect/references/architecture-patterns.md
- ${CLAUDE_PLUGIN_ROOT}/skills/architect/references/cross-cutting-catalog.md
- ${CLAUDE_PLUGIN_ROOT}/skills/architect/references/classification-guide.md

You generate files into:
- architect/ directory (architecture, cross-cutting, interfaces, etc.)
- conductor/tracks/ directory (specs, plans, metadata per track)

[... behavioral instructions, output format, review gates ...]
```

### `skills/architect/SKILL.md` — The Knowledge Base

This is auto-activated when Claude detects relevance. It provides the background knowledge.

```markdown
---
name: architect
description: >
  Architecture decomposition knowledge for Conductor projects.
  Auto-activates when: working with conductor/ directories, discussing
  project decomposition, identifying cross-cutting concerns, or
  processing architectural discoveries.
---

# Architect: Project Decomposition Knowledge

## When This Skill Applies
- Project has a conductor/ directory
- User discusses breaking down a project into tracks
- User mentions cross-cutting concerns, dependencies, or waves
- Discovery files exist in architect/discovery/

## Key References
Read these before generating architecture:
- references/architecture-patterns.md — Signal-to-pattern mapping
- references/cross-cutting-catalog.md — Always-evaluate checklist
- references/classification-guide.md — Discovery classification

## Templates
Use these when generating files:
- templates/track-spec.md — Per-track specification
- templates/track-plan.md — Per-track implementation plan
- templates/context-header.md — Compressed context (~2000 tokens)
- templates/patch-phase.md — Retroactive compliance phase

## Scripts
Run via bash when needed:
- `python scripts/validate_dag.py` — Check for dependency cycles
- `python scripts/topological_sort.py` — Generate wave sequence
- `python scripts/inject_context.py` — Build compressed headers
- `python scripts/merge_discoveries.py` — Process pending discoveries
- `python scripts/validate_wave_completion.py` — Quality gate

## Architecture Overview
[... condensed version of how the system works ...]
```

### `hooks/project-hooks/discovery-check.md` — A Workflow Hook

These files get **copied into the project** (not read from the plugin at runtime). They become part of the project's `architect/hooks/` directory and are read by whichever agent implements the tracks.

```markdown
# Discovery Check Protocol

**When:** After completing each task during /conductor:implement

## Procedure

1. After completing a task, assess:
   - Did this reveal assumptions that don't hold?
   - Is functionality missing from any planned track?
   - Are there uncaptured dependencies?
   - Should a cross-cutting concern change?

2. If YES → write discovery to architect/discovery/pending/
   Filename: {track_id}-{ISO-timestamp}-{6-char-random-hex}.md

3. Classify using the decision tree:
   [... full decision tree from classification-guide.md ...]

4. Continue with current work. Don't scope-creep.
```

### `scripts/validate_dag.py` — An Actual Executable Script

Real Python code, not prompts:

```python
#!/usr/bin/env python3
"""Validate dependency graph for cycles."""
import json, sys
from collections import defaultdict, deque
from pathlib import Path

def load_tracks():
    """Load dependency info from all track metadata files."""
    ...

def detect_cycles(graph):
    """Kahn's algorithm."""
    ...

if __name__ == "__main__":
    ...
```

---

## Installation Flow

### For Development (What You Do Now)

```bash
# 1. Create the plugin repo
mkdir architect-plugin && cd architect-plugin
git init && git checkout -b main

# 2. Create the structure
mkdir -p .claude-plugin commands agents skills/architect/references \
  skills/architect/templates hooks/project-hooks scripts examples

# 3. Let Claude Code generate the content
claude
> Read the design spec (architect-final-design.md) and generate all
  plugin files. Start with plugin.json, then SKILL.md, then references,
  then templates, then scripts, then commands, then agents, then hooks.

# 4. Test locally in a sample project
cd ../test-project
claude plugin install --path ../architect-plugin
claude
> /architect-decompose
```

### For Users (After Publishing)

```bash
# Option A: Self-hosted marketplace
# In your plugin repo, add .claude-plugin/marketplace.json:
{
  "plugins": [{
    "name": "architect",
    "source": ".",
    "description": "...",
    "version": "1.0.0"
  }]
}

# Users add your marketplace + install:
claude plugin marketplace add your-github-user/architect-plugin
claude plugin install architect@architect-plugin

# Option B: Community marketplace submission
# Submit to awesome-agent-skills or similar catalogs

# Option C: Direct git clone (simplest)
git clone https://github.com/you/architect-plugin ~/.claude/plugins/architect
```

---

## Gemini CLI Compatibility

Gemini CLI doesn't use the Claude Code plugin format, but can read the same content files. Add thin TOML wrappers:

```
architect-plugin/
└── gemini/                              # Gemini CLI integration
    ├── architect-decompose.toml
    ├── architect-sync.toml
    └── architect-status.toml
```

Each TOML file points to the shared skill content. The references, templates, hooks, and scripts are agent-agnostic Markdown and Python — they work everywhere.

---

## What Claude Code Needs to Build This

Feed Claude Code these files as context:

1. **architect-final-design.md** — The full spec (what to build)
2. **architect-plugin-packaging.md** — The earlier packaging doc (supplementary)
3. **This file** — The exact structure and format conventions

Then prompt:

```
Read the architect-final-design.md spec and generate the Architect plugin
following the Claude Code plugin structure. Generate files in this order:

1. .claude-plugin/plugin.json
2. skills/architect/SKILL.md
3. skills/architect/references/architecture-patterns.md
4. skills/architect/references/cross-cutting-catalog.md
5. skills/architect/references/classification-guide.md
6. skills/architect/templates/*.md (all templates)
7. scripts/*.py (all Python scripts)
8. commands/architect-decompose.md
9. commands/architect-sync.md
10. commands/architect-status.md
11. agents/architect-expert.md
12. hooks/project-hooks/*.md
13. README.md
```

Estimated effort: **2-4 hours of Claude Code generation + review cycles.**

---

## Summary

| Question | Answer |
|----------|--------|
| What is it? | A Claude Code plugin (git repo with specific structure) |
| How many files? | ~45 files, ~3500-4500 lines |
| How is it installed? | `claude plugin install` or git clone |
| Is it a repo clone? | Yes — a git repo that users clone or install via marketplace |
| Move to local Claude Code? | **Yes.** Create the repo, feed it the design spec, let Claude Code generate the files on a branch. |
| What format are the files? | Markdown (commands, agents, skills, hooks) + Python (scripts) + JSON (plugin.json, metadata) |
| Does it work with Gemini CLI? | The core content (references, templates, hooks, scripts) is agent-agnostic. Add TOML wrappers for Gemini. |
