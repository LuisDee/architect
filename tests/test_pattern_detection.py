#!/usr/bin/env python3
"""Tests for T-PATTERN: Pattern Detection components.

Tests detect_patterns.py fan-in analysis, repetition detection,
and cross-cutting classification.

Uses unittest (stdlib-only). Run with:
    python -m unittest tests/test_pattern_detection.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import detect_patterns as dp

# --- Sample data ---

SAMPLE_ANALYSIS = {
    "codebase_analysis": {
        "modules": [
            {"path": "src/auth/", "imports": ["express", "logger", "validator"], "exports": ["authRouter"]},
            {"path": "src/api/", "imports": ["express", "logger", "validator", "authMiddleware"], "exports": ["apiRouter"]},
            {"path": "src/admin/", "imports": ["express", "logger", "validator", "authMiddleware"], "exports": ["adminRouter"]},
        ],
        "function_calls": [
            {"name": "logger.error", "locations": ["src/auth/login.js:42", "src/api/users.js:78", "src/admin/roles.js:33"]},
            {"name": "validator.validate", "locations": ["src/auth/login.js:15", "src/api/users.js:22", "src/admin/roles.js:11"]},
        ],
        "code_structures": [
            {
                "pattern": "try/catch with error response",
                "locations": [
                    "src/api/users.js:70-85",
                    "src/api/products.js:83-98",
                    "src/admin/roles.js:28-43",
                ],
                "structure": "try { ... } catch (err) { res.status(500).json({ error: err.message }) }",
            },
        ],
    },
    "existing_cross_cutting": {
        "version": "1.2",
        "constraints": [
            "CC v1.0: All API endpoints require authentication",
            "CC v1.1: Use PostgreSQL for persistence",
        ],
    },
}


class TestFanInAnalysis(unittest.TestCase):
    def test_detects_high_fan_in(self):
        modules = SAMPLE_ANALYSIS["codebase_analysis"]["modules"]
        patterns = dp.calculate_fan_in(modules)
        names = [p["name"] for p in patterns]
        # express, logger, validator all imported in 3/3 = 100%
        self.assertIn("express", names)
        self.assertIn("logger", names)
        self.assertIn("validator", names)

    def test_fan_in_score(self):
        modules = SAMPLE_ANALYSIS["codebase_analysis"]["modules"]
        patterns = dp.calculate_fan_in(modules)
        for p in patterns:
            if p["name"] == "logger":
                self.assertEqual(p["fan_in_score"], 1.0)

    def test_low_fan_in_excluded(self):
        modules = [
            {"path": "a/", "imports": ["unique_lib"], "exports": []},
            {"path": "b/", "imports": ["other_lib"], "exports": []},
            {"path": "c/", "imports": ["third_lib"], "exports": []},
        ]
        patterns = dp.calculate_fan_in(modules)
        self.assertEqual(len(patterns), 0)

    def test_empty_modules(self):
        self.assertEqual(dp.calculate_fan_in([]), [])


class TestRepetitionDetection(unittest.TestCase):
    def test_detects_repetition(self):
        structures = SAMPLE_ANALYSIS["codebase_analysis"]["code_structures"]
        patterns = dp.detect_repetitions(structures)
        self.assertGreater(len(patterns), 0)
        self.assertEqual(patterns[0]["type"], "repetition")
        self.assertEqual(patterns[0]["occurrences"], 3)

    def test_below_threshold_excluded(self):
        structures = [
            {"pattern": "small", "locations": ["a/f.py:1", "b/g.py:2"]},
        ]
        patterns = dp.detect_repetitions(structures, threshold=3)
        self.assertEqual(len(patterns), 0)

    def test_single_module_excluded(self):
        structures = [
            {"pattern": "same module", "locations": ["src/api/a.py:1", "src/api/b.py:2", "src/api/c.py:3"]},
        ]
        patterns = dp.detect_repetitions(structures, threshold=3)
        self.assertEqual(len(patterns), 0)


class TestFunctionHotspots(unittest.TestCase):
    def test_detects_hotspots(self):
        calls = SAMPLE_ANALYSIS["codebase_analysis"]["function_calls"]
        patterns = dp.detect_function_hotspots(calls)
        names = [p["name"] for p in patterns]
        self.assertIn("logger.error", names)
        self.assertIn("validator.validate", names)

    def test_below_threshold(self):
        calls = [{"name": "rare.func", "locations": ["a/f.py:1"]}]
        patterns = dp.detect_function_hotspots(calls, threshold=3)
        self.assertEqual(len(patterns), 0)


class TestCrossCuttingClassification(unittest.TestCase):
    def test_classifies_logger(self):
        pattern = {"name": "logger", "type": "fan_in"}
        result = dp.classify_as_cross_cutting(pattern)
        self.assertIsNotNone(result)
        self.assertTrue(result["is_cross_cutting"])
        self.assertEqual(result["category"], "logging")

    def test_classifies_validator(self):
        pattern = {"name": "validator", "type": "fan_in"}
        result = dp.classify_as_cross_cutting(pattern)
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "input_validation")

    def test_unknown_pattern(self):
        pattern = {"name": "random_util", "type": "fan_in"}
        result = dp.classify_as_cross_cutting(pattern)
        self.assertIsNone(result)

    def test_multi_service_category(self):
        pattern = {"name": "distributed_tracing", "type": "fan_in"}
        result = dp.classify_as_cross_cutting(pattern, is_multi_service=True)
        self.assertIsNotNone(result)
        self.assertEqual(result["priority"], "multi_service")

    def test_multi_service_not_triggered_without_flag(self):
        pattern = {"name": "circuit_breaking", "type": "fan_in"}
        result = dp.classify_as_cross_cutting(pattern, is_multi_service=False)
        self.assertIsNone(result)


class TestAlreadyTracked(unittest.TestCase):
    def test_tracked_constraint(self):
        self.assertTrue(dp.is_already_tracked(
            "All API endpoints require authentication",
            ["CC v1.0: All API endpoints require authentication"],
        ))

    def test_not_tracked(self):
        self.assertFalse(dp.is_already_tracked(
            "logger",
            ["CC v1.0: All API endpoints require authentication"],
        ))

    def test_empty_constraints(self):
        self.assertFalse(dp.is_already_tracked("logger", []))


class TestDetectPatterns(unittest.TestCase):
    def test_full_analysis(self):
        result = dp.detect_patterns(SAMPLE_ANALYSIS)
        self.assertGreater(result["summary"]["total_patterns"], 0)
        self.assertGreater(result["summary"]["cross_cutting_candidates"], 0)

    def test_empty_analysis(self):
        result = dp.detect_patterns({
            "codebase_analysis": {"modules": [], "function_calls": [], "code_structures": []},
            "existing_cross_cutting": {"constraints": []},
        })
        self.assertEqual(result["summary"]["total_patterns"], 0)

    def test_project_characteristics(self):
        result = dp.detect_patterns(SAMPLE_ANALYSIS)
        chars = result["project_characteristics"]
        self.assertEqual(chars["total_modules"], 3)

    def test_recommendations_present(self):
        result = dp.detect_patterns(SAMPLE_ANALYSIS)
        patterns_with_recs = [
            p for p in result["patterns_detected"]
            if "recommendation" in p
        ]
        self.assertGreater(len(patterns_with_recs), 0)


class TestIntegration(unittest.TestCase):
    def test_stdin_input(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "detect_patterns.py")],
            input=json.dumps(SAMPLE_ANALYSIS),
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
        data = json.loads(result.stdout)
        self.assertIn("patterns_detected", data)
        self.assertIn("summary", data)

    def test_file_input(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(SAMPLE_ANALYSIS, f)
            f.flush()

            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "detect_patterns.py"),
                 "--analysis-file", f.name],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            data = json.loads(result.stdout)
            self.assertIn("patterns_detected", data)


if __name__ == "__main__":
    unittest.main()
