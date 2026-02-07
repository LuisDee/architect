# Architect: Claude Code + Gemini CLI Compatibility

## Side-by-Side Format Comparison

| Feature | Claude Code Plugin | Gemini CLI Extension |
|---------|-------------------|---------------------|
| **Manifest** | `.claude-plugin/plugin.json` | `gemini-extension.json` (at root) |
| **Commands** | `commands/*.md` (Markdown + YAML frontmatter) | `commands/*.toml` (TOML format) |
| **Agents** | `agents/*.md` (Markdown + YAML frontmatter) | `agents/*.md` (Markdown, experimental) |
| **Skills** | `skills/*/SKILL.md` | `skills/*/SKILL.md` |
| **Hooks** | `hooks/hooks.json` or inline in plugin.json | `hooks/hooks.json` |
| **Context file** | `CLAUDE.md` (auto-loaded) | `GEMINI.md` (auto-loaded, or custom via `contextFileName`) |
| **MCP servers** | `.mcp.json` at root | `mcpServers` in `gemini-extension.json` |
| **Install from GitHub** | `claude plugin install <url>` | `gemini extensions install <url>` |
| **Install local** | `claude plugin install --path ./dir` | `gemini extensions install ./dir` |
| **Path variable** | `${CLAUDE_PLUGIN_ROOT}` | `${extensionPath}` |
| **Command invoke** | `/architect:decompose` | `/decompose` (or `/architect.decompose` on conflict) |
| **Args in commands** | `$ARGUMENTS` | `{{args}}` |
| **Command namespacing** | `plugin-name:command-name` | `extension-name.command-name` (on conflict) |

---

## Key Differences That Matter

### 1. Commands: Markdown vs TOML (THE BIG ONE)

**Claude Code** uses Markdown files with YAML frontmatter:
```markdown
---
description: Decompose a project into architectural tracks
---
You are an expert software architect...
[hundreds of lines of instructions]
```

**Gemini CLI** uses TOML files with a `prompt` field:
```toml
description = "Decompose a project into architectural tracks"
prompt = """
You are an expert software architect...
[hundreds of lines of instructions]
"""
```

**Impact:** The commands ARE the core of Architect. All the intelligence lives in
the prompt text within these files. The actual prompt content is identical —
only the wrapper format differs.

### 2. Manifest Files (trivial)

**Claude Code:** `.claude-plugin/plugin.json`
```json
{
  "name": "architect",
  "version": "1.0.0",
  "description": "Decomposes projects into sequenced tracks..."
}
```

**Gemini CLI:** `gemini-extension.json` (at root)
```json
{
  "name": "architect",
  "version": "1.0.0",
  "description": "Decomposes projects into sequenced tracks..."
}
```

Nearly identical JSON. Both live in slightly different locations.

### 3. Context Files (trivial)

Claude Code loads `CLAUDE.md`, Gemini CLI loads `GEMINI.md`.
Same content, different filename.

### 4. Path Variables

- Claude Code: `${CLAUDE_PLUGIN_ROOT}`
- Gemini CLI: `${extensionPath}`

Used in scripts and hook configurations to reference files within the plugin.

### 5. Argument Substitution

- Claude Code: `$ARGUMENTS`
- Gemini CLI: `{{args}}`

### 6. Agent Format

Both use Markdown files in `agents/` directory. Gemini's sub-agents are
experimental but the format is nearly identical. Claude uses YAML frontmatter
for metadata; Gemini may differ slightly but both are Markdown-based.

### 7. Skills Format

Both use `skills/*/SKILL.md`. This is essentially identical.

### 8. Hooks Format

Both use `hooks/hooks.json`. The event names and matchers may differ but
the structural format is the same JSON.

---

## Compatibility Strategy

The good news: **~80% of Architect is format-agnostic.** The templates,
reference docs, Python scripts, and all the architectural knowledge live
in plain Markdown and Python files that both platforms can read. The
platform-specific parts are thin wrappers.

### Option A: Dual-Format Repo (Recommended)

Ship both formats from the same repo. The shared content (templates,
references, scripts, sample project) lives once. Platform-specific
wrappers are generated or maintained side by side.

