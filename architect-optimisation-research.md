# Multi-agent orchestration for a cross-platform Architect plugin

**The most viable path to parallelizing your Architect plugin across Claude Code and Gemini CLI is an MCP-first architecture with platform-specific sub-agent overlays.** Claude Code offers a mature, production-ready sub-agent system with native parallel execution, while Gemini CLI's sub-agents remain experimental with no parallel spawning. This asymmetry means your orchestration logic should live in a shared MCP server, with platform-native sub-agents layered on top for each environment. The good news: both platforms support an identical Agent Skills format and near-identical MCP configuration, giving you a realistic cross-platform foundation. The existing "Conductor" pattern in the Claude Code plugin ecosystem already solves the track decomposition problem — your Architect plugin can build directly on this proven architecture.

---

## Claude Code's sub-agent system is production-ready and parallel-capable

Claude Code provides a **fully stable sub-agent system** with three invocation mechanisms: automatic delegation (Claude routes based on description matching), explicit user invocation ("Use the code-reviewer subagent"), and programmatic spawning via the Agent SDK. Sub-agents are defined as Markdown files with YAML frontmatter, placed in `.claude/agents/` at the project or user level:

```markdown
---
name: track-analyzer
description: Analyzes a software component and produces a track brief. Use PROACTIVELY for project decomposition.
tools: Read, Grep, Glob, Bash
model: sonnet
---
You are a senior software architect. Analyze the specified component...
```

The configuration schema supports `name`, `description`, `tools` (comma-separated; inherits all if omitted), `model` (sonnet/opus/haiku/inherit), `permissionMode`, and `skills`. Three built-in sub-agents ship by default: **Explore** (Haiku, read-only codebase search), **Plan** (Sonnet, architecture planning), and **general-purpose** (Sonnet, full tool access). The `Task` tool must be in `allowedTools` to enable sub-agent spawning.

**Parallel execution is natively supported.** Multiple sub-agents can run simultaneously when prompted explicitly — phrases like "use parallel sub-agents" or "research these 5 areas in parallel" trigger concurrent spawning. Each sub-agent operates in its own context window, preventing cross-contamination. Results return to the main conversation for synthesis. The critical constraint is **no nesting**: sub-agents cannot spawn other sub-agents, so the orchestrator must directly manage all parallelism in a single fan-out.

Context passing follows a clean separation model. Sub-agents receive only their custom system prompt plus basic environment details (working directory, etc.) — they do **not** inherit the full parent conversation. The orchestrator passes relevant context through the task description, and results are summarized upon return. Skills with `context: fork` provide another mechanism for running work in isolated sub-agent contexts.

A brand-new **Agent Teams** feature launched February 5, 2026, takes this further with multi-instance collaboration: multiple Claude instances with independent context windows, shared task lists, and direct peer-to-peer messaging. This is experimental (enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) and carries roughly **5× token cost** for a 5-agent team, plus known issues with file locking and session resumption.

The **Claude Agent SDK** (`@anthropic-ai/claude-agent-sdk` for TypeScript, `claude_agent_sdk` for Python) enables fully programmatic sub-agent orchestration:

```typescript
import { query } from "@anthropic-ai/claude-agent-sdk";

for await (const message of query({
  prompt: "Decompose this project into tracks...",
  options: {
    model: "opus",
    allowedTools: ["Read", "Glob", "Grep", "Task"],
    agents: {
      "track-analyzer": {
        description: "Analyzes a component for track decomposition",
        prompt: "You are a senior architect...",
        tools: ["Read", "Grep", "Glob"],
        model: "sonnet"
      }
    }
  }
})) { /* handle messages */ }
```

Anthropic's official demos repository (`anthropics/claude-agent-sdk-demos`) includes a **Research Agent** that implements exactly the orchestrator-workers pattern: a lead agent decomposes topics, spawns parallel researcher sub-agents, and synthesizes findings.

---

## Gemini CLI sub-agents are experimental with critical parallel execution gaps

Gemini CLI's sub-agent system requires explicit opt-in via `settings.json`:

```json
{
  "experimental": { "enableAgents": true }
}
```

Custom agents follow a nearly identical Markdown-with-YAML format placed in `.gemini/agents/`:

```markdown
---
name: security-auditor
description: Specialized in finding security vulnerabilities in code.
kind: local
tools:
  - read_file
  - grep_search
model: gemini-2.5-pro
temperature: 0.2
max_turns: 10
timeout_mins: 5
---
You are a ruthless Security Auditor...
```

