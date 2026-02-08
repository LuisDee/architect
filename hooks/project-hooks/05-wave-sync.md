# Hook 05: Wave Sync

**When:** After marking a track as complete (all phases done, all tests passing).

## Purpose

Update track state, check if the current wave is fully complete, and if so, run the quality gate and advance to the next wave.

## Procedure

### 1. Update track metadata

Open `conductor/tracks/<your_track>/metadata.json`:
- Set `status` to `"completed"`
- Set `completed_at` to the current ISO-8601 timestamp

### 2. Update architecture (Living Architecture)

Run the architecture updater to extract decisions, generate ADRs, and patch architecture.md:

```bash
python scripts/architecture_updater.py --track-dir conductor/tracks/<your_track> --architect-dir architect --wave <N>
```

Or if running from the plugin:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/architecture_updater.py --track-dir conductor/tracks/<your_track> --architect-dir architect --wave <N>
```

Review the output:
- Note any ADRs generated (inform the developer)
- Note any architecture patches applied
- If drift warnings appear, flag them for developer review
- The changelog entry is appended automatically

**Tip:** Use `--dry-run` first if you want to preview changes before applying.

### 3. Check wave completion

Open `architect/execution-sequence.md` and find your wave. Are ALL tracks in this wave now "completed"?

**If NOT all complete:**
- Continue to the next track in the wave (or wait for other agents to complete their tracks)
- No further action needed from this hook

**If ALL tracks in the wave are complete:**
Proceed to Step 4.

### 4. Process pending discoveries

Run the merge discoveries script:
```bash
python scripts/merge_discoveries.py --discovery-dir architect/discovery --tracks-dir conductor/tracks
```

Or if running from the plugin:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/merge_discoveries.py --discovery-dir architect/discovery --tracks-dir conductor/tracks
```

Review the output:
- Note any duplicates (informational)
- Present any conflicts to the developer
- Note any urgency escalations

### 5. Run sync check

```bash
python scripts/sync_check.py --tracks-dir conductor/tracks --architect-dir architect
```

Or if running from the plugin:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/sync_check.py --tracks-dir conductor/tracks --architect-dir architect
```

Review drift warnings. If interface mismatches, CC version drift, or structural drift are found, they should be resolved before advancing.

### 6. Run wave quality gate

```bash
python scripts/validate_wave_completion.py --wave <N> --tracks-dir conductor/tracks --discovery-dir architect/discovery
```

Or if running from the plugin:
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/validate_wave_completion.py --wave <N> --tracks-dir conductor/tracks --discovery-dir architect/discovery
```

The quality gate checks:
- **All phases complete:** Every task checkbox checked in every track's plan.md
- **Tests passing:** Each track's `test_command` from metadata.json runs successfully
- **No blocking discoveries:** No BLOCKING-urgency files in `architect/discovery/pending/`
- **Patches applied:** All patches with `blocks_wave == next_wave` have status COMPLETE

### 7. Present results to developer

Show a clear summary:

```
Wave N Quality Gate Results:
  Track 01_infra:     PASS — all checks passed
  Track 13_observability: PASS — all checks passed

  Overall: PASS

  Ready to advance to Wave N+1.
```

Or if failures:
```
Wave N Quality Gate Results:
  Track 02_db:        PASS
  Track 05_frontend:  FAIL — 2/15 tasks unchecked
  Track 06_redis:     WARN — no test_command in metadata

  Options:
  1. Fix issues and re-run /architect-sync
  2. Waive specific checks (provide reason)
  3. Force-advance to Wave N+1
```

### 8. Advance to next wave (if gate passed or developer force-advances)

Present the next wave:
- List tracks in Wave N+1 with their complexity and dependencies
- Note which tracks can run in parallel
- If Agent Teams are available, suggest parallel assignment

Update `architect/execution-sequence.md` status for the completed wave.

### 9. For Agent Teams scenarios

If multiple agents worked on tracks in this wave:
- The lead agent (or the last agent to complete) runs this hook
- Discovery files from all agents are processed together (they're in separate files, no contention)
- The lead agent presents the quality gate results and coordinates the next wave assignment
