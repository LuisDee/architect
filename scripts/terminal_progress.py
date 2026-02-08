#!/usr/bin/env python3
"""Generate ASCII terminal progress bars for /architect-status.

Renders per-wave and overall completion with complexity weighting.
Designed for terminal display — no external dependencies.

Usage:
    python scripts/progress.py --tracks-dir conductor/tracks | \
        python scripts/terminal_progress.py

    echo '{"waves":[...],"tracks_by_status":{...}}' | \
        python scripts/terminal_progress.py

Output: Formatted ASCII progress display to stdout.
"""

import json
import sys

BAR_WIDTH = 20
COMPLETE_CHAR = "\u2588"      # █
IN_PROGRESS_CHAR = "\u2593"   # ▓
REMAINING_CHAR = "\u2591"     # ░

COMPLEXITY_WEIGHTS = {"S": 1, "M": 2, "L": 3, "XL": 4}


def complexity_weight(c: str) -> int:
    """Get numeric weight for complexity string."""
    return COMPLEXITY_WEIGHTS.get(c, 1)


def render_bar(percentage: float) -> str:
    """Render a progress bar string."""
    filled = int(percentage * BAR_WIDTH)
    return COMPLETE_CHAR * filled + REMAINING_CHAR * (BAR_WIDTH - filled)


def render_wave_line(wave: dict) -> str:
    """Render a single wave progress line."""
    tracks = wave.get("tracks", [])
    number = wave.get("number", "?")

    total_points = sum(
        complexity_weight(t.get("complexity", "S")) for t in tracks
    )
    complete_points = sum(
        complexity_weight(t.get("complexity", "S"))
        for t in tracks if t.get("status") == "completed"
    )

    pct = complete_points / total_points if total_points > 0 else 0
    bar = render_bar(pct)
    complete_count = sum(1 for t in tracks if t.get("status") == "completed")
    total_count = len(tracks)

    return (
        f"  Wave {number:<2} {bar}  {pct:>3.0%}  "
        f"({complete_count}/{total_count})  {total_points} pts"
    )


def render_overall_line(waves: list[dict]) -> str:
    """Render the overall progress line."""
    all_tracks = [t for w in waves for t in w.get("tracks", [])]
    total = sum(complexity_weight(t.get("complexity", "S")) for t in all_tracks)
    complete = sum(
        complexity_weight(t.get("complexity", "S"))
        for t in all_tracks if t.get("status") == "completed"
    )
    pct = complete / total if total > 0 else 0
    bar = render_bar(pct)
    return f"  Overall {bar}  {pct:>3.0%}  weighted"


def find_blocked_tracks(waves: list[dict]) -> list[dict]:
    """Identify blocked tracks (paused, needs_patch, or dependency-blocked)."""
    blocked = []
    all_tracks = {
        t.get("track_id", t.get("id", "")): t
        for w in waves for t in w.get("tracks", [])
    }

    for t in all_tracks.values():
        status = t.get("status", "new")
        if status in ("paused", "needs_patch"):
            blocked.append({
                "track_id": t.get("track_id", t.get("id", "?")),
                "reason": status,
            })
        elif status == "new":
            # Check if dependencies are met
            deps = t.get("dependencies", [])
            for dep in deps:
                dep_track = all_tracks.get(dep)
                if dep_track and dep_track.get("status") != "completed":
                    blocked.append({
                        "track_id": t.get("track_id", t.get("id", "?")),
                        "reason": f"depends on {dep}",
                    })
                    break

    return blocked


def render_progress(data: dict) -> str:
    """Render the full progress display."""
    waves = data.get("waves", [])
    lines = []

    # Header
    width = 55
    lines.append("\u250c" + "\u2500" * width + "\u2510")
    lines.append("\u2502" + " PROJECT PROGRESS".ljust(width) + "\u2502")
    lines.append("\u251c" + "\u2500" * width + "\u2524")
    lines.append("\u2502" + "".ljust(width) + "\u2502")

    # Per-wave bars
    for wave in sorted(waves, key=lambda w: w.get("number", 0)):
        wave_line = render_wave_line(wave)
        lines.append("\u2502" + wave_line.ljust(width) + "\u2502")

    lines.append("\u2502" + "".ljust(width) + "\u2502")

    # Overall bar
    overall = render_overall_line(waves)
    lines.append("\u2502" + overall.ljust(width) + "\u2502")

    lines.append("\u2502" + "".ljust(width) + "\u2502")

    # Blocked tracks
    blocked = find_blocked_tracks(waves)
    if blocked:
        for b in blocked[:5]:  # Max 5 to keep display compact
            msg = f"  \u26a0 Blocked: {b['track_id']} ({b['reason']})"
            lines.append("\u2502" + msg.ljust(width) + "\u2502")
        lines.append("\u2502" + "".ljust(width) + "\u2502")

    # Footer
    lines.append("\u2514" + "\u2500" * width + "\u2518")

    return "\n".join(lines)


def transform_progress_data(raw: dict) -> dict:
    """Transform progress.py output into terminal_progress input format.

    progress.py outputs {waves: [{number, tracks: [{track_id, status, complexity}]}]}
    which is already the right shape, but we normalize just in case.
    """
    waves = raw.get("waves", [])
    result_waves = []

    for wave in waves:
        tracks = []
        for t in wave.get("tracks", []):
            tracks.append({
                "track_id": t.get("track_id", t.get("id", "")),
                "status": t.get("status", "new"),
                "complexity": t.get("complexity", "S"),
                "dependencies": t.get("dependencies", []),
            })
        result_waves.append({
            "number": wave.get("number", wave.get("wave", 0)),
            "tracks": tracks,
        })

    return {"waves": result_waves}


def main():
    raw = json.load(sys.stdin)
    data = transform_progress_data(raw)
    print(render_progress(data))


if __name__ == "__main__":
    main()
