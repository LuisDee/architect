# Research Findings

> **Date:** 2026-02-08
> **Purpose:** Synthesize research on best practices for LLM-based architecture tooling, informing Architect v2.1 design decisions.

---

## 1. LLM Agent Orchestration Patterns

### 1.1 Multi-Agent Architecture Patterns

Five core orchestration patterns emerge from recent research, each with distinct applicability to Architect:

| Pattern | Description | Architect Applicability |
|---------|-------------|------------------------|
| **Fan-Out/Fan-In** | Orchestrator dispatches parallel workers, aggregates results | Already used: pattern-matcher + codebase-analyzer in parallel |
| **Orchestrator-Workers** | Central coordinator delegates to specialized workers | Current architect-expert → sub-agents model |
| **Plan-and-Execute** | Separate planning from execution; different model tiers | New opportunity: frontier model plans, cheaper models execute briefs |
| **Evaluator-Optimizer** | Iterative refinement with feedback loops | Potential for track brief quality verification |
| **Hierarchical Decomposition** | Breaking tasks exceeding single context windows | Direct match for feature → tracks decomposition |

**Key finding:** Multi-agent orchestration achieves **100% actionable recommendation rates** vs. 1.7% for single-agent approaches, with 80x improvement in specificity and 140x improvement in correctness for structured decision domains (C# Corner, 2025).

**Heterogeneous model allocation** is a cost-effective technique: frontier models for complex reasoning (architect-expert), mid-tier for standard tasks (brief-generator), smaller models for high-frequency execution. This can reduce costs by up to 90%.

### 1.2 Sub-Agent vs. Inline Reasoning Decision Framework

**Use sub-agents when:**
- Tasks can be cleanly divided without interdependencies
- Exploration is extensive but only summaries are needed upstream
- Different specializations require different context (reference docs vs. codebase vs. templates)
- Total tokens needed exceed a single window

**Use inline reasoning when:**
- Tasks are tightly coupled and require shared state
- Communication overhead between agents would exceed context savings
- Reasoning chain requires continuous access to evolving intermediate results

**Counter-finding (JetBrains Research):** LLM summarization causes trajectory elongation (~15% longer agent runs). **Observation masking** — replacing older tool outputs with placeholders while preserving reasoning — often matches or exceeds summarization effectiveness while being cheaper.

### 1.3 Context Window Management

Five validated strategies, in priority order:

1. **Compaction** — Summarize conversation history when approaching limits, preserving architectural decisions while discarding redundant tool outputs (Anthropic)
2. **Structured note-taking** — Write persisted notes (JSON preferred over Markdown) outside the context window for later retrieval (Anthropic)
3. **Progressive disclosure** — Maintain lightweight identifiers rather than loading all data upfront; retrieve dynamically at runtime (Anthropic)
4. **Tool result clearing** — Remove redundant tool outputs from message history after key information has been extracted (JetBrains)
5. **Repository overviews** — Pre-generated summaries containing project structure, key packages, build commands (Factory.ai)

**Critical insight:** "Treat context the way operating systems treat memory and CPU cycles: as finite resources to be budgeted, compacted, and intelligently paged." — Factory.ai

### 1.4 Handling Ambiguity in Requirements

Three approaches with decreasing automation:

1. **Clarifier-Planner-Implementor pattern** — Multi-agent framework where a Clarifier produces critical question-answer pairs that resolve underspecification before planning begins (EMNLP 2025)
2. **Two-level meta-reasoning** — (1) Detect ambiguity exists, (2) select most informative action to resolve it (Amazon Science)
3. **`ask_question` tool** — Give agents a clarification tool that pauses execution when slot values are missing; agents achieve 0.92 accuracy in ambiguity detection

**Limitation:** LLM ambiguity detection is fundamentally a "concept missing" problem — the model may not know what it doesn't know, making self-detection unreliable for novel domains (arXiv, 2025).

**Recommendation for Architect:** Implement a pre-decomposition clarification phase. When `product.md` is underspecified, prompt the developer with targeted questions before generating tracks.

---

## 2. Structured Prompting for Code Architecture

### 2.1 Structured Chain-of-Thought (SCoT)

SCoT outperforms standard Chain-of-Thought by up to **13.79%** in code generation tasks. The key: use programming structures (sequential, branch, loop) as reasoning scaffolds.

**Recommended scaffold for architecture analysis:**
1. Define I/O structure (what the system receives/produces)
2. Identify sequential flows (happy paths)
3. Identify branch points (decisions creating divergent paths)
4. Identify loops (recurring patterns, retry logic)
5. Map cross-cutting concerns spanning multiple flows

**Applicability:** SCoT provides a more reliable reasoning scaffold than free-form analysis for generating consistent decompositions across different project types.

### 2.2 Few-Shot Learning for Scope Decisions

Anthropic guidance: "Curate diverse, canonical examples rather than exhaustive edge-case lists."

**Recommended examples for single-vs-multi-track decisions:**
- Single track: "Add CSV export" — self-contained, no dependencies
- Multiple tracks: "Add user roles" — needs auth, UI, API changes with clear dependency ordering
- Edge case (keep single): "Add dark mode" — seems multi-file but is a single coherent concern

**Caution:** Few-shot examples create anchoring bias. Include brief rationale with each example explaining *why* the scoping decision was made.

### 2.3 Structured Output Schemas

Clear JSON schemas between agent handoffs minimize context bleed and enable automated validation. Recommended schema for scope decisions:

```json
{
  "track_id": "string",
  "scope_decision": "single|multi",
  "confidence": 0.0-1.0,
  "reasoning": "string",
  "dependencies": ["track_id"],
  "estimated_complexity": "XS|S|M|L|XL",
  "cross_cutting_concerns": ["string"]
}
```

### 2.4 Self-Consistency and Verification

**Confidence-Informed Self-Consistency (CISC)** adds a self-assessment step where a confidence score is assigned to each reasoning path, then selects final answer via weighted majority vote. Reduces required reasoning paths by over 40% (ACL 2025).

**Practical self-verification checklist:**
1. Does every feature in `product.md` map to at least one track?
2. Are there circular dependencies in the track ordering?
3. Does estimated total complexity match project scope expectations?
4. Are cross-cutting concerns addressed consistently across tracks?

---

## 3. Living Architecture Documentation

### 3.1 Architecture Decision Records (ADRs)

Current best practices (AWS, Google Cloud):
- **One decision per ADR** — avoid combining multiple decisions
- **Immutability principle** — accepted ADRs become immutable; new insights create superseding ADRs
- **Context/Decision/Consequences template** (Michael Nygard framework) — usually sufficient
- **Collaborative review** — senior architects initiate, all developers contribute

**Automated ADR generation pipeline:**
1. Code changes trigger LLM with relevant diff
2. LLM drafts ADR in Markdown with consistent structure
3. ADR committed for review
4. Tooling: `log4brains` for management/publication, `adr-agent` for generation

### 3.2 Docs-as-Code Synchronization

Key tools and approaches:
- **Swimm** — Living docs that stay in sync with code via IDE integration
- **DocuWriter.ai** — Git repo sync that auto-updates docs on merge
- **Mintlify** — AI-generated documentation from codebase

**Core insight:** Build documentation updates into CI/CD pipelines, making them "as routine and reliable as running tests." Generated architecture artifacts should be versioned, diffable, and validated.

### 3.3 Terminal-Based Visualization

| Tool | Type | Strengths | Limitations |
|------|------|-----------|-------------|
| **Mermaid** | Text-based diagrams | Renders in GitHub/GitLab, supports flowcharts/sequence/architecture/state diagrams, CLI export to SVG/PNG | Limited terminal rendering |
| **Structurizr DSL** | C4 model diagrams | Domain-specific language, version-controlled, CLI rendering | Requires separate viewer |
| **Swark** | LLM-generated Mermaid | Auto-generates from code, fixes cycles automatically | Dependent on LLM accuracy |

**Practical recommendation:** Generate Mermaid dependency graphs as decomposition artifacts. They render natively on GitHub and are reviewable alongside track briefs.

**Limitation:** Pure terminal rendering of diagrams remains limited to ASCII art. Most approaches require a browser or image viewer for actual visualization.

---

## 4. Pattern Detection in Codebases

### 4.1 LLM Design Pattern Recognition — Current Accuracy

**Sobering data:**
- Best LLMs (GPT-4o, Llama-31-70B) achieve only **38.81% overall accuracy** in GoF design pattern classification (Springer 2025)
- Code2Vec achieves mean F1-score of 0.78 using embedding-based approaches
- Claude achieves highest Pattern Implementation Quality Score of **89.51** (for *implementing* patterns, not detecting them)

**Key challenge:** Design patterns are "embedded implicitly within the code's structure and behavior, rather than being explicitly annotated."

**Recommended approach:** Focus on **role-based detection** — recognizing the roles classes play within pattern instances (e.g., "this class acts as a factory," "this module acts as an observer hub") rather than trying to classify exact GoF patterns. Role-based detection is more robust to implementation variations.

### 4.2 Cross-Cutting Concern Detection

**Fan-in analysis technique:** Identify functions/modules called from many different locations. High fan-in suggests cross-cutting behavior.

**Detection heuristics for codebase-analyzer:**
1. Imports appearing in >50% of modules
2. Function calls appearing across >3 distinct architectural boundaries
3. Patterns matching known categories: logging, auth, validation, error handling, caching, metrics, serialization
4. Report as constraints for track briefs

### 4.3 Promoting Local Patterns to Global Conventions

**Pipeline:**
1. `codebase-analyzer` identifies repeated local patterns
2. `pattern-matcher` validates alignment with known architectural patterns
3. `architect-expert` decides whether to promote to cross-cutting constraint
4. Promoted patterns become requirements in all track briefs

**Key limitation:** LLMs cannot reason reliably across very large codebases (>1M tokens). The modular sub-agent approach — each agent seeing a bounded slice — is the correct mitigation.

---

## 5. Feature Decomposition Best Practices

### 5.1 Decomposition Strategies

**Two granularity levels:**
- **Coarse-grained** — Few large tracks, minimal management overhead. Best for small projects or tightly coupled features.
- **Fine-grained** — Many small tracks, high parallelism potential. Best for team-based execution on larger projects.

**DAG-based task decomposition:** Orchestrator produces a Directed Acyclic Graph with task nodes and dependency edges. Independent tasks run in parallel; dependent tasks wait for predecessors.

**Practical heuristic:**
1. Parse product.md for distinct user-facing capabilities
2. For each capability: identify data model, API, UI, and cross-cutting changes
3. Group atomic changes (cannot be deployed independently) into a single track
4. Split independently verifiable changes into separate tracks
5. Build dependency edges: data model → API → UI (typical layered dependency)

### 5.2 Dependency Categories

Four types of track dependencies:

| Type | Description | Example |
|------|-------------|---------|
| **Data** | Track B needs schemas/models from Track A | User model → user roles track |
| **API** | Track B needs endpoints from Track A | Auth endpoints → admin dashboard |
| **Infrastructure** | Track B needs services/configs from Track A | Database setup → data migration |
| **Knowledge** | Track B's decisions depend on patterns from Track A | Auth patterns → all secured tracks |

### 5.3 Wave Sequencing

**Rolling wave planning:** Near-term work planned in detail; future phases outlined at higher level. As project progresses, plans refine in waves from coarse to fine.

**Applicability:** Track briefs for Wave 1 can be fully detailed. Waves 2-3 are progressively less detailed, refined after Wave 1 patterns are established. This reduces wasted effort on briefs that may change due to Wave 1 discoveries.

**Trade-off:** Full upfront planning provides better cross-track consistency. High-uncertainty projects benefit from rolling waves; low-uncertainty projects benefit from full planning.

### 5.4 Complexity Estimation

- T-shirt sizing (XS/S/M/L/XL) is more appropriate than numeric story points for architecture-level estimation
- Provide few-shot examples of tracks with known complexity levels
- Use structured output: `{"track_id": "auth", "complexity": "L", "factors": ["new data model", "external integration", "security requirements"]}`
- Generate 3 independent estimates and flag disagreements for human review
- **Caution:** LLMs exhibit anchoring bias with reference estimates; avoid providing previous estimates in prompt context

---

## 6. Cross-Cutting Recommendations

Synthesized from all research areas, ordered by impact and implementation feasibility:

| # | Recommendation | Research Basis | Impact | Effort |
|---|---------------|----------------|--------|--------|
| 1 | **Clarification-before-decomposition gate** | EMNLP 2025 ambiguity handling | High | Medium |
| 2 | **Mermaid dependency visualization** | Mermaid + Swark tools | High | Low |
| 3 | **JSON-based inter-agent handoffs** | Structured output schemas research | High | Low |
| 4 | **Lightweight ADR generation** | AWS/Google ADR best practices | Medium | Medium |
| 5 | **Fan-in cross-cutting detection** | Fan-in analysis + import frequency | Medium | Medium |
| 6 | **Context budget accounting** | Anthropic + JetBrains context management | Medium | Low |
| 7 | **Observation masking over summarization** | JetBrains research (15% trajectory savings) | Medium | Low |
| 8 | **Role-based pattern detection** | Springer 2025 (38.81% GoF accuracy is too low) | Medium | High |
| 9 | **SCoT prompting for analysis** | SCoT research (13.79% improvement) | Low-Medium | Low |
| 10 | **Rolling wave brief detail** | Rolling wave planning | Low | Low |

---

## Sources

**LLM Agent Architecture:**
- [LLM Agent Orchestration Patterns — C# Corner](https://www.c-sharpcorner.com/article/llm-agent-orchestration-patterns-architectural-frameworks-for-managing-complex/)
- [AI Agent Design Patterns — Microsoft Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Effective Context Engineering — Anthropic](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective Harnesses for Long-Running Agents — Anthropic](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Efficient Context Management — JetBrains Research](https://blog.jetbrains.com/research/2025/12/efficient-context-management/)
- [The Context Window Problem — Factory.ai](https://factory.ai/news/context-window-problem)

**Structured Prompting:**
- [Structured Chain-of-Thought Prompting — arXiv](https://arxiv.org/abs/2305.06599)
- [Confidence-Informed Self-Consistency — ACL 2025](https://aclanthology.org/2025.findings-acl.1030/)
- [Prompt Chaining Guide — Maxim](https://www.getmaxim.ai/articles/prompt-chaining-for-ai-engineers-a-practical-guide-to-improving-llm-output-quality/)

**Living Architecture Documentation:**
- [ADR Best Practices — AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/master-architecture-decision-records-adrs-best-practices-for-effective-decision-making/)
- [Architecture Decision Records — Google Cloud](https://docs.google.com/architecture/architecture-decision-records)
- [adr-agent — GitHub](https://github.com/macromania/adr-agent)
- [log4brains — GitHub](https://github.com/thomvaill/log4brains)
- [Mermaid Architecture Diagrams](https://mermaid.ai/open-source/syntax/architecture.html)
- [Swark — GitHub](https://github.com/swark-io/swark)

**Pattern Detection:**
- [Design Pattern Recognition Study — Springer 2025](https://link.springer.com/article/10.1007/s10664-025-10625-1)
- [LLM-Based Design Pattern Detection — arXiv 2025](https://arxiv.org/abs/2502.18458)
- [Fan-In Analysis for Cross-Cutting Concerns — arXiv](https://arxiv.org/pdf/cs/0609147)
- [LLM-Driven Code Refactoring — ICSE 2025](https://conf.researchr.org/details/icse-2025/ide-2025-papers/12/LLM-Driven-Code-Refactoring-Opportunities-and-Limitations)

**Feature Decomposition:**
- [Dynamic Task Decomposition — arXiv 2024](https://arxiv.org/html/2410.22457v1)
- [Rolling Wave Planning — ProjectManager.com](https://www.projectmanager.com/blog/rolling-wave-planning)
- [LLMs for Software Estimation — MDPI 2025](https://www.mdpi.com/2076-3417/15/24/13099)
- [Ambiguity Handling in LLM Agents — EMNLP 2025](https://aclanthology.org/2025.emnlp-industry.163.pdf)
