#!/usr/bin/env python3
"""Generate compressed context header for a track's brief.md.

Reads cross-cutting.md, interfaces.md, dependency-graph info from metadata,
filters to only what's relevant for the given track, and outputs a context
header that fits within a ~2000 token budget (~8000 chars). Falls back to
a minimal header if the full version exceeds the budget.

The context header is prepended to brief.md. When Conductor later generates
spec.md, it preserves this header from the brief.

Usage:
    python scripts/inject_context.py --track 04_api_core
    python scripts/inject_context.py --track 04_api_core --tracks-dir conductor/tracks
    python scripts/inject_context.py --track 04_api_core --output conductor/tracks/04_api_core/context-header.md

Output: Rendered context header markdown to stdout (or --output file).
"""

import argparse
import json
import re
import sys
from pathlib import Path

# ~4 chars per token estimate
FULL_TOKEN_BUDGET = 2000
FULL_CHAR_BUDGET = FULL_TOKEN_BUDGET * 4  # 8000 chars
MINIMAL_CHAR_BUDGET = 500 * 4  # 2000 chars


def load_track_metadata(track_id: str, tracks_dir: str = "conductor/tracks") -> dict:
    """Load metadata.json for a specific track."""
    meta_path = Path(tracks_dir) / track_id / "metadata.json"
    if not meta_path.exists():
        print(f"Error: metadata not found: {meta_path}", file=sys.stderr)
        sys.exit(1)
    with open(meta_path) as f:
        return json.load(f)


def load_file_text(path: str) -> str | None:
    """Load a text file, return None if not found."""
    p = Path(path)
    if p.exists():
        return p.read_text()
    return None


def extract_constraints_for_track(cc_text: str, track_id: str) -> list[str]:
    """Extract applicable constraints from cross-cutting.md.

    Parses versioned sections and returns constraint lines that apply to
    ALL tracks or specifically mention this track.
    """
    if not cc_text:
        return []

    constraints = []
    current_concern = None
    lines_for_concern = []

    for line in cc_text.splitlines():
        # Match ### headings (concern names)
        if line.startswith("### "):
            # Flush previous concern
            if current_concern and lines_for_concern:
                constraints.append(
                    f"- {current_concern}: {' '.join(lines_for_concern)}"
                )
            current_concern = line[4:].strip()
            # Remove (NEW) or (MODIFIED) markers
            current_concern = re.sub(r"\s*\((NEW|MODIFIED)\)\s*$", "", current_concern)
            lines_for_concern = []
        elif current_concern and line.startswith("- ") and not line.startswith("- Applies to:") and not line.startswith("- Source:"):
            # Collect constraint details
            lines_for_concern.append(line[2:].strip())
        elif current_concern and line.startswith("- Applies to:"):
            scope = line.split(":", 1)[1].strip()
            # Check if this constraint applies to our track
            applies = (
                scope.upper() == "ALL"
                or "ALL" in scope.upper()
                or track_id in scope
            )
            if not applies:
                # Skip this concern for this track
                current_concern = None
                lines_for_concern = []

    # Flush last concern
    if current_concern and lines_for_concern:
        constraints.append(f"- {current_concern}: {' '.join(lines_for_concern)}")

    return constraints


def extract_interfaces_for_track(
    interfaces_text: str, track_id: str, meta: dict
) -> dict[str, list[str]]:
    """Extract interface info relevant to this track."""
    result = {
        "owns": meta.get("interfaces_owned", []),
        "consumes": meta.get("interfaces_consumed", []),
        "publishes": meta.get("events_published", []),
        "subscribes": meta.get("events_consumed", []),
    }
    return result


def format_dependency_list(meta: dict) -> list[str]:
    """Format dependency list from metadata."""
    return [f"- {dep}" for dep in meta.get("dependencies", [])]


def get_cc_version(cc_text: str) -> str:
    """Extract the latest CC version from cross-cutting.md."""
    if not cc_text:
        return "v1"
    versions = re.findall(r"## (v[\d.]+)", cc_text)
    return versions[-1] if versions else "v1"


