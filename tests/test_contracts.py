#!/usr/bin/env python3
"""
Conductor <-> Architect Integration Contract Tests

Tests the file-format contracts between Architect (producer) and
Conductor (consumer). Runs entirely non-interactively against
fixture files or a real project directory.

Usage:
    # Against fixtures (CI / pre-commit)
    python tests/test_contracts.py --fixtures tests/fixtures

    # Against the bundled sample project
    python tests/test_contracts.py --sample-project

    # Against a real project after /conductor:setup + /architect:decompose
    python tests/test_contracts.py --project /path/to/my-project/conductor

    # Specific test groups
    python tests/test_contracts.py --fixtures tests/fixtures \
        --only tracks,metadata,brief

What CAN'T be tested non-interactively:
    - LLM Q&A quality (gap analysis, design decisions)
    - Spec content quality
    - Plan phase breakdown quality
    These require human review or LLM-as-judge evaluation.

What CAN be tested:
    + tracks.md format (Conductor parser compatibility)
    + metadata.json schema (field names, value enums)
    + brief.md structure (ARCHITECT CONTEXT header, required sections)
    + Brief pickup detection (brief exists, spec doesn't -> trigger flow)
    + spec.md context header preservation (after spec generation)
    + Cross-references (tracks.md <-> directory <-> metadata.json)
    + Dependency graph consistency (cycles, forward-wave deps)
    + State machine validity
"""

import argparse
import json
import re
import sys
from pathlib import Path

# -------------------------------------------------------------------
# Test infrastructure
# -------------------------------------------------------------------

class TestResult:
    __slots__ = ("group", "message", "name", "passed", "severity")

    def __init__(self, name: str, group: str, passed: bool,
                 message: str, severity: str = "CRITICAL"):
        self.name = name
        self.group = group
        self.passed = passed
        self.message = message
        self.severity = severity


# Mapping from --only shorthand to group-name prefix
GROUP_ALIASES = {
    "tracks": "tracks.md",
    "metadata": "metadata.json",
    "brief": "brief.md",
    "pickup": "Brief Pickup",
    "context": "Context Header",
    "xref": "Cross-References",
    "deps": "Dependency Graph",
    "state": "State Machine",
    "negative": "Negative",
}


class TestRunner:
    def __init__(self, only_groups: set[str] | None = None):
        self.results: list[TestResult] = []
        self.current_group = ""
        self._only = only_groups  # None = run all

    def group(self, name: str):
        self.current_group = name

    def _is_active(self) -> bool:
        """Check whether the current group is included by --only filter."""
        if self._only is None:
            return True
        for alias, prefix in GROUP_ALIASES.items():
            if alias in self._only and self.current_group.startswith(prefix):
                return True
        return False

    def check(self, name: str, condition: bool, fail_msg: str,
              severity: str = "CRITICAL", pass_msg: str = "OK") -> bool:
        if not self._is_active():
            return condition
        self.results.append(TestResult(
            name=name,
            group=self.current_group,
            passed=condition,
            message=pass_msg if condition else fail_msg,
            severity=severity,
        ))
        return condition

    def report(self) -> int:
        """Print results and return exit code (0=pass, 1=critical failures)."""
        groups: dict[str, list[TestResult]] = {}
        for r in self.results:
            groups.setdefault(r.group, []).append(r)

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = [r for r in self.results if not r.passed]
        critical = [r for r in failed if r.severity == "CRITICAL"]

        print("\n" + "=" * 70)
        print("  CONDUCTOR <-> ARCHITECT CONTRACT TEST RESULTS")
        print("=" * 70)

        for group_name, tests in groups.items():
            group_ok = all(t.passed for t in tests)
            icon = "PASS" if group_ok else "FAIL"
            print(f"\n[{icon}] {group_name}")
            for t in tests:
                if t.passed:
                    print(f"    PASS: {t.name}")
                else:
                    print(f"    FAIL [{t.severity}]: {t.name}")
                    print(f"           -> {t.message}")

        print("\n" + "-" * 70)
        print(f"  Total: {total}  Passed: {passed}  Failed: {len(failed)}")
        if critical:
            print(f"  ** {len(critical)} CRITICAL failures "
                  f"-- integration will break")
        elif failed:
            print(f"  ** {len(failed)} non-critical failures")
        else:
            print("  All contracts satisfied")
        print("-" * 70 + "\n")

        return 1 if critical else 0


