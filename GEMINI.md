# Architect Plugin

## What This Is
A Gemini CLI extension that decomposes projects into Conductor-compatible implementation tracks. It sits upstream of Conductor — reading product.md/tech-stack.md, running architecture research, and generating fully sequenced tracks with cross-cutting constraints.

## Design Docs (READ THESE FIRST)
- `architect-final-design.md` — The authoritative spec. Everything flows from this.
- `architect-plugin-structure.md` — Exact plugin file tree and format conventions.
- `architect-plugin-packaging.md` — Supplementary packaging context.

## Plugin Structure
This follows the standard Gemini CLI extension format:
```
architect-plugin/
├── gemini-extension.json
├── commands/           # 3 slash commands (.toml with prompt field)
├── agents/             # 4 subagents (.md with YAML frontmatter)
│   ├── architect-expert.md    # Main orchestrator / solo executor
│   ├── pattern-matcher.md     # Architecture research (isolated context)
│   ├── codebase-analyzer.md   # Codebase exploration (isolated context)
│   └── brief-generator.md     # Per-track brief generation (isolated context)
├── skills/architect/   # SKILL.md + references/ + templates/
├── hooks/project-hooks/  # Copied into user projects at decompose time
├── scripts/            # Python utilities (real executable code)
├── examples/           # Sample project showing output
└── README.md
```

## Key Conventions
- Commands use `${extensionPath}` to reference plugin files
- Skills auto-activate based on YAML frontmatter description
- Hooks in `hooks/project-hooks/` are PROJECT hooks (copied into architect/hooks/ during decompose) — NOT Gemini CLI event hooks
- Scripts are real Python (stdlib only, no pip dependencies)
- All templates use Markdown
- Keep SKILL.md under 500 lines; detailed content goes in references/

## Syncing Gemini CLI Commands
After changing any command in commands/*.md, run `scripts/sync-gemini-commands.sh` to update the Gemini CLI commands.

## Implementation Order
Phase 1 (MVP): plugin.json → SKILL.md → references → templates → scripts → commands → agent → project-hooks → README
Phase 2: examples/sample-project
Phase 3: Gemini CLI TOML wrappers

## Sequential Execution Mode
The `/architect-decompose` command on Gemini CLI runs in **sequential mode** (no parallel sub-agents). This is functionally identical to the Claude Code parallel mode but uses more context:

- Reference files (architecture-patterns.md, cross-cutting-catalog.md) are read directly in the current context
- Codebase exploration happens in the current context
- Track briefs are generated one at a time in the current context
- This is acceptable because Gemini CLI has a ~1M token context window

The sub-agent definitions in `agents/` (pattern-matcher.md, codebase-analyzer.md, brief-generator.md) exist for Claude Code's parallel execution. On Gemini CLI, the same logic runs sequentially as a fallback.

If Gemini CLI sub-agent support matures and parallel execution lands, the command will automatically use the parallel path.

## Testing
After generating, test by:
1. Creating a test project with minimal conductor/ files
2. Installing extension: `gemini extensions install ./architect`
3. Running `/architect:decompose`
4. Verify sequential fallback works (no sub-agent errors)
5. Verify all artifacts and briefs are generated correctly
6. Verify review gates still pause for developer approval