```
architect/
├── .claude-plugin/
│   └── plugin.json                    # Claude Code manifest
├── gemini-extension.json              # Gemini CLI manifest
├── CLAUDE.md                          # Claude Code context
├── GEMINI.md                          # Gemini CLI context (same content)
│
├── commands/
│   ├── claude/                        # Claude Code commands (Markdown)
│   │   ├── architect-decompose.md
│   │   ├── architect-sync.md
│   │   └── architect-status.md
│   ├── gemini/                        # Gemini CLI commands (TOML)
│   │   ├── architect/
│   │   │   ├── decompose.toml
│   │   │   ├── sync.toml
│   │   │   └── status.toml
│   ├── prompts/                       # SHARED prompt content
│   │   ├── decompose-prompt.md
│   │   ├── sync-prompt.md
│   │   └── status-prompt.md
│
├── agents/                            # Same format, both platforms
│   └── architect-expert.md
├── skills/                            # Same format, both platforms
│   └── architect/
│       ├── SKILL.md
│       ├── references/
│       └── templates/
├── hooks/                             # Platform-specific hooks
│   ├── hooks.json                     # Used by both (if events align)
│   └── project-hooks/                 # Architect's workflow hooks (read by agent)
├── scripts/                           # Python, works everywhere
│   ├── validate_dag.py
│   ├── topological_sort.py
│   └── ...
└── examples/
    └── sample-project/
```

**How the command wrappers work:**

Claude Code `commands/claude/architect-decompose.md`:
```markdown
---
description: Decompose a project into architectural tracks
---
<!-- This command wraps the shared prompt content -->
<!-- Read the full prompt from the shared location -->

Read and follow the instructions in ${CLAUDE_PLUGIN_ROOT}/commands/prompts/decompose-prompt.md

$ARGUMENTS
```

Gemini CLI `commands/gemini/architect/decompose.toml`:
```toml
description = "Decompose a project into architectural tracks"
prompt = """
Read and follow the instructions in ${extensionPath}/commands/prompts/decompose-prompt.md

{{args}}
"""
```

**The actual prompt intelligence lives in `commands/prompts/decompose-prompt.md`**
— a plain Markdown file that both platforms read. The .md and .toml wrappers
are ~5 lines each that just point to the shared content.

### Option B: Build Script

Maintain Claude Code format as canonical, run a build script that generates
the Gemini extension:

```bash
# scripts/build-gemini-extension.sh
# Converts commands/*.md → commands/*.toml
# Copies CLAUDE.md → GEMINI.md
# Generates gemini-extension.json from plugin.json
# Replaces ${CLAUDE_PLUGIN_ROOT} → ${extensionPath}
# Replaces $ARGUMENTS → {{args}}
```

Pros: Single source of truth, no drift.
Cons: Extra build step, harder for contributors.

### Option C: Shared Prompt Files Only (Simplest)

Don't try to make a single repo install on both platforms. Instead:

```
architect/                    # Claude Code plugin (primary)
architect-gemini/             # Gemini CLI extension (generated or manual)
architect-core/               # Shared: templates, references, scripts
```

`architect-core/` is a git submodule or symlinked into both.

Pros: Clean separation, no path variable conflicts.
Cons: Two repos to maintain.

---

## Recommended Approach: Option A with a Twist

Use Option A (dual-format repo) but with an **install helper** that
symlinks or copies the right files into the right location:

```bash
# For Claude Code users:
git clone https://github.com/LuisDee/architect.git
cd architect
./install.sh claude
# → Creates symlinks so Claude Code sees commands/claude/ as commands/
# → Ensures .claude-plugin/plugin.json is in place

# For Gemini CLI users:
git clone https://github.com/LuisDee/architect.git
cd architect
./install.sh gemini
# → Creates symlinks so Gemini CLI sees commands/gemini/ as commands/
# → Ensures gemini-extension.json is in place
```

OR even simpler — both platforms auto-discover from their respective
locations, so having both formats in the repo simultaneously works.
Claude Code ignores TOML files, Gemini CLI ignores .claude-plugin/.

**The key insight:** Claude Code's command auto-discovery looks for
`commands/*.md`. Gemini CLI's command auto-discovery looks for
`commands/*.toml`. They won't conflict because they look for
different file extensions.

So you could actually do:

```
architect/
├── .claude-plugin/plugin.json         # Claude ignores gemini-extension.json
├── gemini-extension.json              # Gemini ignores .claude-plugin/
├── CLAUDE.md                          # Claude loads this
├── GEMINI.md                          # Gemini loads this
├── commands/
│   ├── architect-decompose.md         # Claude picks this up
│   ├── architect-sync.md              # Claude picks this up
│   ├── architect-status.md            # Claude picks this up
│   ├── architect/                     # Gemini namespacing
│   │   ├── decompose.toml            # Gemini picks this up
│   │   ├── sync.toml                 # Gemini picks this up
│   │   └── status.toml               # Gemini picks this up
├── agents/
│   └── architect-expert.md            # Both platforms use this
├── skills/
│   └── architect/
│       └── SKILL.md                   # Both platforms use this
├── scripts/                           # Both platforms use this
├── hooks/
│   └── project-hooks/                 # Both platforms use this
└── ...
```

Claude Code sees `commands/*.md` → loads 3 commands.
Gemini CLI sees `commands/**/*.toml` → loads 3 commands.
Neither platform chokes on the other's files.

---

## What Needs to Be Platform-Specific

