#!/usr/bin/env python3
"""Prepare a minimal, filtered context bundle for a brief-generator sub-agent.

Extracts only what a single track needs from the full architecture artifacts,
enabling context isolation — each brief-generator sub-agent receives a small
JSON bundle instead of the full architecture files.

Usage:
    # With existing metadata.json:
    python scripts/prepare_brief_context.py --track 03_auth

    # First generation (no metadata.json yet) — provide track info via CLI:
    python scripts/prepare_brief_context.py --track 03_auth \
        --track-name "Authentication & Authorization" \
        --wave 1 --complexity M \
        --description "Handles user auth and RBAC" \
        --dependencies 01_infra_scaffold \
        --interfaces-owned "POST /auth/login" "POST /auth/register" \
        --interfaces-consumed "GET /users/{id}" \
        --events-published "user.logged_in" \
        --events-consumed "user.created"

    python scripts/prepare_brief_context.py --track 03_auth --tracks-dir conductor/tracks --architect-dir architect

Output: JSON to stdout with filtered context for the specified track.
"""

import argparse
import json
import re
import sys
from pathlib import Path


def load_json(path: Path) -> dict | None:
    """Load a JSON file, return None if not found."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def load_text(path: Path) -> str | None:
    """Load a text file, return None if not found."""
    if path.exists():
        return path.read_text()
    return None


def extract_track_metadata(track_id: str, tracks_dir: Path) -> dict | None:
    """Load metadata.json for a specific track."""
    meta_path = tracks_dir / track_id / "metadata.json"
    return load_json(meta_path)


def build_metadata_from_args(args: argparse.Namespace) -> dict:
    """Build a metadata dict from command-line arguments (first generation)."""
    return {
        "track_id": args.track,
        "wave": args.wave,
        "complexity": args.complexity,
        "description": args.description or "",
        "dependencies": args.dependencies or [],
        "interfaces_owned": args.interfaces_owned or [],
        "interfaces_consumed": args.interfaces_consumed or [],
        "events_published": args.events_published or [],
        "events_consumed": args.events_consumed or [],
        "requirements": args.requirements or [],
    }


def derive_track_name(track_id: str) -> str:
    """Derive a human-readable name from a track ID like '03_auth'."""
    parts = track_id.split("_", 1)
    if len(parts) > 1:
        return parts[1].replace("_", " ").title()
    return track_id.replace("_", " ").title()


def extract_constraints_for_track(cc_text: str, track_id: str) -> list[str]:
    """Extract applicable constraints from cross-cutting.md for this track.

    Parses versioned sections and returns constraint descriptions that apply
    to ALL tracks or specifically mention this track.
    """
    if not cc_text:
        return []

    constraints = []
    current_concern = None
    description_lines = []
    applies_to_track = True

    for line in cc_text.splitlines():
        # Match ### headings (concern names)
        if line.startswith("### "):
            # Flush previous concern
            if current_concern and description_lines and applies_to_track:
                desc = " ".join(description_lines)
                constraints.append(f"{current_concern}: {desc}")

            current_concern = line[4:].strip()
            # Remove (NEW) or (MODIFIED) markers
            current_concern = re.sub(r"\s*\((NEW|MODIFIED)\)\s*$", "", current_concern)
            description_lines = []
            applies_to_track = True

        elif current_concern and line.startswith("- Applies to:"):
            scope = line.split(":", 1)[1].strip()
            # Extract track IDs mentioned in scope (e.g., "Tracks 04, 05, 06"
            # or track_id patterns like "03_auth")
            track_refs = re.findall(r"\b(\d{2}_\w+)\b", scope)
            paren_track_nums = re.findall(r"Tracks?\s+([\d,\s]+)", scope)
            if paren_track_nums:
                # Extract 2-digit numbers from "Tracks 04, 05, 06"
                nums = re.findall(r"\d{2}", paren_track_nums[0])
                # Match if our track starts with any of these numbers
                applies_to_track = any(
                    track_id.startswith(n + "_") or track_id == n
                    for n in nums
                )
            elif track_refs:
                # Explicit track IDs mentioned (e.g., "03_auth")
                applies_to_track = track_id in track_refs
            else:
                # Universal scope: "ALL", "ALL services with HTTP endpoints"
                applies_to_track = True

        elif current_concern and line.startswith("- ") and not line.startswith("- Source:"):
            description_lines.append(line[2:].strip())

    # Flush last concern
    if current_concern and description_lines and applies_to_track:
        desc = " ".join(description_lines)
        constraints.append(f"{current_concern}: {desc}")

    return constraints


def extract_architecture_excerpt(arch_text: str, track_id: str, track_name: str) -> str:
    """Extract the relevant section from architecture.md for this track.

    Looks for a section heading that mentions the track name or ID,
    and returns that section's content. Falls back to the component map
    section if no specific section is found.
    """
    if not arch_text:
        return ""

    lines = arch_text.splitlines()
    excerpt_lines = []
    capturing = False
    capture_level = 0

    # Try to find a section mentioning this track
    track_name_lower = track_name.lower() if track_name else ""
    track_id_clean = track_id.replace("_", " ").lower()

    for i, line in enumerate(lines):
        if line.startswith("#"):
            heading_level = len(line) - len(line.lstrip("#"))
            heading_text = line.lstrip("#").strip().lower()

            if capturing:
                # Stop if we hit a heading at same or higher level
                if heading_level <= capture_level:
                    break

            # Check if heading matches track
            if (
                track_id.lower() in heading_text
                or (track_name_lower and track_name_lower in heading_text)
                or any(
                    word in heading_text
                    for word in track_id_clean.split()
                    if len(word) > 3
                )
            ):
                capturing = True
                capture_level = heading_level
                excerpt_lines.append(line)
                continue

        if capturing:
            excerpt_lines.append(line)

    if excerpt_lines:
        return "\n".join(excerpt_lines).strip()

    # Fallback: try to find "Component Map" section
    for i, line in enumerate(lines):
        if line.startswith("#") and "component" in line.lower():
            section_level = len(line) - len(line.lstrip("#"))
            section_lines = [line]
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("#"):
                    next_level = len(lines[j]) - len(lines[j].lstrip("#"))
                    if next_level <= section_level:
                        break
                section_lines.append(lines[j])
            return "\n".join(section_lines).strip()

    return ""


def estimate_tokens(text: str) -> int:
    """Estimate token count (4 chars = 1 token)."""
    return len(text) // 4


def main():
    parser = argparse.ArgumentParser(
        description="Prepare filtered context bundle for a brief-generator sub-agent"
    )
    parser.add_argument("--track", required=True, help="Track ID (e.g., 03_auth)")
    parser.add_argument(
        "--tracks-dir",
        default="conductor/tracks",
        help="Path to conductor tracks directory",
    )
    parser.add_argument(
        "--architect-dir",
        default="architect",
        help="Path to architect directory",
    )

    # CLI overrides for first-generation (when metadata.json doesn't exist yet)
    parser.add_argument("--track-name", help="Human-readable track name")
    parser.add_argument("--wave", type=int, help="Wave number")
    parser.add_argument("--complexity", help="Complexity: S/M/L/XL")
    parser.add_argument("--description", help="Track description")
    parser.add_argument("--dependencies", nargs="*", help="Dependency track IDs")
    parser.add_argument("--interfaces-owned", nargs="*", help="Interfaces this track owns")
    parser.add_argument("--interfaces-consumed", nargs="*", help="Interfaces this track consumes")
    parser.add_argument("--events-published", nargs="*", help="Events this track publishes")
    parser.add_argument("--events-consumed", nargs="*", help="Events this track consumes")
    parser.add_argument("--requirements", nargs="*", default=[], help="Per-track requirements from product.md")
    parser.add_argument("--product-md-path", default="conductor/product.md", help="Path to product.md for fallback access")

    args = parser.parse_args()

    tracks_dir = Path(args.tracks_dir)
    architect_dir = Path(args.architect_dir)

    # Load track metadata from file, or build from CLI args
    meta = extract_track_metadata(args.track, tracks_dir)
    if meta is None:
        # Check if CLI args provide the required data
        if args.wave is not None and args.complexity is not None:
            meta = build_metadata_from_args(args)
        else:
            print(
                json.dumps({
                    "error": f"metadata.json not found for track {args.track} "
                    f"and --wave/--complexity not provided via CLI"
                }),
                file=sys.stdout,
            )
            sys.exit(1)

    # Load architecture artifacts
    cc_text = load_text(architect_dir / "cross-cutting.md")
    arch_text = load_text(architect_dir / "architecture.md")

    # Extract filtered content
    constraints = extract_constraints_for_track(cc_text or "", args.track)

    interfaces_owned = meta.get("interfaces_owned", [])
    interfaces_consumed = meta.get("interfaces_consumed", [])
    events_published = meta.get("events_published", [])
    events_consumed = meta.get("events_consumed", [])
    dependencies = meta.get("dependencies", [])

    # Determine track name: CLI arg > metadata > derive from ID
    track_name = args.track_name or derive_track_name(args.track)

    architecture_excerpt = extract_architecture_excerpt(
        arch_text or "", args.track, track_name
    )

    # Build context bundle
    bundle = {
        "track_id": args.track,
        "track_name": track_name,
        "wave": meta.get("wave", 0),
        "complexity": meta.get("complexity", "M"),
        "description": meta.get("description", ""),
        "requirements": meta.get("requirements", args.requirements or []),
        "product_md_path": args.product_md_path,
        "constraints": constraints,
        "interfaces_owned": interfaces_owned,
        "interfaces_consumed": interfaces_consumed,
        "events_published": events_published,
        "events_consumed": events_consumed,
        "dependencies": dependencies,
        "architecture_excerpt": architecture_excerpt,
    }

    # Estimate total token count
    bundle_text = json.dumps(bundle)
    bundle["token_estimate"] = estimate_tokens(bundle_text)

    print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