# -------------------------------------------------------------------
# Contract validators
# -------------------------------------------------------------------

def validate_tracks_md(t: TestRunner, tracks_path: Path) -> list[dict]:
    """
    Verify tracks.md uses Conductor's expected format.
    Conductor parses by splitting on '---' and matching
    '## [ ] Track:' headings.
    """
    t.group("tracks.md Format (Conductor Parser Compatibility)")

    if not t.check("tracks.md exists", tracks_path.exists(),
                    f"Missing: {tracks_path}"):
        return []

    content = tracks_path.read_text()
    lines = content.strip().split("\n")

    # Must NOT be table format
    table_lines = [l for l in lines
                   if l.strip().startswith("|") and "|" in l[1:]]
    t.check(
        "Not table format",
        len(table_lines) == 0,
        f"Found {len(table_lines)} table rows -- Architect is writing "
        f"table format. Conductor expects ## [ ] Track: blocks.",
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
        r"^##\s+\[([x ~]?)\]\s+Track:\s+(.+)$", re.MULTILINE,
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
        name_m = re.search(r"##\s+\[.\]\s+Track:\s+(.+)", block)
        id_m = re.search(r"\*\*ID:\*\*\s+(\S+)", block)
        wave_m = re.search(r"\*\*Wave:\*\*\s+(\d+)", block)
        cmplx_m = re.search(r"\*\*Complexity:\*\*\s+(S|M|L|XL)", block)
        deps_m = re.search(r"\*\*Dependencies:\*\*\s+(.+)", block)

        has_all = all([name_m, id_m, wave_m, cmplx_m, deps_m])
        track_name = name_m.group(1) if name_m else "unknown"
        t.check(
            f"Track '{track_name}' has all required fields",
            has_all,
            f"Missing fields in track block. Required: ID, Wave, "
            f"Complexity, Dependencies. "
            f"Found: ID={'yes' if id_m else 'NO'}, "
            f"Wave={'yes' if wave_m else 'NO'}, "
            f"Complexity={'yes' if cmplx_m else 'NO'}, "
            f"Deps={'yes' if deps_m else 'NO'}",
        )

        if has_all:
            deps_text = deps_m.group(1).strip()
            parsed_tracks.append({
                "name": name_m.group(1),
                "id": id_m.group(1),
                "wave": int(wave_m.group(1)),
                "complexity": cmplx_m.group(1),
                "dependencies": (
                    [] if deps_text.lower() == "none"
                    else [d.strip() for d in deps_text.split(",")]
                ),
            })

    return parsed_tracks


def validate_metadata_json(t: TestRunner, metadata_path: Path,
                           track_id: str = "") -> dict | None:
    """
    Verify metadata.json uses Conductor's expected schema.
    Conductor reads 'status' field with values:
    new, in_progress, completed, needs_patch, paused, blocked.
    """
    t.group(f"metadata.json Schema ({track_id or metadata_path.name})")

    if not t.check(f"metadata.json exists ({track_id})",
                    metadata_path.exists(), f"Missing: {metadata_path}"):
        return None

    try:
        data = json.loads(metadata_path.read_text())
    except json.JSONDecodeError as e:
        t.check("Valid JSON", False, f"JSON parse error: {e}")
        return None

    t.check("Valid JSON", True, "")

    # Field name: must be "status" not "state"
    has_status = "status" in data
    has_state = "state" in data
    if has_state:
        t.check(
            'Uses "status" field (not "state")',
            False,
            "Found 'state' field. "
            "Conductor reads 'status'. Architect must write 'status'.",
        )
    else:
        t.check(
            'Uses "status" field (not "state")',
            has_status,
            f"Missing 'status' field. Found: {list(data.keys())}",
        )

    # Status values
    valid_statuses = {
        "new", "in_progress", "completed",
        "needs_patch", "paused", "blocked",
    }
    old_statuses = {"NOT_STARTED", "IN_PROGRESS", "COMPLETE", "NEEDS_PATCH"}
    status_val = data.get("status", data.get("state", ""))

    if status_val in old_statuses:
        t.check(
            "Status value uses Conductor enum",
            False,
            f"Value '{status_val}' is Architect's old schema. "
            f"Conductor expects one of: {sorted(valid_statuses)}",
        )
    else:
        t.check(
            "Status value uses Conductor enum",
            status_val in valid_statuses,
            f"Value '{status_val}' not in {sorted(valid_statuses)}",
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
            f"Dependencies type: "
            f"{type(data.get('dependencies')).__name__} (must be list)",
        )

    # Patches use their own internal status field
    for i, patch in enumerate(data.get("patches", [])):
        if "status" in patch:
            t.check(
                f"Patch [{i}] status is valid",
                patch["status"] in {"PENDING", "COMPLETE", "SKIPPED"},
                f"Patch status '{patch['status']}' not in "
                f"{{PENDING, COMPLETE, SKIPPED}}",
                severity="IMPORTANT",
            )

    return data


def validate_brief_md(t: TestRunner, brief_path: Path,
                      track_id: str = "") -> str | None:
    """
    Verify brief.md has required structure including ARCHITECT CONTEXT
    header.
    """
    t.group(f"brief.md Structure ({track_id or brief_path.name})")

    if not t.check(f"brief.md exists ({track_id})",
                    brief_path.exists(), f"Missing: {brief_path}"):
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
            r"<!-- ARCHITECT CONTEXT \| Track: (.+?) "
            r"\| Wave: (\d+) \| CC: (.+?) -->",
            content,
        )
        t.check(
            "Context header has Track, Wave, CC fields",
            ctx_match is not None,
            "Context header present but malformed. Expected: "
            "<!-- ARCHITECT CONTEXT | Track: <id> | Wave: <n> "
            "| CC: <version> -->",
        )

        # Extract context block
        start_idx = content.index("<!-- ARCHITECT CONTEXT")
        end_idx = content.index("<!-- END ARCHITECT CONTEXT -->")
        ctx_block = content[start_idx:end_idx]
        t.check(
            "Context has Cross-Cutting Constraints section",
            "## Cross-Cutting Constraints" in ctx_block
            or "Cross-Cutting Constraints" in ctx_block,
            "Missing Cross-Cutting Constraints in context block",
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
            f"Missing '## {section}' -- needed for: {purpose}",
        )

    # Key Design Decisions should have numbered items
    kdd_match = re.search(
        r"## Key Design Decisions\n(.*?)(?=\n## |\Z)",
        content, re.DOTALL,
    )
    if kdd_match:
        decisions = re.findall(
            r"^\d+\.\s+", kdd_match.group(1), re.MULTILINE,
        )
        t.check(
            "Key Design Decisions has numbered items",
            len(decisions) >= 1,
            "No numbered design decisions found. Brief pickup flow "
            "uses these to drive interactive spec generation.",
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
        "Missing phase estimate -- Conductor uses this for planning",
        severity="MINOR",
    )

    return content


