#!/usr/bin/env python3
"""Tests for scripts/prepare_brief_context.py.

Uses unittest (stdlib-only). Run with:
    python -m unittest tests/test_prepare_brief_context.py -v
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts/ to path so we can import the module under test
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import prepare_brief_context as pbc

# Path to sample project fixtures
SAMPLE_PROJECT = REPO_ROOT / "examples" / "sample-project"
SAMPLE_TRACKS_DIR = SAMPLE_PROJECT / "conductor" / "tracks"
SAMPLE_ARCHITECT_DIR = SAMPLE_PROJECT / "architect"

# Path to the script for integration tests
SCRIPT_PATH = REPO_ROOT / "scripts" / "prepare_brief_context.py"

# Sample cross-cutting markdown for unit tests
SAMPLE_CC_TEXT = """\
## v1 — Initial (Wave 1)

### Observability
- OpenTelemetry SDK for traces and metrics
- structlog for Python backend with JSON output
- Applies to: ALL
- Source: Architecture research

### Error Handling
- RFC 7807 Problem Details format
- No stack traces in production
- Applies to: ALL services with HTTP endpoints
- Source: Cross-cutting catalog

### Transactional Outbox
- All domain event publishing through outbox table
- Outbox relay polls every 500ms
- Applies to: ALL services that publish domain events (Tracks 04, 05, 06)
- Source: Architecture research

### Rate Limiting (NEW)
- Token bucket per user
- Applies to: 03_auth
- Source: Discovery
"""

# Sample architecture markdown for unit tests
SAMPLE_ARCH_TEXT = """\
# System Architecture

## System Overview
A workflow automation platform.

## Component Map
```
[Frontend] -> [Backend] -> [Database]
```

### Component Responsibilities
| Component | Responsibility |
|-----------|---------------|
| Frontend  | UI            |

## Auth Module
Handles JWT issuance and RBAC enforcement.
Uses python-jose for token operations.

## Workflow Engine
Orchestrates multi-step workflows.
"""


class TestDeriveTrackName(unittest.TestCase):
    def test_numbered_prefix(self):
        self.assertEqual(pbc.derive_track_name("03_auth"), "Auth")

    def test_multi_word(self):
        self.assertEqual(pbc.derive_track_name("01_infra_scaffold"), "Infra Scaffold")

    def test_no_prefix(self):
        self.assertEqual(pbc.derive_track_name("standalone"), "Standalone")

    def test_single_digit_prefix(self):
        self.assertEqual(pbc.derive_track_name("1_core"), "Core")


class TestExtractConstraintsForTrack(unittest.TestCase):
    def test_all_scope_included(self):
        constraints = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "01_infra")
        concern_names = [c.split(":")[0] for c in constraints]
        self.assertIn("Observability", concern_names)

    def test_http_endpoints_scope_included_for_any_track(self):
        """'ALL services with HTTP endpoints' contains 'ALL' so it matches."""
        constraints = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "01_infra")
        concern_names = [c.split(":")[0] for c in constraints]
        self.assertIn("Error Handling", concern_names)

    def test_specific_track_scope_excluded(self):
        """Track 01 should NOT get 'Transactional Outbox' (scoped to Tracks 04, 05, 06)."""
        constraints = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "01_infra")
        concern_names = [c.split(":")[0] for c in constraints]
        self.assertNotIn("Transactional Outbox", concern_names)

    def test_specific_track_scope_included(self):
        """Track 04 SHOULD get 'Transactional Outbox' since it's in the scope."""
        constraints = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "04_api")
        concern_names = [c.split(":")[0] for c in constraints]
        self.assertIn("Transactional Outbox", concern_names)

    def test_track_specific_constraint(self):
        """'Rate Limiting' applies only to 03_auth."""
        constraints_03 = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "03_auth")
        constraints_01 = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "01_infra")
        names_03 = [c.split(":")[0] for c in constraints_03]
        names_01 = [c.split(":")[0] for c in constraints_01]
        self.assertIn("Rate Limiting", names_03)
        self.assertNotIn("Rate Limiting", names_01)

    def test_empty_text_returns_empty(self):
        self.assertEqual(pbc.extract_constraints_for_track("", "any_track"), [])

    def test_strips_new_marker(self):
        constraints = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "03_auth")
        concern_names = [c.split(":")[0] for c in constraints]
        # Should be "Rate Limiting" not "Rate Limiting (NEW)"
        self.assertIn("Rate Limiting", concern_names)
        self.assertNotIn("Rate Limiting (NEW)", concern_names)

    def test_constraint_includes_description(self):
        constraints = pbc.extract_constraints_for_track(SAMPLE_CC_TEXT, "01_infra")
        obs = [c for c in constraints if c.startswith("Observability")]
        self.assertEqual(len(obs), 1)
        self.assertIn("OpenTelemetry", obs[0])
        self.assertIn("structlog", obs[0])


