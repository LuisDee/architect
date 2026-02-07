# Architect

Architect is an upstream companion to [Conductor](https://github.com/obra/conductor). It reads your project's product.md and tech-stack.md, performs architecture research to identify patterns and cross-cutting concerns you haven't considered, and generates fully sequenced, dependency-aware track briefs. Each brief captures scope, key design decisions (as questions, not answers), and cross-cutting constraints. When you run `/conductor:implement`, Conductor reads the brief and drives interactive spec and plan generation with developer input. Architect's value is embedded in context headers, hooks, and a living architecture that evolves through automated discovery.

## Installation

### Option A: Plugin marketplace (recommended)

```bash
claude plugin install architect@your-marketplace
```

### Option B: Local path (during development)

```bash
claude plugin install --path /path/to/architect-plugin
```

### Option C: Git clone

```bash
# Per-project
git clone https://github.com/<org>/architect-plugin .claude/plugins/architect

# Global (available in all projects)
git clone https://github.com/<org>/architect-plugin ~/.claude/plugins/architect
```

## Quick Start

```bash
# 1. Set up Conductor (creates conductor/product.md, tech-stack.md, workflow.md)
/conductor:setup

# 2. Decompose into tracks (architecture research → track generation → hook install)
/architect-decompose

# 3. Start building (Architect hooks guide compliance and discovery automatically)
/conductor:implement
```

## Commands

### /architect-decompose

The primary command. Reads Conductor files, runs architecture research (extracting signals from your requirements and matching them to 18 built-in patterns), presents recommendations in three tiers (strongly recommended / recommended / consider for later), then generates a complete system architecture with cross-cutting constraints, interface contracts, and a dependency DAG. From the DAG it produces wave-ordered track briefs, each with scope, key design decisions (questions for the developer), architectural notes, and a compressed context header. Does NOT generate spec.md or plan.md — Conductor does that interactively with developer input during `/conductor:implement`. Installs workflow hooks and initializes the discovery system. Three review gates let you approve architecture, track list, and final output before anything is written.

### /architect-sync

Processes pending discoveries found during implementation. Runs the merge script (deduplication, conflict detection, urgency escalation), executes actions by classification (new tracks, extensions, dependency changes, cross-cutting updates, architecture changes, interface mismatches), checks for drift between artifacts and metadata, and runs the wave completion quality gate when triggered at a wave boundary. Surfaces results to the developer with clear fix/waive/force-advance options.

### /architect-status

Shows bird's-eye progress: complexity-weighted completion per wave and overall, pending discoveries (with BLOCKING items highlighted), cross-cutting version drift, interface mismatches, blocked tracks, and unapplied patches. Ends with actionable recommendations for what to do next.

## How It Works

```
    /conductor:setup                     /architect-decompose
    ────────────────                     ────────────────────
    Creates:                             Reads conductor/* files
      conductor/product.md          ──▶  Extracts architectural signals
      conductor/tech-stack.md       ──▶  Matches to 18 built-in patterns
      conductor/workflow.md              Evaluates 20 cross-cutting concerns
                                         Presents recommendations (3 tiers)
                                              │
                                    Developer accepts/rejects/modifies
                                              │
                                              ▼
                                    Generates:
                                      architect/architecture.md
                                      architect/cross-cutting.md (v1)
                                      architect/interfaces.md
                                      architect/dependency-graph.md
                                      architect/execution-sequence.md
                                      architect/hooks/ (5 workflow hooks)
                                      architect/discovery/ (pending + processed)
                                      conductor/tracks/*/brief.md + metadata.json
                                      conductor/tracks.md (registry)
                                              │
                                              ▼
    /conductor:implement             Hooks fire during implementation
    ────────────────────             ────────────────────────────────
    Reads brief.md                    Before each phase → CC version check
    Generates spec.md + plan.md       Before consuming API → interface verify
      interactively with developer    After each task → discovery check
    Follows plan.md tasks             Before phase complete → CC compliance
    Writes code                       After track complete → wave sync
                                       After track complete → wave sync
                                              │
                                              ▼
                                    /architect-sync (at wave boundary)
                                    ─────────────────────────────────
                                    Processes discoveries
                                    Runs quality gate
                                    Advances to next wave
```

## File Structure

```
architect-plugin/
├── .claude-plugin/plugin.json          # Plugin manifest
├── commands/                           # 3 slash commands
│   ├── architect-decompose.md
│   ├── architect-sync.md
│   └── architect-status.md
├── agents/                             # 1 specialist subagent
│   └── architect-expert.md
├── skills/architect/                   # Knowledge base
│   ├── SKILL.md                        # Skill entry point
│   ├── references/                     # Built-in pattern knowledge
│   │   ├── architecture-patterns.md    # 18 patterns with signals + trade-offs
│   │   ├── cross-cutting-catalog.md    # 20-item always-evaluate checklist
│   │   └── classification-guide.md     # Discovery classification decision tree
│   └── templates/                      # 10 generation templates
│       ├── context-header.md
│       ├── context-header-minimal.md
│       ├── architecture.md
│       ├── cross-cutting.md
│       ├── interfaces.md
│       ├── dependency-graph.md
│       ├── execution-sequence.md
│       ├── track-brief.md
│       ├── track-metadata.json
│       └── patch-phase.md
├── hooks/project-hooks/                # Copied into user projects
│   ├── README.md
│   ├── 01-constraint-update-check.md
│   ├── 02-interface-verification.md
│   ├── 03-discovery-check.md
│   ├── 04-phase-validation.md
│   └── 05-wave-sync.md
├── scripts/                            # Python utilities (stdlib only)
│   ├── validate_dag.py
│   ├── topological_sort.py
│   ├── inject_context.py
│   ├── merge_discoveries.py
│   ├── sync_check.py
│   ├── validate_wave_completion.py
│   ├── check_conductor_compat.py
│   └── progress.py
└── README.md
```

## Conductor Compatibility

Architect is designed to work alongside Conductor without modifying any of Conductor's core files or conventions:

- **Reads** `conductor/product.md`, `conductor/tech-stack.md`, `conductor/workflow.md`, and `conductor/product-guidelines.md` as inputs. Never modifies these except to add one marker line to workflow.md.
- **Writes** to `conductor/tracks/` (brief.md + metadata.json per track) and `conductor/tracks.md` in formats Conductor expects. Conductor generates spec.md and plan.md interactively at implementation time.
- **The single integration point** is the `<!-- ARCHITECT:HOOKS -->` marker in workflow.md. If removed, hooks are disabled and Conductor works normally.
- **All architect/ files** are separate from Conductor. Deleting the `architect/` directory cleanly removes Architect's artifacts without affecting Conductor.
- **Scripts require Python 3.10+** with stdlib only (no pip install needed).

## Design Documents

For full specification details, see the design docs in this repo:

- `architect-final-design.md` — The original spec (superseded in part by the amendment).
- `architect-design-ammendment.md` — Brief-based handoff model amendment.
- `architect-refactoring-plan.md` — Detailed refactoring plan from spec to brief model.
- `architect-plugin-structure.md` — Plugin file tree and format conventions.
- `architect-plugin-packaging.md` — Supplementary packaging and delivery context.

## License

MIT
