#!/usr/bin/env python3
"""Validate wave completion: all tracks complete, tests passing, no blockers.

Given a wave number, checks each track in that wave for:
1. All phases marked complete in plan.md
2. Tests passing (runs test_command from metadata.json)
3. No BLOCKING discoveries in pending/
4. All patches with blocks_wave == next_wave are COMPLETE

Usage:
    python scripts/validate_wave_completion.py --wave 2
    python scripts/validate_wave_completion.py --wave 2 --skip-tests
    python scripts/validate_wave_completion.py --wave 2 --tracks-dir conductor/tracks

Output (JSON to stdout):
    {
      "wave": 2,
      "passed": false,
      "results": [
        { "status": "PASS", "track_id": "02_db", "message": "All checks passed" },
        { "status": "FAIL", "track_id": "05_frontend", "message": "Incomplete phases" }
      ],
      "summary": { "pass": 2, "fail": 1, "warn": 0 }
    }
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def load_wave_tracks(wave: int, tracks_dir: str) -> list[dict]:
    """Load metadata for all tracks in the given wave."""
    tracks = []
    tracks_path = Path(tracks_dir)

    if not tracks_path.exists():
        print(f"Error: tracks directory not found: {tracks_dir}", file=sys.stderr)
        sys.exit(1)

    for meta_path in sorted(tracks_path.glob("*/metadata.json")):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            if meta.get("wave") == wave:
                meta["_dir"] = str(meta_path.parent)
                tracks.append(meta)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: skipping {meta_path}: {e}", file=sys.stderr)

    return tracks


def check_phases_complete(track_dir: str) -> tuple[bool, str]:
    """Check if all phases in plan.md are complete (all checkboxes checked)."""
    plan_path = Path(track_dir) / "plan.md"
    if not plan_path.exists():
        return False, "plan.md not found"

    text = plan_path.read_text()

    # Count checkboxes
    checked = len(re.findall(r"- \[x\]", text, re.IGNORECASE))
    unchecked = len(re.findall(r"- \[ \]", text))
    total = checked + unchecked

    if total == 0:
        return False, "No task checkboxes found in plan.md"

    if unchecked > 0:
        return False, f"Incomplete phases: {unchecked}/{total} tasks unchecked"

    return True, f"All {total} tasks complete"


def run_tests(test_command: str, timeout: int = 300) -> tuple[bool, str]:
    """Run the track's test command and return pass/fail."""
    try:
        result = subprocess.run(
            test_command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, "Tests passing"
        else:
            # Get last few lines of output for context
            output = result.stdout + result.stderr
            last_lines = "\n".join(output.strip().splitlines()[-5:])
            return False, f"Tests failing (exit {result.returncode}): {last_lines[:200]}"
    except subprocess.TimeoutExpired:
        return False, f"Tests timed out after {timeout}s"
    except OSError as e:
        return False, f"Failed to run tests: {e}"


def check_blocking_discoveries(
    track_id: str, discovery_dir: str
) -> tuple[bool, str]:
    """Check for BLOCKING discoveries from this track in pending/."""
    pending_dir = Path(discovery_dir) / "pending"
    if not pending_dir.exists():
        return True, "No pending discoveries directory"

    blocking = []
    for fp in pending_dir.glob("*.md"):
        text = fp.read_text()
        # Check if this discovery is from our track and is BLOCKING
        is_from_track = track_id in fp.name or f"Track {track_id}" in text
        is_blocking = "BLOCKING" in text and "**Urgency:**" in text

        if is_from_track and is_blocking:
            blocking.append(fp.name)

    if blocking:
        return False, f"{len(blocking)} blocking discoveries: {', '.join(blocking[:3])}"

    return True, "No blocking discoveries"


def check_test_prerequisites(
    meta: dict, all_tracks_dir: str
) -> tuple[bool, str]:
    """Check that test prerequisites (other tracks) are completed."""
    prereqs = meta.get("test_prerequisites", [])
    if not prereqs:
        return True, "No test prerequisites"

    tracks_path = Path(all_tracks_dir)
    incomplete = []

    for prereq_id in prereqs:
        prereq_meta_path = tracks_path / prereq_id / "metadata.json"
        if not prereq_meta_path.exists():
            incomplete.append(f"{prereq_id} (not found)")
            continue

        try:
            with open(prereq_meta_path) as f:
                prereq_meta = json.load(f)
            if prereq_meta.get("status") != "completed":
                incomplete.append(f"{prereq_id} ({prereq_meta.get('status', 'unknown')})")
        except (json.JSONDecodeError, OSError):
            incomplete.append(f"{prereq_id} (unreadable)")

    if incomplete:
        return False, f"Prerequisites not met: {', '.join(incomplete)}"
    return True, f"All {len(prereqs)} prerequisites completed"


def check_quality_threshold(
    meta: dict
) -> tuple[bool, str]:
    """Check if quality thresholds are defined (advisory warning only)."""
    threshold = meta.get("quality_threshold")
    if not threshold:
        return True, "No quality threshold defined"

    coverage = threshold.get("line_coverage", 0)
    pass_rate = threshold.get("pass_rate", 100)

    # This is advisory only — we just report the thresholds
    # Actual measurement happens when tests run
    return True, f"Thresholds: {coverage}% coverage, {pass_rate}% pass rate (advisory)"


def log_override(
    meta: dict, meta_path: Path, check: str, reason: str
) -> None:
    """Append an override entry to metadata.json override_log."""
    from datetime import datetime, timezone
    override_entry = {
        "check": check,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    override_log = meta.get("override_log", [])
    override_log.append(override_entry)
    meta["override_log"] = override_log

    try:
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
    except OSError as e:
        print(f"Warning: could not write override to {meta_path}: {e}", file=sys.stderr)


def check_patches(meta: dict, next_wave: int) -> tuple[bool, str]:
    """Check that patches blocking the next wave are complete."""
    patches = meta.get("patches", [])
    pending = [
        p for p in patches
        if p.get("blocks_wave") == next_wave and p.get("status") != "COMPLETE"
    ]

    if pending:
        ids = [p.get("id", "unknown") for p in pending]
        return False, f"{len(pending)} unapplied patches blocking wave {next_wave}: {', '.join(ids)}"

    return True, "All patches complete" if patches else "No patches"


def main():
    parser = argparse.ArgumentParser(
        description="Validate wave completion quality gate"
    )
    parser.add_argument("--wave", required=True, type=int,
                        help="Wave number to validate")
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")
    parser.add_argument("--discovery-dir", default="architect/discovery",
                        help="Path to discovery directory")
    parser.add_argument("--skip-tests", action="store_true",
                        help="Skip running test commands")

    args = parser.parse_args()
    tracks = load_wave_tracks(args.wave, args.tracks_dir)
    next_wave = args.wave + 1

    if not tracks:
        print(json.dumps({
            "wave": args.wave,
            "passed": False,
            "results": [],
            "summary": {"pass": 0, "fail": 0, "warn": 0},
            "message": f"No tracks found for wave {args.wave}",
        }, indent=2))
        sys.exit(1)

    results = []
    summary = {"pass": 0, "fail": 0, "warn": 0}

    for meta in tracks:
        tid = meta["track_id"]
        track_dir = meta["_dir"]
        track_ok = True

        # 1. Check test prerequisites
        prereq_ok, prereq_msg = check_test_prerequisites(meta, args.tracks_dir)
        if not prereq_ok:
            results.append({"status": "FAIL", "track_id": tid, "check": "prerequisites", "message": prereq_msg})
            track_ok = False

        # 2. Check phases
        phases_ok, phases_msg = check_phases_complete(track_dir)
        if not phases_ok:
            results.append({"status": "FAIL", "track_id": tid, "check": "phases", "message": phases_msg})
            track_ok = False

        # 3. Check tests
        test_cmd = meta.get("test_command")
        if test_cmd and not args.skip_tests:
            timeout = meta.get("test_timeout_seconds", 300)
            tests_ok, tests_msg = run_tests(test_cmd, timeout)
            if not tests_ok:
                results.append({"status": "FAIL", "track_id": tid, "check": "tests", "message": tests_msg})
                track_ok = False
        elif not test_cmd:
            results.append({"status": "WARN", "track_id": tid, "check": "tests", "message": "No test_command in metadata"})
            summary["warn"] += 1
        elif args.skip_tests:
            results.append({"status": "WARN", "track_id": tid, "check": "tests", "message": "Tests skipped (--skip-tests)"})
            summary["warn"] += 1

        # 4. Check quality thresholds (advisory)
        thresh_ok, thresh_msg = check_quality_threshold(meta)
        if thresh_ok and "advisory" in thresh_msg:
            results.append({"status": "INFO", "track_id": tid, "check": "quality", "message": thresh_msg})

        # 5. Check blocking discoveries
        disc_ok, disc_msg = check_blocking_discoveries(tid, args.discovery_dir)
        if not disc_ok:
            results.append({"status": "FAIL", "track_id": tid, "check": "discoveries", "message": disc_msg})
            track_ok = False

        # 6. Check patches
        patches_ok, patches_msg = check_patches(meta, next_wave)
        if not patches_ok:
            results.append({"status": "FAIL", "track_id": tid, "check": "patches", "message": patches_msg})
            track_ok = False

        if track_ok:
            results.append({"status": "PASS", "track_id": tid, "check": "all", "message": "All checks passed"})
            summary["pass"] += 1
        else:
            summary["fail"] += 1

    passed = summary["fail"] == 0
    output = {
        "wave": args.wave,
        "passed": passed,
        "results": results,
        "summary": summary,
    }

    print(json.dumps(output, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