def validate_brief_pickup_detection(t: TestRunner, track_dir: Path,
                                    track_id: str):
    """
    Verify the brief pickup flow would trigger correctly.
    Tests detection logic, not the LLM-driven flow.
    """
    t.group(f"Brief Pickup Detection ({track_id})")

    brief_exists = (track_dir / "brief.md").exists()
    spec_exists = (track_dir / "spec.md").exists()
    plan_exists = (track_dir / "plan.md").exists()
    metadata_exists = (track_dir / "metadata.json").exists()

    t.check(
        "metadata.json exists",
        metadata_exists,
        "No metadata.json -- track is in invalid state",
    )

    if brief_exists and not spec_exists:
        # Architect-generated case -- brief pickup should trigger
        t.check("Brief pickup would trigger (brief=yes, spec=no)",
                True, "")
        t.check(
            "No orphaned plan.md without spec.md",
            not plan_exists,
            "plan.md exists without spec.md -- inconsistent state. "
            "Plan should only exist after spec generation.",
            severity="IMPORTANT",
        )
    elif spec_exists and plan_exists:
        # Manual track or already processed -- skip brief pickup
        t.check("Direct implementation path (spec+plan exist)",
                True, "")
    elif spec_exists and not plan_exists:
        t.check(
            "Spec without plan -- partial state",
            False,
            "spec.md exists but plan.md doesn't. "
            "Implementation requires both.",
            severity="IMPORTANT",
        )
    elif not brief_exists and not spec_exists:
        t.check("No brief or spec -- error state detected correctly",
                True, "")
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
    carried from brief.md into spec.md verbatim.
    """
    t.group(f"Context Header Preservation ({track_id})")

    if not brief_path.exists():
        t.check("brief.md available for comparison", False,
                f"Missing: {brief_path}")
        return
    if not spec_path.exists():
        t.check("spec.md available for comparison", False,
                f"Missing: {spec_path} -- spec not yet generated")
        return

    brief_content = brief_path.read_text()
    spec_content = spec_path.read_text()

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
            "Context block matches brief.md verbatim",
            brief_block == spec_block,
            "ARCHITECT CONTEXT in spec.md differs from brief.md. "
            "The header must be copied verbatim.",
            severity="IMPORTANT",
        )


def validate_cross_references(t: TestRunner, conductor_dir: Path,
                              parsed_tracks: list[dict]):
    """
    Verify consistency between tracks.md, directory structure,
    and metadata files.
    """
    t.group("Cross-References (tracks.md <-> filesystem <-> metadata)")

    tracks_dir = conductor_dir / "tracks"
    if not tracks_dir.exists():
        t.check("tracks/ directory exists", False,
                f"Missing: {tracks_dir}")
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
        f"Mismatch -- tracks.md has {md_track_ids}, "
        f"filesystem has {fs_track_ids}. "
        f"Missing from tracks.md: "
        f"{sorted(set(fs_track_ids) - set(md_track_ids))}. "
        f"Missing from filesystem: "
        f"{sorted(set(md_track_ids) - set(fs_track_ids))}.",
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
            "Track directory has neither brief.md nor spec.md "
            "-- cannot implement",
        )


def validate_dependency_graph(t: TestRunner, parsed_tracks: list[dict]):
    """
    Verify dependency graph is valid: no cycles, no forward-wave
    dependencies.
    """
    t.group("Dependency Graph Consistency")

    if not parsed_tracks:
        t.check("Tracks available for graph validation", False,
                "No parsed tracks -- skipping dependency validation")
        return

    track_by_id = {trk["id"]: trk for trk in parsed_tracks}
    all_ids = set(track_by_id.keys())

    # All dependencies reference existing tracks
    for trk in parsed_tracks:
        for dep in trk["dependencies"]:
            t.check(
                f"Dependency '{dep}' exists "
                f"(referenced by {trk['id']})",
                dep in all_ids,
                f"Track {trk['id']} depends on '{dep}' "
                f"which is not in tracks.md",
            )

    # No track depends on a same-or-later wave
    for trk in parsed_tracks:
        for dep_id in trk["dependencies"]:
            if dep_id in track_by_id:
                dep_wave = track_by_id[dep_id]["wave"]
                t.check(
                    f"{trk['id']} (wave {trk['wave']}) -> "
                    f"{dep_id} (wave {dep_wave})",
                    dep_wave < trk["wave"],
                    f"Track {trk['id']} (wave {trk['wave']}) depends "
                    f"on {dep_id} (wave {dep_wave}). Dependencies "
                    f"must be in earlier waves.",
                )

    # Cycle detection (DFS with recursion stack)
    visited: set[str] = set()
    rec_stack: set[str] = set()
    has_cycle = False

    def dfs(track_id: str):
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
        rec_stack.discard(track_id)

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
    Verify all tracks are in valid states and state transitions
    are consistent.
    """
    t.group("State Machine Validity")

    tracks_dir = conductor_dir / "tracks"
    if not tracks_dir.exists():
        return

    valid_statuses = {
        "new", "in_progress", "completed",
        "needs_patch", "paused", "blocked",
    }

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
            f"Status '{status}' not in {sorted(valid_statuses)}",
        )

        # State consistency with files
        has_spec = (track_dir / "spec.md").exists()
        has_plan = (track_dir / "plan.md").exists()
        started = meta.get("started_at") is not None
        completed = meta.get("completed_at") is not None

        if status == "new":
            t.check(
                f"Track {track_id}: 'new' -> not started",
                not started,
                "Status is 'new' but started_at is set",
                severity="IMPORTANT",
            )
        elif status == "in_progress":
            t.check(
                f"Track {track_id}: 'in_progress' -> has spec+plan",
                has_spec and has_plan,
                f"Status is 'in_progress' but "
                f"spec={has_spec}, plan={has_plan}. "
                f"Brief pickup should have generated these.",
                severity="IMPORTANT",
            )
        elif status == "completed":
            t.check(
                f"Track {track_id}: 'completed' -> completed_at set",
                completed,
                "Status is 'completed' but completed_at is null",
                severity="IMPORTANT",
            )


