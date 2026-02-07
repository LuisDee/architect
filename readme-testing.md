# Conductor ↔ Architect Contract Test Suite

Non-interactive tests that validate the file-format contracts between Architect (producer) and Conductor (consumer). Catches all four FAIL items from the walkthrough analysis without requiring an LLM in the loop.

## Quick Start

```bash
# Generate fixtures + run tests
python generate_fixtures.py && python test_contracts.py --fixtures ./fixtures

# Against a real project after running /conductor:setup + /architect:decompose
python test_contracts.py --project /path/to/my-project/conductor
```

## What It Tests

| Test Group | Checks | Catches |
|---|---|---|
| **tracks.md format** | `## [ ] Track:` blocks, `---` separators, required fields | Table format mismatch (CRITICAL) |
| **metadata.json schema** | `status` not `state`, `new` not `NOT_STARTED` | Field name/value mismatch (CRITICAL) |
| **brief.md structure** | ARCHITECT CONTEXT header, required sections, numbered decisions | Missing context header (CRITICAL) |
| **Brief pickup detection** | brief exists + spec missing → trigger, spec+plan exists → skip | implement.md would error (CRITICAL) |
| **Context header preservation** | spec.md carries forward verbatim ARCHITECT CONTEXT from brief.md | Hooks lose constraint info (CRITICAL) |
| **Cross-references** | tracks.md ↔ filesystem ↔ metadata.json consistency | Orphaned tracks, missing files |
| **Dependency graph** | All deps exist, no same/later-wave deps, no cycles | Wave sequencing errors |
| **State machine** | Valid status values, consistent with file state | Bad state transitions |

## What It Can't Test

These require an LLM in the loop or human review:

- Gap analysis question quality
- Design decision presentation quality  
- Spec generation content quality
- Plan phase breakdown appropriateness
- Natural language transitions between Conductor and Architect

## Fixture Structure

```
fixtures/
├── architect-output/          # Scenario 1: Good Architect output
│   ├── tracks.md              # Conductor-compatible format
│   └── tracks/
│       ├── 01_infra_scaffold/ # brief.md + metadata.json (no spec/plan)
│       ├── 02_auth_system/    
│       └── 03_data_layer/     # Has dependency on Track 01
├── conductor-manual/          # Scenario 2: Manual track (regression test)
│   └── tracks/
│       └── 99_manual_track/   # spec.md + plan.md (no brief) 
├── post-spec-gen/             # Scenario 3: After brief pickup
│   └── tracks/
│       └── 01_infra_scaffold/ # brief.md + spec.md (context preserved)
└── bad/                       # Scenario 4: Deliberately broken fixtures
    ├── tracks_table_format.md # Old table format → should FAIL
    ├── metadata_old_schema.json # state/NOT_STARTED → should FAIL  
    ├── brief_no_context_header.md # Missing ARCHITECT CONTEXT → should FAIL
    └── spec_lost_context.md   # Context not preserved → should FAIL
```

## Using Against a Real Project

After running `/conductor:setup` + `/architect:decompose`:

```bash
python test_contracts.py --project ./conductor
```

This validates:
- Architect wrote tracks.md in the right format
- All metadata.json files use Conductor's schema
- All briefs have proper ARCHITECT CONTEXT headers
- Brief pickup would trigger correctly for each track
- Dependency graph is valid
- Cross-references are consistent

Run it again after `/conductor:implement` to verify context header preservation.

## Integration with CI/Pre-commit

```bash
# In your project's pre-commit or CI:
cd architect-plugin/tests
python generate_fixtures.py
python test_contracts.py --fixtures ./fixtures
# Exit code: 0 = all contracts satisfied, 1 = critical failures
```

## Adding New Fixtures

1. Add fixture files in the appropriate scenario directory
2. If adding a new scenario, create a new directory under `fixtures/`
3. Add the scenario to `generate_fixtures.py` for reproducibility
4. The test runner auto-discovers tracks in any scenario directory
