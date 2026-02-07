# Architect Design Amendment: Brief-Based Handoff Model

> **Amends:** architect-final-design.md
> **Sections affected:** 5 (Commands), 7 (metadata.json), 9 (Context Headers)
> **Reason:** Conductor already generates specs and plans interactively with developer input. Architect should provide architectural context, not duplicate that work.

---

## The Change

Architect no longer generates `spec.md` or `plan.md` per track. Instead it generates `brief.md` — a lightweight handoff artifact containing scope, key design decisions (as questions), cross-cutting constraints, and architectural notes.

When the developer runs `/conductor:implement`, Conductor reads the brief, uses it to ask informed design questions, and generates full spec.md and plan.md with developer input — exactly as it does natively, but now with architectural context it wouldn't otherwise have.

## What Architect Generates Per Track

```
conductor/tracks/{id}/
├── brief.md          ← Architect generates (scope, decisions, constraints)
├── metadata.json     ← Architect generates (state, complexity, wave, deps)
├── spec.md           ← Conductor generates at implementation time (interactive)
└── plan.md           ← Conductor generates from spec (interactive)
```

## Brief Format

```markdown
<!-- ARCHITECT CONTEXT | Track: {id} | Wave: {N} | CC: v{X.Y} -->
## Cross-Cutting Constraints
- {only constraints relevant to this track}
## Interfaces
- OWNS: {endpoints/events this track produces}
- CONSUMES: {endpoints/events from other tracks}
## Dependencies
- {track_id}: {what this track needs from it}
<!-- END ARCHITECT CONTEXT -->

# Track {NN}: {Name}

## What This Track Delivers
{one paragraph}

## Scope
IN:
- {what's included}

OUT:
- {what's excluded and why/where it lives}

## Key Design Decisions
These should be resolved with the developer during spec generation:
1. {decision area}: {option A} vs {option B}? {what trade-off?}
2. ...

## Architectural Notes
- {integration points with other tracks}
- {future track considerations ("design API with Track 08 split panes in mind")}
- {technical gotchas the implementing agent needs to know}

## Complexity: {S|M|L|XL}
## Estimated Phases: ~{count}
```

## Separation of Concerns

| Responsibility | Architect | Conductor |
|----------------|-----------|-----------|
| Identify all tracks | ✅ | |
| Sequence dependencies | ✅ | |
| Wave-based parallelism | ✅ | |
| Cross-cutting constraints | ✅ | |
| Interface contracts | ✅ | |
| Architecture research | ✅ | |
| Track scope (IN/OUT) | ✅ | |
| Key design decisions (questions) | ✅ | |
| Design decisions (answers) | | ✅ (asks developer) |
| Functional requirements | | ✅ (from developer answers) |
| Implementation plan + tasks | | ✅ (from spec) |
| TDD task structure | | ✅ |
| Implementation | | ✅ |

## Autonomous Mode (Agent Teams)

When tracks run via Agent Teams without a developer, Architect can optionally
pre-answer the Key Design Decisions with sensible defaults marked `[AUTO]`:

```markdown
## Key Design Decisions [AUTO-RESOLVED for autonomous execution]
1. Shell spawning: $SHELL with /bin/sh fallback [AUTO — standard convention]
2. Threading: dedicated reader only [AUTO — sufficient for single pane]
3. Cursor: all styles + blink [AUTO — product spec requires it]
```

The implementing agent treats `[AUTO]` answers as defaults it can override
if implementation reveals a better choice (logged as a discovery).
