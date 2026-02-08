#!/usr/bin/env python3
"""Analyze feature scope and recommend single vs. multi-track decomposition.

Given a feature description and existing architecture state, decides whether
the feature needs 1 track or N tracks, identifies which architectural
boundaries are crossed, and outputs a decomposition recommendation.

Usage:
    echo '{"feature_description":"Add RBAC","architecture_state":{...}}' | \
        python scripts/scope_analyzer.py

    python scripts/scope_analyzer.py --feature "Add RBAC" \
        --context-file /tmp/feature_context.json

Output (JSON to stdout): Decomposition recommendation with tracks,
    confidence, reasoning, and alternatives.
"""

import argparse
import json
import re
import sys


# --- Boundary identification ---

BOUNDARY_SIGNALS = {
    "data_model": [
        "schema", "model", "table", "migration", "column", "database",
        "entity", "record", "field", "index", "foreign key", "relation",
        "orm", "seed", "fixture", "sql",
    ],
    "api_layer": [
        "endpoint", "api", "route", "middleware", "controller", "rest",
        "graphql", "handler", "request", "response", "http", "webhook",
        "grpc", "socket",
    ],
    "ui_layer": [
        "page", "component", "form", "button", "ui", "dashboard",
        "view", "template", "layout", "modal", "widget", "screen",
        "frontend", "react", "vue", "angular", "css", "style",
    ],
    "infrastructure": [
        "deploy", "config", "environment", "docker", "ci", "cd",
        "kubernetes", "terraform", "nginx", "redis", "cache",
        "queue", "worker", "cron", "monitoring", "logging",
    ],
    "external_integration": [
        "integrate", "third-party", "oauth", "payment", "stripe",
        "email", "sms", "notification", "s3", "aws", "gcp", "azure",
        "twilio", "sendgrid", "external",
    ],
}

# --- Ambiguity detection ---

VAGUE_TERMS = [
    "improve", "optimize", "make better", "enhance", "fix",
    "update", "refactor", "clean up", "faster", "slower",
    "performance", "better",
]

SLOT_PATTERNS = {
    "auth_method": r"\b(auth|authentication|login)\b",
    "data_store": r"\b(store|persist|save|database)\b",
    "api_format": r"\b(api|endpoint|interface)\b",
}


def detect_ambiguity(description: str) -> list[dict]:
    """Detect underspecification or vagueness in feature description."""
    desc_lower = description.lower()
    signals = []

    # Check for vague terms
    for term in VAGUE_TERMS:
        if term in desc_lower:
            signals.append({
                "type": "vague_scope",
                "term": term,
                "question": f"What specific aspect should be {term}d? "
                            f"Please describe the concrete outcome.",
            })

    # Check word count (too short = likely underspecified)
    word_count = len(description.split())
    if word_count < 5:
        signals.append({
            "type": "missing_detail",
            "term": description,
            "question": f"Can you describe what '{description}' should do? "
                        f"Key scenarios and expected behavior?",
        })

    return signals[:3]  # Max 3 clarification questions


def identify_boundaries(
    description: str, tech_stack_summary: str = ""
) -> list[str]:
    """Identify which architectural boundaries the feature crosses.

    Only the feature description is used for boundary detection.
    Tech stack summary is not included to avoid false positives
    (e.g., "PostgreSQL" in tech stack triggering data_model for
    every feature).
    """
    text = description.lower()
    crossed = []

    for boundary, signals in BOUNDARY_SIGNALS.items():
        score = sum(1 for s in signals if s in text)
        if score >= 1:
            crossed.append(boundary)

    return crossed


def is_atomic(description: str, boundaries: list[str]) -> bool:
    """Check if changes across boundaries can be deployed atomically.

    Heuristic: if <= 2 boundaries and description suggests tight coupling,
    treat as atomic.
    """
    if len(boundaries) <= 1:
        return True

    desc_lower = description.lower()

    # Atomic signals: tight coupling language
    atomic_signals = [
        "simple", "basic", "minimal", "small", "tiny", "quick",
        "single", "one", "just", "only", "toggle", "flag",
    ]
    atomic_score = sum(1 for s in atomic_signals if s in desc_lower)

    # Non-atomic signals: complex scope language
    non_atomic_signals = [
        "system", "framework", "platform", "comprehensive", "full",
        "complete", "entire", "multiple", "several", "complex",
        "migration", "restructure",
    ]
    non_atomic_score = sum(1 for s in non_atomic_signals if s in desc_lower)

    if len(boundaries) == 2 and atomic_score > non_atomic_score:
        return True

    return False