The YAML schema includes fields absent from Claude Code's format: `kind` (local/remote), `temperature`, `max_turns`, and `timeout_mins`. Built-in agents include the **Codebase Investigator** (deep code analysis), a **CLI Help Agent**, and a **Generalist Agent**. Extensions can bundle sub-agents in an `agents/` directory alongside `gemini-extension.json`.

**The parallel execution gap is the biggest cross-platform obstacle.** GitHub Issue #17749 explicitly tracks "Parallel Execution of Subagents" with 0 of 4 subtasks completed. The original sub-agent architecture proposal (Issue #3132) states sub-agents are "intended to be blocking." Tool calls execute sequentially, meaning spawning multiple sub-agents results in serial execution. Community workarounds exist — spawning separate `gemini` CLI processes via shell commands — but these lack coordinated state sharing.

Additional limitations compound this gap: sub-agents operate in **YOLO mode** (executing tools without user confirmation), there's **no shared state** between sub-agents (the only communication is the final report back to the main agent), and Issue #18064 reports agents can hang indefinitely on "Starting Agent Creation" in recent versions. Remote sub-agents via the **A2A (Agent-to-Agent) protocol** are also experimental.

Gemini CLI does support **remote sub-agents** via A2A protocol using `kind: remote` in the YAML frontmatter, which could enable delegation to external orchestration systems like Google ADK.

---

## Google ADK provides the orchestration patterns both platforms lack natively

Google's Agent Development Kit is an **open-source, code-first framework** (Python, TypeScript, Go, Java) that provides the most sophisticated multi-agent orchestration primitives available. While it doesn't integrate directly into either CLI tool, its patterns are the architectural blueprint your Architect plugin should follow, and it can be bridged to both platforms via MCP or A2A.

ADK's four agent types map directly to the Architect plugin's needs:

- **LlmAgent**: The workhorse. Wraps a model call with `name`, `model`, `instruction`, `tools`, `sub_agents`, and critically `output_key` — which automatically saves the agent's response to `session.state[key]` for downstream consumption.
- **SequentialAgent**: Executes sub-agents in order, passing the same `InvocationContext`. Data flows between steps via `output_key` → `{key}` template injection in instructions.
- **ParallelAgent**: Executes sub-agents **concurrently**, all sharing `session.state`. Each parallel child must write to distinct keys to avoid race conditions.
- **LoopAgent**: Iterative execution with configurable `max_iterations` and escape via `escalate`.

The fan-out/fan-in pattern maps perfectly to track brief generation:

```python
# Phase 1: Parallel analysis
parallel_research = ParallelAgent(
    name="AnalysisSwarm",
    sub_agents=[
        LlmAgent(name="StructureAnalyzer", output_key="structure_analysis", ...),
        LlmAgent(name="DependencyMapper", output_key="dependency_analysis", ...),
        LlmAgent(name="PatternIdentifier", output_key="pattern_analysis", ...)
    ]
)

# Phase 2: Sequential synthesis
synthesizer = LlmAgent(
    name="TrackDecomposer",
    instruction="Using {structure_analysis}, {dependency_analysis}, {pattern_analysis}, "
                "decompose into implementation tracks..."
)

pipeline = SequentialAgent(
    name="ArchitectPipeline",
    sub_agents=[parallel_research, synthesizer]
)
```

ADK's three inter-agent communication mechanisms provide flexibility: **shared session state** (scratchpad via `output_key`), **LLM-driven delegation** (auto-routing via `transfer_to_agent()`), and **AgentTool** (wrapping an agent as a callable tool where the parent retains control). For the Architect plugin, `AgentTool` is most appropriate — the orchestrator calls track generators as tools and retains full control over sequencing and aggregation.

---

## Framework patterns that solve the track generation problem

The research reveals four frameworks with directly applicable orchestration patterns, ranked by fit for the Architect plugin's specific need (batched generation of 10–20 track briefs):

**LangGraph's Send API** is the strongest match for dynamic map-reduce. Unlike static fan-out (where parallel branches are defined at design time), Send allows spawning N parallel agents at runtime based on the decomposition output:

```python
def route_to_track_generators(state):
    return [
        Send("generate_track_brief", {
            "track_name": track.name,
            "relevant_context": extract_relevant(state.analysis, track),
        })
        for track in state.tracks  # N determined at runtime
    ]
```

Results aggregate via reducer functions (e.g., `operator.add` for list concatenation). Parallel nodes execute in "supersteps" with **atomic failure semantics** — if one track brief fails, the entire superstep fails, but checkpointing preserves successful results for partial retry. Benchmarks show **137× speedup** for parallel vs. sequential execution in research tasks.

