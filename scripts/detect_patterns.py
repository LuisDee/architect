#!/usr/bin/env python3
"""Detect emerging patterns in codebase analysis output.

Analyzes codebase-analyzer output to identify:
  - Fan-in: modules with high cross-boundary import frequency
  - Repetition: code structures appearing 3+ times across modules
  - Cross-cutting candidates: patterns that should be promoted to constraints

Usage:
    echo '{"codebase_analysis":{...},"existing_cross_cutting":{...}}' | \
        python scripts/detect_patterns.py

    python scripts/detect_patterns.py --analysis-file /tmp/analysis.json

Output (JSON to stdout): Detected patterns with recommendations.
"""

import argparse
import json
import re
import sys
from pathlib import Path


# Known cross-cutting categories (from cross-cutting-catalog.md)
ALWAYS_EVALUATE = [
    "logging", "error_handling", "authentication", "authorization",
    "input_validation", "configuration", "monitoring", "testing",
]

IF_MULTI_SERVICE = [
    "service_discovery", "circuit_breaking", "distributed_tracing",
    "api_gateway", "event_bus",
]

IF_USER_FACING = [
    "i18n", "accessibility", "rate_limiting",
]

IF_DATA_HEAVY = [
    "caching", "connection_pooling", "migration_strategy", "backup",
]

# Keywords mapping common imports/modules to CC categories
CATEGORY_KEYWORDS = {
    "logging": ["log", "logger", "logging", "structlog", "winston", "pino", "bunyan"],
    "error_handling": ["error", "exception", "catch", "throw", "try", "fault"],
    "authentication": ["auth", "jwt", "token", "passport", "session", "login"],
    "authorization": ["rbac", "role", "permission", "acl", "guard", "policy"],
    "input_validation": ["validator", "validate", "schema", "joi", "zod", "pydantic"],
    "configuration": ["config", "env", "settings", "dotenv"],
    "monitoring": ["metrics", "prometheus", "otel", "telemetry", "health"],
    "testing": ["test", "mock", "fixture", "assert", "jest", "pytest"],
    "caching": ["cache", "redis", "memcache", "lru"],
    "rate_limiting": ["rate", "limit", "throttle"],
    "distributed_tracing": ["trace", "tracing", "span", "otel", "jaeger", "zipkin"],
}


def calculate_fan_in(modules: list[dict]) -> list[dict]:
    """Count how many modules import each dependency.

    High fan-in (>50% of modules) suggests cross-cutting behavior.

    Args:
        modules: List of {path, imports, exports} dicts.

    Returns:
        List of fan-in patterns detected.
    """
    import_counts: dict[str, int] = {}
    total_modules = len(modules)

    if total_modules == 0:
        return []

    for module in modules:
        seen = set()
        for imp in module.get("imports", []):
            imp_lower = imp.lower()
            if imp_lower not in seen:
                import_counts[imp_lower] = import_counts.get(imp_lower, 0) + 1
                seen.add(imp_lower)

    patterns = []
    for imp, count in sorted(import_counts.items(), key=lambda x: -x[1]):
        fan_in_score = count / total_modules
        if fan_in_score > 0.5:
            patterns.append({
                "type": "fan_in",
                "name": imp,
                "fan_in_score": round(fan_in_score, 2),
                "evidence": f"Imported in {count}/{total_modules} modules ({fan_in_score:.0%})",
                "module_count": count,
            })

    return patterns


def detect_repetitions(
    code_structures: list[dict], threshold: int = 3
) -> list[dict]:
    """Identify code structures that appear in 3+ locations across 2+ modules.

    Args:
        code_structures: List of {pattern, locations, structure} dicts.
        threshold: Minimum occurrences to flag.

    Returns:
        List of repetition patterns detected.
    """
    patterns = []

    for structure in code_structures:
        locations = structure.get("locations", [])
        if len(locations) < threshold:
            continue

        # Check locations span multiple modules
        modules = set()
        for loc in locations:
            parts = loc.replace("\\", "/").split("/")
            if len(parts) >= 2:
                modules.add(parts[1] if parts[0] in ("src", ".", "") else parts[0])

        if len(modules) >= 2:
            patterns.append({
                "type": "repetition",
                "name": structure.get("pattern", "Unknown pattern"),
                "occurrences": len(locations),
                "locations": locations,
                "modules_spanned": len(modules),
                "evidence": (
                    f"Same structure in {len(locations)} locations "
                    f"across {len(modules)} modules"
                ),
            })

    return patterns


def detect_function_hotspots(
    function_calls: list[dict], threshold: int = 3
) -> list[dict]:
    """Identify frequently called functions that span multiple modules."""
    patterns = []

    for call in function_calls:
        locations = call.get("locations", [])
        if len(locations) < threshold:
            continue

        modules = set()
        for loc in locations:
            parts = loc.replace("\\", "/").split("/")
            if len(parts) >= 2:
                modules.add(parts[1] if parts[0] in ("src", ".", "") else parts[0])

        if len(modules) >= 2:
            patterns.append({
                "type": "function_hotspot",
                "name": call.get("name", "unknown"),
                "call_count": len(locations),
                "modules_spanned": len(modules),
                "evidence": (
                    f"Called {len(locations)} times "
                    f"across {len(modules)} modules"
                ),
            })

    return patterns


