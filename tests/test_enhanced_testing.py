#!/usr/bin/env python3
"""Tests for T-TEST: Enhanced Testing Integration components.

Tests the test strategy section in briefs, test_prerequisites and
quality_threshold in metadata, prerequisite validation in
validate_wave_completion.py, and override audit trail.

Uses unittest (stdlib-only). Run with:
    python -m unittest tests/test_enhanced_testing.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_wave_completion as vwc

# --- Test Brief Template ---


class TestBriefTemplateTestStrategy(unittest.TestCase):
    """Verify track-brief.md template includes Test Strategy section."""

    def setUp(self):
        template_path = REPO_ROOT / "skills" / "architect" / "templates" / "track-brief.md"
        self.template = template_path.read_text()

    def test_has_test_strategy_section(self):
        self.assertIn("## Test Strategy", self.template)

    def test_has_test_strategy_placeholder(self):
        self.assertIn("{test_strategy}", self.template)

    def test_test_strategy_between_architectural_notes_and_complexity(self):
        arch_notes_pos = self.template.index("## Architectural Notes")
        test_strategy_pos = self.template.index("## Test Strategy")
        complexity_pos = self.template.index("## Complexity")
        self.assertGreater(test_strategy_pos, arch_notes_pos,
                           "Test Strategy should come after Architectural Notes")
        self.assertLess(test_strategy_pos, complexity_pos,
                        "Test Strategy should come before Complexity")

    def test_test_strategy_comment_mentions_frameworks(self):
        # The comment guidance should mention test framework inference
        self.assertIn("Test framework", self.template)

    def test_test_strategy_comment_mentions_prerequisites(self):
        self.assertIn("Prerequisites", self.template)

    def test_test_strategy_comment_mentions_quality_threshold(self):
        self.assertIn("Quality threshold", self.template)


# --- Test Metadata Template ---


class TestMetadataTemplate(unittest.TestCase):
    """Verify track-metadata.json template includes new T-TEST fields."""

    def setUp(self):
        template_path = REPO_ROOT / "skills" / "architect" / "templates" / "track-metadata.json"
        self.meta = json.loads(template_path.read_text())

    def test_has_test_prerequisites(self):
        self.assertIn("test_prerequisites", self.meta)
        self.assertIsInstance(self.meta["test_prerequisites"], list)

    def test_has_quality_threshold(self):
        self.assertIn("quality_threshold", self.meta)
        self.assertIsInstance(self.meta["quality_threshold"], dict)

    def test_quality_threshold_has_line_coverage(self):
        qt = self.meta["quality_threshold"]
        self.assertIn("line_coverage", qt)
        self.assertEqual(qt["line_coverage"], 80)

    def test_quality_threshold_has_pass_rate(self):
        qt = self.meta["quality_threshold"]
        self.assertIn("pass_rate", qt)
        self.assertEqual(qt["pass_rate"], 100)

    def test_has_override_log(self):
        self.assertIn("override_log", self.meta)
        self.assertIsInstance(self.meta["override_log"], list)
        self.assertEqual(len(self.meta["override_log"]), 0)

    def test_no_test_command_in_template(self):
        """Template should NOT include test_command — Conductor adds that."""
        self.assertNotIn("test_command", self.meta)

    def test_no_test_timeout_in_template(self):
        """Template should NOT include test_timeout_seconds — Conductor adds that."""
        self.assertNotIn("test_timeout_seconds", self.meta)


# --- Test Prerequisites Validation ---


class TestCheckTestPrerequisites(unittest.TestCase):
    """Test check_test_prerequisites() in validate_wave_completion.py."""

    def test_no_prerequisites_passes(self):
        meta = {"test_prerequisites": []}
        ok, msg = vwc.check_test_prerequisites(meta, "/nonexistent")
        self.assertTrue(ok)
        self.assertIn("No test prerequisites", msg)

    def test_missing_prerequisites_key_passes(self):
        meta = {}
        ok, _msg = vwc.check_test_prerequisites(meta, "/nonexistent")
        self.assertTrue(ok)

    def test_prerequisite_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prereq_dir = Path(tmpdir) / "01_infra"
            prereq_dir.mkdir()
            (prereq_dir / "metadata.json").write_text(
                json.dumps({"track_id": "01_infra", "status": "completed"})
            )
            meta = {"test_prerequisites": ["01_infra"]}
            ok, msg = vwc.check_test_prerequisites(meta, tmpdir)
            self.assertTrue(ok)
            self.assertIn("1 prerequisites completed", msg)

    def test_prerequisite_not_completed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prereq_dir = Path(tmpdir) / "01_infra"
            prereq_dir.mkdir()
            (prereq_dir / "metadata.json").write_text(
                json.dumps({"track_id": "01_infra", "status": "in_progress"})
            )
            meta = {"test_prerequisites": ["01_infra"]}
            ok, msg = vwc.check_test_prerequisites(meta, tmpdir)
            self.assertFalse(ok)
            self.assertIn("Prerequisites not met", msg)
            self.assertIn("01_infra (in_progress)", msg)

    def test_prerequisite_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta = {"test_prerequisites": ["99_nonexistent"]}
            ok, msg = vwc.check_test_prerequisites(meta, tmpdir)
            self.assertFalse(ok)
            self.assertIn("99_nonexistent (not found)", msg)

    def test_multiple_prerequisites_mixed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # One completed, one not
            d1 = Path(tmpdir) / "01_infra"
            d1.mkdir()
            (d1 / "metadata.json").write_text(
                json.dumps({"track_id": "01_infra", "status": "completed"})
            )
            d2 = Path(tmpdir) / "02_db"
            d2.mkdir()
            (d2 / "metadata.json").write_text(
                json.dumps({"track_id": "02_db", "status": "new"})
            )
            meta = {"test_prerequisites": ["01_infra", "02_db"]}
            ok, msg = vwc.check_test_prerequisites(meta, tmpdir)
            self.assertFalse(ok)
            self.assertIn("02_db (new)", msg)
            self.assertNotIn("01_infra", msg)  # completed one shouldn't appear in failure


# --- Quality Threshold ---


class TestCheckQualityThreshold(unittest.TestCase):
    """Test check_quality_threshold() — always advisory, never fails."""

    def test_no_threshold_defined(self):
        meta = {}
        ok, msg = vwc.check_quality_threshold(meta)
        self.assertTrue(ok)
        self.assertIn("No quality threshold", msg)

    def test_threshold_reports_values(self):
        meta = {"quality_threshold": {"line_coverage": 80, "pass_rate": 100}}
        ok, msg = vwc.check_quality_threshold(meta)
        self.assertTrue(ok)  # Always true — advisory only
        self.assertIn("80%", msg)
        self.assertIn("100%", msg)
        self.assertIn("advisory", msg)

    def test_custom_threshold_values(self):
        meta = {"quality_threshold": {"line_coverage": 60, "pass_rate": 95}}
        ok, msg = vwc.check_quality_threshold(meta)
        self.assertTrue(ok)
        self.assertIn("60%", msg)
        self.assertIn("95%", msg)

    def test_threshold_never_fails(self):
        """Quality threshold check should NEVER return False — it's advisory."""
        meta = {"quality_threshold": {"line_coverage": 0, "pass_rate": 0}}
        ok, msg = vwc.check_quality_threshold(meta)
        self.assertTrue(ok)


