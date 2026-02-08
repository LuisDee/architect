#!/usr/bin/env python3
"""Validate the track dependency graph for cycles.

Loads dependency information from conductor/tracks/*/metadata.json files
and checks for cycles using Kahn's algorithm. Supports incremental
node/edge addition for feature decomposition.

Usage:
    python scripts/validate_dag.py
    python scripts/validate_dag.py --check-edge --from 05_frontend --to 03_auth
    python scripts/validate_dag.py --tracks-dir conductor/tracks

    # Incremental: add new tracks and validate (v2.1)
    python scripts/validate_dag.py --add-tracks '[{"id":"T-RBAC","depends_on":["T-AUTH"]}]'
    python scripts/validate_dag.py --add-tracks '[{"id":"T-RBAC","depends_on":["T-AUTH"]}]' --write

Output (JSON to stdout):
    { "valid": true, "node_count": 12, "edge_count": 18 }
    { "valid": false, "cycle_nodes": ["A", "B", "C"] }
    { "cycle": false }  (for --check-edge)
    { "cycle": true, "source": "X", "target": "Y" }  (for --check-edge)
    { "valid": true, "added_nodes": [...], "added_edges": [...] }  (for --add-tracks)
"""

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path


def load_graph(tracks_dir: str = "conductor/tracks") -> dict[str, list[str]]:
    """Load dependency graph from track metadata.json files.

    Returns adjacency list: { track_id: [dependency_track_ids] }
    Every track appears as a key even if it has no dependencies.
    """
    graph = {}
    tracks_path = Path(tracks_dir)

    if not tracks_path.exists():
        print(f"Error: tracks directory not found: {tracks_dir}", file=sys.stderr)
        sys.exit(1)

    for meta_path in sorted(tracks_path.glob("*/metadata.json")):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error reading {meta_path}: {e}", file=sys.stderr)
            sys.exit(1)

        track_id = meta.get("track_id", meta_path.parent.name)
        deps = meta.get("dependencies", [])
        graph[track_id] = deps

    # Ensure all dependency targets also appear as keys
    all_deps = {d for deps in graph.values() for d in deps}
    for dep in all_deps:
        if dep not in graph:
            graph[dep] = []

    return graph