def classify_as_cross_cutting(
    pattern: dict, is_multi_service: bool = False,
    is_user_facing: bool = False, is_data_heavy: bool = False,
) -> dict | None:
    """Check if a detected pattern matches a known cross-cutting category."""
    name_lower = pattern["name"].lower()

    # Check always-evaluate categories
    for category in ALWAYS_EVALUATE:
        keywords = CATEGORY_KEYWORDS.get(category, [category])
        if any(kw in name_lower for kw in keywords):
            return {
                "is_cross_cutting": True,
                "category": category,
                "priority": "always",
            }

    # Check conditional categories
    if is_multi_service:
        for category in IF_MULTI_SERVICE:
            keywords = CATEGORY_KEYWORDS.get(category, [category])
            if any(kw in name_lower for kw in keywords):
                return {
                    "is_cross_cutting": True,
                    "category": category,
                    "priority": "multi_service",
                }

    if is_user_facing:
        for category in IF_USER_FACING:
            keywords = CATEGORY_KEYWORDS.get(category, [category])
            if any(kw in name_lower for kw in keywords):
                return {
                    "is_cross_cutting": True,
                    "category": category,
                    "priority": "user_facing",
                }

    if is_data_heavy:
        for category in IF_DATA_HEAVY:
            keywords = CATEGORY_KEYWORDS.get(category, [category])
            if any(kw in name_lower for kw in keywords):
                return {
                    "is_cross_cutting": True,
                    "category": category,
                    "priority": "data_heavy",
                }

    return None


def is_already_tracked(
    pattern_name: str, existing_constraints: list[str]
) -> bool:
    """Check if pattern is already covered by existing cross-cutting constraints.

    Uses word-overlap (Jaccard > 0.5) for semantic deduplication.
    """
    pattern_words = set(re.findall(r"\w+", pattern_name.lower()))
    if not pattern_words:
        return False

    for constraint in existing_constraints:
        constraint_words = set(re.findall(r"\w+", constraint.lower()))
        if not constraint_words:
            continue
        overlap = len(pattern_words & constraint_words)
        union = len(pattern_words | constraint_words)
        if union > 0 and overlap / union > 0.5:
            return True

    return False


def detect_patterns(input_data: dict) -> dict:
    """Main entry point: analyze codebase data and detect patterns.

    Args:
        input_data: Dict with codebase_analysis and existing_cross_cutting.

    Returns:
        Detection results with patterns, classifications, and summary.
    """
    analysis = input_data.get("codebase_analysis", {})
    existing_cc = input_data.get("existing_cross_cutting", {})

    modules = analysis.get("modules", [])
    function_calls = analysis.get("function_calls", [])
    code_structures = analysis.get("code_structures", [])
    existing_constraints = existing_cc.get("constraints", [])

    # Detect project characteristics
    is_multi_service = len(modules) > 3
    is_user_facing = any(
        any(kw in m.get("path", "").lower() for kw in ["frontend", "ui", "web", "app"])
        for m in modules
    )
    is_data_heavy = any(
        any(kw in str(m.get("imports", [])).lower() for kw in ["database", "orm", "sql", "mongo"])
        for m in modules
    )

    # Run detectors
    all_patterns = []
    all_patterns.extend(calculate_fan_in(modules))
    all_patterns.extend(detect_repetitions(code_structures))
    all_patterns.extend(detect_function_hotspots(function_calls))

    # Classify and enrich
    cc_candidates = 0
    already_tracked = 0
    new_recommendations = 0

    for pattern in all_patterns:
        classification = classify_as_cross_cutting(
            pattern, is_multi_service, is_user_facing, is_data_heavy
        )
        if classification:
            pattern["is_cross_cutting"] = True
            pattern["category"] = classification["category"]
            pattern["priority"] = classification["priority"]
            cc_candidates += 1

            tracked = is_already_tracked(pattern["name"], existing_constraints)
            pattern["already_tracked"] = tracked
            if tracked:
                already_tracked += 1
            else:
                new_recommendations += 1
                pattern["recommendation"] = (
                    f"Consider adding CC: 'All modules must use "
                    f"{pattern['name']} consistently'"
                )
        else:
            pattern["is_cross_cutting"] = False
            pattern["already_tracked"] = False

    return {
        "patterns_detected": all_patterns,
        "summary": {
            "total_patterns": len(all_patterns),
            "cross_cutting_candidates": cc_candidates,
            "already_tracked": already_tracked,
            "new_recommendations": new_recommendations,
        },
        "project_characteristics": {
            "is_multi_service": is_multi_service,
            "is_user_facing": is_user_facing,
            "is_data_heavy": is_data_heavy,
            "total_modules": len(modules),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Detect emerging patterns in codebase analysis"
    )
    parser.add_argument(
        "--analysis-file", type=str,
        help="Path to codebase analysis JSON file (alternative to stdin)",
    )

    args = parser.parse_args()

    if args.analysis_file:
        with open(args.analysis_file) as f:
            input_data = json.load(f)
    else:
        input_data = json.load(sys.stdin)

    result = detect_patterns(input_data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
