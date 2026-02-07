#!/usr/bin/env python3
"""Process pending discoveries: deduplicate, detect conflicts, merge to log.

Reads all files from architect/discovery/pending/, sorts chronologically,
deduplicates by word overlap on suggested scope, checks for constraint
conflicts, validates urgency against track states, appends to
discovery-log.md, and moves processed files to processed/.

Usage:
    python scripts/merge_discoveries.py
    python scripts/merge_discoveries.py --discovery-dir architect/discovery
    python scripts/merge_discoveries.py --dry-run

Output (JSON to stdout):
    {
      "processed": 3,
      "duplicates": 1,
      "conflicts": 0,
      "escalated": 1,
      "errors": 0,
      "details": [...]
    }
"""

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def parse_discovery_file(path: Path) -> dict | None:
    """Parse a discovery markdown file into a structured dict."""
    try:
        text = path.read_text()
    except OSError as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        return None

    entry = {"file": path.name, "path": str(path)}

    field_map = {
        "source": "source",
        "timestamp": "timestamp",
        "discovery": "discovery",
        "classification": "classification",
        "suggested scope": "suggested_scope",
        "dependencies": "dependencies",
        "urgency": "urgency",
    }

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- **") and ":**" in line:
            match = re.match(r"- \*\*(.+?):\*\*\s*(.*)", line)
            if match:
                key = match.group(1).lower().strip()
                value = match.group(2).strip()
                if key in field_map:
                    entry[field_map[key]] = value

    # Extract track ID from filename (e.g., track-04-2026-...)
    fname_match = re.match(r"(track[_-]\d+\w*)", path.stem.replace("-", "_"))
    if fname_match:
        entry.setdefault("source_track", fname_match.group(1))

    return entry if "discovery" in entry else None