# --- Override Audit Trail ---


class TestLogOverride(unittest.TestCase):
    """Test log_override() writes override entries to metadata."""

    def test_appends_override_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta = {"track_id": "03_auth", "override_log": []}
            meta_path.write_text(json.dumps(meta))

            vwc.log_override(meta, meta_path, "tests", "Flaky test — known issue #42")

            saved = json.loads(meta_path.read_text())
            self.assertEqual(len(saved["override_log"]), 1)
            entry = saved["override_log"][0]
            self.assertEqual(entry["check"], "tests")
            self.assertEqual(entry["reason"], "Flaky test — known issue #42")
            self.assertIn("timestamp", entry)

    def test_preserves_existing_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            existing = {"check": "phases", "reason": "manual override", "timestamp": "2026-01-01T00:00:00Z"}
            meta = {"track_id": "03_auth", "override_log": [existing]}
            meta_path.write_text(json.dumps(meta))

            vwc.log_override(meta, meta_path, "tests", "Second override")

            saved = json.loads(meta_path.read_text())
            self.assertEqual(len(saved["override_log"]), 2)
            self.assertEqual(saved["override_log"][0]["check"], "phases")
            self.assertEqual(saved["override_log"][1]["check"], "tests")

    def test_creates_override_log_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta = {"track_id": "03_auth"}  # No override_log key
            meta_path.write_text(json.dumps(meta))

            vwc.log_override(meta, meta_path, "discoveries", "Deferred to next sprint")

            saved = json.loads(meta_path.read_text())
            self.assertIn("override_log", saved)
            self.assertEqual(len(saved["override_log"]), 1)

    def test_override_has_iso_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta = {"track_id": "03_auth", "override_log": []}
            meta_path.write_text(json.dumps(meta))

            vwc.log_override(meta, meta_path, "tests", "reason")

            saved = json.loads(meta_path.read_text())
            ts = saved["override_log"][0]["timestamp"]
            # ISO 8601 format check
            self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# --- Brief Generator Agent ---


