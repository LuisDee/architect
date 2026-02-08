#!/usr/bin/env python3
"""Update architecture artifacts after track completion.

Reads completed track artifacts, extracts implementation decisions via
extract_decisions.py, and generates additive patches to architecture.md,
ADR files, and changelog entries.

Usage:
    python scripts/architecture_updater.py \
        --track-dir conductor/tracks/01_infra \
        --architect-dir architect

    python scripts/architecture_updater.py \
        --track-dir conductor/tracks/01_infra \
        --architect-dir architect \
        --wave 1 \
        --dry-run

Output (JSON to stdout): Summary of patches applied, ADRs generated,
    and changelog entries created.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import sibling module
sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_decisions as ed


def read_file_safe(path: Path) -> str | None:
    """Read a file, returning None if it doesn't exist."""
    if not path.exists():
        return None
    try:
        return path.read_text()
    except OSError:
        return None


def read_template(template_name: str) -> str | None:
    """Read a template file from the plugin templates directory."""
    # Try relative to this script (plugin structure)
    script_dir = Path(__file__).resolve().parent.parent
    template_path = script_dir / "skills" / "architect" / "templates" / template_name
    if template_path.exists():
        return template_path.read_text()
    return None


# --- Architecture patching ---

def generate_architecture_patches(
    decisions: list[dict], track_id: str, arch_text: str | None
) -> list[dict]:
    """Generate additive patches for architecture.md.

    Rules:
    1. Additive only — never delete content
    2. Section targeting — each patch targets a specific ## section
    3. Status markers — ✅ for confirmed, → for modified
    4. Cross-reference ADRs when available
    """
    patches = []

    if not arch_text:
        return patches

    # Group decisions by type
    tech_decisions = [d for d in decisions if d["type"] == "TECHNOLOGY"]
    pattern_decisions = [d for d in decisions if d["type"] == "PATTERN"]
    interface_decisions = [d for d in decisions if d["type"] == "INTERFACE"]

    # Patch: Technology Decisions table
    if tech_decisions:
        for d in tech_decisions:
            patches.append({
                "section": "## Technology Decisions",
                "action": "confirm_choice",
                "target": d["chosen"],
                "patch": f"| {d['chosen']} | ✅ Confirmed ({track_id}) | "
                        f"{d.get('context_line', '')} |",
                "track_id": track_id,
            })

    # Patch: Accepted Architecture Patterns
    if pattern_decisions:
        for d in pattern_decisions:
            patches.append({
                "section": "## Accepted Architecture Patterns",
                "action": "confirm_pattern",
                "target": d["chosen"],
                "patch": f"| {d['chosen']} | ✅ Implemented ({track_id}) | "
                        f"{d.get('context_line', '')} |",
                "track_id": track_id,
            })

    # Patch: Component Map status updates
    # If interfaces were defined, the component is implemented
    if interface_decisions:
        patches.append({
            "section": "## Component Map",
            "action": "update_status",
            "target": track_id,
            "patch": f"<!-- {track_id}: {len(interface_decisions)} "
                    f"interface(s) implemented -->",
            "track_id": track_id,
        })

    return patches


def apply_patches(
    arch_text: str, patches: list[dict], dry_run: bool = False
) -> tuple[str, list[dict]]:
    """Apply patches to architecture.md content.

    Returns (updated_text, applied_patches).
    Skips patches where content already exists (idempotent).
    """
    applied = []
    lines = arch_text.splitlines()
    insertions: list[tuple[int, str]] = []

    for patch in patches:
        section = patch["section"]
        patch_text = patch["patch"]

        # Check if already applied
        if patch_text in arch_text:
            continue

        # Find section
        section_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith(section.lstrip("#").strip()):
                heading_match = re.match(r"^(#{1,3})\s+", line)
                if heading_match:
                    section_idx = i
                    break

        if section_idx is None:
            # Section not found — append at end
            insertions.append((len(lines), f"\n{section}\n\n{patch_text}"))
            applied.append({**patch, "placement": "appended_new_section"})
        else:
            # Find end of section (next ## heading or end of file)
            section_end = len(lines)
            heading_level = len(section.split()[0])  # count #s
            for i in range(section_idx + 1, len(lines)):
                line_match = re.match(r"^(#{1,3})\s+", lines[i])
                if line_match and len(line_match.group(1)) <= heading_level:
                    section_end = i
                    break

            # Insert before section end
            insertions.append((section_end, patch_text))
            applied.append({**patch, "placement": "within_section"})

    if dry_run or not insertions:
        return arch_text, applied

    # Apply insertions from bottom to top to preserve indices
    insertions.sort(key=lambda x: x[0], reverse=True)
    for idx, text in insertions:
        lines.insert(idx, text)

    return "\n".join(lines), applied