# -------------------------------------------------------------------
# Negative-case validators (expect specific failures)
# -------------------------------------------------------------------

def validate_negative_tracks_table(t: TestRunner, path: Path):
    """Tracks in table format must be detected as wrong."""
    t.group("Negative Tests (detect bad output)")
    content = path.read_text()
    lines = content.strip().split("\n")
    table_lines = [l for l in lines
                   if l.strip().startswith("|") and "|" in l[1:]]
    t.check(
        "Detects table format as invalid",
        len(table_lines) > 0,
        "Expected table rows to prove detector works",
    )
    track_pattern = re.compile(
        r"^##\s+\[([x ~]?)\]\s+Track:\s+(.+)$", re.MULTILINE,
    )
    t.check(
        "No ## [ ] Track: headings in table format",
        len(track_pattern.findall(content)) == 0,
        "Table format should not have ## [ ] Track: headings",
    )


def validate_negative_metadata_old(t: TestRunner, path: Path):
    """Old metadata schema (state/NOT_STARTED) must be detected."""
    t.group("Negative Tests (detect bad output)")
    data = json.loads(path.read_text())
    t.check(
        "Detects 'state' field (old schema)",
        "state" in data,
        "Expected 'state' field to prove detector works",
    )
    t.check(
        "Detects old status value (NOT_STARTED)",
        data.get("state") in {"NOT_STARTED", "IN_PROGRESS", "COMPLETE"},
        "Expected old-style value to prove detector works",
    )