**CrewAI** offers a simpler abstraction with `kickoff_for_each` (running a crew for each item in a list) and `kickoff_async` (asynchronous execution). Its hierarchical process mode maps naturally to the Architect pattern: a manager agent decomposes work and delegates to specialist agents, with built-in memory sharing across the crew.

**Anthropic's own multi-agent research system** provides the most relevant production evidence. Their architecture uses an Opus 4 lead agent with Sonnet 4 sub-agents in an orchestrator-workers pattern. Key findings: multi-agent **outperformed single-agent by 90.2%** on research evaluations, token usage explains **80% of performance variance**, and agents use ~15× more tokens than chat. Their delegation principles are directly applicable: each sub-agent needs a clear objective, specified output format, tool/source guidance, and explicit task boundaries.

**AutoGen** (Microsoft) is less naturally suited to the Architect pattern due to its conversation-centric approach, but its nested chat pattern could enable sub-agent delegation for specific use cases.

---

## Context window management is the critical engineering challenge

The #1 technical risk for aggregating 10–20 sub-agent outputs is **context explosion**. Each sub-agent generates output that accumulates in the orchestrator's context. With 20 track briefs at even 500 tokens each, you're consuming 10K+ tokens of context just for results, before any synthesis reasoning occurs.

Five proven strategies address this, in order of impact:

**Context isolation** is the foundation. Each sub-agent should receive only its specific task context — not the full parent conversation or all other tracks' data. Claude Code enforces this by default (sub-agents get only their system prompt + task description). ADK achieves it through isolated subgraph state schemas.

**Structured, bounded outputs** prevent bloat at the source. Define a strict output schema for track briefs with field-level token limits. Since your output is "lightweight briefs, not full specs," enforce this constraint in each sub-agent's system prompt. A JSON schema with specific fields (name, description, dependencies, interfaces, estimated complexity) keeps outputs predictable and compact.

**Token budget allocation** treats context like memory. Budget explicitly: ~1K for system prompt, ~1K for conversation history, ~5K for aggregated track summaries, ~1K for output margin. Track token usage at each workflow step and alert at 80%+ utilization.

**Hierarchical summarization** condenses outputs into layered summaries. Rather than passing full sub-agent outputs to the synthesizer, have each sub-agent produce a one-paragraph summary alongside its full brief. The synthesizer works from summaries; full briefs are stored as artifacts.

**Progressive detail** uses a two-pass approach: first pass generates brief summaries of all tracks, second pass expands only tracks that need deeper analysis. This prevents upfront over-investment in tracks that may be merged or eliminated during dependency analysis.

---

## Cross-platform architecture should use MCP as the foundation