### Commands (3 files × 2 formats = 6 files)
The TOML wrappers are thin. The actual prompt content can be:
- **Inlined** in both formats (duplicate but explicit)
- **Referenced** via file read instruction (DRY but adds indirection)

For a plugin this complex, I'd inline the prompts in both formats.
Yes, it means maintaining 2 copies of each command prompt, but:
- Commands change rarely after stabilization
- The alternative (file-read indirection) adds fragility
- It's only 3 commands

### Context Files (CLAUDE.md + GEMINI.md)
Same content, two filenames. Maintain one, copy to the other.
Or just have both files with identical content.

### Manifest Files (plugin.json + gemini-extension.json)
Two small JSON files. Trivially maintained.

### Path Variables in Scripts
The Python scripts don't use `${CLAUDE_PLUGIN_ROOT}` or `${extensionPath}`.
They're called with explicit paths from the commands. No changes needed.

### Hooks
`hooks/hooks.json` format might differ between platforms for
**event hooks** (PreToolUse, PostToolUse etc). But Architect's hooks
are **project hooks** — they're Markdown files read by the agent during
implementation, not event-driven hooks. So they work identically on
both platforms.

---

## Limitations & Gotchas

### 1. Gemini CLI Sub-Agents Are Experimental
Gemini marks sub-agents as experimental. The `architect-expert.md` agent
may not activate as reliably on Gemini as on Claude Code. Test this.

### 2. Gemini CLI Skills Are Experimental
Agent skills (`skills/*/SKILL.md`) also require `experimental.skills`
to be enabled in Gemini CLI. Users will need to enable this.

### 3. Command Argument Handling
Claude Code appends `$ARGUMENTS` to the prompt. Gemini CLI uses
`{{args}}` for injection or appends if no placeholder is present.
The decompose command doesn't take arguments (it's interactive),
so this is a non-issue for Architect specifically.

### 4. File Reading in Prompts
Claude Code commands can reference `${CLAUDE_PLUGIN_ROOT}/path/to/file`
and the agent reads it. Gemini CLI commands can use `!{cat file}` for
shell command injection in TOML prompts. Different mechanism, same result.

### 5. Hook Event Names
If you ever add Claude Code event hooks (PreToolUse, PostToolUse),
Gemini CLI has different event names. Cross that bridge when you get there.

### 6. Context Window Differences
Gemini 2.5 Pro has a 1M token context window vs Claude's ~200K.
Not a limitation but worth knowing — Architect's prompts are well within
both limits.

---

## Implementation Plan

### Phase 1: Ship Claude Code Plugin (current work)
Finish the refactoring to brief-based model. Ship it. Get it working.

### Phase 2: Add Gemini CLI Compatibility (~2-4 hours)

1. **Add `gemini-extension.json`** at repo root:
   ```json
   {
     "name": "architect",
     "version": "1.0.0",
     "description": "Decomposes projects into sequenced, dependency-aware tracks for Conductor."
   }
   ```

2. **Create TOML command wrappers** (3 files):
   Convert each `commands/*.md` to a corresponding TOML file under
   `commands/architect/*.toml`. The prompt content is copied from the
   Markdown file's body (everything after the YAML frontmatter).

3. **Create `GEMINI.md`** by copying `CLAUDE.md` content.

4. **Replace path variables** in TOML commands:
   `${CLAUDE_PLUGIN_ROOT}` → `${extensionPath}`

5. **Test on Gemini CLI:**
   ```bash
   gemini extensions install --path ./architect
   gemini
   > /architect:decompose
   ```

6. **Update README** with dual install instructions:
   ```markdown
   ## Installation

   **Claude Code:**
   git clone https://github.com/LuisDee/architect.git
   claude plugin install --path ./architect

   **Gemini CLI:**
   git clone https://github.com/LuisDee/architect.git
   gemini extensions install ./architect
   ```

### Phase 3: Validate (1-2 hours)
- Run decompose on a test project with Gemini CLI
- Verify briefs generate correctly
- Verify hooks are read during implementation
- Test with Conductor (if Conductor also has Gemini CLI support)

---

## Summary

The two platforms are remarkably similar. Both have:
- Slash commands (different wrapper format: MD vs TOML)
- Agents/sub-agents (both Markdown)
- Skills (both SKILL.md)
- Hooks (both hooks.json)
- Context files (CLAUDE.md vs GEMINI.md)
- GitHub-based install

The core intellectual property — the templates, references, scripts,
architectural patterns, brief format, discovery system — is all
platform-agnostic Markdown and Python. The platform-specific layer
is ~6 thin wrapper files (3 TOML commands + manifest + context file + 
any path variable substitutions).

**Effort estimate: 2-4 hours after the Claude Code plugin is stable.**
**Ongoing maintenance: minimal — commands rarely change after stabilization.**