def validate_negative_brief_no_header(t: TestRunner, path: Path):
    """Brief without ARCHITECT CONTEXT must be detected."""
    t.group("Negative Tests (detect bad output)")
    content = path.read_text()
    t.check(
        "Detects missing ARCHITECT CONTEXT",
        "<!-- ARCHITECT CONTEXT" not in content,
        "Expected no context header to prove detector works",
    )


def validate_negative_brief_malformed(t: TestRunner, path: Path):
    """Brief with malformed ARCHITECT CONTEXT must be detected."""
    t.group("Negative Tests (detect bad output)")
    content = path.read_text()
    t.check(
        "Has ARCHITECT CONTEXT tags (malformed)",
        "<!-- ARCHITECT CONTEXT" in content,
        "Expected context tags to exist",
    )
    ctx_match = re.search(
        r"<!-- ARCHITECT CONTEXT \| Track: (.+?) "
        r"\| Wave: (\d+) \| CC: (.+?) -->",
        content,
    )
    t.check(
        "Detects malformed context header (no Track|Wave|CC)",
        ctx_match is None,
        "Expected malformed header (missing Track|Wave|CC fields)",
    )


def validate_negative_spec_lost_context(t: TestRunner,
                                        brief_path: Path,
                                        spec_path: Path):
    """Spec without context header (lost during generation)."""
    t.group("Negative Tests (detect bad output)")
    spec_content = spec_path.read_text()
    t.check(
        "Detects spec without ARCHITECT CONTEXT",
        "<!-- ARCHITECT CONTEXT" not in spec_content,
        "Expected spec to be missing context header",
    )


