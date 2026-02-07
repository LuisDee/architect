# Architect

Architect is an upstream companion to [Conductor](https://github.com/obra/conductor).It takes a project description and decomposes it into a fully sequenced, dependency-aware set of implementation tracks - identifying architectural patterns the developer hasn't considered, injecting cross-cutting constraints, mapping interfaces between tracks, and ordering everything into parallelisable waves.

Architect generates briefs, not specs. Each track gets a lightweight handoff file with scope, key design decisions (as questions, not answers), and architectural context. When Conductor picks up a track, it reads the brief and runs its own interactive refinement — asking the developer targeted design questions before generating the full spec and plan.

During implementation, a discovery system catches emergent work that affects other tracks, and hooks enforce architectural consistency without requiring the developer to remember constraints.

Architect owns the architecture. Conductor owns the implementation.

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

The primary command. Reads Conductor files, runs architecture research (extracting signals from your requirements and matching them to 18 built-in patterns), presents recommendations in three tiers (strongly recommended / recommended / consider for later), then generates a complete system architecture with cross-cutting constraints, interface contracts, and a dependency DAG. From the DAG it produces wave-ordered tracks, each with a spec (including compressed context header), implementation plan (phased tasks with done criteria), and metadata. Installs workflow hooks and initializes the discovery system. Three review gates let you approve architecture, track list, and final output before anything is written.

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
                                      conductor/tracks/*/spec.md + plan.md + metadata.json
                                      conductor/tracks.md (registry)
                                              │
                                              ▼
    /conductor:implement             Hooks fire during implementation
    ────────────────────             ────────────────────────────────
    Reads spec.md (with               Before each phase → CC version check
      context header)                  Before consuming API → interface verify
    Follows plan.md tasks              After each task → discovery check
    Writes code                        Before phase complete → CC compliance
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
│   └── templates/                      # 11 generation templates
│       ├── context-header.md
│       ├── context-header-minimal.md
│       ├── architecture.md
│       ├── cross-cutting.md
│       ├── interfaces.md
│       ├── dependency-graph.md
│       ├── execution-sequence.md
│       ├── track-spec.md
│       ├── track-plan.md
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
│   ├── progress.py
│   └── regenerate_specs.py
└── README.md
```

## Conductor Compatibility

Architect is designed to work alongside Conductor without modifying any of Conductor's core files or conventions:

- **Reads** `conductor/product.md`, `conductor/tech-stack.md`, `conductor/workflow.md`, and `conductor/product-guidelines.md` as inputs. Never modifies these except to add one marker line to workflow.md.
- **Writes** to `conductor/tracks/` (spec.md, plan.md, metadata.json per track) and `conductor/tracks.md` in formats Conductor expects.
- **The single integration point** is the `<!-- ARCHITECT:HOOKS -->` marker in workflow.md. If removed, hooks are disabled and Conductor works normally.
- **All architect/ files** are separate from Conductor. Deleting the `architect/` directory cleanly removes Architect's artifacts without affecting Conductor.
- **Scripts require Python 3.10+** with stdlib only (no pip install needed).

## Design Documents

For full specification details, see the design docs in this repo:

- `architect-final-design.md` — The authoritative spec. Everything flows from this.
- `architect-plugin-structure.md` — Exact plugin file tree and format conventions.
- `architect-plugin-packaging.md` — Supplementary packaging and delivery context.

## License

MIT