Both platforms support MCP with **near-identical configuration schemas**. The `mcpServers` object format — `command`, `args`, `env` — works on both with minimal adaptation. The divergence is in file location (`.mcp.json` for Claude Code, `settings.json` for Gemini CLI) and wrapper structure. An open feature request (Issue #13765) asks Gemini CLI to support `.mcp.json` directly.

The recommended architecture has three layers:

**Layer 1: MCP Server (shared core).** Define all Architect capabilities as MCP tools: `architect_analyze`, `architect_decompose`, `architect_generate_brief`, `architect_validate_graph`. The MCP server handles orchestration logic internally — this is critical because Gemini CLI can't do parallel sub-agent spawning, so the server must manage concurrency itself. The November 2025 MCP spec explicitly supports "server-side agent loops" where servers implement multi-step reasoning using standard primitives, plus experimental Tasks for async "call-now, fetch-later" patterns.

**Layer 2: Agent Skills (cross-platform instructions).** Both platforms support the **Agent Skills standard** with identical `SKILL.md` format. Define skills for each Architect workflow phase: `/architect-plan`, `/architect-decompose`, `/architect-review`. Skills work across Claude Code, Gemini CLI, Cursor, GitHub Copilot, Codex CLI, and Windsurf with a single codebase.

**Layer 3: Platform-specific sub-agents (native acceleration).** On Claude Code, define `.claude/agents/track-*.md` files that leverage native parallel spawning via the `Task` tool. On Gemini CLI, define `.gemini/agents/track-*.md` files that work sequentially but benefit from isolated context windows. The MCP server provides the orchestration backbone; platform-native sub-agents provide acceleration where available.

```
architect-plugin/
├── mcp-server/              # Shared orchestration core
│   └── index.ts             # MCP tools for decomposition, analysis, validation
├── skills/
│   ├── architect-plan/SKILL.md     # Cross-platform skill
│   ├── architect-decompose/SKILL.md
│   └── architect-review/SKILL.md
├── .claude/
│   ├── agents/              # Claude Code sub-agents (parallel-capable)
│   │   ├── codebase-analyzer.md
│   │   ├── track-generator.md
│   │   └── dependency-validator.md
│   └── .mcp.json            # Claude Code MCP config
├── .gemini/
│   ├── agents/              # Gemini CLI sub-agents (sequential)
│   │   ├── codebase-analyzer.md
│   │   └── track-generator.md
│   └── settings.json        # Gemini CLI MCP config
└── gemini-extension.json    # Gemini CLI extension manifest
```

The key capability differences to design around:

| Capability | Claude Code | Gemini CLI |
|---|---|---|
| Sub-agent maturity | Stable, production-ready | Experimental, opt-in required |
| Parallel sub-agents | Native via Task tool | Not supported (Issue #17749) |
| Sub-agent nesting | Single level only | Single level only |
| Context window | ~200K tokens | ~1M tokens (Gemini 2.5 Pro) |
| MCP config | `.mcp.json` (project root) | `settings.json` (nested) |
| Agent definition | `.claude/agents/*.md` | `.gemini/agents/*.md` |
| Agent Skills | `.claude/skills/` | `.gemini/skills/` (identical format) |
| YOLO mode concern | No (permission controls) | Yes (sub-agents bypass confirmation) |

---

## The Conductor pattern already solves track decomposition

The Claude Code plugin ecosystem has converged on a **"Conductor" pattern** that directly maps to your Architect plugin's requirements. The most complete implementation (in the `wshobson/agents` repository with 27.9K stars) decomposes work into tracks with this structure:

```
conductor/
├── product.md             # Product vision and context
├── tech-stack.md          # Technology choices
├── workflow.md            # Development practices
├── tracks.md              # Master track registry
└── tracks/
    └── <track_id>/
        ├── spec.md        # Requirements specification (WHAT)
        ├── plan.md        # Phased task breakdown (HOW)
        └── metadata.json  # Track metadata and dependencies
```

The workflow follows: `/conductor:setup` (establish project context) → `/conductor:new-track` (generate spec.md and hierarchical plan.md with phases → tasks) → `/conductor:implement` (execute tasks, updating status: `[ ] → [~] → [x]`) → `/conductor:revert` (git-aware logical undo by track/phase/task). Multiple independent implementations exist (fcoury/conductor, lackeyjb/claude-conductor with background agent support, ShalomObongo/claude-conductor with interactive Q&A).

For the Architect plugin specifically, the recommended execution flow combines Conductor's track structure with Anthropic's orchestrator-workers pattern:

**Phase 1 — Parallel Analysis** (fan-out). Spawn 3–4 Explore sub-agents simultaneously to analyze the codebase from different angles: structure/module mapping, dependency analysis, pattern identification, and technology stack assessment. Each returns a brief (~300–500 tokens). On Gemini CLI, these run sequentially but benefit from independent context isolation and Gemini's larger context window.

**Phase 2 — Sequential Synthesis** (single agent). The orchestrator aggregates analysis briefs and decomposes the project into 10–20 tracks with a dependency DAG. This step is inherently sequential — it must see all analysis before making decomposition decisions. Output: a `tracks.md` registry plus skeleton `metadata.json` for each track.

**Phase 3 — Batched Brief Generation** (map-reduce). The most parallelizable phase. For each track, spawn a sub-agent with only the track's description and relevant analysis subset. Each generates a lightweight brief (spec.md) in isolation. On Claude Code, these run in parallel via `Task` tool. On Gemini CLI, the MCP server can manage concurrency internally or they run sequentially.

**Phase 4 — Validation** (sequential). A judge agent validates completeness, checks for interface mismatches between tracks, verifies the dependency graph is acyclic, and sequences tracks into parallelizable execution waves.

---

## Conclusion

The cross-platform Architect plugin is feasible today, with a clear architecture: MCP server for shared orchestration logic, Agent Skills for cross-platform instructions, and platform-native sub-agents for acceleration. Claude Code is the stronger platform for this use case — its parallel sub-agent execution, mature plugin system, and Agent SDK provide everything needed for production deployment. Gemini CLI brings a **1M-token context window** advantage (valuable for analyzing large codebases in a single pass) but its sequential-only sub-agents and experimental status mean the plugin will run slower there.

Three design decisions matter most. First, **keep sub-agent outputs small and structured** — the "briefs not specs" approach is exactly right, and enforcing output schemas prevents context explosion during aggregation. Second, **put orchestration in the MCP server, not in platform-native agents** — this ensures the core logic works identically on both platforms, with platform-native sub-agents providing optional parallelism rather than required functionality. Third, **adopt the Conductor track structure** rather than inventing a new format — it's battle-tested across multiple community implementations and maps directly to your decomposition model of tracks, dependency graphs, and parallelizable waves.
