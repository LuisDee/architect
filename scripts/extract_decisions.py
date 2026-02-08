#!/usr/bin/env python3
"""Extract implementation decisions from completed track artifacts.

Parses spec.md and plan.md for technology choices, pattern selections,
interface definitions, and rejected alternatives. Classifies each decision
and determines ADR-worthiness.

Usage:
    python scripts/extract_decisions.py --track-dir conductor/tracks/01_infra
    python scripts/extract_decisions.py --track-dir conductor/tracks/01_infra \
        --architect-dir architect

Output (JSON to stdout): List of classified decisions with ADR recommendations.
"""

import argparse
import json
import re
import sys
from pathlib import Path


# --- Decision search patterns ---

# Patterns that indicate a technology choice
TECHNOLOGY_PATTERNS = [
    re.compile(r"(?:chose|choosing|selected|picked|using|use)\s+(.+?)\s+(?:over|instead of|rather than)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:decided on|going with|opted for)\s+(.+?)(?:\s+(?:for|because|due to))", re.IGNORECASE),
    re.compile(r"(?:using|use)\s+(.+?)\s+(?:for|as)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:install|add)\s+(.+?)(?:\s+(?:for|as|to))", re.IGNORECASE),
]

# Patterns that indicate a pattern/architecture decision
PATTERN_PATTERNS = [
    re.compile(r"(?:applying|apply|adopted|adopt)\s+(.+?)\s+pattern", re.IGNORECASE),
    re.compile(r"(?:following|follow)\s+(.+?)\s+(?:pattern|approach|strategy)", re.IGNORECASE),
    re.compile(r"(?:implemented|implement)\s+(?:a\s+)?(.+?)\s+(?:pattern|architecture|approach)", re.IGNORECASE),
]

# Patterns that indicate interface definitions
INTERFACE_PATTERNS = [
    re.compile(r"(?:endpoint|route|api):\s*`?([A-Z]+\s+/\S+)`?", re.IGNORECASE),
    re.compile(r"(?:POST|GET|PUT|DELETE|PATCH)\s+(/\S+)", re.IGNORECASE),
    re.compile(r"(?:exposes?|provides?|publishes?)\s+(?:an?\s+)?(?:endpoint|route|api)\s+(?:at\s+)?`?(/\S+)`?", re.IGNORECASE),
]

# Patterns that indicate rejected alternatives
REJECTION_PATTERNS = [
    re.compile(r"(?:rejected|discarded|avoided|not using|won't use)\s+(.+?)(?:\s+because)", re.IGNORECASE),
    re.compile(r"(.+?)\s+(?:was rejected|was discarded|was considered but)", re.IGNORECASE),
    re.compile(r"(?:instead of|rather than|over)\s+(.+?)(?:\.|,|$)", re.IGNORECASE),
]

# Section headers that typically contain decisions
DECISION_SECTIONS = [
    "design decisions", "technology choices", "technical decisions",
    "architecture decisions", "key decisions", "approach",
    "implementation approach", "chosen approach",
]


def read_file_safe(path: Path) -> str | None:
    """Read a file, returning None if it doesn't exist."""
    if not path.exists():
        return None
    try:
        return path.read_text()
    except OSError:
        return None


