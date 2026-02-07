# Conductor Workflow

## How to Implement

Use `/conductor:implement` to execute tracks. Follow the brief.md for context, then use /conductor:implement to generate spec and plan.

## Track Selection

Pick the next track from the current wave in tracks.md. All tracks in a wave are independent and can be worked in any order, but all must complete before advancing to the next wave.

## Implementation Loop

For each track:
1. Read the track's brief.md (includes context header with cross-cutting constraints)
2. Conductor generates spec.md and plan.md interactively
3. Complete all tasks in each phase before moving to the next
4. Run validation at the end of each phase
5. After all phases complete, run final validation

## Quality Standards

- All tests must pass before marking a phase complete
- Code follows project conventions (ruff, mypy, eslint, prettier)
- No TODO/FIXME without a linked track or discovery

<!-- ARCHITECT:HOOKS — Read architect/hooks/*.md for additional workflow steps -->
