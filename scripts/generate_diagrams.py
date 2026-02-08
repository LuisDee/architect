#!/usr/bin/env python3
"""Generate Mermaid diagram files from Architect artifacts.

Reads dependency-graph.md, architecture.md, execution-sequence.md,
and track metadata to produce:
  - dependency-graph.mmd (status-colored DAG)
  - component-map.mmd (architecture components)
  - wave-timeline.mmd (Gantt chart)

Usage:
    python scripts/generate_diagrams.py \
        --tracks-dir conductor/tracks \
        --architect-dir architect \
        --output-dir architect/diagrams

Output (JSON to stdout + files written to output-dir).
"""

import argparse
import json
import re
import sys
from pathlib import Path


# --- Status styling ---

STATUS_CLASSES = {
    "completed": "complete",
    "in_progress": "in_progress",
    "new": "pending",
    "pending": "pending",
    "paused": "blocked",
    "needs_patch": "blocked",
}

MERMAID_CLASS_DEFS = """\
    classDef complete fill:#28a745,color:#fff,stroke:#1e7e34
    classDef in_progress fill:#007bff,color:#fff,stroke:#0056b3
    classDef pending fill:#6c757d,color:#fff,stroke:#495057
    classDef blocked fill:#dc3545,color:#fff,stroke:#bd2130
"""


def load_all_metadata(tracks_dir: str) -> dict[str, dict]:
    """Load all track metadata keyed by track_id."""
    tracks = {}
    tracks_path = Path(tracks_dir)
    if not tracks_path.exists():
        return tracks

    for meta_path in sorted(tracks_path.glob("*/metadata.json")):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            tracks[meta.get("track_id", meta_path.parent.name)] = meta
        except (json.JSONDecodeError, OSError):
            pass

    return tracks


def parse_dependency_graph(architect_dir: str) -> dict[str, list[str]]:
    """Parse dependency-graph.md into {track: [depends_on]} dict."""
    dep_path = Path(architect_dir) / "dependency-graph.md"
    if not dep_path.exists():
        return {}

    text = dep_path.read_text()
    graph: dict[str, list[str]] = {}

    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("| Track") or line.startswith("|---"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) >= 3:
            track = cols[1].strip()
            deps_str = cols[2].strip()
            if track and track != "-":
                deps = []
                if deps_str and deps_str != "-":
                    deps = [d.strip() for d in deps_str.split(",") if d.strip() and d.strip() != "-"]
                graph[track] = deps

    return graph