class TestBriefGeneratorAgent(unittest.TestCase):
    """Verify brief-generator.md agent includes T-TEST instructions."""

    def setUp(self):
        agent_path = REPO_ROOT / "agents" / "brief-generator.md"
        self.content = agent_path.read_text()

    def test_mentions_test_strategy(self):
        self.assertIn("Test Strategy", self.content)

    def test_mentions_test_framework_derivation(self):
        self.assertIn("Test framework", self.content)

    def test_mentions_test_prerequisites_in_metadata(self):
        self.assertIn("test_prerequisites", self.content)

    def test_mentions_quality_threshold_in_metadata(self):
        self.assertIn("quality_threshold", self.content)

    def test_mentions_override_log(self):
        self.assertIn("override_log", self.content)

    def test_does_not_set_test_command(self):
        """Brief generator should NOT set test_command — Conductor does."""
        self.assertIn("Do NOT set `test_command`", self.content)


# --- Wave Validation Integration ---


class TestWaveValidationIntegration(unittest.TestCase):
    """Integration tests for the full wave validation with T-TEST fields."""

    def _create_track(self, tmpdir, track_id, wave, status="completed",
                      prereqs=None, quality=None, plan_complete=True):
        """Helper to create a track directory with metadata and plan."""
        track_dir = Path(tmpdir) / track_id
        track_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "track_id": track_id,
            "wave": wave,
            "status": status,
            "test_prerequisites": prereqs or [],
            "quality_threshold": quality or {"line_coverage": 80, "pass_rate": 100},
            "override_log": [],
            "patches": [],
        }
        (track_dir / "metadata.json").write_text(json.dumps(meta, indent=2))

        if plan_complete:
            (track_dir / "plan.md").write_text("- [x] Task 1\n- [x] Task 2\n")
        else:
            (track_dir / "plan.md").write_text("- [x] Task 1\n- [ ] Task 2\n")

        return track_dir

    def test_cli_with_prerequisites_pass(self):
        """Full CLI run where prerequisites are met."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create prerequisite track (completed)
            self._create_track(tmpdir, "01_infra", wave=1, status="completed")
            # Create wave 2 track with prerequisite on 01_infra
            self._create_track(tmpdir, "03_api", wave=2, prereqs=["01_infra"])

            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "validate_wave_completion.py"),
                 "--wave", "2", "--tracks-dir", tmpdir, "--skip-tests"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0)
            output = json.loads(result.stdout)
            self.assertTrue(output["passed"])

    def test_cli_with_prerequisites_fail(self):
        """Full CLI run where prerequisites are NOT met."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create prerequisite track (still in progress)
            self._create_track(tmpdir, "01_infra", wave=1, status="in_progress")
            # Create wave 2 track with prerequisite on 01_infra
            self._create_track(tmpdir, "03_api", wave=2, prereqs=["01_infra"])

            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "validate_wave_completion.py"),
                 "--wave", "2", "--tracks-dir", tmpdir, "--skip-tests"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            output = json.loads(result.stdout)
            self.assertFalse(output["passed"])
            # Find the prerequisite failure
            prereq_results = [r for r in output["results"] if r.get("check") == "prerequisites"]
            self.assertTrue(len(prereq_results) > 0)
            self.assertEqual(prereq_results[0]["status"], "FAIL")

    def test_cli_quality_threshold_advisory(self):
        """Quality threshold appears as INFO, never FAIL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_track(tmpdir, "03_api", wave=2,
                               quality={"line_coverage": 80, "pass_rate": 100})

            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "validate_wave_completion.py"),
                 "--wave", "2", "--tracks-dir", tmpdir, "--skip-tests"],
                capture_output=True, text=True,
            )
            output = json.loads(result.stdout)
            # Quality check should be INFO, not FAIL
            quality_results = [r for r in output["results"] if r.get("check") == "quality"]
            for r in quality_results:
                self.assertNotEqual(r["status"], "FAIL")


# --- SKILL.md Documentation ---


class TestSkillDocumentation(unittest.TestCase):
    """Verify SKILL.md documents T-TEST features."""

    def setUp(self):
        skill_path = REPO_ROOT / "skills" / "architect" / "SKILL.md"
        self.content = skill_path.read_text()

    def test_has_enhanced_testing_section(self):
        self.assertIn("Enhanced Testing Integration", self.content)

    def test_mentions_test_prerequisites(self):
        self.assertIn("test_prerequisites", self.content)

    def test_mentions_quality_thresholds(self):
        self.assertIn("quality_threshold", self.content)

    def test_mentions_override_audit(self):
        self.assertIn("override", self.content.lower())

    def test_mentions_advisory_principle(self):
        self.assertIn("advisory", self.content.lower())


if __name__ == "__main__":
    unittest.main()
