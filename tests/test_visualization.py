#!/usr/bin/env python3
"""Tests for T-VIZ: Visualization components.

Tests generate_diagrams.py and terminal_progress.py.

Uses unittest (stdlib-only). Run with:
    python -m unittest tests/test_visualization.py -v
"""

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_diagrams as gd
import terminal_progress as tp

SAMPLE_PROJECT = REPO_ROOT / "examples" / "sample-project"


# --- Sample data ---

SAMPLE_DEP_GRAPH = textwrap.dedent("""\
    # Dependency Graph

    | Track | Depends On |
    |-------|-----------|
    | 01_infra | - |
    | 02_db | 01_infra |
    | 03_auth | 01_infra, 02_db |
    | 04_api | 02_db, 03_auth |
""")

SAMPLE_EXEC_SEQ = textwrap.dedent("""\
    # Execution Sequence

    ## Wave 1

    | Track | Complexity |
    |-------|-----------|
    | 01_infra | S |

    ## Wave 2

    | Track | Complexity |
    |-------|-----------|
    | 02_db | M |
    | 03_auth | M |

    ## Wave 3

    | Track | Complexity |
    |-------|-----------|
    | 04_api | L |
""")

SAMPLE_ARCHITECTURE = textwrap.dedent("""\
    # System Architecture

    ## Component Map

    | Component | Technology | Responsibility | Interfaces |
    |-----------|-----------|----------------|------------|
    | API Gateway | FastAPI | Routes requests | /v1/* |
    | Auth Service | FastAPI | Authentication | /auth/* |
    | Database | PostgreSQL | Persistence | SQLAlchemy |
""")


class TestParseDependencyGraph(unittest.TestCase):
    def test_parses_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "dependency-graph.md").write_text(SAMPLE_DEP_GRAPH)
            graph = gd.parse_dependency_graph(tmpdir)
            self.assertIn("01_infra", graph)
            self.assertIn("02_db", graph)
            self.assertEqual(graph["01_infra"], [])
            self.assertEqual(graph["02_db"], ["01_infra"])
            self.assertIn("01_infra", graph["03_auth"])
            self.assertIn("02_db", graph["03_auth"])

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(gd.parse_dependency_graph(tmpdir), {})


class TestParseExecutionSequence(unittest.TestCase):
    def test_parses_waves(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "execution-sequence.md").write_text(SAMPLE_EXEC_SEQ)
            waves = gd.parse_execution_sequence(tmpdir)
            self.assertEqual(len(waves), 3)
            self.assertEqual(waves[0]["number"], 1)
            self.assertIn("01_infra", waves[0]["tracks"])

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(gd.parse_execution_sequence(tmpdir), [])


class TestParseArchitectureComponents(unittest.TestCase):
    def test_parses_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "architecture.md").write_text(SAMPLE_ARCHITECTURE)
            components = gd.parse_architecture_components(tmpdir)
            names = [c["name"] for c in components]
            self.assertIn("API Gateway", names)
            self.assertIn("Auth Service", names)


class TestGenerateDependencyGraph(unittest.TestCase):
    def test_generates_mermaid(self):
        graph = {"01_infra": [], "02_db": ["01_infra"]}
        metadata = {
            "01_infra": {"status": "completed", "complexity": "S"},
            "02_db": {"status": "in_progress", "complexity": "M"},
        }
        mmd = gd.generate_dependency_graph(graph, metadata)
        self.assertIn("graph LR", mmd)
        self.assertIn("complete", mmd)
        self.assertIn("in_progress", mmd)
        self.assertIn("01_infra", mmd)

    def test_status_coloring(self):
        graph = {"a": []}
        metadata = {"a": {"status": "completed", "complexity": "S"}}
        mmd = gd.generate_dependency_graph(graph, metadata)
        self.assertIn(":::complete", mmd)


class TestGenerateComponentMap(unittest.TestCase):
    def test_generates_mermaid(self):
        components = [
            {"name": "API Gateway", "technology": "FastAPI"},
            {"name": "Database", "technology": "PostgreSQL"},
        ]
        mmd = gd.generate_component_map(components)
        self.assertIn("graph TD", mmd)
        self.assertIn("API Gateway", mmd)

    def test_empty_components(self):
        mmd = gd.generate_component_map([])
        self.assertIn("No components found", mmd)


class TestGenerateWaveTimeline(unittest.TestCase):
    def test_generates_gantt(self):
        waves = [
            {"number": 1, "tracks": ["01_infra"]},
            {"number": 2, "tracks": ["02_db", "03_auth"]},
        ]
        metadata = {
            "01_infra": {"status": "completed"},
            "02_db": {"status": "in_progress"},
            "03_auth": {"status": "new"},
        }
        mmd = gd.generate_wave_timeline(waves, metadata)
        self.assertIn("gantt", mmd)
        self.assertIn("Wave 1", mmd)
        self.assertIn("done", mmd)
        self.assertIn("active", mmd)