def is_trivial(
    description: str, boundaries: list[str], existing_tracks: list[dict]
) -> bool:
    """Check if feature is too small to warrant track decomposition.

    Trivial if ALL: crosses <= 1 boundary, estimated <= 2 files,
    no dependencies on pending tracks, no cross-cutting implications.
    """
    if len(boundaries) > 1:
        return False

    desc_lower = description.lower()
    word_count = len(description.split())

    # Very short description + single boundary = likely trivial
    if word_count <= 8 and len(boundaries) <= 1:
        trivial_signals = [
            "add field", "rename", "fix typo", "update label",
            "change color", "add button", "remove", "hide",
            "show", "toggle", "move",
        ]
        if any(s in desc_lower for s in trivial_signals):
            return True

    return False


def find_covering_track(
    boundary: str, existing_tracks: list[dict]
) -> dict | None:
    """Find an in-progress track that already covers a boundary."""
    for track in existing_tracks:
        if (track.get("status") == "in_progress"
                and boundary in track.get("boundaries", [])):
            return track
    return None


def compute_wave(
    depends_on: list[str], existing_tracks: list[dict]
) -> int:
    """Compute the earliest wave a new track can be placed in."""
    if not depends_on:
        # No dependencies: place in current latest wave + 1
        max_wave = max((t.get("wave", 1) for t in existing_tracks), default=1)
        return max_wave

    dep_waves = []
    track_by_id = {t["id"]: t for t in existing_tracks}
    for dep_id in depends_on:
        if dep_id in track_by_id:
            dep_waves.append(track_by_id[dep_id].get("wave", 1))
        else:
            dep_waves.append(1)

    return max(dep_waves) + 1


def analyze_scope(input_data: dict) -> dict:
    """Main entry point: analyze feature scope and return recommendation.

    Args:
        input_data: Dict with feature_description, architecture_state,
                    and optional clarifications.

    Returns:
        Decomposition recommendation dict.
    """
    description = input_data.get("feature_description", "")
    arch_state = input_data.get("architecture_state", {})
    clarifications = input_data.get("clarifications", {})
    existing_tracks = arch_state.get("existing_tracks", [])
    tech_stack = arch_state.get("tech_stack_summary", "")

    # Step 1: Check for ambiguity
    ambiguity = detect_ambiguity(description)
    if ambiguity and not clarifications:
        return {
            "recommendation": "needs_clarification",
            "confidence": 0.0,
            "reasoning": "Feature description is underspecified",
            "questions": [a["question"] for a in ambiguity],
            "ambiguity_signals": ambiguity,
        }

    # Step 2: Identify boundaries
    boundaries = identify_boundaries(description, tech_stack)

    # Step 3: Check if trivial
    if is_trivial(description, boundaries, existing_tracks):
        return {
            "recommendation": "skip_tracking",
            "confidence": 0.9,
            "reasoning": "Feature is small enough to implement directly "
                         "without track decomposition",
            "boundaries": boundaries,
        }

    # Step 4: Check atomicity for single-track case
    if len(boundaries) <= 1 or is_atomic(description, boundaries):
        wave = compute_wave([], existing_tracks)
        return {
            "recommendation": "single_track",
            "confidence": 0.8 if len(boundaries) <= 1 else 0.65,
            "reasoning": (
                f"Feature touches {len(boundaries)} boundary(ies) "
                f"({', '.join(boundaries) or 'none identified'}) "
                f"and can be implemented atomically"
            ),
            "tracks": [{
                "suggested_id": generate_track_id(description, existing_tracks),
                "scope": description,
                "boundaries": boundaries,
                "depends_on": [],
                "estimated_complexity": estimate_complexity(description, boundaries),
                "cross_cutting_concerns": [],
            }],
            "boundaries": boundaries,
        }

    # Step 5: Multi-track decomposition
    tracks = []
    extensions = []

    for boundary in boundaries:
        covering = find_covering_track(boundary, existing_tracks)
        if covering:
            extensions.append({
                "type": "TRACK_EXTENSION",
                "track_id": covering["id"],
                "boundary": boundary,
                "reason": f"Existing in-progress track {covering['id']} "
                          f"already covers {boundary}",
            })
        else:
            track_id = generate_track_id(
                f"{description} {boundary}", existing_tracks
            )
            deps = compute_dependencies(boundary, boundaries, tracks, existing_tracks)
            tracks.append({
                "suggested_id": track_id,
                "scope": f"{description} — {boundary} boundary",
                "boundaries": [boundary],
                "depends_on": deps,
                "estimated_complexity": estimate_complexity(
                    description, [boundary]
                ),
                "cross_cutting_concerns": [],
            })

    # Compute wave for each track
    all_tracks_for_wave = existing_tracks + [
        {"id": t["suggested_id"], "wave": 0, **t} for t in tracks
    ]
    for track in tracks:
        track["suggested_wave"] = compute_wave(
            track["depends_on"], all_tracks_for_wave
        )

    result = {
        "recommendation": "multi_track",
        "confidence": 0.75,
        "reasoning": (
            f"Feature crosses {len(boundaries)} boundaries "
            f"({', '.join(boundaries)}) with non-atomic changes"
        ),
        "tracks": tracks,
        "boundaries": boundaries,
    }

    if extensions:
        result["extensions"] = extensions

    # Provide single-track alternative
    if len(tracks) <= 3:
        result["alternative"] = {
            "recommendation": "single_track",
            "condition": "If the feature scope can be reduced or "
                         "changes can be deployed atomically",
            "reasoning": "A single track is simpler if tight coupling "
                         "is acceptable",
        }

    return result


