#!/usr/bin/env python3
"""Validate requirements coverage across track briefs.

Post-decompose safety net — checks that every requirement from product.md
is mapped to at least one track, present in briefs, and covered in Scope IN.

Uses a multi-strategy matching approach (stdlib only):
- difflib.SequenceMatcher for edit-distance similarity
- Token-based Jaccard similarity for word overlap
- N-gram shingling for partial phrase matching
- Substring containment as a fast path
- Normalized number extraction for numeric requirement matching

Usage:
    python scripts/validate_requirements.py \
        --product-md conductor/product.md \
        --tracks-dir conductor/tracks

    python scripts/validate_requirements.py \
        --product-md conductor/product.md \
        --tracks-dir conductor/tracks \
        --requirements-map architect/requirements-map.json

Output: JSON report to stdout. Exit code 0 if 100% mapped, 1 if gaps exist.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

# ---------------------------------------------------------------------------
# Requirement extraction
# ---------------------------------------------------------------------------

# RFC 2119 keywords + common requirement language
REQUIREMENT_KEYWORDS = [
    # RFC 2119 (https://datatracker.ietf.org/doc/html/rfc2119)
    "must", "must not", "required", "shall", "shall not",
    "should", "should not", "recommended", "may", "optional",
    # Common requirement language
    "support", "handle", "provide", "implement", "enforce",
    "maximum", "minimum", "at least", "up to", "within",
    "timeout", "limit", "require", "ensure", "allow",
    "enable", "prevent", "restrict", "authenticate", "authorize",
    "validate", "verify", "configure", "configurable",
    "persist", "retain", "store", "expire", "rotate",
    "scale", "concurrent", "parallel", "throttle", "rate",
    "encrypt", "decrypt", "hash", "sign", "token",
    "retry", "backoff", "fallback", "failover", "circuit",
    "notify", "alert", "log", "audit", "track",
    "respond", "return", "accept", "reject", "deny",
]

# Section headings that indicate requirements content
REQUIREMENT_HEADINGS = [
    "requirement", "constraint", "acceptance", "criteria",
    "non-functional", "performance", "security", "reliability",
    "scalability", "availability", "feature", "capability",
    "user stor", "use case", "functional", "behavior",
    "specification", "expectation",
]

# Stopwords to ignore during matching (common English words that add noise)
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "this", "that",
    "these", "those", "it", "its", "they", "them", "their", "we", "our",
    "not", "no", "if", "then", "else", "when", "where", "how", "all",
    "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "than", "too", "very", "also", "any",
}


def extract_requirements_from_product_md(product_md_path: str) -> list[str]:
    """Extract lines that look like requirements from product.md.

    Heuristics (layered, catch different requirement styles):
    1. Lines containing specific numbers/quantities (in list or requirement section)
    2. List items containing RFC 2119 or requirement keywords
    3. All list items under requirement-related section headings
    4. Prose sentences containing strong requirement indicators ("must", "shall")
    """
    path = Path(product_md_path)
    if not path.exists():
        print(f"Error: product.md not found: {path}", file=sys.stderr)
        sys.exit(1)

    text = path.read_text()
    lines = text.splitlines()
    requirements: list[str] = []
    in_requirement_section = False
    in_html_comment = False

    for line in lines:
        stripped = line.strip()

        # Track HTML comment blocks
        if "<!--" in stripped:
            in_html_comment = True
        if "-->" in stripped:
            in_html_comment = False
            continue
        if in_html_comment:
            continue

        # Track section headings
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip().lower()
            in_requirement_section = any(
                kw in heading_text for kw in REQUIREMENT_HEADINGS
            )
            continue

        # Skip empty lines
        if not stripped:
            continue

        is_list_item = stripped.startswith("- ") or stripped.startswith("* ")
        content = stripped[2:] if is_list_item else stripped
        content_lower = content.lower()

        is_requirement = False

        # Heuristic 1: Lines containing specific numbers/quantities
        if re.search(r"\d+", stripped) and (is_list_item or in_requirement_section):
            is_requirement = True

        # Heuristic 2: List items with requirement keywords
        if is_list_item and any(kw in content_lower for kw in REQUIREMENT_KEYWORDS):
            is_requirement = True

        # Heuristic 3: All list items in requirement sections
        if in_requirement_section and is_list_item:
            is_requirement = True

        # Heuristic 4: Prose with strong requirement indicators
        # Catches requirements not formatted as list items
        if not is_list_item and not stripped.startswith("#"):
            strong_indicators = ["must ", "must not ", "shall ", "shall not ",
                                 "required to ", "is required"]
            if any(ind in content_lower for ind in strong_indicators):
                is_requirement = True

        if is_requirement:
            req_text = content.strip()
            if req_text and req_text not in requirements:
                requirements.append(req_text)

    return requirements


# ---------------------------------------------------------------------------
# Multi-strategy fuzzy matching
# ---------------------------------------------------------------------------

def crude_stem(word: str) -> str:
    """Minimal suffix stripping for matching purposes.

    Not a real stemmer — just handles the most common suffixes that cause
    false negatives in requirement matching (e.g., "rotatable"/"rotation",
    "concurrent"/"concurrency", "configurable"/"configuration").
    """
    if len(word) <= 4:
        return word
    # Order matters: check longer suffixes first
    for suffix in (
        "ation", "ition", "ement", "ment", "ence", "ance",
        "ible", "able", "ting", "ness", "ious", "eous",
        "ency", "ancy", "ment", "sion", "tion",
        "ing", "ble", "ity", "ful", "ous", "ive",
        "ual", "ary", "ory", "ure", "ize",
        "ly", "ed", "er", "es", "al",
    ):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    if word.endswith("s") and len(word) > 4:
        return word[:-1]
    return word


def tokenize(text: str, remove_stopwords: bool = True, stem: bool = False) -> list[str]:
    """Tokenize text into lowercase words, optionally stemmed."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    if stem:
        tokens = [crude_stem(t) for t in tokens]
    return tokens