class TestExtractArchitectureExcerpt(unittest.TestCase):
    def test_finds_section_by_track_name(self):
        excerpt = pbc.extract_architecture_excerpt(SAMPLE_ARCH_TEXT, "03_auth", "Auth Module")
        self.assertIn("JWT issuance", excerpt)
        self.assertIn("RBAC", excerpt)

    def test_finds_section_by_word_match(self):
        excerpt = pbc.extract_architecture_excerpt(
            SAMPLE_ARCH_TEXT, "05_workflow_engine", "Workflow Engine"
        )
        self.assertIn("multi-step workflows", excerpt)

    def test_fallback_to_component_map(self):
        """When no track-specific section found, returns Component Map."""
        excerpt = pbc.extract_architecture_excerpt(
            SAMPLE_ARCH_TEXT, "99_nonexistent", "Nonexistent Track"
        )
        self.assertIn("Component", excerpt)

    def test_empty_text_returns_empty(self):
        self.assertEqual(pbc.extract_architecture_excerpt("", "any", "Any"), "")

    def test_none_text_returns_empty(self):
        self.assertEqual(pbc.extract_architecture_excerpt(None, "any", "Any"), "")

    def test_section_stops_at_same_level_heading(self):
        """Auth Module section should NOT include Workflow Engine content."""
        excerpt = pbc.extract_architecture_excerpt(SAMPLE_ARCH_TEXT, "03_auth", "Auth Module")
        self.assertNotIn("multi-step workflows", excerpt)


class TestEstimateTokens(unittest.TestCase):
    def test_standard(self):
        self.assertEqual(pbc.estimate_tokens("a" * 8000), 2000)

    def test_empty(self):
        self.assertEqual(pbc.estimate_tokens(""), 0)

    def test_short(self):
        self.assertEqual(pbc.estimate_tokens("abc"), 0)  # 3 // 4 = 0

    def test_exact_boundary(self):
        self.assertEqual(pbc.estimate_tokens("abcd"), 1)


class TestBuildMetadataFromArgs(unittest.TestCase):
    def test_all_fields(self):
        args = argparse.Namespace(
            track="03_auth",
            wave=2,
            complexity="L",
            description="Auth system",
            dependencies=["01_infra", "02_db"],
            interfaces_owned=["POST /auth/login"],
            interfaces_consumed=["GET /users/{id}"],
            events_published=["user.logged_in"],
            events_consumed=["user.created"],
            requirements=["Support JWT auth"],
        )
        meta = pbc.build_metadata_from_args(args)
        self.assertEqual(meta["track_id"], "03_auth")
        self.assertEqual(meta["wave"], 2)
        self.assertEqual(meta["complexity"], "L")
        self.assertEqual(meta["description"], "Auth system")
        self.assertEqual(meta["dependencies"], ["01_infra", "02_db"])
        self.assertEqual(meta["interfaces_owned"], ["POST /auth/login"])
        self.assertEqual(meta["events_published"], ["user.logged_in"])

    def test_none_optional_fields_default(self):
        args = argparse.Namespace(
            track="01_core",
            wave=1,
            complexity="S",
            description=None,
            dependencies=None,
            interfaces_owned=None,
            interfaces_consumed=None,
            events_published=None,
            events_consumed=None,
            requirements=None,
        )
        meta = pbc.build_metadata_from_args(args)
        self.assertEqual(meta["description"], "")
        self.assertEqual(meta["dependencies"], [])
        self.assertEqual(meta["interfaces_owned"], [])
        self.assertEqual(meta["events_published"], [])


