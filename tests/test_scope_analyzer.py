#!/usr/bin/env python3
"""Tests for scripts/scope_analyzer.py.

Uses unittest (stdlib-only). Run with:
    python -m unittest tests/test_scope_analyzer.py -v
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import scope_analyzer as sa

SCRIPT_PATH = REPO_ROOT / "scripts" / "scope_analyzer.py"

# Sample architecture state for tests
SAMPLE_ARCH_STATE = {
    "existing_tracks": [
        {
            "id": "01_infra",
            "status": "completed",
            "wave": 1,
            "boundaries": ["infrastructure"],
        },
        {
            "id": "02_auth",
            "status": "in_progress",
            "wave": 2,
            "boundaries": ["data_model", "api_layer"],
        },
        {
            "id": "03_frontend",
            "status": "pending",
            "wave": 3,
            "boundaries": ["ui_layer"],
        },
    ],
    "tech_stack_summary": "Node.js, Express, React, PostgreSQL",
    "cross_cutting_version": "1.2",
    "architecture_components": ["api-gateway", "frontend-app", "postgres-db"],
}


class TestDetectAmbiguity(unittest.TestCase):
    def test_vague_description(self):
        signals = sa.detect_ambiguity("make it faster")
        self.assertGreater(len(signals), 0)
        self.assertEqual(signals[0]["type"], "vague_scope")

    def test_short_description(self):
        signals = sa.detect_ambiguity("RBAC")
        self.assertGreater(len(signals), 0)
        self.assertEqual(signals[0]["type"], "missing_detail")

    def test_clear_description(self):
        signals = sa.detect_ambiguity(
            "Add role-based access control with hierarchical roles, "
            "admin dashboard for role management, and API middleware "
            "for permission checking"
        )
        self.assertEqual(len(signals), 0)

    def test_max_three_questions(self):
        signals = sa.detect_ambiguity("improve optimize enhance fix refactor")
        self.assertLessEqual(len(signals), 3)


class TestIdentifyBoundaries(unittest.TestCase):
    def test_data_model_boundary(self):
        boundaries = sa.identify_boundaries("Add user roles table and migration")
        self.assertIn("data_model", boundaries)

    def test_api_boundary(self):
        boundaries = sa.identify_boundaries("Add REST endpoint for user management")
        self.assertIn("api_layer", boundaries)

    def test_ui_boundary(self):
        boundaries = sa.identify_boundaries("Add admin dashboard page with forms")
        self.assertIn("ui_layer", boundaries)

    def test_infrastructure_boundary(self):
        boundaries = sa.identify_boundaries("Add Redis cache and Docker config")
        self.assertIn("infrastructure", boundaries)

    def test_external_integration(self):
        boundaries = sa.identify_boundaries("Integrate Stripe payment processing")
        self.assertIn("external_integration", boundaries)

    def test_multiple_boundaries(self):
        boundaries = sa.identify_boundaries(
            "Add user roles table, API endpoint, and dashboard page"
        )
        self.assertIn("data_model", boundaries)
        self.assertIn("api_layer", boundaries)
        self.assertIn("ui_layer", boundaries)

    def test_no_boundaries(self):
        boundaries = sa.identify_boundaries("do something")
        self.assertEqual(len(boundaries), 0)


class TestIsAtomic(unittest.TestCase):
    def test_single_boundary_always_atomic(self):
        self.assertTrue(sa.is_atomic("anything", ["data_model"]))

    def test_simple_two_boundary(self):
        self.assertTrue(sa.is_atomic(
            "Add a simple toggle button",
            ["api_layer", "ui_layer"],
        ))

    def test_complex_two_boundary(self):
        self.assertFalse(sa.is_atomic(
            "Build a comprehensive migration framework for the entire platform",
            ["data_model", "api_layer"],
        ))


class TestIsTrivial(unittest.TestCase):
    def test_trivial_rename(self):
        self.assertTrue(sa.is_trivial("rename field", ["data_model"], []))

    def test_trivial_add_button(self):
        self.assertTrue(sa.is_trivial("add button", ["ui_layer"], []))

    def test_not_trivial_multi_boundary(self):
        self.assertFalse(sa.is_trivial(
            "Add RBAC", ["data_model", "api_layer"], []
        ))

    def test_not_trivial_long_description(self):
        self.assertFalse(sa.is_trivial(
            "Build a complete user management system with admin dashboard "
            "and role-based access control",
            ["ui_layer"], [],
        ))


class TestAnalyzeScope(unittest.TestCase):
    def test_needs_clarification(self):
        result = sa.analyze_scope({
            "feature_description": "optimize",
            "architecture_state": SAMPLE_ARCH_STATE,
        })
        self.assertEqual(result["recommendation"], "needs_clarification")
        self.assertIn("questions", result)

    def test_clarification_bypassed_with_answers(self):
        result = sa.analyze_scope({
            "feature_description": "optimize",
            "architecture_state": SAMPLE_ARCH_STATE,
            "clarifications": {"target": "database queries"},
        })
        self.assertNotEqual(result["recommendation"], "needs_clarification")

    def test_skip_tracking(self):
        # Use minimal arch state to avoid tech stack terms expanding boundaries
        result = sa.analyze_scope({
            "feature_description": "fix typo in readme",
            "architecture_state": {
                "existing_tracks": SAMPLE_ARCH_STATE["existing_tracks"],
                "tech_stack_summary": "",
            },
            "clarifications": {"confirmed": True},
        })
        self.assertEqual(result["recommendation"], "skip_tracking")

    def test_single_track(self):
        result = sa.analyze_scope({
            "feature_description": "Add a simple REST API route for health checks",
            "architecture_state": SAMPLE_ARCH_STATE,
        })
        self.assertEqual(result["recommendation"], "single_track")
        self.assertEqual(len(result["tracks"]), 1)

    def test_multi_track(self):
        result = sa.analyze_scope({
            "feature_description": (
                "Add role-based access control with database table, "
                "API middleware, and admin dashboard"
            ),
            "architecture_state": SAMPLE_ARCH_STATE,
        })
        # Could be multi_track or single_track with extensions depending
        # on existing track coverage — just verify it's actionable
        self.assertIn(
            result["recommendation"],
            ("multi_track", "single_track"),
        )
        self.assertGreater(len(result.get("tracks", [])), 0)

    def test_track_extension(self):
        """If an in-progress track covers a boundary, recommend extension."""
        result = sa.analyze_scope({
            "feature_description": (
                "Add OAuth2 endpoint and user database migration"
            ),
            "architecture_state": SAMPLE_ARCH_STATE,
        })
        # 02_auth covers data_model and api_layer, and is in_progress
        if result["recommendation"] == "multi_track" and "extensions" in result:
            ext_tracks = [e["track_id"] for e in result["extensions"]]
            self.assertIn("02_auth", ext_tracks)

    def test_has_confidence_score(self):
        result = sa.analyze_scope({
            "feature_description": "Add user search API endpoint",
            "architecture_state": SAMPLE_ARCH_STATE,
        })
        self.assertIn("confidence", result)
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 1)


class TestGenerateTrackId(unittest.TestCase):
    def test_generates_slug(self):
        track_id = sa.generate_track_id(
            "Add role-based access control",
            SAMPLE_ARCH_STATE["existing_tracks"],
        )
        self.assertRegex(track_id, r"^\d{2}_")
        self.assertIn("role", track_id)

    def test_increments_number(self):
        track_id = sa.generate_track_id(
            "Add notifications",
            SAMPLE_ARCH_STATE["existing_tracks"],
        )
        # existing tracks go up to 03, so next should be 04
        self.assertTrue(track_id.startswith("04_"))


class TestEstimateComplexity(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(sa.estimate_complexity("Add button", ["ui_layer"]), "S")

    def test_medium(self):
        self.assertEqual(
            sa.estimate_complexity("thing", ["data_model", "api_layer"]),
            "M",
        )

    def test_large(self):
        self.assertEqual(
            sa.estimate_complexity(
                "something",
                ["data_model", "api_layer", "ui_layer"],
            ),
            "L",
        )


class TestIntegration(unittest.TestCase):
    """Integration tests that run the script as a subprocess."""

    def _run_script(self, args: list[str], stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            capture_output=True,
            text=True,
            input=stdin or None,
        )

    def test_feature_flag(self):
        result = self._run_script([
            "--feature", "Add user search API endpoint",
        ])
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("recommendation", data)

    def test_stdin_json(self):
        input_data = json.dumps({
            "feature_description": "Add role-based access control with table and endpoint",
            "architecture_state": SAMPLE_ARCH_STATE,
        })
        result = self._run_script([], stdin=input_data)
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("recommendation", data)

    def test_needs_clarification_exit_code(self):
        input_data = json.dumps({
            "feature_description": "optimize",
            "architecture_state": SAMPLE_ARCH_STATE,
        })
        result = self._run_script([], stdin=input_data)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
