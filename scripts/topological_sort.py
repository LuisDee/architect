#!/usr/bin/env python3
"""Generate wave-based execution sequence from the track dependency DAG.

Loads track metadata, performs topological sort, and groups tracks into
waves where all tracks in a wave can run in parallel.

Usage:
    python scripts/topological_sort.py
    python scripts/topological_sort.py --tracks-dir conductor/tracks

Output (JSON to stdout):
    {
      "waves": [
        { "wave": 1, "name": "Foundation", "tracks": ["01_infra", "13_observability"] },
        { "wave": 2, "name": "Wave 2", "tracks": ["02_db", "05_frontend", "06_redis"] }
      ],
      "total_tracks": 13
    }
"""

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path


def load_tracks(tracks_dir: str = "conductor/tracks") -> list[dict]:
    """Load all track metadata files."""
    tracks = []
    tracks_path = Path(tracks_dir)

    if not tracks_path.exists():
        print(f"Error: tracks directory not found: {tracks_dir}", file=sys.stderr)
        sys.exit(1)

    for meta_path in sorted(tracks_path.glob("*/metadata.json")):
        try:
            with open(meta_path) as f:
                tracks.append(json.load(f))
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error reading {meta_path}: {e}", file=sys.stderr)
            sys.exit(1)

    return tracks


def build_graph(tracks: list[dict]) -> tuple[dict[str, list[str]], dict[str, dict]]:
    """Build adjacency list and track lookup from metadata.

    Returns (graph, track_by_id).
    graph[A] = [B, C] means A depends on B and C.
    """
    track_by_id = {}
    graph = {}

    for t in tracks:
        tid = t["track_id"]
        track_by_id[tid] = t
        graph[tid] = t.get("dependencies", [])

    # Ensure dependency targets exist as keys
    all_deps = {d for deps in graph.values() for d in deps}
    for dep in all_deps:
        if dep not in graph:
            graph[dep] = []

    return graph, track_by_id


def topological_waves(graph: dict[str, list[str]]) -> list[list[str]] | None:
    """Compute wave-based topological ordering.

    Each wave contains nodes whose dependencies are all in earlier waves.
    Returns list of waves (each wave is a sorted list of track IDs),
    or None if a cycle is detected.
    """
    in_degree = defaultdict(int)
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

    waves = []
    remaining = dict(in_degree)

    while True:
        # Find all nodes with in_degree 0 among remaining
        wave = sorted(n for n, deg in remaining.items() if deg == 0)
        if not wave:
            break

        waves.append(wave)

        # Remove these nodes and update in-degrees
        for node in wave:
            del remaining[node]
            for dependent in reverse.get(node, []):
                if dependent in remaining:
                    remaining[dependent] -= 1

    if remaining:
        return None  # Cycle detected

    return waves


def main():
    parser = argparse.ArgumentParser(
        description="Generate wave-based execution sequence from track DAG"
    )
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")

    args = parser.parse_args()
    tracks = load_tracks(args.tracks_dir)
    graph, track_by_id = build_graph(tracks)
    waves = topological_waves(graph)

    if waves is None:
        print("Error: cycle detected in dependency graph", file=sys.stderr)
        sys.exit(1)

    result_waves = []
    for i, wave_tracks in enumerate(waves, 1):
        wave_info = {
            "wave": i,
            "name": f"Wave {i}",
            "tracks": wave_tracks,
            "complexity": [],
        }
        for tid in wave_tracks:
            t = track_by_id.get(tid, {})
            wave_info["complexity"].append({
                "track_id": tid,
                "complexity": t.get("complexity", "M"),
                "state": t.get("state", "UNKNOWN"),
            })
        result_waves.append(wave_info)

    result = {
        "waves": result_waves,
        "total_tracks": len(graph),
        "total_waves": len(waves),
    }

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
