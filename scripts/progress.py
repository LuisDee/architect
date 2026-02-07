#!/usr/bin/env python3
"""Calculate complexity-weighted progress across all tracks.

Loads track metadata and plan.md files to compute per-wave and overall
progress. Complexity weights: S=1, M=2, L=3, XL=4.

Usage:
    python scripts/progress.py
    python scripts/progress.py --tracks-dir conductor/tracks

Output (JSON to stdout):
    {
      "overall_progress": 0.42,
      "waves": [...],
      "pending_items": { "discoveries": 2, "patches": 1 },
      "tracks_by_status": { "completed": 4, "in_progress": 2, "new": 6 }
    }
"""

import argparse
import json
import re
import sys
from pathlib import Path

COMPLEXITY_WEIGHTS = {"S": 1, "M": 2, "L": 3, "XL": 4}


def load_all_tracks(tracks_dir: str) -> list[dict]:
    """Load all track metadata with plan.md phase info."""
    tracks = []
    tracks_path = Path(tracks_dir)

    if not tracks_path.exists():
        print(f"Error: tracks directory not found: {tracks_dir}", file=sys.stderr)
        sys.exit(1)

    for meta_path in sorted(tracks_path.glob("*/metadata.json")):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: skipping {meta_path}: {e}", file=sys.stderr)
            continue

        meta["_dir"] = str(meta_path.parent)
        meta["_completion_pct"] = calculate_track_completion(meta)
        tracks.append(meta)

    return tracks


def calculate_track_completion(meta: dict) -> float:
    """Calculate completion percentage for a single track."""
    state = meta.get("status", "new")

    # Fully complete with no pending patches
    pending_patches = [
        p for p in meta.get("patches", [])
        if p.get("status") != "COMPLETE"
    ]
    if state == "completed" and not pending_patches:
        return 1.0

    if state == "new":
        return 0.0

    # Parse plan.md for phase completion
    plan_path = Path(meta.get("_dir", "")) / "plan.md"
    if not plan_path.exists():
        # No plan file — estimate from state
        if state == "completed":
            return 0.9  # Complete but has pending patches
        return 0.1  # In progress but can't measure

    text = plan_path.read_text()
    checked = len(re.findall(r"- \[x\]", text, re.IGNORECASE))
    unchecked = len(re.findall(r"- \[ \]", text))
    total = checked + unchecked

    if total == 0:
        return 0.5 if state == "in_progress" else 0.0

    base_completion = checked / total

    # If complete but has pending patches, cap at 90%
    if state == "completed" and pending_patches:
        return min(base_completion, 0.9)

    return base_completion


def count_pending_discoveries(discovery_dir: str) -> int:
    """Count pending discovery files."""
    pending = Path(discovery_dir) / "pending"
    if not pending.exists():
        return 0
    return len(list(pending.glob("*.md")))


def count_pending_patches(tracks: list[dict]) -> int:
    """Count total pending patches across all tracks."""
    count = 0
    for t in tracks:
        for p in t.get("patches", []):
            if p.get("status") != "COMPLETE":
                count += 1
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Calculate complexity-weighted progress"
    )
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")
    parser.add_argument("--discovery-dir", default="architect/discovery",
                        help="Path to discovery directory")

    args = parser.parse_args()
    tracks = load_all_tracks(args.tracks_dir)

    if not tracks:
        print(json.dumps({
            "overall_progress": 0.0,
            "waves": [],
            "pending_items": {"discoveries": 0, "patches": 0},
            "tracks_by_status": {},
            "message": "No tracks found",
        }, indent=2))
        sys.exit(0)

    # Group by wave
    waves = {}
    for t in tracks:
        w = t.get("wave", 0)
        waves.setdefault(w, []).append(t)

    # Calculate per-wave progress
    wave_results = []
    total_weighted = 0
    done_weighted = 0.0

    for wave_num in sorted(waves.keys()):
        wave_tracks = waves[wave_num]
        wave_total = 0
        wave_done = 0.0
        wave_track_details = []

        for t in wave_tracks:
            complexity = t.get("complexity", "M")
            weight = COMPLEXITY_WEIGHTS.get(complexity, 2)
            completion = t["_completion_pct"]

            wave_total += weight
            wave_done += weight * completion
            total_weighted += weight
            done_weighted += weight * completion

            wave_track_details.append({
                "track_id": t["track_id"],
                "status": t.get("status", "new"),
                "complexity": complexity,
                "weight": weight,
                "completion": round(completion, 2),
            })

        wave_results.append({
            "wave": wave_num,
            "tracks": wave_track_details,
            "total_weight": wave_total,
            "progress": round(wave_done / wave_total, 2) if wave_total else 0.0,
        })

    # Overall progress
    overall = done_weighted / total_weighted if total_weighted else 0.0

    # State counts
    state_counts = {}
    for t in tracks:
        state = t.get("status", "new")
        state_counts[state] = state_counts.get(state, 0) + 1

    # Pending items
    pending_discoveries = count_pending_discoveries(args.discovery_dir)
    pending_patches = count_pending_patches(tracks)

    result = {
        "overall_progress": round(overall, 3),
        "total_tracks": len(tracks),
        "total_weighted_units": total_weighted,
        "completed_weighted_units": round(done_weighted, 1),
        "waves": wave_results,
        "tracks_by_status": state_counts,
        "pending_items": {
            "discoveries": pending_discoveries,
            "patches": pending_patches,
        },
    }

    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
