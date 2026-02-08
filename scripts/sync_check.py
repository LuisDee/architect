#!/usr/bin/env python3
"""Check for drift between architecture artifacts and track metadata.

Compares interfaces.md contracts against what tracks actually declare
in their metadata.json files. Checks cross-cutting version consistency
across tracks (are any tracks running against stale CC versions?).
Detects structural drift where implementation diverges from architecture.md.

Usage:
    python scripts/sync_check.py
    python scripts/sync_check.py --tracks-dir conductor/tracks --architect-dir architect

Output (JSON to stdout):
    {
      "in_sync": false,
      "interface_mismatches": [...],
      "cc_version_drift": [...],
      "structural_drift": [...],
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
        state = t.get("status", "new")
        cc_at_start = t.get("cc_version_at_start")
        cc_current = t.get("cc_version_current")

        if state == "new":
            continue  # Will get regenerated header anyway

        if cc_current and cc_current != current_version:
            drift.append({
                "track_id": tid,
                "status": state,
                "track_cc_version": cc_current,
                "current_cc_version": current_version,
                "action": "NEEDS_PATCH" if state == "completed" else "MID_TRACK_ADOPTION",
            })
        elif cc_at_start and cc_at_start != current_version and not cc_current:
            drift.append({
                "track_id": tid,
                "status": state,
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


def extract_architecture_components(architect_dir: str) -> list[dict]:
    """Extract declared components from architecture.md.

    Looks for ### component headings with status markers and technology info.
    Returns list of {name, technology, status} dicts.
    """
    arch_path = Path(architect_dir) / "architecture.md"
    if not arch_path.exists():
        return []

    text = arch_path.read_text()
    components = []
    in_component_map = False

    for line in text.splitlines():
        # Detect Component Map section
        if re.match(r"^##\s+Component\s+Map", line, re.IGNORECASE):
            in_component_map = True
            continue
        # Detect next ## section (exit component map)
        if in_component_map and re.match(r"^##\s+", line) and not re.match(r"^###", line):
            in_component_map = False
            continue

        # Match ### component headings within Component Map
        if in_component_map:
            comp_match = re.match(r"^###\s+(.+?)(?:\s*[—–-]\s*(.+))?$", line)
            if comp_match:
                name = comp_match.group(1).strip()
                rest = comp_match.group(2) or ""
                # Check for status markers
                status = "planned"
                if "✅" in rest or "✅" in name:
                    status = "implemented"
                    name = name.replace("✅", "").strip()
                elif "→" in rest:
                    status = "modified"
                elif "⚠" in rest or "⚠️" in rest:
                    status = "drift"
                components.append({
                    "name": name,
                    "status": status,
                    "detail": rest.strip(),
                })

    return components


def extract_track_components(tracks: list[dict]) -> dict[str, list[str]]:
    """Extract component references from track metadata.

    Looks at boundaries, interfaces_owned, and the track scope
    to determine which architecture components each track touches.
    """
    track_components: dict[str, list[str]] = {}
    for t in tracks:
        tid = t["track_id"]
        components = []
        # Extract from boundaries
        components.extend(t.get("boundaries", []))
        # Extract from scope keywords
        scope = t.get("scope", "")
        if scope:
            components.append(scope)
        track_components[tid] = components
    return track_components


def check_structural_drift(
    tracks: list[dict], architect_dir: str
) -> list[dict]:
    """Detect structural drift between architecture.md and track reality.

    Checks:
    1. Components declared in architecture.md with no covering track
    2. Completed tracks that reference components not in architecture.md
    3. Technology mismatches between architecture.md and track metadata
    """
    drift = []

    arch_components = extract_architecture_components(architect_dir)
    if not arch_components:
        return drift

    arch_component_names = {c["name"].lower() for c in arch_components}

    # Check 1: Tracks referencing undeclared components
    for t in tracks:
        tid = t["track_id"]
        if t.get("status") not in ("in_progress", "completed"):
            continue

        # Check if track's scope references components not in architecture
        scope = t.get("scope", "").lower()
        boundaries = [b.lower() for b in t.get("boundaries", [])]

        for boundary in boundaries:
            # Check if the boundary's target exists in architecture
            boundary_words = set(boundary.replace("_", " ").split())
            found = False
            for comp_name in arch_component_names:
                comp_words = set(comp_name.replace("_", " ").replace("-", " ").split())
                if boundary_words & comp_words:
                    found = True
                    break
            # Don't flag standard boundary names (they're categories not components)
            standard_boundaries = {
                "data_model", "api_layer", "ui_layer",
                "infrastructure", "external_integration",
            }
            if not found and boundary not in standard_boundaries:
                drift.append({
                    "type": "undeclared_component",
                    "track_id": tid,
                    "component": boundary,
                    "message": f"Track {tid} references component '{boundary}' "
                              f"not found in architecture.md",
                })

    # Check 2: Architecture components with no covering track
    track_scopes = " ".join(
        t.get("scope", "") for t in tracks
    ).lower()
    track_ids = " ".join(t["track_id"] for t in tracks).lower()

    for comp in arch_components:
        comp_name = comp["name"].lower()
        comp_words = set(comp_name.replace("-", " ").replace("_", " ").split())

        # Check if any track covers this component
        covered = False
        for word in comp_words:
            if len(word) > 2 and (word in track_scopes or word in track_ids):
                covered = True
                break

        if not covered and comp["status"] == "planned":
            drift.append({
                "type": "uncovered_component",
                "component": comp["name"],
                "status": comp["status"],
                "message": f"Architecture component '{comp['name']}' has no "
                          f"covering track",
            })

    # Check 3: Architecture.md shows "planned" but track is completed
    for comp in arch_components:
        if comp["status"] != "planned":
            continue
        comp_lower = comp["name"].lower()
        for t in tracks:
            if t.get("status") != "completed":
                continue
            scope_lower = t.get("scope", "").lower()
            tid_lower = t["track_id"].lower()
            comp_words = set(comp_lower.replace("-", " ").replace("_", " ").split())
            for word in comp_words:
                if len(word) > 2 and (word in scope_lower or word in tid_lower):
                    drift.append({
                        "type": "stale_status",
                        "component": comp["name"],
                        "track_id": t["track_id"],
                        "message": f"Component '{comp['name']}' still marked as "
                                  f"'planned' in architecture.md but track "
                                  f"{t['track_id']} is completed",
                    })
                    break

    return drift


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
            "structural_drift": [],
            "orphaned_interfaces": [],
            "warnings": [],
        }, indent=2))
        sys.exit(0)

    # Check interfaces
    declared_interfaces = extract_interfaces_from_md(args.architect_dir)
    mismatches, orphaned = check_interface_sync(tracks, declared_interfaces)

    # Check CC version drift
    current_cc = get_current_cc_version(args.architect_dir)
    cc_drift = check_cc_version_drift(tracks, current_cc)

    # Check structural drift
    struct_drift = check_structural_drift(tracks, args.architect_dir)

    # Check consumed interfaces
    warnings = check_consumed_interfaces(tracks)

    in_sync = not mismatches and not cc_drift and not orphaned and not struct_drift
    result = {
        "in_sync": in_sync,
        "current_cc_version": current_cc,
        "interface_mismatches": mismatches,
        "cc_version_drift": cc_drift,
        "structural_drift": struct_drift,
        "orphaned_interfaces": orphaned,
        "warnings": warnings,
    }

    print(json.dumps(result, indent=2))
    sys.exit(0 if in_sync else 1)


if __name__ == "__main__":
    main()
