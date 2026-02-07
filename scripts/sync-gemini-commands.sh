#!/usr/bin/env bash
# sync-gemini-commands.sh
#
# Reads each commands/*.md file (Claude Code format) and generates the
# corresponding commands/architect/*.toml file (Gemini CLI format).
#
# Safe to run repeatedly — overwrites existing .toml files.
# No dependencies beyond bash, sed, and awk.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMMANDS_DIR="$REPO_DIR/commands"
TOML_DIR="$COMMANDS_DIR/architect"

mkdir -p "$TOML_DIR"

count=0

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

    echo "OK: $basename.md -> architect/$toml_name.toml ($description)"
    count=$((count + 1))
done

echo ""
echo "Done. Generated $count TOML command(s) in commands/architect/"