def extract_numbers(text: str) -> set[str]:
    """Extract normalized numeric values from text.

    Matches integers, decimals, and numbers with units.
    Normalizes "5 minutes" and "5min" to comparable forms.
    """
    # Find all numbers (possibly with units)
    patterns = re.findall(r"(\d+(?:\.\d+)?)\s*(%|ms|s|sec|min|minutes?|hours?|hr|days?|gb|mb|kb|tb|k\b)?", text.lower())
    numbers = set()
    for num, unit in patterns:
        # Normalize units
        unit = unit.strip() if unit else ""
        if unit in ("min", "minutes", "minute"):
            unit = "min"
        elif unit in ("sec", "s", "seconds", "second"):
            unit = "s"
        elif unit in ("hr", "hours", "hour"):
            unit = "hr"
        elif unit in ("days", "day"):
            unit = "day"
        numbers.add(f"{num}{unit}")
        numbers.add(num)  # Also add raw number for looser matching
    return numbers


def char_ngrams(text: str, n: int = 3) -> Counter:
    """Generate character n-grams (shingling) for a text.

    Returns a Counter of n-gram frequencies for cosine similarity.
    """
    text = re.sub(r"\s+", " ", text.lower().strip())
    if len(text) < n:
        return Counter([text])
    return Counter(text[i:i + n] for i in range(len(text) - n + 1))


