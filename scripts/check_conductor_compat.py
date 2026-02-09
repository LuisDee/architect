#!/usr/bin/env python3
"""Check Conductor directory compatibility before running Architect.

Verifies that the conductor/ directory exists and contains expected files
(product.md, tech-stack.md, workflow.md). Performs basic format validation
to ensure Architect can read the files.

Usage:
    python scripts/check_conductor_compat.py
    python scripts/check_conductor_compat.py --conductor-dir conductor

Output (JSON to stdout):
    {
      "compatible": true,
      "files": { "product.md": "found", "tech-stack.md": "found", ... },
      "warnings": []
    }
"""

import argparse
import json
import sys
from pathlib import Path

REQUIRED_FILES = ["product.md", "tech-stack.md", "workflow.md"]
OPTIONAL_FILES = ["product-guidelines.md", "tracks.md"]


def check_file(conductor_dir: Path, filename: str) -> tuple[str, list[str]]:
    """Check if a file exists and perform basic validation.

    Returns (status, warnings).
    Status: "found", "missing", "empty"
    """
    filepath = conductor_dir / filename
    warnings = []

    if not filepath.exists():
        return "missing", [f"{filename} not found"]

    try:
        content = filepath.read_text().strip()
    except OSError as e:
        return "error", [f"Cannot read {filename}: {e}"]

    if not content:
        return "empty", [f"{filename} exists but is empty"]

    # Basic format checks
    if filename == "product.md":
        if len(content) < 50:
            warnings.append(f"product.md seems too short ({len(content)} chars) — may be incomplete")
        if "#" not in content:
            warnings.append("product.md has no Markdown headings — may not follow expected format")

    elif filename == "tech-stack.md":
        if len(content) < 30:
            warnings.append(f"tech-stack.md seems too short ({len(content)} chars) — may be incomplete")

    elif filename == "workflow.md":
        if len(content) < 30:
            warnings.append(f"workflow.md seems too short ({len(content)} chars) — may be incomplete")

    return "found", warnings


def main():
    parser = argparse.ArgumentParser(
        description="Check Conductor directory compatibility"
    )
    parser.add_argument("--conductor-dir", default="conductor",
                        help="Path to conductor directory")

    args = parser.parse_args()
    conductor_dir = Path(args.conductor_dir)

    if not conductor_dir.exists():
        print(json.dumps({
            "compatible": False,
            "files": {},
            "warnings": [],
            "error": f"Conductor directory not found: {args.conductor_dir}. Run /conductor:setup first.",
        }, indent=2))
        sys.exit(1)

    if not conductor_dir.is_dir():
        print(json.dumps({
            "compatible": False,
            "files": {},
            "warnings": [],
            "error": f"{args.conductor_dir} exists but is not a directory",
        }, indent=2))
        sys.exit(1)

    files = {}
    all_warnings = []
    missing_required = []

    for filename in REQUIRED_FILES:
        status, warnings = check_file(conductor_dir, filename)
        files[filename] = status
        all_warnings.extend(warnings)
        if status in ("missing", "empty"):
            missing_required.append(filename)

    for filename in OPTIONAL_FILES:
        status, warnings = check_file(conductor_dir, filename)
        files[filename] = status
        # Optional file warnings are informational, not blocking
        if status == "found":
            all_warnings.extend(warnings)

    # Check for ARCHITECT:HOOKS marker if workflow.md exists
    workflow_path = conductor_dir / "workflow.md"
    if workflow_path.exists():
        content = workflow_path.read_text()
        if "ARCHITECT:HOOKS" in content:
            all_warnings.append(
                "workflow.md already has ARCHITECT:HOOKS marker — "
                "Architect hooks may already be installed"
            )

    compatible = len(missing_required) == 0

    result = {
        "compatible": compatible,
        "files": files,
        "warnings": all_warnings,
    }

    if not compatible:
        result["error"] = (
            f"Missing required files: {', '.join(missing_required)}. "
            "Run /conductor:setup first."
        )

    print(json.dumps(result, indent=2))
    sys.exit(0 if compatible else 1)


if __name__ == "__main__":
    main()