# --- ADR generation ---

def generate_adr_content(
    adr_candidate: dict, track_id: str, date: str
) -> str:
    """Generate ADR content from a candidate and template."""
    template = read_template("adr.md")

    if template:
        content = template
        content = content.replace("{{NUMBER}}", f"{adr_candidate['number']:03d}")
        content = content.replace("{{TITLE}}", adr_candidate["title"])
        content = content.replace("{{DATE}}", date)
        content = content.replace("{{TRACK_ID}}", track_id)
        content = content.replace(
            "{{CONTEXT}}",
            adr_candidate.get("context_line", "Decision made during track implementation."),
        )
        content = content.replace(
            "{{DECISION}}",
            f"Chose {adr_candidate['title']}.",
        )

        alternatives = adr_candidate.get("alternatives", [])
        if alternatives:
            alt_text = "\n".join(f"- **{a}** — Considered but not selected" for a in alternatives)
        else:
            alt_text = "- No alternatives explicitly documented"
        content = content.replace("{{ALTERNATIVES}}", alt_text)
        content = content.replace(
            "{{CONSEQUENCES}}",
            f"- Decision documented from {adr_candidate['source']} in track {track_id}",
        )
        return content

    # Fallback if template not found
    alternatives = adr_candidate.get("alternatives", [])
    alt_section = "\n".join(f"- **{a}** — Considered but not selected" for a in alternatives) if alternatives else "- No alternatives explicitly documented"

    return f"""# ADR-{adr_candidate['number']:03d}: {adr_candidate['title']}

**Date:** {date}
**Status:** Accepted
**Track:** {track_id}

## Context

{adr_candidate.get('context_line', 'Decision made during track implementation.')}

## Decision

Chose {adr_candidate['title']}.

## Alternatives Considered

{alt_section}

## Consequences

- Decision documented from {adr_candidate['source']} in track {track_id}
"""


def write_adrs(
    adr_candidates: list[dict], track_id: str,
    architect_dir: Path, date: str, dry_run: bool = False
) -> list[dict]:
    """Write ADR files to architect/decisions/."""
    decisions_dir = architect_dir / "decisions"
    written = []

    for candidate in adr_candidates:
        filename = candidate["filename"]
        filepath = decisions_dir / filename

        # Skip if already exists
        if filepath.exists():
            written.append({
                "filename": filename,
                "status": "already_exists",
            })
            continue

        content = generate_adr_content(candidate, track_id, date)

        if not dry_run:
            decisions_dir.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content)

        written.append({
            "filename": filename,
            "status": "written" if not dry_run else "dry_run",
            "title": candidate["title"],
        })

    return written


# --- Changelog generation ---