def word_set(text: str) -> set[str]:
    """Extract word set from text, lowercased, alphanumeric only."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def word_overlap(a: str, b: str) -> float:
    """Calculate Jaccard word overlap between two strings."""
    words_a = word_set(a)
    words_b = word_set(b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def check_constraint_conflict(
    entry: dict, existing: list[dict]
) -> dict | None:
    """Check if a CROSS_CUTTING_CHANGE conflicts with existing constraints.

    Looks for must/must-not contradictions on the same subject.
    Returns conflict info or None.
    """
    if entry.get("classification") != "CROSS_CUTTING_CHANGE":
        return None

    text = entry.get("discovery", "").lower()
    must_match = re.findall(r"must\s+(?:not\s+)?(\w+(?:\s+\w+){0,3})", text)
    if not must_match:
        return None

    has_must_not = "must not" in text

    for existing_entry in existing:
        if existing_entry.get("classification") != "CROSS_CUTTING_CHANGE":
            continue
        ex_text = existing_entry.get("discovery", "").lower()
        ex_has_must_not = "must not" in ex_text

        # Check if they contradict (one says must, other says must not)
        if has_must_not != ex_has_must_not:
            # Check subject overlap
            overlap = word_overlap(text, ex_text)
            if overlap > 0.5:
                return {
                    "conflicting_entry": existing_entry.get("file", "unknown"),
                    "overlap": round(overlap, 2),
                    "this": entry.get("discovery", ""),
                    "that": existing_entry.get("discovery", ""),
                }

    return None


def load_track_states(tracks_dir: str = "conductor/tracks") -> dict[str, dict]:
    """Load track states from metadata files."""
    states = {}
    tracks_path = Path(tracks_dir)
    if not tracks_path.exists():
        return states

    for meta_path in tracks_path.glob("*/metadata.json"):
        try:
            with open(meta_path) as f:
                meta = json.load(f)
            states[meta["track_id"]] = meta
        except (json.JSONDecodeError, OSError, KeyError):
            continue

    return states


def validate_urgency(entry: dict, track_states: dict) -> str | None:
    """Validate and potentially escalate urgency based on track states.

    Returns new urgency if escalated, None if unchanged.
    """
    urgency = entry.get("urgency", "BACKLOG").upper()
    deps_text = entry.get("dependencies", "")

    if urgency == "BLOCKING":
        return None  # Already highest

    # Check if this blocks an IN_PROGRESS track
    for tid, meta in track_states.items():
        if meta.get("status") == "in_progress" and tid in deps_text:
            return "BLOCKING"

    # Check if this blocks a track in the next wave
    if urgency == "BACKLOG":
        for tid, meta in track_states.items():
            state = meta.get("status", "new")
            if state == "new" and tid in deps_text:
                return "NEXT_WAVE"

    return None


def append_to_log(log_path: Path, entry: dict, action: str):
    """Append a processed entry to discovery-log.md."""
    timestamp = entry.get("timestamp", datetime.now().isoformat())
    classification = entry.get("classification", "UNKNOWN")
    urgency = entry.get("urgency", "BACKLOG")
    discovery = entry.get("discovery", "(no description)")
    source = entry.get("source", "(unknown)")

    log_entry = (
        f"\n### {timestamp} — {classification} ({urgency})\n"
        f"- **Source:** {source}\n"
        f"- **Discovery:** {discovery}\n"
        f"- **Action:** {action}\n"
        f"- **File:** {entry.get('file', 'unknown')}\n"
    )

    with open(log_path, "a") as f:
        f.write(log_entry)


def main():
    parser = argparse.ArgumentParser(
        description="Process pending discoveries"
    )
    parser.add_argument("--discovery-dir", default="architect/discovery",
                        help="Path to discovery directory")
    parser.add_argument("--tracks-dir", default="conductor/tracks",
                        help="Path to conductor tracks directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")

    args = parser.parse_args()

    pending_dir = Path(args.discovery_dir) / "pending"
    processed_dir = Path(args.discovery_dir) / "processed"
    log_path = Path(args.discovery_dir) / "discovery-log.md"

    if not pending_dir.exists():
        print(json.dumps({
            "processed": 0,
            "duplicates": 0,
            "conflicts": 0,
            "escalated": 0,
            "errors": 0,
            "details": [],
            "message": "No pending directory found",
        }, indent=2))
        sys.exit(0)

    # Ensure output dirs exist
    if not args.dry_run:
        processed_dir.mkdir(parents=True, exist_ok=True)

    # Load pending files sorted chronologically by filename
    pending_files = sorted(pending_dir.glob("*.md"))
    if not pending_files:
        print(json.dumps({
            "processed": 0,
            "duplicates": 0,
            "conflicts": 0,
            "escalated": 0,
            "errors": 0,
            "details": [],
            "message": "No pending discoveries",
        }, indent=2))
        sys.exit(0)

    # Parse all entries
    entries = []
    parse_errors = 0
    for fp in pending_files:
        entry = parse_discovery_file(fp)
        if entry:
            entries.append(entry)
        else:
            parse_errors += 1

    # Load track states for urgency validation
    track_states = load_track_states(args.tracks_dir)

    # Process entries
    processed_entries = []  # Already accepted entries for dedup comparison
    results = []
    stats = {"processed": 0, "duplicates": 0, "conflicts": 0, "escalated": 0, "errors": parse_errors}

    # Initialize log if it doesn't exist
    if not args.dry_run and not log_path.exists():
        log_path.write_text("# Discovery Log\n\n> Auto-generated by merge_discoveries.py. Read-only reference.\n\n---\n")

    for entry in entries:
        action_taken = None

        # 1. Dedup check
        is_dup = False
        scope = entry.get("suggested_scope", entry.get("discovery", ""))
        for prev in processed_entries:
            prev_scope = prev.get("suggested_scope", prev.get("discovery", ""))
            if word_overlap(scope, prev_scope) > 0.7:
                is_dup = True
                action_taken = f"DUPLICATE of {prev.get('file', 'unknown')}"
                stats["duplicates"] += 1
                break

        # 2. Conflict check (only for non-duplicates)
        conflict = None
        if not is_dup:
            conflict = check_constraint_conflict(entry, processed_entries)
            if conflict:
                entry["classification"] = "ARCHITECTURE_CHANGE"
                action_taken = f"CONFLICT: reclassified to ARCHITECTURE_CHANGE (conflicts with {conflict['conflicting_entry']})"
                stats["conflicts"] += 1

        # 3. Urgency validation
        if not is_dup:
            new_urgency = validate_urgency(entry, track_states)
            if new_urgency:
                old = entry.get("urgency", "BACKLOG")
                entry["urgency"] = new_urgency
                if action_taken:
                    action_taken += f"; ESCALATED {old} -> {new_urgency}"
                else:
                    action_taken = f"ESCALATED {old} -> {new_urgency}"
                stats["escalated"] += 1

        if not action_taken:
            action_taken = f"PROCESSED as {entry.get('classification', 'UNKNOWN')}"

        # 4. Record result
        result_entry = {
            "file": entry.get("file"),
            "classification": entry.get("classification"),
            "urgency": entry.get("urgency"),
            "action": action_taken,
            "duplicate": is_dup,
        }
        results.append(result_entry)

        # 5. Append to log and move file
        if not args.dry_run:
            append_to_log(log_path, entry, action_taken)
            src = Path(entry["path"])
            dst = processed_dir / src.name
            try:
                shutil.move(str(src), str(dst))
            except OSError as e:
                print(f"Error moving {src} to {dst}: {e}", file=sys.stderr)
                stats["errors"] += 1

        if not is_dup:
            processed_entries.append(entry)
        stats["processed"] += 1

    output = {**stats, "details": results}
    print(json.dumps(output, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
