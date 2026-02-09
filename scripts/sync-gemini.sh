#!/usr/bin/env bash
# sync-gemini.sh
#
# Generates Gemini CLI-compatible files from Claude Code canonical sources:
#   1. commands/*.md  → commands/architect/*.toml  (command sync)
#   2. agents/*.md    → agents/gemini/*.md         (agent tool-name mapping)
#
# Safe to run repeatedly — overwrites existing generated files.
# No dependencies beyond bash, sed, and awk.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─────────────────────────────────────────────────────────────
# Part 1: Command sync (commands/*.md → commands/architect/*.toml)
# ─────────────────────────────────────────────────────────────

COMMANDS_DIR="$REPO_DIR/commands"
TOML_DIR="$COMMANDS_DIR/architect"

mkdir -p "$TOML_DIR"

cmd_count=0

for md_file in "$COMMANDS_DIR"/*.md; do
    [ -f "$md_file" ] || continue

    basename="$(basename "$md_file" .md)"

    # Verify file has YAML frontmatter (starts with ---)
    head_line="$(head -1 "$md_file")"
    if [ "$head_line" != "---" ]; then
        echo "SKIP: $basename.md (no YAML frontmatter)"
        continue
    fi

    # Extract description from frontmatter (between first and second ---)
    description="$(awk '/^---$/{n++; next} n==1 && /^description:/{sub(/^description:[[:space:]]*/, ""); print; exit}' "$md_file")"

    if [ -z "$description" ]; then
        echo "SKIP: $basename.md (no description in frontmatter)"
        continue
    fi

    # Extract prompt body (everything after the closing --- of frontmatter)
    body="$(awk 'BEGIN{n=0} /^---$/{n++; if(n==2){found=1; next}} found{print}' "$md_file")"

    # Strip leading blank lines
    body="$(echo "$body" | sed '/./,$!d')"

    # Replace platform-specific variables
    body="$(echo "$body" | sed 's/\${CLAUDE_PLUGIN_ROOT}/\${extensionPath}/g')"
    body="$(echo "$body" | sed 's/\$ARGUMENTS/{{args}}/g')"

    # Derive toml filename: architect-decompose -> decompose
    toml_name="${basename#architect-}"
    toml_file="$TOML_DIR/$toml_name.toml"

    # Write TOML file
    {
        printf 'description = "%s"\n' "$description"
        printf 'prompt = """\n'
        printf '%s\n' "$body"
        printf '"""\n'
    } > "$toml_file"

    echo "OK: $basename.md -> architect/$toml_name.toml"
    cmd_count=$((cmd_count + 1))
done

echo ""
echo "Commands: generated $cmd_count TOML file(s) in commands/architect/"

# ─────────────────────────────────────────────────────────────
# Part 2: Agent sync (agents/*.md → agents/gemini/*.md)
# ─────────────────────────────────────────────────────────────

AGENTS_DIR="$REPO_DIR/agents"
GEMINI_AGENTS_DIR="$AGENTS_DIR/gemini"

mkdir -p "$GEMINI_AGENTS_DIR"

# Tool name mapping: Claude Code PascalCase → Gemini CLI snake_case
map_tool_name() {
    case "$1" in
        Read)      echo "read_file" ;;
        Write)     echo "write_file" ;;
        Bash)      echo "run_shell_command" ;;
        Grep)      echo "grep_search" ;;
        Glob)      echo "glob" ;;
        WebSearch) echo "google_web_search" ;;
        WebFetch)  echo "web_fetch" ;;
        *)         echo "$1" ;;  # fallback: keep original
    esac
}

agent_count=0

for md_file in "$AGENTS_DIR"/*.md; do
    [ -f "$md_file" ] || continue

    basename="$(basename "$md_file")"

    # Skip the gemini/ subdirectory marker if it somehow matches
    [ "$basename" = "gemini" ] && continue

    # Verify file has YAML frontmatter
    head_line="$(head -1 "$md_file")"
    if [ "$head_line" != "---" ]; then
        echo "SKIP: $basename (no YAML frontmatter)"
        continue
    fi

    # Extract the tools line from frontmatter
    tools_line="$(awk '/^---$/{n++; next} n==1 && /^tools:/{print; exit}' "$md_file")"

    if [ -z "$tools_line" ]; then
        echo "SKIP: $basename (no tools in frontmatter)"
        continue
    fi

    # Parse tool names from comma-separated string: "tools: Read, Grep, Glob, Bash"
    raw_tools="$(echo "$tools_line" | sed 's/^tools:[[:space:]]*//')"

    # Map each tool name to Gemini equivalent
    gemini_tools=""
    IFS=',' read -ra tool_array <<< "$raw_tools"
    for tool in "${tool_array[@]}"; do
        tool="$(echo "$tool" | xargs)"  # trim whitespace
        mapped="$(map_tool_name "$tool")"
        if [ -n "$gemini_tools" ]; then
            gemini_tools="$gemini_tools, $mapped"
        else
            gemini_tools="$mapped"
        fi
    done

    # Build the new tools line as YAML array
    new_tools_line="tools: [$gemini_tools]"

    # Check if file has a skills line in frontmatter
    skills_line="$(awk '/^---$/{n++; next} n==1 && /^skills:/{print; exit}' "$md_file")"
    skills_value=""
    if [ -n "$skills_line" ]; then
        skills_value="$(echo "$skills_line" | sed 's/^skills:[[:space:]]*//')"
    fi

    # Generate the Gemini-compatible agent file:
    # 1. Replace tools line with YAML array + Gemini names
    # 2. Remove skills line from frontmatter
    # 3. Add "Linked Skill:" after the first heading if skills existed
    {
        in_frontmatter=0
        frontmatter_count=0
        first_heading_done=0

        while IFS= read -r line; do
            if [ "$line" = "---" ]; then
                frontmatter_count=$((frontmatter_count + 1))
                if [ "$frontmatter_count" -eq 1 ]; then
                    in_frontmatter=1
                    echo "$line"
                    continue
                elif [ "$frontmatter_count" -eq 2 ]; then
                    in_frontmatter=0
                    echo "$line"
                    continue
                fi
            fi

            if [ "$in_frontmatter" -eq 1 ]; then
                # Inside frontmatter: replace tools, skip skills
                case "$line" in
                    tools:*)
                        echo "$new_tools_line"
                        ;;
                    skills:*)
                        # Skip — will add as body text
                        ;;
                    *)
                        echo "$line"
                        ;;
                esac
            else
                # Body: inject "Linked Skill" after first heading
                if [ "$first_heading_done" -eq 0 ] && echo "$line" | grep -q '^# '; then
                    echo "$line"
                    if [ -n "$skills_value" ]; then
                        echo ""
                        echo "**Linked Skill:** $skills_value"
                    fi
                    first_heading_done=1
                else
                    echo "$line"
                fi
            fi
        done < "$md_file"
    } > "$GEMINI_AGENTS_DIR/$basename"

    echo "OK: $basename -> agents/gemini/$basename ($raw_tools → $gemini_tools)"
    agent_count=$((agent_count + 1))
done

echo ""
echo "Agents: generated $agent_count file(s) in agents/gemini/"
echo ""
echo "Done. To apply Gemini agents for validation: cp agents/gemini/*.md agents/"