def render_full_header(
    track_id: str, wave: int, cc_version: str,
    constraints: list[str], interfaces: dict[str, list[str]],
    dependencies: list[str],
) -> str:
    """Render the full context header."""
    lines = [
        f"<!-- ARCHITECT CONTEXT v2 | Track: {track_id} | Wave: {wave} | CC: {cc_version} -->",
        "",
        "## Constraints (filtered for this track)",
        "",
    ]
    if constraints:
        lines.extend(constraints)
    else:
        lines.append("- (none applicable)")
    lines.append("")

    lines.append("## Interfaces")
    lines.append("")
    lines.append("### Owns")
    if interfaces["owns"]:
        for iface in interfaces["owns"]:
            lines.append(f"- {iface}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("### Consumes")
    if interfaces["consumes"]:
        for iface in interfaces["consumes"]:
            lines.append(f"- {iface}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("### Publishes")
    if interfaces["publishes"]:
        for ev in interfaces["publishes"]:
            lines.append(f"- {ev}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("### Subscribes")
    if interfaces["subscribes"]:
        for ev in interfaces["subscribes"]:
            lines.append(f"- {ev}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Dependencies")
    lines.append("")
    if dependencies:
        lines.extend(dependencies)
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Full Context (read if needed)")
    lines.append("")
    lines.append("- architect/architecture.md")
    lines.append("- architect/cross-cutting.md")
    lines.append("- architect/interfaces.md")
    lines.append("- architect/dependency-graph.md")
    lines.append("")
    lines.append("<!-- END ARCHITECT CONTEXT -->")

    return "\n".join(lines)


def render_minimal_header(
    track_id: str, wave: int, cc_version: str,
    constraints: list[str], interfaces: dict[str, list[str]],
    dependencies: list[str],
) -> str:
    """Render the minimal context header (~500 tokens)."""
    lines = [
        f"<!-- ARCHITECT CONTEXT v2-minimal | Track: {track_id} | Wave: {wave} | CC: {cc_version} -->",
        "",
        "## Constraints",
        "",
    ]
    # Top 5 constraints only
    for c in constraints[:5]:
        lines.append(c)
    lines.append("")

    lines.append("## Interfaces")
    owns_count = len(interfaces["owns"])
    consumes_summary = ", ".join(interfaces["consumes"][:3])
    publishes_summary = ", ".join(interfaces["publishes"][:3])
    lines.append(f"- OWNS: {owns_count} endpoint(s)")
    lines.append(f"- CONSUMES: {consumes_summary or '(none)'}")
    lines.append(f"- PUBLISHES: {publishes_summary or '(none)'}")
    lines.append("")

    lines.append("## Dependencies")
    for dep in dependencies[:5]:
        lines.append(dep)
    lines.append("")

    lines.append("Full context: architect/cross-cutting.md | architect/interfaces.md | architect/dependency-graph.md")
    lines.append("")
    lines.append("<!-- END ARCHITECT CONTEXT -->")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate compressed context header for a track"
    )
    parser.add_argument("--track", required=True, help="Track ID")
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")
    parser.add_argument("--architect-dir", default="architect",
                        help="Path to architect directory")
    parser.add_argument("--output", help="Output file path (default: stdout)")

    args = parser.parse_args()

    meta = load_track_metadata(args.track, args.tracks_dir)

    cc_text = load_file_text(f"{args.architect_dir}/cross-cutting.md")
    interfaces_text = load_file_text(f"{args.architect_dir}/interfaces.md")

    cc_version = get_cc_version(cc_text) if cc_text else meta.get("cc_version_current", "v1")
    wave = meta.get("wave", 0)

    constraints = extract_constraints_for_track(cc_text or "", args.track)
    interfaces = extract_interfaces_for_track(interfaces_text or "", args.track, meta)
    dependencies = format_dependency_list(meta)

    # Try full header first
    full = render_full_header(
        args.track, wave, cc_version, constraints, interfaces, dependencies
    )

    if len(full) <= FULL_CHAR_BUDGET:
        header = full
    else:
        # Fall back to minimal
        header = render_minimal_header(
            args.track, wave, cc_version, constraints, interfaces, dependencies
        )
        if len(header) > MINIMAL_CHAR_BUDGET:
            print(
                f"Warning: minimal header still over budget ({len(header)} chars)",
                file=sys.stderr,
            )

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(header)
        result = {
            "track_id": args.track,
            "template": "full" if len(full) <= FULL_CHAR_BUDGET else "minimal",
            "chars": len(header),
            "estimated_tokens": len(header) // 4,
            "output": args.output,
        }
    else:
        result = {
            "track_id": args.track,
            "template": "full" if len(full) <= FULL_CHAR_BUDGET else "minimal",
            "chars": len(header),
            "estimated_tokens": len(header) // 4,
            "header": header,
        }

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