def detect_cycles(graph: dict[str, list[str]]) -> list[str] | None:
    """Kahn's algorithm for cycle detection.

    Returns None if no cycle, or list of nodes involved in the cycle.
    """
    # Build in-degree map (edges point from dependent -> dependency,
    # but for topological sort we need: dependency -> dependent)
    # graph[A] = [B, C] means A depends on B and C
    # For Kahn's: in_degree[A] = number of things A depends on
    in_degree = defaultdict(int)
    # Reverse adjacency: who depends on me?
    reverse = defaultdict(list)

    for node in graph:
        if node not in in_degree:
            in_degree[node] = 0

    for node, deps in graph.items():
        in_degree[node] = len(deps)
        for dep in deps:
            reverse[dep].append(node)
            if dep not in in_degree:
                in_degree[dep] = 0

    # Start with nodes that have no dependencies
    queue = deque(n for n, deg in in_degree.items() if deg == 0)
    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1
        for dependent in reverse.get(node, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if visited == len(in_degree):
        return None  # No cycle

    # Return nodes still with in_degree > 0 (part of cycles)
    return [n for n, deg in in_degree.items() if deg > 0]


def count_edges(graph: dict[str, list[str]]) -> int:
    """Count total edges in the graph."""
    return sum(len(deps) for deps in graph.values())


def check_edge(graph: dict[str, list[str]], source: str, target: str) -> bool:
    """Check if adding source -> target (source depends on target) creates a cycle."""
    temp = {k: list(v) for k, v in graph.items()}
    if source not in temp:
        temp[source] = []
    if target not in temp:
        temp[target] = []
    temp[source].append(target)
    return detect_cycles(temp) is not None


def add_tracks_to_graph(
    graph: dict[str, list[str]], new_tracks: list[dict]
) -> tuple[dict[str, list[str]], list[str], list[tuple[str, str]]]:
    """Add new track nodes and edges to an existing graph.

    Args:
        graph: Existing adjacency list.
        new_tracks: List of dicts with "id" and "depends_on" keys.

    Returns:
        (updated_graph, added_nodes, added_edges)
    """
    updated = {k: list(v) for k, v in graph.items()}
    added_nodes = []
    added_edges = []

    for track in new_tracks:
        track_id = track["id"]
        deps = track.get("depends_on", [])

        if track_id not in updated:
            updated[track_id] = []
            added_nodes.append(track_id)

        for dep in deps:
            if dep not in updated:
                updated[dep] = []
                added_nodes.append(dep)
            if dep not in updated[track_id]:
                updated[track_id].append(dep)
                added_edges.append((track_id, dep))

    return updated, added_nodes, added_edges


def main():
    parser = argparse.ArgumentParser(description="Validate track dependency DAG")
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")
    parser.add_argument("--check-edge", action="store_true",
                        help="Check if adding an edge would create a cycle")
    parser.add_argument("--from", dest="edge_from",
                        help="Source track for --check-edge (the dependent)")
    parser.add_argument("--to", dest="edge_to",
                        help="Target track for --check-edge (the dependency)")
    parser.add_argument("--add-tracks", type=str, default=None,
                        help='JSON array of tracks to add: '
                             '[{"id":"T-NEW","depends_on":["T-OLD"]}]')
    parser.add_argument("--write", action="store_true",
                        help="Write updated metadata.json files for added tracks "
                             "(only with --add-tracks)")

    args = parser.parse_args()

    graph = load_graph(args.tracks_dir)

    if args.add_tracks:
        try:
            new_tracks = json.loads(args.add_tracks)
        except json.JSONDecodeError as e:
            print(f"Error parsing --add-tracks JSON: {e}", file=sys.stderr)
            sys.exit(1)

        updated, added_nodes, added_edges = add_tracks_to_graph(graph, new_tracks)
        cycle_nodes = detect_cycles(updated)

        if cycle_nodes is not None:
            result = {
                "valid": False,
                "cycle_nodes": sorted(cycle_nodes),
                "added_nodes": added_nodes,
                "added_edges": [list(e) for e in added_edges],
            }
            print(json.dumps(result, indent=2))
            sys.exit(1)

        if args.write:
            tracks_path = Path(args.tracks_dir)
            for track in new_tracks:
                track_dir = tracks_path / track["id"]
                track_dir.mkdir(parents=True, exist_ok=True)
                meta_path = track_dir / "metadata.json"
                if meta_path.exists():
                    # Update existing metadata with new dependencies
                    with open(meta_path) as f:
                        meta = json.load(f)
                    existing_deps = set(meta.get("dependencies", []))
                    existing_deps.update(track.get("depends_on", []))
                    meta["dependencies"] = sorted(existing_deps)
                    with open(meta_path, "w") as f:
                        json.dump(meta, f, indent=2)
                        f.write("\n")

        result = {
            "valid": True,
            "node_count": len(updated),
            "edge_count": count_edges(updated),
            "added_nodes": added_nodes,
            "added_edges": [list(e) for e in added_edges],
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    if args.check_edge:
        if not args.edge_from or not args.edge_to:
            print("Error: --check-edge requires --from and --to", file=sys.stderr)
            sys.exit(1)

        has_cycle = check_edge(graph, args.edge_from, args.edge_to)
        result = {
            "cycle": has_cycle,
            "source": args.edge_from,
            "target": args.edge_to,
        }
        print(json.dumps(result, indent=2))
        sys.exit(1 if has_cycle else 0)
    else:
        cycle_nodes = detect_cycles(graph)
        if cycle_nodes is None:
            result = {
                "valid": True,
                "node_count": len(graph),
                "edge_count": count_edges(graph),
            }
            print(json.dumps(result, indent=2))
            sys.exit(0)
        else:
            result = {
                "valid": False,
                "cycle_nodes": sorted(cycle_nodes),
                "node_count": len(graph),
                "edge_count": count_edges(graph),
            }
            print(json.dumps(result, indent=2))
            sys.exit(1)


if __name__ == "__main__":
    main()
