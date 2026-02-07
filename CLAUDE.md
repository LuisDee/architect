# Architect Plugin

## What This Is
A Claude Code plugin that decomposes projects into Conductor-compatible implementation tracks. It sits upstream of Conductor — reading product.md/tech-stack.md, running architecture research, and generating fully sequenced tracks with cross-cutting constraints.

## Design Docs (READ THESE FIRST)
- `architect-final-design.md` — The authoritative spec. Everything flows from this.
- `architect-plugin-structure.md` — Exact plugin file tree and format conventions.
- `architect-plugin-packaging.md` — Supplementary packaging context.

## Plugin Structure
This follows the standard Claude Code plugin format:
```
architect-plugin/
├── .claude-plugin/plugin.json
├── commands/           # 3 slash commands (.md with YAML frontmatter)
├── agents/             # 1 subagent (.md with YAML frontmatter)  
├── skills/architect/   # SKILL.md + references/ + templates/
├── hooks/project-hooks/  # Copied into user projects at decompose time
├── scripts/            # Python utilities (real executable code)
├── examples/           # Sample project showing output
└── README.md
```

## Key Conventions
- Commands use `${CLAUDE_PLUGIN_ROOT}` to reference plugin files
- Skills auto-activate based on YAML frontmatter description
- Hooks in `hooks/project-hooks/` are PROJECT hooks (copied into architect/hooks/ during decompose) — NOT Claude Code event hooks
- Scripts are real Python (stdlib only, no pip dependencies)
- All templates use Markdown
- Keep SKILL.md under 500 lines; detailed content goes in references/

## Syncing Gemini CLI Commands
After changing any command in commands/*.md, run `scripts/sync-gemini-commands.sh` to update the Gemini CLI commands.

## Implementation Order
Phase 1 (MVP): plugin.json → SKILL.md → references → templates → scripts → commands → agent → project-hooks → README
Phase 2: examples/sample-project
Phase 3: Gemini CLI TOML wrappers

## Testing
After generating, test by:
1. Creating a test project with minimal conductor/ files
2. Installing plugin: `claude plugin install --path .`
3. Running `/architect-decompose`