def validate_negative_cycle(t: TestRunner, tracks_path: Path):
    """Dependency cycle must be detected."""
    t.group("Negative Tests (dependency cycle)")
    parsed = []
    content = tracks_path.read_text()
    blocks = re.split(r"\n---\n", content)
    for block in blocks:
        name_m = re.search(r"##\s+\[.\]\s+Track:\s+(.+)", block)
        id_m = re.search(r"\*\*ID:\*\*\s+(\S+)", block)
        wave_m = re.search(r"\*\*Wave:\*\*\s+(\d+)", block)
        cmplx_m = re.search(r"\*\*Complexity:\*\*\s+(S|M|L|XL)", block)
        deps_m = re.search(r"\*\*Dependencies:\*\*\s+(.+)", block)
        if all([name_m, id_m, wave_m, cmplx_m, deps_m]):
            deps_text = deps_m.group(1).strip()
            parsed.append({
                "name": name_m.group(1),
                "id": id_m.group(1),
                "wave": int(wave_m.group(1)),
                "complexity": cmplx_m.group(1),
                "dependencies": (
                    [] if deps_text.lower() == "none"
                    else [d.strip() for d in deps_text.split(",")]
                ),
            })

    # Run cycle detection
    track_by_id = {trk["id"]: trk for trk in parsed}
    visited: set[str] = set()
    rec_stack: set[str] = set()
    has_cycle = False

    def dfs(tid: str):
        nonlocal has_cycle
        visited.add(tid)
        rec_stack.add(tid)
        trk = track_by_id.get(tid)
        if trk:
            for dep in trk["dependencies"]:
                if dep not in visited:
                    dfs(dep)
                elif dep in rec_stack:
                    has_cycle = True
        rec_stack.discard(tid)

    for tid in track_by_id:
        if tid not in visited:
            dfs(tid)

    t.check(
        "Cycle detected in bad fixture",
        has_cycle,
        "Expected cycle to be detected in cycle fixture",
    )


def validate_negative_forward_wave(t: TestRunner, tracks_path: Path):
    """Forward-wave dependency must be detected."""
    t.group("Negative Tests (forward-wave dependency)")
    parsed = []
    content = tracks_path.read_text()
    blocks = re.split(r"\n---\n", content)
    for block in blocks:
        name_m = re.search(r"##\s+\[.\]\s+Track:\s+(.+)", block)
        id_m = re.search(r"\*\*ID:\*\*\s+(\S+)", block)
        wave_m = re.search(r"\*\*Wave:\*\*\s+(\d+)", block)
        cmplx_m = re.search(r"\*\*Complexity:\*\*\s+(S|M|L|XL)", block)
        deps_m = re.search(r"\*\*Dependencies:\*\*\s+(.+)", block)
        if all([name_m, id_m, wave_m, cmplx_m, deps_m]):
            deps_text = deps_m.group(1).strip()
            parsed.append({
                "name": name_m.group(1),
                "id": id_m.group(1),
                "wave": int(wave_m.group(1)),
                "complexity": cmplx_m.group(1),
                "dependencies": (
                    [] if deps_text.lower() == "none"
                    else [d.strip() for d in deps_text.split(",")]
                ),
            })

    track_by_id = {trk["id"]: trk for trk in parsed}
    found_forward = False
    for trk in parsed:
        for dep_id in trk["dependencies"]:
            if dep_id in track_by_id and track_by_id[dep_id]["wave"] >= trk["wave"]:
                found_forward = True

    t.check(
        "Forward-wave dependency detected in bad fixture",
        found_forward,
        "Expected forward-wave dependency to be detected",
    )