class TestIntegration(unittest.TestCase):
    """Integration tests that run the script as a subprocess."""

    def _run_script(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            capture_output=True,
            text=True,
        )

    def test_with_sample_project(self):
        """Run against the real sample project fixtures."""
        result = self._run_script([
            "--track", "01_infra_scaffold",
            "--tracks-dir", str(SAMPLE_TRACKS_DIR),
            "--architect-dir", str(SAMPLE_ARCHITECT_DIR),
        ])
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

        bundle = json.loads(result.stdout)
        self.assertEqual(bundle["track_id"], "01_infra_scaffold")
        self.assertEqual(bundle["wave"], 1)
        self.assertEqual(bundle["complexity"], "M")
        self.assertIsInstance(bundle["constraints"], list)
        self.assertGreater(len(bundle["constraints"]), 0)
        self.assertIsInstance(bundle["interfaces_owned"], list)
        self.assertIsInstance(bundle["dependencies"], list)
        self.assertIsInstance(bundle["token_estimate"], int)
        self.assertGreater(bundle["token_estimate"], 0)
        self.assertIn("architecture_excerpt", bundle)

    def test_sample_project_track_with_dependencies(self):
        """Track 02 depends on 01 — verify dependency is in output."""
        result = self._run_script([
            "--track", "02_database_schema",
            "--tracks-dir", str(SAMPLE_TRACKS_DIR),
            "--architect-dir", str(SAMPLE_ARCHITECT_DIR),
        ])
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

        bundle = json.loads(result.stdout)
        self.assertEqual(bundle["track_id"], "02_database_schema")
        self.assertEqual(bundle["wave"], 2)
        self.assertIn("01_infra_scaffold", bundle["dependencies"])

    def test_cli_args_fallback(self):
        """When metadata.json doesn't exist, CLI args should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_script([
                "--track", "99_test",
                "--tracks-dir", tmpdir,
                "--architect-dir", str(SAMPLE_ARCHITECT_DIR),
                "--wave", "3",
                "--complexity", "L",
                "--track-name", "Test Track",
                "--description", "A test track",
                "--dependencies", "01_infra",
                "--interfaces-owned", "POST /test",
                "--events-published", "test.created",
            ])
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

            bundle = json.loads(result.stdout)
            self.assertEqual(bundle["track_id"], "99_test")
            self.assertEqual(bundle["track_name"], "Test Track")
            self.assertEqual(bundle["wave"], 3)
            self.assertEqual(bundle["complexity"], "L")
            self.assertEqual(bundle["description"], "A test track")
            self.assertEqual(bundle["dependencies"], ["01_infra"])
            self.assertEqual(bundle["interfaces_owned"], ["POST /test"])
            self.assertEqual(bundle["events_published"], ["test.created"])

    def test_missing_metadata_no_cli_args(self):
        """No metadata.json and no CLI args → exit 1 with error JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_script([
                "--track", "99_missing",
                "--tracks-dir", tmpdir,
                "--architect-dir", tmpdir,
            ])
            self.assertEqual(result.returncode, 1)

            error = json.loads(result.stdout)
            self.assertIn("error", error)
            self.assertIn("99_missing", error["error"])

    def test_missing_architect_dir(self):
        """Valid metadata but missing architect/ → succeeds with empty constraints."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_script([
                "--track", "01_test",
                "--tracks-dir", tmpdir,
                "--architect-dir", os.path.join(tmpdir, "nonexistent"),
                "--wave", "1",
                "--complexity", "S",
            ])
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

            bundle = json.loads(result.stdout)
            self.assertEqual(bundle["constraints"], [])
            self.assertEqual(bundle["architecture_excerpt"], "")


if __name__ == "__main__":
    unittest.main()