class TestGenerateDiagramsIntegration(unittest.TestCase):
    def test_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arch_dir = Path(tmpdir) / "architect"
            arch_dir.mkdir()
            (arch_dir / "dependency-graph.md").write_text(SAMPLE_DEP_GRAPH)
            (arch_dir / "execution-sequence.md").write_text(SAMPLE_EXEC_SEQ)
            (arch_dir / "architecture.md").write_text(SAMPLE_ARCHITECTURE)

            tracks_dir = Path(tmpdir) / "conductor" / "tracks"
            tracks_dir.mkdir(parents=True)

            output_dir = Path(tmpdir) / "diagrams"

            result = gd.generate_diagrams(
                str(tracks_dir), str(arch_dir), str(output_dir), dry_run=True
            )
            self.assertGreater(len(result["diagrams_generated"]), 0)
            self.assertFalse(output_dir.exists())

    def test_writes_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arch_dir = Path(tmpdir) / "architect"
            arch_dir.mkdir()
            (arch_dir / "dependency-graph.md").write_text(SAMPLE_DEP_GRAPH)
            (arch_dir / "execution-sequence.md").write_text(SAMPLE_EXEC_SEQ)
            (arch_dir / "architecture.md").write_text(SAMPLE_ARCHITECTURE)

            tracks_dir = Path(tmpdir) / "conductor" / "tracks"
            tracks_dir.mkdir(parents=True)

            output_dir = Path(tmpdir) / "diagrams"

            gd.generate_diagrams(
                str(tracks_dir), str(arch_dir), str(output_dir)
            )
            self.assertTrue(output_dir.exists())
            self.assertTrue((output_dir / "dependency-graph.mmd").exists())
            self.assertTrue((output_dir / "wave-timeline.mmd").exists())

    def test_sample_project(self):
        """Run against the real sample project."""
        if not SAMPLE_PROJECT.exists():
            self.skipTest("Sample project not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            result = gd.generate_diagrams(
                str(SAMPLE_PROJECT / "conductor" / "tracks"),
                str(SAMPLE_PROJECT / "architect"),
                str(Path(tmpdir) / "diagrams"),
            )
            self.assertGreater(len(result["diagrams_generated"]), 0)


class TestTerminalProgress(unittest.TestCase):
    def test_render_bar(self):
        bar = tp.render_bar(0.5)
        self.assertEqual(len(bar), tp.BAR_WIDTH)
        self.assertIn(tp.COMPLETE_CHAR, bar)
        self.assertIn(tp.REMAINING_CHAR, bar)

    def test_render_bar_full(self):
        bar = tp.render_bar(1.0)
        self.assertEqual(bar, tp.COMPLETE_CHAR * tp.BAR_WIDTH)

    def test_render_bar_empty(self):
        bar = tp.render_bar(0.0)
        self.assertEqual(bar, tp.REMAINING_CHAR * tp.BAR_WIDTH)

    def test_render_wave_line(self):
        wave = {
            "number": 1,
            "tracks": [
                {"complexity": "S", "status": "completed"},
                {"complexity": "M", "status": "in_progress"},
            ],
        }
        line = tp.render_wave_line(wave)
        self.assertIn("Wave 1", line)
        self.assertIn("(1/2)", line)

    def test_render_overall(self):
        waves = [{
            "number": 1,
            "tracks": [
                {"complexity": "S", "status": "completed"},
                {"complexity": "M", "status": "completed"},
            ],
        }]
        line = tp.render_overall_line(waves)
        self.assertIn("100%", line)
        self.assertIn("Overall", line)

    def test_render_progress_full(self):
        data = {
            "waves": [
                {
                    "number": 1,
                    "tracks": [
                        {"track_id": "01_infra", "status": "completed", "complexity": "S"},
                    ],
                },
                {
                    "number": 2,
                    "tracks": [
                        {"track_id": "02_db", "status": "in_progress", "complexity": "M"},
                        {"track_id": "03_auth", "status": "new", "complexity": "M", "dependencies": ["02_db"]},
                    ],
                },
            ],
        }
        output = tp.render_progress(data)
        self.assertIn("PROJECT PROGRESS", output)
        self.assertIn("Wave 1", output)
        self.assertIn("Wave 2", output)
        self.assertIn("Overall", output)

    def test_blocked_track_detection(self):
        waves = [{
            "number": 1,
            "tracks": [
                {"track_id": "01", "status": "paused", "complexity": "S"},
            ],
        }]
        blocked = tp.find_blocked_tracks(waves)
        self.assertGreater(len(blocked), 0)
        self.assertEqual(blocked[0]["track_id"], "01")

    def test_transform_progress_data(self):
        raw = {
            "waves": [{
                "number": 1,
                "tracks": [{"track_id": "01", "status": "completed", "complexity": "S"}],
            }],
        }
        result = tp.transform_progress_data(raw)
        self.assertEqual(len(result["waves"]), 1)
        self.assertEqual(result["waves"][0]["tracks"][0]["track_id"], "01")


class TestCLIIntegration(unittest.TestCase):
    def test_generate_diagrams_cli(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            arch_dir = Path(tmpdir) / "architect"
            arch_dir.mkdir()
            (arch_dir / "dependency-graph.md").write_text(SAMPLE_DEP_GRAPH)

            tracks_dir = Path(tmpdir) / "conductor" / "tracks"
            tracks_dir.mkdir(parents=True)

            result = subprocess.run(
                [sys.executable, str(REPO_ROOT / "scripts" / "generate_diagrams.py"),
                 "--tracks-dir", str(tracks_dir),
                 "--architect-dir", str(arch_dir),
                 "--output-dir", str(Path(tmpdir) / "diagrams"),
                 "--dry-run"],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, f"stderr: {result.stderr}")
            data = json.loads(result.stdout)
            self.assertIn("diagrams_generated", data)


if __name__ == "__main__":
    unittest.main()