def generate_track_id(description: str, existing_tracks: list[dict]) -> str:
    """Generate a track ID from description."""
    # Extract key words, create slug
    words = re.findall(r"[a-zA-Z]+", description.lower())
    stop_words = {
        "a", "an", "the", "add", "create", "make", "build", "implement",
        "new", "with", "for", "and", "or", "to", "in", "on", "of",
        "is", "it", "this", "that", "be", "as", "at", "by", "from",
        "support", "feature", "system", "should", "will", "can",
        "data", "model", "api", "layer", "ui", "infrastructure",
        "external", "integration", "boundary",
    }
    meaningful = [w for w in words if w not in stop_words and len(w) > 2][:3]

    if not meaningful:
        meaningful = ["feature"]

    # Find next available number
    existing_nums = []
    for t in existing_tracks:
        m = re.match(r"(\d+)", t.get("id", ""))
        if m:
            existing_nums.append(int(m.group(1)))

    next_num = max(existing_nums, default=0) + 1
    slug = "_".join(meaningful)

    return f"{next_num:02d}_{slug}"


def estimate_complexity(description: str, boundaries: list[str]) -> str:
    """Estimate complexity: S, M, L, XL."""
    word_count = len(description.split())
    boundary_count = len(boundaries)

    if boundary_count >= 3 or word_count > 50:
        return "L"
    elif boundary_count >= 2 or word_count > 20:
        return "M"
    else:
        return "S"


def compute_dependencies(
    boundary: str, all_boundaries: list[str],
    tracks_so_far: list[dict], existing_tracks: list[dict]
) -> list[str]:
    """Compute dependencies for a boundary-specific track."""
    deps = []

    # Data model tracks are typically depended on by API and UI tracks
    dep_order = ["data_model", "infrastructure", "api_layer", "ui_layer",
                 "external_integration"]

    boundary_idx = dep_order.index(boundary) if boundary in dep_order else -1

    # Depend on earlier-ordered boundaries that are also part of this feature
    for earlier_boundary in dep_order[:max(boundary_idx, 0)]:
        if earlier_boundary in all_boundaries and earlier_boundary != boundary:
            for t in tracks_so_far:
                if earlier_boundary in t.get("boundaries", []):
                    deps.append(t["suggested_id"])

    # Also depend on related existing tracks
    for existing in existing_tracks:
        if (existing.get("status") in ("completed", "in_progress")
                and boundary in existing.get("boundaries", [])):
            deps.append(existing["id"])

    return list(dict.fromkeys(deps))  # Deduplicate preserving order


def main():
    parser = argparse.ArgumentParser(
        description="Analyze feature scope for track decomposition"
    )
    parser.add_argument(
        "--feature", type=str,
        help="Feature description (alternative to stdin JSON)",
    )
    parser.add_argument(
        "--context-file", type=str,
        help="Path to feature context JSON file (from feature_context.py)",
    )

    args = parser.parse_args()

    if args.feature:
        # Simple mode: feature description only
        context = {}
        if args.context_file:
            with open(args.context_file) as f:
                context = json.load(f)

        input_data = {
            "feature_description": args.feature,
            "architecture_state": {
                "existing_tracks": context.get("existing_tracks", []),
                "tech_stack_summary": "",
                "cross_cutting_version": "",
                "architecture_components": context.get(
                    "architecture_summary", {}
                ).get("components", []),
            },
        }
    else:
        # Full mode: JSON from stdin
        input_data = json.load(sys.stdin)

    result = analyze_scope(input_data)
    print(json.dumps(result, indent=2))

    # Exit code: 0 = actionable recommendation, 2 = needs clarification
    if result.get("recommendation") == "needs_clarification":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
