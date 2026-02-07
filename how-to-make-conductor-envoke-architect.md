The change is in Conductor's setup command. After it writes product.md, tech-stack.md, and workflow.md, instead of checking for tracks and prompting, it should automatically invoke /architect:decompose:
markdown## Post-Setup Behavior

After setup completes successfully (product.md, tech-stack.md, workflow.md exist):

1. Check if `tracks/` directory exists and has any track subdirectories
2. If NO tracks exist:
   - Do NOT ask the user if they want to create a track
   - Instead, announce: "Project context established. Running architectural 
     decomposition to generate track briefs..."
   - Invoke `/architect:decompose` automatically
3. If tracks already exist:
   - Announce: "Project context updated. X existing tracks found."
   - Show track summary via `/architect:status`
```

The key insight is that **Conductor should never create tracks directly**. That's Architect's job. Conductor's `new-track` command becomes a fallback for adding individual tracks later, not the primary flow.

The sequence becomes:
```
User runs /conductor:setup
  → Interactive Q&A (product vision, tech stack, workflow)
  → Writes product.md, tech-stack.md, workflow.md
  → Detects empty tracks/
  → Automatically runs /architect:decompose
      → Reads product.md, tech-stack.md (Architect's input)
      → Gap analysis questions (if needed)
      → Generates track briefs
      → Writes tracks/ directory structure
      → Builds dependency graph
      → Sequences waves
  → Returns to Conductor context
  → "Decomposition complete. 14 tracks generated across 4 waves.
     Run /conductor:implement to begin Wave 1."
This means adding one clause to the Conductor setup command's prompt — something like:
markdownAfter writing all project context files, if the tracks/ directory is empty 
or does not exist, immediately run the architect-decompose command. Do NOT 
ask the user whether they want to create tracks. The architectural 
decomposition is the natural next step after project setup and should 
proceed automatically.