def generate_changelog_entry(
    track_id: str, decisions: list[dict],
    adr_written: list[dict], wave: int | None, date: str,
) -> str:
    """Generate a changelog entry for the completed track."""
    template = read_template("changelog-entry.md")

    wave_str = str(wave) if wave else "?"

    # Build sections
    tracks_line = f"- **{track_id}**: Completed"
    arch_changes = []
    for d in decisions:
        if d["type"] == "TECHNOLOGY":
            arch_changes.append(f"- Confirmed technology choice: {d['chosen']}")
        elif d["type"] == "PATTERN":
            arch_changes.append(f"- Confirmed pattern: {d['chosen']}")
    arch_text = "\n".join(arch_changes) if arch_changes else "- No architecture changes"

    adrs_text = "\n".join(
        f"- {a['filename']}: {a.get('title', 'Decision')}"
        for a in adr_written if a["status"] in ("written", "dry_run")
    ) or "- No ADRs generated"

    if template:
        content = template
        content = content.replace("{{WAVE_NUMBER}}", wave_str)
        content = content.replace("{{DATE}}", date)
        content = content.replace("{{TRACKS_COMPLETED}}", tracks_line)
        content = content.replace("{{ARCHITECTURE_CHANGES}}", arch_text)
        content = content.replace("{{ADRS_GENERATED}}", adrs_text)
        content = content.replace("{{CC_UPDATES}}", "No cross-cutting changes.")
        return content

    # Fallback
    return f"""## Wave {wave_str} — {date}

### Tracks Completed
{tracks_line}

### Architecture Changes
{arch_text}

### ADRs Generated
{adrs_text}

### Cross-Cutting Updates
No cross-cutting changes.
"""


def append_changelog(
    entry: str, architect_dir: Path, dry_run: bool = False
) -> str:
    """Append changelog entry to architect/CHANGELOG.md."""
    changelog_path = architect_dir / "CHANGELOG.md"

    if changelog_path.exists():
        existing = changelog_path.read_text()
        # Don't duplicate if entry already present
        if entry.strip().splitlines()[0] in existing:
            return "already_present"
    else:
        existing = "# Architecture Changelog\n\n"

    if not dry_run:
        changelog_path.write_text(existing + "\n" + entry + "\n")

    return "appended" if not dry_run else "dry_run"


# --- Main orchestration ---

def update_architecture(
    track_dir: str, architect_dir: str = "architect",
    wave: int | None = None, dry_run: bool = False,
) -> dict:
    """Main entry point: update architecture artifacts for a completed track.

    Args:
        track_dir: Path to the completed track directory
        architect_dir: Path to the architect directory
        wave: Wave number (for changelog grouping)
        dry_run: If True, compute patches but don't write files

    Returns:
        Summary dict with patches, ADRs, changelog, and warnings.
    """
    arch_path = Path(architect_dir)
    track_path = Path(track_dir)
    track_id = track_path.name
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Step 1: Extract decisions
    extraction = ed.extract_decisions(track_dir, architect_dir)
    decisions = extraction["decisions"]
    adr_candidates = extraction["adr_candidates"]

    # Step 2: Generate architecture patches
    arch_text = read_file_safe(arch_path / "architecture.md")
    patches = generate_architecture_patches(
        decisions, track_id, arch_text
    )

    applied_patches = []
    if arch_text and patches:
        updated_text, applied_patches = apply_patches(
            arch_text, patches, dry_run=dry_run
        )
        if not dry_run and applied_patches:
            (arch_path / "architecture.md").write_text(updated_text)

    # Step 3: Generate ADRs
    adr_written = write_adrs(
        adr_candidates, track_id, arch_path, date, dry_run=dry_run
    )

    # Step 4: Generate changelog entry
    changelog_entry = generate_changelog_entry(
        track_id, decisions, adr_written, wave, date
    )
    changelog_status = append_changelog(
        changelog_entry, arch_path, dry_run=dry_run
    )

    # Step 5: Check for drift warnings
    drift_warnings = []
    if not arch_text:
        drift_warnings.append(
            "architecture.md not found — patches could not be applied"
        )

    return {
        "track_id": track_id,
        "date": date,
        "dry_run": dry_run,
        "decisions_extracted": extraction["summary"],
        "architecture_patches": applied_patches,
        "adrs_generated": adr_written,
        "changelog": {
            "status": changelog_status,
            "wave": wave,
        },
        "drift_warnings": drift_warnings,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Update architecture artifacts after track completion"
    )
    parser.add_argument(
        "--track-dir", type=str, required=True,
        help="Path to the completed track directory",
    )
    parser.add_argument(
        "--architect-dir", type=str, default="architect",
        help="Path to the architect directory",
    )
    parser.add_argument(
        "--wave", type=int, default=None,
        help="Wave number for changelog grouping",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Compute patches without writing files",
    )

    args = parser.parse_args()
    result = update_architecture(
        args.track_dir, args.architect_dir, args.wave, args.dry_run
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