def cosine_similarity_ngrams(ngrams_a: Counter, ngrams_b: Counter) -> float:
    """Cosine similarity between two n-gram frequency vectors.

    Implemented with stdlib only (Counter + math).
    """
    if not ngrams_a or not ngrams_b:
        return 0.0

    # Dot product
    common_keys = set(ngrams_a.keys()) & set(ngrams_b.keys())
    dot_product = sum(ngrams_a[k] * ngrams_b[k] for k in common_keys)

    # Magnitudes
    mag_a = math.sqrt(sum(v * v for v in ngrams_a.values()))
    mag_b = math.sqrt(sum(v * v for v in ngrams_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot_product / (mag_a * mag_b)


def jaccard_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Jaccard similarity on token sets."""
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def fuzzy_match(requirement: str, candidate: str, threshold: float = 0.45) -> bool:
    """Multi-strategy similarity check between two strings.

    Combines four complementary approaches:
    1. Substring containment (fast path)
    2. SequenceMatcher ratio (edit distance — catches reworded requirements)
    3. Token Jaccard similarity (word overlap — catches reordered requirements)
    4. N-gram cosine similarity (character shingling — catches partial matches)
    5. Numeric agreement (requirements with numbers must agree on the numbers)

    A match on ANY strategy (above its threshold) is considered a match,
    BUT numeric disagreement can veto the match.
    """
    req_lower = requirement.lower().strip()
    cand_lower = candidate.lower().strip()

    # Fast path: substring containment
    if req_lower in cand_lower or cand_lower in req_lower:
        return True

    # Strategy 1: SequenceMatcher (Ratcliff/Obershelp)
    # Uses Python's stdlib difflib — good for edit distance on similar strings
    # Threshold 0.55 catches reworded but structurally similar sentences
    seq_ratio = SequenceMatcher(None, req_lower, cand_lower).ratio()

    # Strategy 2: Token Jaccard (word overlap, stopwords removed)
    req_tokens = tokenize(requirement)
    cand_tokens = tokenize(candidate)
    jaccard = jaccard_similarity(req_tokens, cand_tokens)

    # Strategy 3: Stemmed Token Jaccard (catches "rotatable"/"rotation",
    # "concurrent"/"concurrency", "configurable"/"configuration")
    req_stems = tokenize(requirement, stem=True)
    cand_stems = tokenize(candidate, stem=True)
    jaccard_stemmed = jaccard_similarity(req_stems, cand_stems)

    # Strategy 4: Character 3-gram cosine similarity
    # Good at catching partial phrase overlap and word reordering
    req_ngrams = char_ngrams(req_lower)
    cand_ngrams = char_ngrams(cand_lower)
    ngram_cosine = cosine_similarity_ngrams(req_ngrams, cand_ngrams)

    # Strategy 5: Numeric agreement check
    # If the requirement contains numbers, the candidate must contain
    # at least one matching number — otherwise it's likely a different requirement
    req_numbers = extract_numbers(requirement)
    cand_numbers = extract_numbers(candidate)

    if req_numbers and cand_numbers:
        # Both have numbers — check if any overlap
        numbers_agree = bool(req_numbers & cand_numbers)
        if not numbers_agree:
            # Numbers disagree — this is likely NOT the same requirement
            # Even if text is similar (e.g., "timeout: 5 min" vs "timeout: 30 min")
            return False

    # Combined decision: match if ANY text strategy exceeds its threshold
    return (
        seq_ratio >= 0.55
        or jaccard >= threshold
        or jaccard_stemmed >= (threshold - 0.05)
        or ngram_cosine >= 0.5
    )


# ---------------------------------------------------------------------------
# Section extraction from brief.md
# ---------------------------------------------------------------------------

def extract_brief_section(brief_text: str, section_name: str) -> list[str]:
    """Extract bullet items from a named section in brief.md.

    Uses exact heading match for short section names (like "IN")
    to avoid false matches on "Interface Contracts", "Enriched Context", etc.
    """
    lines = brief_text.splitlines()
    items = []
    in_section = False
    section_depth = 0

    for line in lines:
        stripped = line.strip()

        # Check for section heading
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip()
            heading_depth = len(stripped) - len(stripped.lstrip("#"))

            # For short section names (<=3 chars like "IN"), use exact match
            # to avoid matching "Interface", "Enriched", etc.
            if len(section_name) <= 3:
                matches = heading_text.strip().upper() == section_name.upper()
            else:
                matches = section_name.lower() in heading_text.lower()

            if matches:
                in_section = True
                section_depth = heading_depth
                continue
            elif in_section and heading_depth <= section_depth:
                in_section = False
                continue

        if in_section and (stripped.startswith("- ") or stripped.startswith("* ")):
            item = stripped[2:].strip()
            if item and not item.startswith("("):
                items.append(item)

    return items


# ---------------------------------------------------------------------------
# Coverage checks
# ---------------------------------------------------------------------------

def load_track_requirements(tracks_dir: str) -> dict[str, list[str]]:
    """Load requirements from each track's metadata.json."""
    tracks_path = Path(tracks_dir)
    track_reqs: dict[str, list[str]] = {}

    if not tracks_path.exists():
        return track_reqs

    for track_dir in sorted(tracks_path.iterdir()):
        if not track_dir.is_dir():
            continue
        meta_path = track_dir / "metadata.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            reqs = meta.get("requirements", [])
            if reqs:
                track_reqs[track_dir.name] = reqs

    return track_reqs


def load_requirements_map(map_path: str) -> dict[str, list[str]] | None:
    """Load optional Step 4g requirements map JSON."""
    path = Path(map_path)
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def check_brief_coverage(tracks_dir: str, track_reqs: dict[str, list[str]]) -> dict:
    """Check that each track's requirements appear in its brief.md Source Requirements."""
    tracks_path = Path(tracks_dir)
    present = []
    missing = []

    for track_id, reqs in track_reqs.items():
        brief_path = tracks_path / track_id / "brief.md"
        if not brief_path.exists():
            for req in reqs:
                missing.append({"track": track_id, "requirement": req, "reason": "brief.md not found"})
            continue

        brief_text = brief_path.read_text()
        brief_reqs = extract_brief_section(brief_text, "Source Requirements")

        for req in reqs:
            found = any(fuzzy_match(req, br) for br in brief_reqs)
            if found:
                present.append({"track": track_id, "requirement": req})
            else:
                missing.append({"track": track_id, "requirement": req, "reason": "not in Source Requirements"})

    return {"present": present, "missing": missing}


def check_scope_coverage(tracks_dir: str, track_reqs: dict[str, list[str]]) -> dict:
    """Check that each requirement in Source Requirements has a Scope IN item."""
    tracks_path = Path(tracks_dir)
    covered = []
    gaps = []

    for track_id, reqs in track_reqs.items():
        brief_path = tracks_path / track_id / "brief.md"
        if not brief_path.exists():
            continue

        brief_text = brief_path.read_text()
        scope_items = extract_brief_section(brief_text, "IN")

        for req in reqs:
            found = any(fuzzy_match(req, si, threshold=0.35) for si in scope_items)
            if found:
                covered.append({"track": track_id, "requirement": req})
            else:
                gaps.append({"track": track_id, "requirement": req, "section": "Scope IN"})

    return {"covered": covered, "gaps": gaps}


def check_product_coverage(
    product_reqs: list[str], track_reqs: dict[str, list[str]]
) -> dict:
    """Check that each product.md requirement appears in at least one track."""
    all_track_reqs = []
    for reqs in track_reqs.values():
        all_track_reqs.extend(reqs)

    mapped = []
    unmapped = []

    for preq in product_reqs:
        found = any(fuzzy_match(preq, tr) for tr in all_track_reqs)
        if found:
            # Find which tracks
            tracks = []
            for tid, reqs in track_reqs.items():
                if any(fuzzy_match(preq, r) for r in reqs):
                    tracks.append(tid)
            mapped.append({"requirement": preq, "tracks": tracks})
        else:
            unmapped.append(preq)

    return {"mapped": mapped, "unmapped": unmapped}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Validate requirements coverage across track briefs"
    )
    parser.add_argument(
        "--product-md",
        required=True,
        help="Path to product.md",
    )
    parser.add_argument(
        "--tracks-dir",
        default="conductor/tracks",
        help="Path to conductor tracks directory",
    )
    parser.add_argument(
        "--requirements-map",
        help="Optional path to Step 4g requirements map JSON",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    # Step 1: Extract requirements from product.md
    product_reqs = extract_requirements_from_product_md(args.product_md)

    # Step 2: Load track requirements
    if args.requirements_map:
        track_reqs = load_requirements_map(args.requirements_map)
        if track_reqs is None:
            print(f"Error: requirements map not found: {args.requirements_map}", file=sys.stderr)
            sys.exit(1)
    else:
        track_reqs = load_track_requirements(args.tracks_dir)

    # Step 3: Check product.md → tracks coverage
    product_coverage = check_product_coverage(product_reqs, track_reqs)

    # Step 4: Check tracks → briefs coverage
    brief_coverage = check_brief_coverage(args.tracks_dir, track_reqs)

    # Step 5: Check briefs → scope coverage
    scope_coverage = check_scope_coverage(args.tracks_dir, track_reqs)

    # Build report
    total_product = len(product_reqs)
    total_mapped = len(product_coverage["mapped"])
    total_unmapped = len(product_coverage["unmapped"])
    total_in_briefs = len(brief_coverage["present"])
    total_missing_from_briefs = len(brief_coverage["missing"])
    total_scope_covered = len(scope_coverage["covered"])
    total_scope_gaps = len(scope_coverage["gaps"])

    total_track_reqs = sum(len(r) for r in track_reqs.values())
    brief_pct = (total_in_briefs / total_track_reqs * 100) if total_track_reqs > 0 else 100.0
    scope_pct = (total_scope_covered / total_track_reqs * 100) if total_track_reqs > 0 else 100.0

    report = {
        "total_product_requirements": total_product,
        "mapped_to_tracks": total_mapped,
        "unmapped": product_coverage["unmapped"],
        "total_track_requirements": total_track_reqs,
        "present_in_briefs": total_in_briefs,
        "missing_from_briefs": brief_coverage["missing"],
        "scope_coverage": {
            "covered": total_scope_covered,
            "gaps": scope_coverage["gaps"],
        },
        "brief_coverage_pct": round(brief_pct, 1),
        "scope_coverage_pct": round(scope_pct, 1),
    }

    has_gaps = total_unmapped > 0 or total_missing_from_briefs > 0 or total_scope_gaps > 0

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        # Human-readable text output
        print("Requirements Coverage Report:")
        print(f"  Product.md requirements extracted: {total_product}")
        print(f"  Mapped to tracks: {total_mapped}/{total_product} ({100.0 if total_product == 0 else round(total_mapped / total_product * 100, 1)}%)")
        if total_unmapped > 0:
            print("\n  UNMAPPED requirements from product.md:")
            for req in product_coverage["unmapped"]:
                print(f"    - {req}")
        print(f"\n  Track requirements in briefs: {total_in_briefs}/{total_track_reqs} ({round(brief_pct, 1)}%)")
        if total_missing_from_briefs > 0:
            print("\n  MISSING from briefs (in metadata but not in brief Source Requirements):")
            for item in brief_coverage["missing"]:
                print(f"    - Track {item['track']}: \"{item['requirement']}\" — {item['reason']}")
        print(f"\n  Scope IN coverage: {total_scope_covered}/{total_track_reqs} ({round(scope_pct, 1)}%)")
        if total_scope_gaps > 0:
            print("\n  GAPS (requirement in brief but not in Scope IN):")
            for gap in scope_coverage["gaps"]:
                print(f"    - Track {gap['track']}: \"{gap['requirement']}\" — not in {gap['section']}")

        if not has_gaps:
            print("\n  All requirements covered.")
        else:
            print("\n  GAPS FOUND — review and fix before proceeding.")

    sys.exit(1 if has_gaps else 0)


if __name__ == "__main__":
    main()