def extract_sections(text: str) -> list[dict]:
    """Extract markdown sections with their content."""
    sections = []
    current_heading = ""
    current_level = 0
    current_lines: list[str] = []

    for line in text.splitlines():
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading_match:
            if current_heading:
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "content": "\n".join(current_lines),
                })
            current_heading = heading_match.group(2).strip()
            current_level = len(heading_match.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    if current_heading:
        sections.append({
            "heading": current_heading,
            "level": current_level,
            "content": "\n".join(current_lines),
        })

    return sections


def is_decision_section(heading: str) -> bool:
    """Check if a section heading indicates decision content."""
    heading_lower = heading.lower()
    return any(ds in heading_lower for ds in DECISION_SECTIONS)


def extract_technology_decisions(text: str, source: str) -> list[dict]:
    """Extract technology choice decisions from text."""
    decisions = []

    for pattern in TECHNOLOGY_PATTERNS:
        for match in pattern.finditer(text):
            chosen = match.group(1).strip().strip("`'\"")
            alternative = match.group(2).strip().strip("`'\"") if match.lastindex >= 2 else None

            # Skip overly generic matches
            if len(chosen) < 2 or len(chosen) > 80:
                continue

            decision = {
                "type": "TECHNOLOGY",
                "chosen": chosen,
                "source": source,
                "context_line": match.group(0).strip(),
            }
            if alternative and len(alternative) < 80:
                decision["alternatives_rejected"] = [alternative]
            decisions.append(decision)

    return decisions


def extract_pattern_decisions(text: str, source: str) -> list[dict]:
    """Extract architecture pattern decisions from text."""
    decisions = []

    for pattern in PATTERN_PATTERNS:
        for match in pattern.finditer(text):
            pattern_name = match.group(1).strip().strip("`'\"")
            if len(pattern_name) < 2 or len(pattern_name) > 80:
                continue

            decisions.append({
                "type": "PATTERN",
                "chosen": pattern_name,
                "source": source,
                "context_line": match.group(0).strip(),
            })

    return decisions


def extract_interface_decisions(text: str, source: str) -> list[dict]:
    """Extract interface/endpoint definitions from text."""
    decisions = []
    seen = set()

    for pattern in INTERFACE_PATTERNS:
        for match in pattern.finditer(text):
            endpoint = match.group(match.lastindex).strip()
            if endpoint in seen or len(endpoint) < 2:
                continue
            seen.add(endpoint)

            decisions.append({
                "type": "INTERFACE",
                "chosen": endpoint,
                "source": source,
                "context_line": match.group(0).strip(),
            })

    return decisions


def extract_rejections(text: str) -> list[str]:
    """Extract rejected alternatives from text."""
    rejections = []
    for pattern in REJECTION_PATTERNS:
        for match in pattern.finditer(text):
            rejected = match.group(1).strip().strip("`'\"")
            if 2 < len(rejected) < 80:
                rejections.append(rejected)
    return rejections


def classify_adr_worthiness(decision: dict, all_decisions: list[dict]) -> bool:
    """Determine if a decision warrants a standalone ADR.

    ADR-worthy if any of:
    - Multiple alternatives were considered/rejected
    - Decision type is PATTERN (architectural pattern choices are significant)
    - Decision appears in a dedicated decision section
    """
    if decision.get("alternatives_rejected"):
        return True
    if decision["type"] == "PATTERN":
        return True
    if decision.get("in_decision_section"):
        return True
    return False


def generate_adr_slug(decision: dict) -> str:
    """Generate a slug for an ADR filename."""
    chosen = decision["chosen"]
    words = re.findall(r"[a-zA-Z0-9]+", chosen.lower())
    slug = "-".join(words[:6])
    return slug or "decision"


def get_next_adr_number(architect_dir: Path) -> int:
    """Find the next available ADR number."""
    decisions_dir = architect_dir / "decisions"
    if not decisions_dir.exists():
        return 1

    max_num = 0
    for f in decisions_dir.glob("ADR-*.md"):
        m = re.match(r"ADR-(\d+)", f.stem)
        if m:
            max_num = max(max_num, int(m.group(1)))

    return max_num + 1


def extract_decisions(track_dir: str, architect_dir: str = "architect") -> dict:
    """Main entry point: extract all decisions from a track's artifacts.

    Args:
        track_dir: Path to the track directory (e.g., conductor/tracks/01_infra)
        architect_dir: Path to the architect directory

    Returns:
        Dict with classified decisions, ADR recommendations, and summary.
    """
    track_path = Path(track_dir)
    arch_path = Path(architect_dir)
    track_id = track_path.name

    spec_text = read_file_safe(track_path / "spec.md")
    plan_text = read_file_safe(track_path / "plan.md")
    brief_text = read_file_safe(track_path / "brief.md")

    all_decisions: list[dict] = []

    # Process each artifact
    for text, source_name in [
        (spec_text, "spec.md"),
        (plan_text, "plan.md"),
        (brief_text, "brief.md"),
    ]:
        if not text:
            continue

        # Extract from decision sections with higher priority
        sections = extract_sections(text)
        decision_section_text = ""
        for section in sections:
            if is_decision_section(section["heading"]):
                decision_section_text += section["content"] + "\n"

        # Extract from full text
        tech = extract_technology_decisions(text, source_name)
        patterns = extract_pattern_decisions(text, source_name)
        interfaces = extract_interface_decisions(text, source_name)

        # Mark decisions that come from decision sections
        if decision_section_text:
            ds_tech = extract_technology_decisions(decision_section_text, source_name)
            ds_patterns = extract_pattern_decisions(decision_section_text, source_name)
            ds_chosen = {d["chosen"] for d in ds_tech + ds_patterns}

            for d in tech + patterns:
                if d["chosen"] in ds_chosen:
                    d["in_decision_section"] = True

        all_decisions.extend(tech + patterns + interfaces)

    # Deduplicate by (type, chosen)
    seen = set()
    unique_decisions = []
    for d in all_decisions:
        key = (d["type"], d["chosen"].lower())
        if key not in seen:
            seen.add(key)
            unique_decisions.append(d)
    all_decisions = unique_decisions

    # Collect rejections from all artifacts
    all_rejections = []
    for text in [spec_text, plan_text, brief_text]:
        if text:
            all_rejections.extend(extract_rejections(text))

    # Classify ADR-worthiness
    adr_candidates = []
    next_adr_num = get_next_adr_number(arch_path)

    for d in all_decisions:
        d["adr_worthy"] = classify_adr_worthiness(d, all_decisions)
        if d["adr_worthy"]:
            slug = generate_adr_slug(d)
            adr_num = next_adr_num
            next_adr_num += 1
            adr_candidates.append({
                "filename": f"ADR-{adr_num:03d}-{slug}.md",
                "number": adr_num,
                "title": d["chosen"],
                "type": d["type"],
                "source": d["source"],
                "context_line": d.get("context_line", ""),
                "alternatives": d.get("alternatives_rejected", []),
            })

    return {
        "track_id": track_id,
        "decisions": all_decisions,
        "adr_candidates": adr_candidates,
        "rejected_alternatives": list(set(all_rejections)),
        "summary": {
            "total_decisions": len(all_decisions),
            "technology_decisions": sum(1 for d in all_decisions if d["type"] == "TECHNOLOGY"),
            "pattern_decisions": sum(1 for d in all_decisions if d["type"] == "PATTERN"),
            "interface_decisions": sum(1 for d in all_decisions if d["type"] == "INTERFACE"),
            "adr_worthy": len(adr_candidates),
        },
        "sources_read": [
            s for s, t in [
                ("spec.md", spec_text),
                ("plan.md", plan_text),
                ("brief.md", brief_text),
            ] if t is not None
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract implementation decisions from track artifacts"
    )
    parser.add_argument(
        "--track-dir", type=str, required=True,
        help="Path to the completed track directory",
    )
    parser.add_argument(
        "--architect-dir", type=str, default="architect",
        help="Path to the architect directory (for ADR numbering)",
    )

    args = parser.parse_args()
    result = extract_decisions(args.track_dir, args.architect_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
