#!/usr/bin/env python3
"""
Conductor ↔ Architect Integration Contract Tests

Tests the file-format contracts between Architect (producer) and
Conductor (consumer). Runs entirely non-interactively against
fixture files or a real project directory.

Usage:
    # Against fixtures (CI / pre-commit)
    python test_contracts.py --fixtures ./fixtures

    # Against a real project after running /conductor:setup + /architect:decompose
    python test_contracts.py --project /path/to/my-project/conductor

    # Specific test groups
    python test_contracts.py --fixtures ./fixtures --only tracks,metadata,brief

What CAN'T be tested non-interactively:
    - LLM Q&A quality (gap analysis, design decisions)
    - Spec content quality
    - Plan phase breakdown quality
    These require human review or LLM-as-judge evaluation.

What CAN be tested:
    ✓ tracks.md format (Conductor parser compatibility)
    ✓ metadata.json schema (field names, value enums)
    ✓ brief.md structure (ARCHITECT CONTEXT header, required sections)
    ✓ Brief pickup detection (brief exists, spec doesn't → trigger flow)
    ✓ spec.md context header preservation (after spec generation)
    ✓ Cross-references (tracks.md ↔ directory ↔ metadata.json)
    ✓ Dependency graph consistency
    ✓ State machine validity
    ✓ Wave sequencing (no track depends on same/later wave)
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Test infrastructure
# ─────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    group: str
    passed: bool
    message: str
    severity: str = "CRITICAL"  # CRITICAL | IMPORTANT | MINOR


class TestRunner:
    def __init__(self):
        self.results: list[TestResult] = []
        self.current_group = ""

    def group(self, name: str):
        self.current_group = name

    def check(self, name: str, condition: bool, fail_msg: str,
              severity: str = "CRITICAL", pass_msg: str = "OK"):
        result = TestResult(
            name=name,
            group=self.current_group,
            passed=condition,
            message=pass_msg if condition else fail_msg,
            severity=severity,
        )
        self.results.append(result)
        return condition

    def report(self) -> int:
        """Print results and return exit code (0=pass, 1=failures)."""
        groups: dict[str, list[TestResult]] = {}
        for r in self.results:
            groups.setdefault(r.group, []).append(r)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = [r for r in self.results if not r.passed]
        critical = [r for r in failed if r.severity == "CRITICAL"]

        print("\n" + "=" * 70)
        print("  CONDUCTOR ↔ ARCHITECT CONTRACT TEST RESULTS")
        print("=" * 70)

        for group_name, tests in groups.items():
            group_pass = all(t.passed for t in tests)
            icon = "✅" if group_pass else "❌"
            print(f"\n{icon} {group_name}")
            for t in tests:
                status = "  PASS" if t.passed else f"  FAIL [{t.severity}]"
                print(f"  {status}: {t.name}")
                if not t.passed:
                    print(f"         → {t.message}")

        print("\n" + "-" * 70)
        print(f"  Total: {total}  Passed: {passed}  Failed: {len(failed)}")
        if critical:
            print(f"  ⚠️  {len(critical)} CRITICAL failures — integration will break")
        elif failed:
            print(f"  ⚠️  {len(failed)} non-critical failures")
        else:
            print("  ✅ All contracts satisfied")
        print("-" * 70 + "\n")

        return 1 if critical else 0


# ─────────────────────────────────────────────────────────────
# Contract validators
# ─────────────────────────────────────────────────────────────

def validate_tracks_md(t: TestRunner, tracks_path: Path):
    """
    Verify tracks.md uses Conductor's expected format.
    Conductor parses by splitting on '---' and matching '## [ ] Track:' headings.
    """
    t.group("tracks.md Format (Conductor Parser Compatibility)")

    if not t.check("tracks.md exists", tracks_path.exists(),
                    f"Missing: {tracks_path}"):
        return []

    content = tracks_path.read_text()
    lines = content.strip().split("\n")

    # Must NOT be table format
    table_lines = [l for l in lines if l.strip().startswith("|") and "|" in l[1:]]
    t.check(
        "Not table format",
        len(table_lines) == 0,
        f"Found {len(table_lines)} table rows — Architect is writing table format. "
        f"Conductor expects ## [ ] Track: blocks.",
    )

    # Must have --- separators
    separator_count = sum(1 for l in lines if l.strip() == "---")
    t.check(
        "Has --- separators",
        separator_count >= 2,
        f"Found {separator_count} separators, expected at least 2. "
        f"Conductor splits on --- to parse track blocks.",
    )

    # Parse track blocks
    track_pattern = re.compile(
        r"^##\s+\[([x ~]?)\]\s+Track:\s+(.+)$", re.MULTILINE
    )
    tracks = track_pattern.findall(content)

    t.check(
        "Has track headings",
        len(tracks) > 0,
        "No '## [ ] Track: <name>' headings found. "
        "Conductor's parser requires this exact format.",
    )

    # Each track block must have required fields
    blocks = re.split(r"\n---\n", content)
    track_blocks = [b for b in blocks if "## [" in b and "Track:" in b]

    parsed_tracks = []
    for block in track_blocks:
        name_match = re.search(r"##\s+\[.\]\s+Track:\s+(.+)", block)
        id_match = re.search(r"\*\*ID:\*\*\s+(\S+)", block)
        wave_match = re.search(r"\*\*Wave:\*\*\s+(\d+)", block)
        complexity_match = re.search(r"\*\*Complexity:\*\*\s+(S|M|L|XL)", block)
        deps_match = re.search(r"\*\*Dependencies:\*\*\s+(.+)", block)

        has_all = all([name_match, id_match, wave_match, complexity_match, deps_match])
        track_name = name_match.group(1) if name_match else "unknown"
        t.check(
            f"Track '{track_name}' has all required fields",
            has_all,
            f"Missing fields in track block. Required: ID, Wave, Complexity, Dependencies. "
            f"Found: ID={'yes' if id_match else 'NO'}, Wave={'yes' if wave_match else 'NO'}, "
            f"Complexity={'yes' if complexity_match else 'NO'}, Deps={'yes' if deps_match else 'NO'}",
        )

        if has_all:
            parsed_tracks.append({
                "name": name_match.group(1),
                "id": id_match.group(1),
                "wave": int(wave_match.group(1)),
                "complexity": complexity_match.group(1),
                "dependencies": [] if deps_match.group(1).strip().lower() == "none"
                    else [d.strip() for d in deps_match.group(1).split(",")],
                "status": "not_started",  # [ ] = not started
            })

    return parsed_tracks


def validate_metadata_json(t: TestRunner, metadata_path: Path, track_id: str = ""):
    """
    Verify metadata.json uses Conductor's expected schema.
    Conductor reads 'status' field with values: new, in_progress, completed, blocked.
    """
    t.group(f"metadata.json Schema ({track_id or metadata_path.name})")

    if not t.check(f"metadata.json exists ({track_id})", metadata_path.exists(),
                    f"Missing: {metadata_path}"):
        return None

    try:
        data = json.loads(metadata_path.read_text())
    except json.JSONDecodeError as e:
        t.check("Valid JSON", False, f"JSON parse error: {e}")
        return None

    t.check("Valid JSON", True, "")

    # Field name: must be "status" not "state"
    t.check(
        'Uses "status" field (not "state")',
        "status" in data and "state" not in data,
        f"Found fields: {list(data.keys())}. "
        f"Conductor reads 'status'. Architect is writing 'state'."
        if "state" in data else
        f"Missing 'status' field. Found: {list(data.keys())}",
    )

    # Status values
    valid_statuses = {"new", "in_progress", "completed", "blocked"}
    old_statuses = {"NOT_STARTED", "IN_PROGRESS", "COMPLETE"}
    status_val = data.get("status", data.get("state", ""))

    if status_val in old_statuses:
        t.check(
            "Status value uses Conductor enum",
            False,
            f"Value '{status_val}' is Architect's old schema. "
            f"Conductor expects one of: {valid_statuses}",
        )
    else:
        t.check(
            "Status value uses Conductor enum",
            status_val in valid_statuses,
            f"Value '{status_val}' not in {valid_statuses}",
        )

    # Required fields
    required = ["track_id", "complexity", "wave", "dependencies"]
    missing = [f for f in required if f not in data]
    t.check(
        "Has all required fields",
        len(missing) == 0,
        f"Missing required fields: {missing}",
    )

    # Wave is positive integer
    if "wave" in data:
        t.check(
            "Wave is positive integer",
            isinstance(data["wave"], int) and data["wave"] > 0,
            f"Wave value: {data.get('wave')} (must be positive integer)",
            severity="IMPORTANT",
        )

    # Dependencies is a list
    if "dependencies" in data:
        t.check(
            "Dependencies is a list",
            isinstance(data["dependencies"], list),
            f"Dependencies type: {type(data.get('dependencies')).__name__} (must be list)",
        )

    return data


def validate_brief_md(t: TestRunner, brief_path: Path, track_id: str = ""):
    """
    Verify brief.md has required structure including ARCHITECT CONTEXT header.
    """
    t.group(f"brief.md Structure ({track_id or brief_path.name})")

    if not t.check(f"brief.md exists ({track_id})", brief_path.exists(),
                    f"Missing: {brief_path}"):
        return None

    content = brief_path.read_text()

    # ARCHITECT CONTEXT header
    has_start = "<!-- ARCHITECT CONTEXT" in content
    has_end = "<!-- END ARCHITECT CONTEXT -->" in content
    t.check(
        "Has ARCHITECT CONTEXT start tag",
        has_start,
        "Missing '<!-- ARCHITECT CONTEXT ...' header. "
        "Hooks use this to identify applicable constraints.",
    )
    t.check(
        "Has ARCHITECT CONTEXT end tag",
        has_end,
        "Missing '<!-- END ARCHITECT CONTEXT -->' closing tag.",
    )

    # Context header fields
    if has_start and has_end:
        ctx_match = re.search(
            r"<!-- ARCHITECT CONTEXT \| Track: (.+?) \| Wave: (\d+) \| CC: (.+?) -->",
            content,
        )
        t.check(
            "Context header has Track, Wave, CC fields",
            ctx_match is not None,
            "Context header present but malformed. Expected: "
            "<!-- ARCHITECT CONTEXT | Track: <id> | Wave: <n> | CC: <version> -->",
        )

        # Extract context block
        ctx_block = content[content.index("<!-- ARCHITECT CONTEXT"):
                            content.index("<!-- END ARCHITECT CONTEXT -->")]
        t.check(
            "Context has Cross-Cutting Constraints section",
            "## Cross-Cutting Constraints" in ctx_block,
            "Missing '## Cross-Cutting Constraints' in context block",
            severity="IMPORTANT",
        )
        t.check(
            "Context has Interfaces section",
            "## Interfaces" in ctx_block or "Interfaces" in ctx_block,
            "Missing interfaces info in context block",
            severity="IMPORTANT",
        )
        t.check(
            "Context has Dependencies section",
            "## Dependencies" in ctx_block or "Dependencies" in ctx_block,
            "Missing dependencies info in context block",
            severity="IMPORTANT",
        )

    # Required brief sections
    required_sections = {
        "What This Track Delivers": "One-paragraph track description",
        "Scope": "IN/OUT boundaries",
        "Key Design Decisions": "Questions for developer during spec gen",
    }
    for section, purpose in required_sections.items():
        t.check(
            f"Has '{section}' section",
            f"## {section}" in content,
            f"Missing '## {section}' — needed for: {purpose}",
        )

    # Key Design Decisions should have numbered items
    kdd_match = re.search(r"## Key Design Decisions\n(.*?)(?=\n## |\Z)",
                          content, re.DOTALL)
    if kdd_match:
        decisions = re.findall(r"^\d+\.\s+", kdd_match.group(1), re.MULTILINE)
        t.check(
            "Key Design Decisions has numbered items",
            len(decisions) >= 1,
            "No numbered design decisions found. Brief pickup flow uses these "
            "to drive interactive spec generation.",
            severity="IMPORTANT",
        )

    # Complexity and estimated phases
    t.check(
        "Has Complexity rating",
        "## Complexity:" in content or "**Complexity**" in content,
        "Missing complexity estimate (S/M/L/XL)",
        severity="MINOR",
    )
    t.check(
        "Has Estimated Phases",
        "Estimated Phases" in content,
        "Missing phase estimate — Conductor uses this for planning",
        severity="MINOR",
    )

    return content


def validate_brief_pickup_detection(t: TestRunner, track_dir: Path, track_id: str):
    """
    Verify the brief pickup flow would trigger correctly.
    This tests the detection logic, not the LLM-driven flow.
    """
    t.group(f"Brief Pickup Detection ({track_id})")

    brief_exists = (track_dir / "brief.md").exists()
    spec_exists = (track_dir / "spec.md").exists()
    plan_exists = (track_dir / "plan.md").exists()
    metadata_exists = (track_dir / "metadata.json").exists()

    t.check(
        "metadata.json exists",
        metadata_exists,
        "No metadata.json — track is in invalid state",
    )

    if brief_exists and not spec_exists:
        # This is the Architect-generated case — brief pickup should trigger
        t.check(
            "Brief pickup would trigger (brief=yes, spec=no)",
            True,
            "",
        )
        t.check(
            "No orphaned plan.md without spec.md",
            not plan_exists,
            "plan.md exists without spec.md — inconsistent state. "
            "Plan should only exist after spec generation.",
            severity="IMPORTANT",
        )
    elif spec_exists and plan_exists:
        # Manual track or already processed — skip brief pickup
        t.check(
            "Direct implementation path (spec+plan exist)",
            True,
            "",
        )
    elif spec_exists and not plan_exists:
        t.check(
            "Spec without plan — partial state",
            False,
            "spec.md exists but plan.md doesn't. Implementation requires both.",
            severity="IMPORTANT",
        )
    elif not brief_exists and not spec_exists:
        t.check(
            "No brief or spec — error state detected correctly",
            True,  # This is correctly detected as an error
            "",
        )
        t.check(
            "Track has either brief or spec",
            False,
            "Track has neither brief.md nor spec.md. "
            "Run /architect:decompose or /conductor:new-track.",
        )


def validate_context_header_preservation(t: TestRunner, brief_path: Path,
                                          spec_path: Path, track_id: str):
    """
    After spec generation, verify the ARCHITECT CONTEXT header was
    carried from brief.md into spec.md.
    """
    t.group(f"Context Header Preservation ({track_id})")

    if not brief_path.exists():
        t.check("brief.md available for comparison", False,
                f"Missing: {brief_path}")
        return
    if not spec_path.exists():
        t.check("spec.md available for comparison", False,
                f"Missing: {spec_path} — spec not yet generated")
        return

    brief_content = brief_path.read_text()
    spec_content = spec_path.read_text()

    # Extract context blocks
    ctx_pattern = re.compile(
        r"(<!-- ARCHITECT CONTEXT.*?<!-- END ARCHITECT CONTEXT -->)",
        re.DOTALL,
    )

    brief_ctx = ctx_pattern.search(brief_content)
    spec_ctx = ctx_pattern.search(spec_content)

    t.check(
        "spec.md has ARCHITECT CONTEXT block",
        spec_ctx is not None,
        "ARCHITECT CONTEXT header was NOT preserved in spec.md. "
        "Hooks depend on this header for constraint checking.",
    )

    if brief_ctx and spec_ctx:
        # Normalize whitespace for comparison
        brief_block = " ".join(brief_ctx.group(1).split())
        spec_block = " ".join(spec_ctx.group(1).split())
        t.check(
            "Context block matches brief.md",
            brief_block == spec_block,
            "ARCHITECT CONTEXT in spec.md differs from brief.md. "
            "The header must be copied verbatim.",
            severity="IMPORTANT",
        )


def validate_cross_references(t: TestRunner, conductor_dir: Path,
                               parsed_tracks: list[dict]):
    """
    Verify consistency between tracks.md, directory structure, and metadata files.
    """
    t.group("Cross-References (tracks.md ↔ filesystem ↔ metadata)")

    tracks_dir = conductor_dir / "tracks"
    if not tracks_dir.exists():
        t.check("tracks/ directory exists", False, f"Missing: {tracks_dir}")
        return

    # Get all track directories
    fs_track_ids = sorted([
        d.name for d in tracks_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ])

    # Get track IDs from parsed tracks.md
    md_track_ids = sorted([trk["id"] for trk in parsed_tracks])

    t.check(
        "tracks.md lists all track directories",
        set(md_track_ids) == set(fs_track_ids),
        f"Mismatch — tracks.md has {md_track_ids}, "
        f"filesystem has {fs_track_ids}. "
        f"Missing from tracks.md: {set(fs_track_ids) - set(md_track_ids)}. "
        f"Missing from filesystem: {set(md_track_ids) - set(fs_track_ids)}.",
    )

    # Each track directory has metadata.json
    for track_id in fs_track_ids:
        track_dir = tracks_dir / track_id
        t.check(
            f"Track {track_id} has metadata.json",
            (track_dir / "metadata.json").exists(),
            f"Missing metadata.json in {track_dir}",
        )

        # metadata.json track_id matches directory name
        meta_path = track_dir / "metadata.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                t.check(
                    f"Track {track_id} metadata.track_id matches directory",
                    meta.get("track_id") == track_id,
                    f"metadata.track_id='{meta.get('track_id')}' "
                    f"but directory is '{track_id}'",
                    severity="IMPORTANT",
                )
            except json.JSONDecodeError:
                pass

        # Track has either brief.md or spec.md
        has_brief = (track_dir / "brief.md").exists()
        has_spec = (track_dir / "spec.md").exists()
        t.check(
            f"Track {track_id} has brief.md or spec.md",
            has_brief or has_spec,
            f"Track directory has neither brief.md nor spec.md — "
            f"cannot implement",
        )


def validate_dependency_graph(t: TestRunner, parsed_tracks: list[dict]):
    """
    Verify dependency graph is valid: no cycles, no forward-wave dependencies.
    """
    t.group("Dependency Graph Consistency")

    if not parsed_tracks:
        t.check("Tracks available for graph validation", False,
                "No parsed tracks — skipping dependency validation")
        return

    track_by_id = {trk["id"]: trk for trk in parsed_tracks}
    all_ids = set(track_by_id.keys())

    # All dependencies reference existing tracks
    for trk in parsed_tracks:
        for dep in trk["dependencies"]:
            t.check(
                f"Dependency '{dep}' exists (referenced by {trk['id']})",
                dep in all_ids,
                f"Track {trk['id']} depends on '{dep}' which is not in tracks.md",
            )

    # No track depends on a same-or-later wave
    for trk in parsed_tracks:
        for dep_id in trk["dependencies"]:
            if dep_id in track_by_id:
                dep_wave = track_by_id[dep_id]["wave"]
                t.check(
                    f"{trk['id']} (wave {trk['wave']}) → {dep_id} (wave {dep_wave})",
                    dep_wave < trk["wave"],
                    f"Track {trk['id']} (wave {trk['wave']}) depends on "
                    f"{dep_id} (wave {dep_wave}). Dependencies must be in "
                    f"earlier waves.",
                )

    # Simple cycle detection (topological sort)
    visited = set()
    rec_stack = set()
    has_cycle = False

    def dfs(track_id):
        nonlocal has_cycle
        visited.add(track_id)
        rec_stack.add(track_id)
        trk = track_by_id.get(track_id)
        if trk:
            for dep in trk["dependencies"]:
                if dep not in visited:
                    dfs(dep)
                elif dep in rec_stack:
                    has_cycle = True
        rec_stack.remove(track_id)

    for tid in all_ids:
        if tid not in visited:
            dfs(tid)

    t.check(
        "Dependency graph is acyclic",
        not has_cycle,
        "Circular dependency detected in track graph",
    )


def validate_state_machine(t: TestRunner, conductor_dir: Path):
    """
    Verify all tracks are in valid states and state transitions are consistent.
    """
    t.group("State Machine Validity")

    tracks_dir = conductor_dir / "tracks"
    if not tracks_dir.exists():
        return

    valid_statuses = {"new", "in_progress", "completed", "blocked"}

    for track_dir in sorted(tracks_dir.iterdir()):
        if not track_dir.is_dir() or track_dir.name.startswith("."):
            continue

        meta_path = track_dir / "metadata.json"
        if not meta_path.exists():
            continue

        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            continue

        track_id = track_dir.name
        status = meta.get("status", meta.get("state", "UNKNOWN"))

        t.check(
            f"Track {track_id} status is valid",
            status in valid_statuses,
            f"Status '{status}' not in {valid_statuses}",
        )

        # State consistency with files
        has_spec = (track_dir / "spec.md").exists()
        has_plan = (track_dir / "plan.md").exists()
        started = meta.get("started_at") is not None
        completed = meta.get("completed_at") is not None

        if status == "new":
            t.check(
                f"Track {track_id}: 'new' → not started",
                not started,
                "Status is 'new' but started_at is set",
                severity="IMPORTANT",
            )
        elif status == "in_progress":
            t.check(
                f"Track {track_id}: 'in_progress' → has spec+plan",
                has_spec and has_plan,
                f"Status is 'in_progress' but spec={has_spec}, plan={has_plan}. "
                f"Brief pickup should have generated these.",
                severity="IMPORTANT",
            )
        elif status == "completed":
            t.check(
                f"Track {track_id}: 'completed' → completed_at set",
                completed,
                "Status is 'completed' but completed_at is null",
                severity="IMPORTANT",
            )


# ─────────────────────────────────────────────────────────────
# Test scenarios
# ─────────────────────────────────────────────────────────────

def run_fixture_tests(t: TestRunner, fixtures_dir: Path):
    """Run tests against fixture files."""

    # ── Scenario 1: Architect output validation ──────────────
    arch_dir = fixtures_dir / "architect-output"
    if arch_dir.exists():
        parsed = validate_tracks_md(t, arch_dir / "tracks.md")

        # Validate each track's metadata + brief
        tracks_dir = arch_dir / "tracks"
        if tracks_dir.exists():
            for track_dir in sorted(tracks_dir.iterdir()):
                if not track_dir.is_dir():
                    continue
                tid = track_dir.name
                validate_metadata_json(t, track_dir / "metadata.json", tid)
                validate_brief_md(t, track_dir / "brief.md", tid)
                validate_brief_pickup_detection(t, track_dir, tid)

        if parsed:
            validate_dependency_graph(t, parsed)
            validate_cross_references(t, arch_dir, parsed)
            validate_state_machine(t, arch_dir)

    # ── Scenario 2: Manual track (regression) ────────────────
    manual_dir = fixtures_dir / "conductor-manual"
    if manual_dir.exists():
        tracks_dir = manual_dir / "tracks"
        if tracks_dir.exists():
            for track_dir in sorted(tracks_dir.iterdir()):
                if not track_dir.is_dir():
                    continue
                tid = track_dir.name
                validate_metadata_json(t, track_dir / "metadata.json", tid)
                validate_brief_pickup_detection(t, track_dir, tid)

    # ── Scenario 3: Post spec-gen (context preservation) ─────
    post_dir = fixtures_dir / "post-spec-gen"
    if post_dir.exists():
        tracks_dir = post_dir / "tracks"
        if tracks_dir.exists():
            for track_dir in sorted(tracks_dir.iterdir()):
                if not track_dir.is_dir():
                    continue
                tid = track_dir.name
                validate_context_header_preservation(
                    t,
                    track_dir / "brief.md",
                    track_dir / "spec.md",
                    tid,
                )

    # ── Scenario 4: Negative cases (bad fixtures) ────────────
    bad_dir = fixtures_dir / "bad"
    if bad_dir.exists():
        t.group("Negative Tests (detect bad output)")

        # Bad tracks.md (table format)
        if (bad_dir / "tracks_table_format.md").exists():
            bad_parsed = validate_tracks_md(
                t, bad_dir / "tracks_table_format.md"
            )
            # We EXPECT these to fail — the failures prove our
            # validators catch bad output

        # Bad metadata (old schema)
        if (bad_dir / "metadata_old_schema.json").exists():
            validate_metadata_json(
                t, bad_dir / "metadata_old_schema.json", "BAD_old_schema"
            )

        # Bad brief (no context header)
        if (bad_dir / "brief_no_context_header.md").exists():
            validate_brief_md(
                t, bad_dir / "brief_no_context_header.md", "BAD_no_header"
            )


def run_project_tests(t: TestRunner, conductor_dir: Path):
    """Run tests against a real project directory."""

    parsed = validate_tracks_md(t, conductor_dir / "tracks.md")

    tracks_dir = conductor_dir / "tracks"
    if tracks_dir.exists():
        for track_dir in sorted(tracks_dir.iterdir()):
            if not track_dir.is_dir() or track_dir.name.startswith("."):
                continue
            tid = track_dir.name
            validate_metadata_json(t, track_dir / "metadata.json", tid)

            if (track_dir / "brief.md").exists():
                validate_brief_md(t, track_dir / "brief.md", tid)

            validate_brief_pickup_detection(t, track_dir, tid)

            if (track_dir / "brief.md").exists() and (track_dir / "spec.md").exists():
                validate_context_header_preservation(
                    t, track_dir / "brief.md", track_dir / "spec.md", tid,
                )

    if parsed:
        validate_dependency_graph(t, parsed)
        validate_cross_references(t, conductor_dir, parsed)

    validate_state_machine(t, conductor_dir)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Conductor ↔ Architect integration contract tests"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--fixtures", type=Path,
                       help="Run against fixture directory")
    group.add_argument("--project", type=Path,
                       help="Run against a real project's conductor/ directory")
    parser.add_argument("--only", type=str, default=None,
                        help="Comma-separated test groups: "
                             "tracks,metadata,brief,pickup,context,xref,deps,state")
    args = parser.parse_args()

    t = TestRunner()

    if args.fixtures:
        run_fixture_tests(t, args.fixtures)
    else:
        run_project_tests(t, args.project)

    sys.exit(t.report())


if __name__ == "__main__":
    main()
