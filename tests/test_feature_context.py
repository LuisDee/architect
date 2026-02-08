#!/usr/bin/env python3
"""Tests for scripts/feature_context.py.

Uses unittest (stdlib-only). Run with:
    python -m unittest tests/test_feature_context.py -v
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import feature_context as fc

SCRIPT_PATH = REPO_ROOT / "scripts" / "feature_context.py"

SAMPLE_PROJECT = REPO_ROOT / "examples" / "sample-project"
SAMPLE_CONDUCTOR_DIR = SAMPLE_PROJECT / "conductor"
SAMPLE_ARCHITECT_DIR = SAMPLE_PROJECT / "architect"

SAMPLE_ARCH_TEXT = """\
# System Architecture

## System Overview
A task management platform.

## Component Map
```
[Frontend] -> [API Gateway] -> [Database]
```

### Auth Service
Handles authentication with JWT tokens.
- Language: Python
- Framework: FastAPI

### API Gateway
Routes and validates all API requests.
- Language: Python
- Framework: FastAPI
"""

SAMPLE_CC_TEXT = """\
## CC v1.0

### Structured Logging
- Use structlog for all Python services
- JSON output format
- Applies to: ALL
- Source: Architecture research

### Input Validation
- Validate all API inputs with Pydantic
- Applies to: ALL services with HTTP endpoints
- Source: Cross-cutting catalog
"""

SAMPLE_DEP_TEXT = """\
| Track | Depends On |
|-------|-----------|
| 01_infra | - |
| 02_auth | 01_infra |
| 03_api | 01_infra, 02_auth |
"""


class TestExtractKeywords(unittest.TestCase):
    def test_filters_stop_words(self):
        keywords = fc.extract_keywords("Add a new role-based access control system")
        self.assertNotIn("add", keywords)
        self.assertNotIn("new", keywords)
        self.assertIn("role", keywords)
        self.assertIn("based", keywords)
        self.assertIn("access", keywords)
        self.assertIn("control", keywords)

    def test_empty_description(self):
        self.assertEqual(fc.extract_keywords(""), [])

    def test_filters_short_words(self):
        keywords = fc.extract_keywords("an if to be")
        self.assertEqual(keywords, [])


class TestExtractArchitectureSummary(unittest.TestCase):
    def test_extracts_components(self):
        summary = fc.extract_architecture_summary(SAMPLE_ARCH_TEXT, 6000)
        self.assertIsInstance(summary["components"], list)

    def test_returns_excerpt(self):
        summary = fc.extract_architecture_summary(SAMPLE_ARCH_TEXT, 6000)
        self.assertIn("System Architecture", summary["excerpt"])

    def test_none_input(self):
        summary = fc.extract_architecture_summary(None, 6000)
        self.assertEqual(summary["components"], [])
        self.assertEqual(summary["confirmed_technologies"], {})
        self.assertEqual(summary["excerpt"], "")

    def test_truncation(self):
        summary = fc.extract_architecture_summary(SAMPLE_ARCH_TEXT, 50)
        self.assertLessEqual(len(summary["excerpt"]), 50)


class TestExtractActiveConstraints(unittest.TestCase):
    def test_extracts_constraints(self):
        constraints = fc.extract_active_constraints(SAMPLE_CC_TEXT, 2000)
        self.assertGreater(len(constraints), 0)

    def test_includes_version(self):
        constraints = fc.extract_active_constraints(SAMPLE_CC_TEXT, 2000)
        self.assertTrue(any("CC v1.0" in c for c in constraints))

    def test_none_input(self):
        self.assertEqual(fc.extract_active_constraints(None, 2000), [])


class TestExtractDependencyGraph(unittest.TestCase):
    def test_extracts_nodes(self):
        graph = fc.extract_dependency_graph(SAMPLE_DEP_TEXT, 2000)
        self.assertIn("01_infra", graph["nodes"])
        self.assertIn("02_auth", graph["nodes"])
        self.assertIn("03_api", graph["nodes"])

    def test_extracts_edges(self):
        graph = fc.extract_dependency_graph(SAMPLE_DEP_TEXT, 2000)
        self.assertIn(["01_infra", "02_auth"], graph["edges"])

    def test_none_input(self):
        graph = fc.extract_dependency_graph(None, 2000)
        self.assertEqual(graph["nodes"], [])
        self.assertEqual(graph["edges"], [])


class TestTruncate(unittest.TestCase):
    def test_no_truncation_needed(self):
        self.assertEqual(fc.truncate("short", 100), "short")

    def test_truncation(self):
        result = fc.truncate("a" * 200, 50)
        self.assertLessEqual(len(result), 50)
        self.assertTrue(result.endswith("[truncated]"))


class TestIntegration(unittest.TestCase):
    """Integration tests that run the script as a subprocess."""

    def _run_script(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH)] + args,
            capture_output=True,
            text=True,
        )

    def test_with_sample_project(self):
        """Run against the real sample project."""
        result = self._run_script([
            "--feature-description", "Add role-based access control",
            "--conductor-dir", str(SAMPLE_CONDUCTOR_DIR),
            "--architect-dir", str(SAMPLE_ARCHITECT_DIR),
        ])
        self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

        bundle = json.loads(result.stdout)
        self.assertEqual(
            bundle["feature_description"],
            "Add role-based access control",
        )
        self.assertIn("architecture_summary", bundle)
        self.assertIn("existing_tracks", bundle)
        self.assertIn("active_constraints", bundle)
        self.assertIn("dependency_graph", bundle)
        self.assertIn("codebase_hints", bundle)
        self.assertIn("estimated_tokens", bundle)

    def test_missing_dirs(self):
        """Gracefully handles missing directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_script([
                "--feature-description", "Add something",
                "--conductor-dir", f"{tmpdir}/nonexistent",
                "--architect-dir", f"{tmpdir}/nonexistent",
            ])
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")

            bundle = json.loads(result.stdout)
            self.assertEqual(bundle["existing_tracks"], [])
            self.assertEqual(bundle["active_constraints"], [])

    def test_token_budget_present(self):
        """Output includes token budget breakdown."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self._run_script([
                "--feature-description", "Add something",
                "--conductor-dir", tmpdir,
                "--architect-dir", tmpdir,
            ])
            self.assertEqual(result.returncode, 0)
            bundle = json.loads(result.stdout)
            self.assertIn("token_budget", bundle)


if __name__ == "__main__":
    unittest.main()
