#!/usr/bin/env python3
"""Prepare a context bundle for feature decomposition.

Reads existing architecture state (architecture.md, cross-cutting.md,
metadata.json files, dependency-graph.md) and prepares a filtered,
token-budgeted context bundle for feature analysis. Similar to
prepare_brief_context.py but optimized for mid-project feature
decomposition rather than initial project decomposition.

Usage:
    python scripts/feature_context.py \
        --feature-description "Add role-based access control" \
        --conductor-dir conductor/ \
        --architect-dir architect/

Output: JSON to stdout with filtered context for feature analysis.
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Token budget per section (chars / 4 ≈ tokens)
TOKEN_BUDGET = {
    "architecture_summary": 6000,   # ~1500 tokens
    "tracks_summary": 8000,         # ~2000 tokens
    "constraints": 2000,            # ~500 tokens
    "dependency_graph": 2000,       # ~500 tokens
    "codebase_hints": 6000,         # ~1500 tokens
    "reserved": 8000,               # ~2000 tokens
}
TOTAL_CHAR_BUDGET = sum(TOKEN_BUDGET.values())


def load_text(path: Path) -> str | None:
    """Load a text file, return None if not found."""
    if path.exists():
        return path.read_text()
    return None


def load_json(path: Path) -> dict | None:
    """Load a JSON file, return None if not found."""
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
    return None


def truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, adding [truncated] marker."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 14] + "\n[truncated]"


def extract_architecture_summary(arch_text: str | None, budget: int) -> dict:
    """Extract components, technologies, and topology from architecture.md."""
    if not arch_text:
        return {"components": [], "confirmed_technologies": {}, "excerpt": ""}

    components = []
    technologies = {}
    excerpt_lines = []

    for line in arch_text.splitlines():
        # Extract component names from headings
        if re.match(r"^###?\s+", line):
            heading = line.lstrip("#").strip()
            if any(kw in heading.lower() for kw in
                   ("component", "service", "module", "layer")):
                components.append(heading)

        # Extract confirmed technology choices
        tech_match = re.match(
            r"[-*]\s*\*?\*?(.+?)\*?\*?\s*:\s*(.+)", line
        )
        if tech_match:
            key = tech_match.group(1).strip()
            val = tech_match.group(2).strip()
            if any(kw in key.lower() for kw in
                   ("language", "framework", "database", "auth",
                    "cache", "queue", "api", "frontend", "backend")):
                technologies[key] = val

        excerpt_lines.append(line)

    excerpt = truncate("\n".join(excerpt_lines), budget)

    return {
        "components": components[:20],
        "confirmed_technologies": dict(list(technologies.items())[:15]),
        "excerpt": excerpt,
    }


def extract_track_summaries(
    tracks_dir: Path, feature_keywords: list[str], budget: int
) -> list[dict]:
    """Extract track summaries with status, filtered by relevance."""
    summaries = []

    if not tracks_dir.exists():
        return summaries

    for meta_path in sorted(tracks_dir.glob("*/metadata.json")):
        meta = load_json(meta_path)
        if not meta:
            continue

        track_id = meta.get("track_id", meta_path.parent.name)
        brief_path = meta_path.parent / "brief.md"
        brief_text = load_text(brief_path)

        # Compute relevance score based on keyword overlap
        track_text = (
            f"{track_id} {meta.get('description', '')} "
            f"{' '.join(meta.get('dependencies', []))}"
        ).lower()
        if brief_text:
            track_text += f" {brief_text[:500].lower()}"

        relevance = sum(
            1 for kw in feature_keywords if kw in track_text
        )

        # Extract key decisions from brief if present
        key_decisions = []
        if brief_text:
            for m in re.finditer(
                r"^\d+\.\s+(.+?)(?:\n|$)", brief_text, re.MULTILINE
            ):
                key_decisions.append(m.group(1).strip()[:100])

        summaries.append({
            "id": track_id,
            "title": meta.get("description", ""),
            "status": meta.get("status", "new"),
            "wave": meta.get("wave", 0),
            "complexity": meta.get("complexity", "M"),
            "boundaries": meta.get("boundaries", []),
            "dependencies": meta.get("dependencies", []),
            "key_decisions": key_decisions[:5],
            "interfaces_owned": meta.get("interfaces_owned", []),
            "interfaces_consumed": meta.get("interfaces_consumed", []),
            "_relevance": relevance,
        })

    # Sort by relevance (highest first), then by wave
    summaries.sort(key=lambda s: (-s["_relevance"], s["wave"]))

    # Truncate to budget
    result = []
    chars_used = 0
    for s in summaries:
        del s["_relevance"]
        entry_json = json.dumps(s)
        if chars_used + len(entry_json) > budget:
            break
        result.append(s)
        chars_used += len(entry_json)

    return result


def extract_active_constraints(cc_text: str | None, budget: int) -> list[str]:
    """Extract active cross-cutting constraints from cross-cutting.md."""
    if not cc_text:
        return []

    constraints = []
    current_version = None

    for line in cc_text.splitlines():
        # Match version headers like "## CC v1.2"
        ver_match = re.match(r"^##\s+(CC\s+v[\d.]+)", line)
        if ver_match:
            current_version = ver_match.group(1)
            continue

        # Match constraint entries
        if current_version and line.startswith("### "):
            constraint_name = line[4:].strip()
            constraint_name = re.sub(
                r"\s*\((NEW|MODIFIED)\)\s*$", "", constraint_name
            )
            constraints.append(f"{current_version}: {constraint_name}")

    result_text = "\n".join(constraints)
    if len(result_text) > budget:
        constraints = constraints[:budget // 80]

    return constraints


def extract_dependency_graph(
    dep_text: str | None, budget: int
) -> dict:
    """Extract graph structure from dependency-graph.md."""
    if not dep_text:
        return {"nodes": [], "edges": []}

    nodes = set()
    edges = []

    # Parse table rows: | Track | Depends On |
    for line in dep_text.splitlines():
        row_match = re.match(
            r"\|\s*(\S+)\s*\|\s*(.+?)\s*\|", line
        )
        if row_match:
            track = row_match.group(1).strip()
            deps_text = row_match.group(2).strip()

            if track.lower() in ("track", "---", ""):
                continue

            nodes.add(track)
            if deps_text not in ("-", "None", "none", ""):
                for dep in re.split(r"[,\s]+", deps_text):
                    dep = dep.strip()
                    if dep and dep != "-":
                        nodes.add(dep)
                        edges.append([dep, track])

    return {
        "nodes": sorted(nodes),
        "edges": edges,
    }


def extract_codebase_hints(
    feature_description: str, tracks_dir: Path, budget: int
) -> dict:
    """Generate codebase hints by matching feature keywords to track scopes."""
    hints = {
        "relevant_directories": [],
        "relevant_tracks": [],
        "detected_patterns": [],
    }

    keywords = extract_keywords(feature_description)

    if not tracks_dir.exists():
        return hints

    for meta_path in sorted(tracks_dir.glob("*/metadata.json")):
        meta = load_json(meta_path)
        if not meta:
            continue

        track_id = meta.get("track_id", meta_path.parent.name)
        desc = meta.get("description", "").lower()

        if any(kw in desc for kw in keywords):
            hints["relevant_tracks"].append(track_id)

    return hints


def extract_keywords(description: str) -> list[str]:
    """Extract meaningful keywords from a feature description."""
    stop_words = {
        "a", "an", "the", "add", "create", "make", "build", "implement",
        "new", "with", "for", "and", "or", "to", "in", "on", "of",
        "is", "it", "this", "that", "be", "as", "at", "by", "from",
        "support", "feature", "system", "should", "will", "can",
    }
    words = re.findall(r"[a-zA-Z]+", description.lower())
    return [w for w in words if w not in stop_words and len(w) > 2]


def main():
    parser = argparse.ArgumentParser(
        description="Prepare context bundle for feature decomposition"
    )
    parser.add_argument(
        "--feature-description", required=True,
        help="Description of the feature to decompose",
    )
    parser.add_argument(
        "--conductor-dir", default="conductor",
        help="Path to conductor directory",
    )
    parser.add_argument(
        "--architect-dir", default="architect",
        help="Path to architect directory",
    )

    args = parser.parse_args()

    conductor_dir = Path(args.conductor_dir)
    architect_dir = Path(args.architect_dir)
    tracks_dir = conductor_dir / "tracks"

    feature_keywords = extract_keywords(args.feature_description)

    # 1. Architecture summary
    arch_text = load_text(architect_dir / "architecture.md")
    architecture_summary = extract_architecture_summary(
        arch_text, TOKEN_BUDGET["architecture_summary"]
    )

    # 2. Track summaries
    existing_tracks = extract_track_summaries(
        tracks_dir, feature_keywords, TOKEN_BUDGET["tracks_summary"]
    )

    # 3. Active constraints
    cc_text = load_text(architect_dir / "cross-cutting.md")
    active_constraints = extract_active_constraints(
        cc_text, TOKEN_BUDGET["constraints"]
    )

    # 4. Dependency graph
    dep_text = load_text(architect_dir / "dependency-graph.md")
    dependency_graph = extract_dependency_graph(
        dep_text, TOKEN_BUDGET["dependency_graph"]
    )

    # 5. Codebase hints
    codebase_hints = extract_codebase_hints(
        args.feature_description, tracks_dir,
        TOKEN_BUDGET["codebase_hints"]
    )

    # Assemble bundle
    bundle = {
        "feature_description": args.feature_description,
        "architecture_summary": architecture_summary,
        "existing_tracks": existing_tracks,
        "active_constraints": active_constraints,
        "dependency_graph": dependency_graph,
        "codebase_hints": codebase_hints,
        "token_budget": {
            k: v // 4 for k, v in TOKEN_BUDGET.items()
        },
    }

    # Estimate total size
    bundle_json = json.dumps(bundle)
    bundle["total_chars"] = len(bundle_json)
    bundle["estimated_tokens"] = len(bundle_json) // 4

    print(json.dumps(bundle, indent=2))


if __name__ == "__main__":
    main()