# -------------------------------------------------------------------
# Test scenarios
# -------------------------------------------------------------------

def run_fixture_tests(t: TestRunner, fixtures_dir: Path):
    """Run tests against fixture files."""

    # -- Scenario 1: Good Architect output ---------------------
    arch_dir = fixtures_dir / "architect-output"
    if arch_dir.exists():
        parsed = validate_tracks_md(t, arch_dir / "tracks.md")

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

    # -- Scenario 2: Manual track (regression) -----------------
    manual_dir = fixtures_dir / "conductor-manual"
    if manual_dir.exists():
        tracks_dir = manual_dir / "tracks"
        if tracks_dir.exists():
            for track_dir in sorted(tracks_dir.iterdir()):
                if not track_dir.is_dir():
                    continue
                tid = track_dir.name
                validate_metadata_json(
                    t, track_dir / "metadata.json", tid,
                )
                validate_brief_pickup_detection(t, track_dir, tid)

    # -- Scenario 3: Post spec-gen (context preservation) ------
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

    # -- Scenario 4: Negative cases (bad fixtures) -------------
    bad_dir = fixtures_dir / "bad"
    if bad_dir.exists():
        if (bad_dir / "tracks_table_format.md").exists():
            validate_negative_tracks_table(
                t, bad_dir / "tracks_table_format.md",
            )

        if (bad_dir / "metadata_old_schema.json").exists():
            validate_negative_metadata_old(
                t, bad_dir / "metadata_old_schema.json",
            )

        if (bad_dir / "brief_no_context_header.md").exists():
            validate_negative_brief_no_header(
                t, bad_dir / "brief_no_context_header.md",
            )

        if (bad_dir / "brief_malformed_context.md").exists():
            validate_negative_brief_malformed(
                t, bad_dir / "brief_malformed_context.md",
            )

        if (bad_dir / "spec_lost_context.md").exists():
            # Use any brief as reference
            any_brief = (fixtures_dir / "architect-output"
                         / "tracks" / "01_infra_scaffold" / "brief.md")
            validate_negative_spec_lost_context(
                t, any_brief, bad_dir / "spec_lost_context.md",
            )

        if (bad_dir / "tracks_cycle.md").exists():
            validate_negative_cycle(t, bad_dir / "tracks_cycle.md")

        if (bad_dir / "tracks_forward_wave.md").exists():
            validate_negative_forward_wave(
                t, bad_dir / "tracks_forward_wave.md",
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

            if ((track_dir / "brief.md").exists()
                    and (track_dir / "spec.md").exists()):
                validate_context_header_preservation(
                    t, track_dir / "brief.md",
                    track_dir / "spec.md", tid,
                )

    if parsed:
        validate_dependency_graph(t, parsed)
        validate_cross_references(t, conductor_dir, parsed)

    validate_state_machine(t, conductor_dir)


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Conductor <-> Architect integration contract tests",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--fixtures", type=Path,
        help="Run against fixture directory",
    )
    group.add_argument(
        "--project", type=Path,
        help="Run against a real project's conductor/ directory",
    )
    group.add_argument(
        "--sample-project", action="store_true",
        help="Run against examples/sample-project/conductor",
    )
    parser.add_argument(
        "--only", type=str, default=None,
        help="Comma-separated test groups: "
             "tracks,metadata,brief,pickup,context,xref,deps,state,negative",
    )
    args = parser.parse_args()

    only = set(args.only.split(",")) if args.only else None
    t = TestRunner(only_groups=only)

    if args.fixtures:
        run_fixture_tests(t, args.fixtures)
    elif args.sample_project:
        sample = (Path(__file__).parent.parent
                  / "examples" / "sample-project" / "conductor")
        run_project_tests(t, sample)
    else:
        run_project_tests(t, args.project)

    sys.exit(t.report())


if __name__ == "__main__":
    main()
