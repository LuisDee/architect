#!/usr/bin/env python3
"""Check for drift between architecture artifacts and track metadata.

Compares interfaces.md contracts against what tracks actually declare
in their metadata.json files. Checks cross-cutting version consistency
across tracks (are any tracks running against stale CC versions?).

Usage:
    python scripts/sync_check.py
    python scripts/sync_check.py --tracks-dir conductor/tracks --architect-dir architect

Output (JSON to stdout):
    {
      "in_sync": false,
      "interface_mismatches": [...],
      "cc_version_drift": [...],
      "orphaned_interfaces": [...],
      "warnings": [...]
    }
"""

import argparse
import json
import re
import sys
from pathlib import Path


def load_all_metadata(tracks_dir: str) -> list[dict]:
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
            print(f"Warning: skipping {meta_path}: {e}", file=sys.stderr)

    return tracks


def get_current_cc_version(architect_dir: str) -> str | None:
    """Extract latest CC version from cross-cutting.md."""
    cc_path = Path(architect_dir) / "cross-cutting.md"
    if not cc_path.exists():
        return None

    text = cc_path.read_text()
    versions = re.findall(r"## (v[\d.]+)", text)
    return versions[-1] if versions else None


def extract_interfaces_from_md(architect_dir: str) -> dict[str, list[str]]:
    """Extract declared interfaces per track from interfaces.md.

    Returns { track_id: ["/v1/endpoint1", "/v1/endpoint2"] }
    """
    iface_path = Path(architect_dir) / "interfaces.md"
    if not iface_path.exists():
        return {}

    text = iface_path.read_text()
    interfaces = {}
    current_track = None

    for line in text.splitlines():
        # Match ### track headers like "### 04_api_core: Core Resource API"
        track_match = re.match(r"^###\s+(\w+):", line)
        if track_match:
            current_track = track_match.group(1)
            interfaces.setdefault(current_track, [])
            continue

        # Match base paths
        base_match = re.match(r"\*\*Base path:\*\*\s*`(.+?)`", line)
        if base_match and current_track:
            interfaces[current_track].append(base_match.group(1))
            continue

        # Match table rows with endpoints
        if current_track and line.startswith("|") and not line.startswith("| Method") and not line.startswith("|---"):
            cols = [c.strip() for c in line.split("|")]
            if len(cols) >= 4:
                path = cols[2] if len(cols) > 2 else ""
                if path.startswith("/"):
                    interfaces[current_track].append(path)

    return interfaces


def check_interface_sync(
    tracks: list[dict], declared_interfaces: dict[str, list[str]]
) -> tuple[list[dict], list[dict]]:
    """Compare metadata-declared interfaces with interfaces.md.

    Returns (mismatches, orphaned).
    """
    mismatches = []
    orphaned = []

    # Build lookup of what each track claims to own
    track_owned = {}
    for t in tracks:
        tid = t["track_id"]
        track_owned[tid] = set(t.get("interfaces_owned", []))

    # Check each track in interfaces.md
    for tid, declared in declared_interfaces.items():
        owned = track_owned.get(tid, set())
        declared_set = set(declared)

        # Interfaces in interfaces.md but not in metadata
        in_doc_not_meta = declared_set - owned
        # Interfaces in metadata but not in interfaces.md
        in_meta_not_doc = owned - declared_set

        if in_doc_not_meta:
            mismatches.append({
                "track_id": tid,
                "type": "in_interfaces_md_not_metadata",
                "interfaces": sorted(in_doc_not_meta),
            })
        if in_meta_not_doc:
            mismatches.append({
                "track_id": tid,
                "type": "in_metadata_not_interfaces_md",
                "interfaces": sorted(in_meta_not_doc),
            })

    # Check for tracks with interfaces_owned not listed in interfaces.md
    declared_tracks = set(declared_interfaces.keys())
    for t in tracks:
        tid = t["track_id"]
        if t.get("interfaces_owned") and tid not in declared_tracks:
            orphaned.append({
                "track_id": tid,
                "interfaces": t["interfaces_owned"],
                "message": "Track owns interfaces but is not documented in interfaces.md",
            })

    return mismatches, orphaned


def check_cc_version_drift(
    tracks: list[dict], current_version: str | None
) -> list[dict]:
    """Check for CC version drift across tracks."""
    if not current_version:
        return []

    drift = []
    for t in tracks:
        tid = t["track_id"]
        state = t.get("state", "NOT_STARTED")
        cc_at_start = t.get("cc_version_at_start")
        cc_current = t.get("cc_version_current")

        if state == "NOT_STARTED":
            continue  # Will get regenerated header anyway

        if cc_current and cc_current != current_version:
            drift.append({
                "track_id": tid,
                "state": state,
                "track_cc_version": cc_current,
                "current_cc_version": current_version,
                "action": "NEEDS_PATCH" if state == "COMPLETE" else "MID_TRACK_ADOPTION",
            })
        elif cc_at_start and cc_at_start != current_version and not cc_current:
            drift.append({
                "track_id": tid,
                "state": state,
                "track_cc_version": cc_at_start,
                "current_cc_version": current_version,
                "action": "cc_version_current not updated",
            })

    return drift


def check_consumed_interfaces(tracks: list[dict]) -> list[dict]:
    """Check that consumed interfaces are actually owned by some track."""
    warnings = []

    # Build set of all owned interfaces
    all_owned = {}
    for t in tracks:
        for iface in t.get("interfaces_owned", []):
            all_owned[iface] = t["track_id"]

    for t in tracks:
        tid = t["track_id"]
        for consumed in t.get("interfaces_consumed", []):
            if consumed not in all_owned:
                warnings.append({
                    "track_id": tid,
                    "consumed_interface": consumed,
                    "message": "Consumed interface not owned by any track",
                })

    return warnings


def main():
    parser = argparse.ArgumentParser(
        description="Check for drift between architecture artifacts and track metadata"
    )
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")
    parser.add_argument("--architect-dir", default="architect",
                        help="Path to architect directory")

    args = parser.parse_args()
    tracks = load_all_metadata(args.tracks_dir)

    if not tracks:
        print(json.dumps({
            "in_sync": True,
            "message": "No tracks found",
            "interface_mismatches": [],
            "cc_version_drift": [],
            "orphaned_interfaces": [],
            "warnings": [],
        }, indent=2))
        sys.exit(0)

    # Check interfaces
    declared_interfaces = extract_interfaces_from_md(args.architect_dir)
    mismatches, orphaned = check_interface_sync(tracks, declared_interfaces)

    # Check CC version drift
    current_cc = get_current_cc_version(args.architect_dir)
    drift = check_cc_version_drift(tracks, current_cc)

    # Check consumed interfaces
    warnings = check_consumed_interfaces(tracks)

    in_sync = not mismatches and not drift and not orphaned
    result = {
        "in_sync": in_sync,
        "current_cc_version": current_cc,
        "interface_mismatches": mismatches,
        "cc_version_drift": drift,
        "orphaned_interfaces": orphaned,
        "warnings": warnings,
    }

    print(json.dumps(result, indent=2))
    sys.exit(0 if in_sync else 1)


if __name__ == "__main__":
    main()