def parse_execution_sequence(architect_dir: str) -> list[dict]:
    """Parse execution-sequence.md into wave data."""
    seq_path = Path(architect_dir) / "execution-sequence.md"
    if not seq_path.exists():
        return []

    text = seq_path.read_text()
    waves = []
    current_wave = None

    for line in text.splitlines():
        wave_match = re.match(r"^##\s+Wave\s+(\d+)", line)
        if wave_match:
            if current_wave:
                waves.append(current_wave)
            current_wave = {
                "number": int(wave_match.group(1)),
                "tracks": [],
            }
            continue

        if current_wave and line.startswith("|") and not line.startswith("| Track") and not line.startswith("|---"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 2 and cols[1] and cols[1] != "-":
                current_wave["tracks"].append(cols[1].strip())

    if current_wave:
        waves.append(current_wave)

    return waves


def parse_architecture_components(architect_dir: str) -> list[dict]:
    """Parse architecture.md for component info."""
    arch_path = Path(architect_dir) / "architecture.md"
    if not arch_path.exists():
        return []

    text = arch_path.read_text()
    components = []
    in_component_section = False

    for line in text.splitlines():
        if re.match(r"^##\s+Component", line, re.IGNORECASE):
            in_component_section = True
            continue
        if in_component_section and re.match(r"^##\s+", line) and not re.match(r"^###", line):
            in_component_section = False
            continue

        if in_component_section:
            # Match table rows
            if line.startswith("|") and not line.startswith("| Component") and not line.startswith("|---"):
                cols = [c.strip() for c in line.split("|")]
                if len(cols) >= 4 and cols[1]:
                    components.append({
                        "name": cols[1],
                        "technology": cols[2] if len(cols) > 2 else "",
                        "responsibility": cols[3] if len(cols) > 3 else "",
                    })

            # Match ### headings
            comp_match = re.match(r"^###\s+(.+)", line)
            if comp_match:
                name = comp_match.group(1).strip()
                components.append({
                    "name": name,
                    "technology": "",
                    "responsibility": "",
                })

    return components


def sanitize_id(track_id: str) -> str:
    """Make a track ID safe for Mermaid node names."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", track_id)


# --- Diagram generators ---

def generate_dependency_graph(
    graph: dict[str, list[str]], metadata: dict[str, dict]
) -> str:
    """Generate Mermaid dependency graph with status coloring."""
    lines = ["graph LR"]

    # Add all nodes with labels
    all_nodes = set(graph.keys())
    for deps in graph.values():
        all_nodes.update(deps)

    for node in sorted(all_nodes):
        safe_id = sanitize_id(node)
        meta = metadata.get(node, {})
        status = meta.get("status", "new")
        css_class = STATUS_CLASSES.get(status, "pending")
        complexity = meta.get("complexity", "?")
        lines.append(f"    {safe_id}[\"{node} ({complexity})\"]:::{css_class}")

    # Add edges
    for track, deps in sorted(graph.items()):
        safe_track = sanitize_id(track)
        for dep in deps:
            safe_dep = sanitize_id(dep)
            lines.append(f"    {safe_dep} --> {safe_track}")

    lines.append("")
    lines.append(MERMAID_CLASS_DEFS.rstrip())
    return "\n".join(lines)


def generate_component_map(components: list[dict]) -> str:
    """Generate Mermaid flowchart for component map."""
    if not components:
        return "graph TD\n    empty[\"No components found in architecture.md\"]"

    lines = ["graph TD"]

    for i, comp in enumerate(components):
        safe_id = sanitize_id(comp["name"])
        tech = comp.get("technology", "")
        label = comp["name"]
        if tech:
            label += f"\\n({tech})"
        lines.append(f"    {safe_id}[\"{label}\"]")

    # Simple connections based on common patterns
    # (real projects will have explicit connections in architecture.md)
    if len(components) >= 2:
        lines.append("")
        lines.append("    %% Auto-generated connections — review and customize")

    return "\n".join(lines)


def generate_wave_timeline(
    waves: list[dict], metadata: dict[str, dict]
) -> str:
    """Generate Mermaid Gantt chart for wave timeline."""
    lines = [
        "gantt",
        "    title Project Execution Waves",
        "    dateFormat X",
        "    axisFormat Wave %s",
        "",
    ]

    for wave in sorted(waves, key=lambda w: w["number"]):
        lines.append(f"    section Wave {wave['number']}")
        for track_id in wave["tracks"]:
            meta = metadata.get(track_id, {})
            status = meta.get("status", "new")
            wave_num = wave["number"]

            if status == "completed":
                gantt_status = "done"
            elif status == "in_progress":
                gantt_status = "active"
            else:
                gantt_status = ""

            marker = f"{gantt_status}, " if gantt_status else ""
            lines.append(
                f"    {track_id} :{marker}{wave_num}, {wave_num + 1}"
            )

    return "\n".join(lines)


def generate_diagrams(
    tracks_dir: str, architect_dir: str, output_dir: str,
    dry_run: bool = False,
) -> dict:
    """Main entry point: generate all diagram files."""
    metadata = load_all_metadata(tracks_dir)
    graph = parse_dependency_graph(architect_dir)
    waves = parse_execution_sequence(architect_dir)
    components = parse_architecture_components(architect_dir)

    output_path = Path(output_dir)
    results = {"diagrams_generated": [], "warnings": []}

    # 1. Dependency graph
    if graph:
        mmd = generate_dependency_graph(graph, metadata)
        if not dry_run:
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "dependency-graph.mmd").write_text(mmd)
        results["diagrams_generated"].append({
            "file": str(output_path / "dependency-graph.mmd"),
            "type": "dependency_graph",
            "tracks": len(set(graph.keys()) | {d for deps in graph.values() for d in deps}),
            "edges": sum(len(deps) for deps in graph.values()),
        })
    else:
        results["warnings"].append("No dependency-graph.md found — skipping dependency diagram")

    # 2. Component map
    if components:
        mmd = generate_component_map(components)
        if not dry_run:
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "component-map.mmd").write_text(mmd)
        results["diagrams_generated"].append({
            "file": str(output_path / "component-map.mmd"),
            "type": "component_map",
            "components": len(components),
        })
    else:
        results["warnings"].append("No components found in architecture.md — skipping component map")

    # 3. Wave timeline
    if waves:
        mmd = generate_wave_timeline(waves, metadata)
        if not dry_run:
            output_path.mkdir(parents=True, exist_ok=True)
            (output_path / "wave-timeline.mmd").write_text(mmd)
        results["diagrams_generated"].append({
            "file": str(output_path / "wave-timeline.mmd"),
            "type": "wave_timeline",
            "waves": len(waves),
        })
    else:
        results["warnings"].append("No execution-sequence.md found — skipping timeline")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Generate Mermaid diagrams from Architect artifacts"
    )
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")
    parser.add_argument("--architect-dir", default="architect",
                        help="Path to architect directory")
    parser.add_argument("--output-dir", default="architect/diagrams",
                        help="Path for generated diagram files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate content without writing files")

    args = parser.parse_args()
    result = generate_diagrams(
        args.tracks_dir, args.architect_dir, args.output_dir, args.dry_run
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
