# 🏗️ Solution Architecture: ClawBoi v2 — Personal AI That Does Things

## Architecture Overview

ClawBoi v2 is not a new system — it is four new SKILL.md files and one context-file update deployed into the OpenClaw workspace that already runs on the VPS with Telegram I/O and 50+ skills. The mental model is a **skill pipeline**: freeform diary text enters through Telegram, flows through processing → storage → reflection → action proposal, and exits as either a stored memory entry, a challenged assumption, or a dispatched action through an existing skill like apple-reminders or himalaya. No new daemons, no new repos, no build step.

The key architectural insight is that the intelligence layer is **prompt composition, not code composition**. Each skill is a SKILL.md file that describes what the agent should do, what context to read, and what tools to use. The agent orchestrates skill selection based on input type — a diary-like message triggers the processing pipeline; a `/reflect` command triggers deep analysis. The skills communicate through the filesystem: diary-process writes a memory entry, pattern-detect reads memory entries, reality-check reads both the current entry and historical entries to compute deltas. The shared medium is the established `2026-*.md` memory format already in `~/.openclaw/workspace/memory/`.

The second insight is that the BullshitBench judge pattern transfers to personal reflection through a single pivot: replace the planted-nonsense anchor with a memory-history delta anchor. Instead of asking "did the model catch the lie we planted," the personal version asks "did I catch the contradiction between what I said today and what I said three weeks ago." The scoring mechanism (0/1/2 per challenged assumption) and the calibration guardrail (challenge rationalizations, preserve experiences) carry over directly. This is an adaptation of a proven prompt pattern, not a novel system.

## Design Principles

| Principle | Application in ClawBoi v2 |
|-----------|---------------------------|
| **P6 — Skills First** | All four capabilities ship as SKILL.md files in the OpenClaw workspace. No plugin graduation unless skills hit a real limit. No build step, no compiled artifacts, iterate by editing markdown. |
| **P4 — No Speculative Abstractions** | One user, one channel (Telegram), one runtime (OpenClaw). No generic "reflection framework" — each skill does one concrete thing. No plugin registry for four skills. |
| **P1 — Adapter Boundary** | Skills never call Claude CLI or external tools directly. They describe tool invocations; OpenClaw's runtime handles execution. Action dispatch routes through existing skill names, never raw subprocess calls. |
| **P6 — References as Source of Truth** | Skills reference `MEMORY.md`, `USER.md`, and `SOUL.md` for identity and context rather than duplicating that content inline. The BS-detection calibration rules live in one place and are referenced by both the auto-light and full-analysis modes. |
| **P6 — Channel-Aware Output** | Every skill output must fit Telegram's 4096-character limit. Pattern detection and reality check must compress findings into ranked, terse summaries — not essays. |
| **P2 — Thin Layer (adapted)** | Skills contain no business logic — they are declarative descriptions of what the agent should do. The agent interprets; the skill describes. |

## Component Design

### Diary Processing Skill

**Purpose**: Convert freeform Telegram text into a structured memory entry in the established format. This is the entry point for the entire pipeline — every downstream skill depends on diary entries existing in a consistent, parseable shape.

**Boundary**: Accepts raw text (any length, any structure). Outputs a memory entry file at `~/.openclaw/workspace/memory/` in the `2026-*.md` format. Supports optional hashtag annotations (`#win`, `#struggle`) but does not require them. Extraction covers mood, events, wins, struggles, and tomorrow's stated priority.

**Key constraint**: The skill must produce output that is both human-readable (Sam reviews memory files directly) and machine-parseable (pattern detection reads them programmatically). The existing `2026-*.md` format already satisfies both — the skill writes to it, not a new schema.

**Input model**: Freeform, not structured. The friction cost of a form-like interface on Telegram would suppress daily usage. The AI extraction step absorbs the ambiguity cost instead — a better trade-off for a single-consumer tool where the consumer's writing style is learnable from 20+ existing entries.

### Pattern Detection Skill

**Purpose**: Read memory history and surface what a person inside their own head cannot see — stalled goals, recurring statements, priority drift, and contradictions across entries. This is the "rearview mirror" that turns a pile of diary entries into longitudinal self-awareness.

**Boundary**: Reads memory entries from the filesystem. Does not write new entries — it produces a pattern report as Telegram output. Operates in two modes: **inline** (triggered as part of the diary pipeline, scoped to the last 2–4 weeks, optimized for speed) and **deep** (triggered by `/reflect` or cold-start bootstrap, reads the full available history within the timeout window).

**Key constraint**: The Claude CLI subprocess timeout is 3600 seconds. Pattern detection must complete within this ceiling, which means the skill must specify a memory window strategy. For inline mode, the window is the most recent 14–28 days of entries. For deep mode, the skill reads all available entries but must declare a bail-out heuristic — if context assembly exceeds a token threshold, it summarizes older entries rather than passing them verbatim. The window expands over time as entries accumulate; the architecture must not assume a fixed corpus size.

**Stalled-goal detection**: A goal is flagged as stalled when it appears in 3+ entries across 2+ weeks with no corresponding action taken or progress reported. The count threshold and time window are declared in the skill, not hardcoded in a config file — this is a single-consumer tool, and the thresholds will be tuned by editing the SKILL.md directly.

### Reality Check Skill

**Purpose**: Apply calibrated skepticism to the user's own reasoning, adapted from the BullshitBench judge prompt pattern. This is not a therapist — it is a scoring system that distinguishes rationalizations from facts and assigns a confidence-degradation score to challenged assumptions.

**Boundary**: Reads the current diary entry (from diary-process output) and relevant memory history (from pattern-detect's context). Produces a set of challenged assumptions, each scored 0/1/2, with a one-line rationale per challenge. Operates in two modes: **auto-light** (runs on every diary entry, challenges at most 1–2 assumptions, completes fast, stays within Telegram's character limit as part of the combined diary response) and **full** (triggered by `/reflect`, challenges all detected assumptions with deeper memory-anchored reasoning).

**Adaptation from BullshitBench**: The BullshitBench judge works by planting a known falsehood and measuring whether the pipeline caught it. The personal version has no planted element — instead, it anchors on **memory-history deltas**: the difference between what was said today and what the history shows. Five anchor types map directly from the brain dump: wish-vs-plan (repeated without progress), avoidance (planning around bottleneck instead of through it), contradiction (flip-flopping across entries), feeling-as-fact (strategy built on mood), and sunk-cost (continuing due to investment, not results). Each anchor type has a detection heuristic described in the skill and a scoring rubric: 0 = no issue detected, 1 = possible rationalization worth examining, 2 = clear contradiction or pattern with supporting evidence from prior entries.

**Calibration guardrail**: The skill must preserve the BullshitBench distinction between user data and domain claims. Experiences ("I had a bad week"), measurements ("revenue was CHF 400"), and external facts ("FINMA has 1486 licensed firms") are not challengeable. Rationalizations ("I'll start next week"), plans ("this will definitely work because..."), and causal claims ("the reason I haven't shipped is...") are fair game. This guardrail is the difference between a useful sharp-friend and a demoralizing critic — it is the most important prompt-engineering constraint in the system.

### Action Dispatch Skill

**Purpose**: Convert reflection output into concrete, executable actions routed through existing OpenClaw skills. This closes the loop from thought to action — the reason this system exists.

**Boundary**: Takes processed diary output (validated wins, challenged assumptions, detected patterns) and proposes 1–3 concrete actions. Each action maps to an existing OpenClaw skill by name: `apple-reminders` for follow-ups and deadlines, `himalaya` for email drafts and sends. The skill proposes actions in natural language and **confirms before executing** — no autonomous dispatch. The confirmation happens inline in the Telegram conversation.

**Routing model**: The skill maintains a simple mapping of action types to OpenClaw skill names. Follow-up reminders → `apple-reminders`. Email drafts → `himalaya`. The mapping is declared in the SKILL.md, not in a config file or registry. When a new skill becomes available (e.g., if wacli is verified working), the mapping is updated by editing one line in the SKILL.md. No plugin system, no dynamic discovery — explicit is better for a four-skill system.

**Confirm-before-execute**: Every proposed action requires explicit user confirmation in the Telegram thread before the skill is invoked. This is a non-negotiable safety constraint. The cost is one extra message per action; the benefit is that the system never sends an email or sets a reminder the user didn't approve. For a personal assistant that touches email and messaging, trust requires a human in the loop.

### Cold-Start Bootstrap

**Purpose**: One-time pass of pattern detection against the existing 20+ memory entries to establish a baseline. Without this, the pattern detector has no historical context on its first real run and cannot detect stalled goals or contradictions.

**Boundary**: This is not a separate skill — it is a single invocation of the pattern-detect skill in deep mode against the full memory corpus. The output is a baseline pattern report stored as a reference file in the workspace (not as a memory entry — it is metadata about memory, not memory itself). Subsequent pattern-detect runs compare against this baseline to identify new patterns vs. known ones.

**One-time nature**: The bootstrap runs once during initial setup. It is not a recurring job. As the pattern-detect skill runs on each diary entry (inline mode) and on `/reflect` commands (deep mode), the baseline becomes less relevant — the rolling window of recent detections supersedes it. The bootstrap exists solely to avoid a cold-start gap where the first 2–3 weeks of diary entries get no pattern feedback.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Runtime | OpenClaw (existing VPS deployment) | Already running, already Telegram-connected, already has 50+ skills. Zero new infrastructure. |
| AI execution | Claude CLI subprocess (3600s timeout) | Established OpenClaw provider. Pattern detection and reality check fit within the timeout for the current corpus size (~20 entries). Migrate to Anthropic SDK only if corpus growth pushes past the timeout ceiling. |
| Input channel | Telegram (existing) | Primary mobile interface. Already working. 4096-char response limit shapes all output design. |
| Memory storage | Filesystem (`~/.openclaw/workspace/memory/2026-*.md`) | Established format. Human-readable. No database, no migration. Pattern detection reads files directly. |
| Context injection | Workspace files (`MEMORY.md`, `USER.md`, `SOUL.md`) | Auto-loaded every OpenClaw session. Skills reference these rather than duplicating identity or preference context. |
| Action targets | Existing OpenClaw skills (`apple-reminders`, `himalaya`) | No new integrations. Dispatch routes to skills that already work. |

## Composition Model

The four skills are **independent but sequentially composable**. The OpenClaw agent decides which skills to invoke based on input type, not a hardcoded pipeline. The expected flows are:

**Daily diary flow** (triggered by diary-like Telegram message): diary-process → inline pattern-detect (last 2–4 weeks) → auto-light reality-check (1–2 challenges max) → action-dispatch (1–3 proposals with confirmation). This entire flow completes in a single Telegram interaction and produces one combined response under the 4096-character limit.

**Deep reflection flow** (triggered by `/reflect`): deep pattern-detect (full history) → full reality-check (all detected assumptions scored) → action-dispatch. This may produce a longer response, split across multiple Telegram messages if needed.

**Standalone action** (triggered by explicit request like "remind me to..." or "draft an email to..."): action-dispatch only, bypassing the diary pipeline entirely.

The agent — not the skills — owns the orchestration logic. Skills are declarative; the agent is imperative. This means the composition can change by updating the agent's session instructions (`AGENTS.md`), not by refactoring skill files. The trade-off is that orchestration logic lives in a less-structured place (agent instructions vs. skill definitions), but for a four-skill system with one consumer, the flexibility outweighs the rigor cost.

## Memory Window Strategy

Pattern detection must read historical entries without exceeding the Claude CLI timeout or context window. The strategy is **recency-weighted windowing**:

- **Inline mode** (daily diary): Load the most recent 14–28 days of entries verbatim. This is the hot window where stalled goals and contradictions are most detectable and most actionable.
- **Deep mode** (`/reflect` and bootstrap): Load all entries, but if the total exceeds a token budget (declared in the skill), summarize entries older than 30 days into compressed theme summaries before passing them to the prompt. The summaries preserve goal mentions, stated priorities, and action commitments — the fields pattern detection needs — while discarding narrative detail.
- **Growth plan**: At the current rate of ~1 entry per day, the corpus will reach ~180 entries by end of 2026. The inline window (14–28 entries) stays constant. The deep window grows linearly. If deep mode hits the timeout ceiling, the summarization threshold moves forward (summarize entries older than 21 days instead of 30). This is a manual tuning knob in the SKILL.md, not an automatic system.

## BS Detection Scoring Model

The reality-check skill uses the same 0/1/2 scoring rubric as BullshitBench, reinterpreted for personal reflection:

| Score | BullshitBench Meaning | Personal Reflection Meaning |
|-------|----------------------|----------------------------|
| 0 | Failed to catch planted nonsense | No rationalization detected — statement is grounded in experience or data |
| 1 | Partially caught — hedged or incomplete | Possible rationalization — worth examining, but could be legitimate |
| 2 | Fully caught and clearly challenged | Clear pattern match — contradicts prior entries, shows stalled-goal signature, or reveals sunk-cost reasoning with supporting evidence |

Each challenged assumption includes: the assumption text, the score, the anchor (which prior entry or pattern it contradicts), and a one-line rationale. The auto-light mode surfaces at most the single highest-scored challenge. The full mode surfaces all challenges scored 1 or 2.

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| **Freeform diary input** (not structured forms) | Lower friction maximizes daily usage. The AI extraction step is cheap; the habit formation cost of a rigid format is high. One consumer means the AI can learn the writing style from 20+ existing entries. | Extraction quality depends on prompt engineering. Ambiguous entries may produce incomplete structured output. Mitigated by optional `#tag` support for days when the user wants to be explicit. |
| **Skills-first, no plugin graduation** | Four skills with one consumer. A plugin package adds build steps, versioning, and packaging overhead for zero benefit at this scale. Per P6, graduate only when skills hit real limits. | No versioning, no rollback, no dependency declaration. Acceptable for a personal tool iterated by the sole developer. |
| **Auto-light reality check on every entry** | The BS detector's value comes from consistency — patterns are only visible when every entry gets the same scrutiny. Running only on-demand means the most dangerous rationalizations (the ones that feel true) never get checked. | Adds latency to every diary response. May feel intrusive on low-energy days. Mitigated by limiting auto-light to one challenge max and keeping tone calibrated (sharp friend, not critic). |
| **Confirm-before-execute for all actions** | Trust requires a human in the loop when the system touches email and reminders. A single bad autonomous email destroys confidence in the tool. The extra confirmation message costs 2 seconds; rebuilding trust costs weeks. | Slower action execution. Cannot batch multiple actions silently. Acceptable because the goal is decisions improved, not actions automated. |
| **Memory-delta anchoring** (not planted nonsense) | BullshitBench plants a known falsehood as ground truth. Personal reflection has no planted element — the ground truth is the user's own prior entries. Memory deltas (contradictions, stalled goals, repeated statements) serve the same structural role: a known reference point against which current claims are evaluated. | No objective "right answer" — all anchors are probabilistic. A user who legitimately changed their mind looks like a flip-flopper. Mitigated by the calibration guardrail: score 1 (examine) not score 2 (clear contradiction) when the evidence is ambiguous. |
| **wacli excluded from MVP dispatch targets** | The brain dump contradicts itself — wacli is listed as priority #4 but also noted as "WhatsApp broken" in prior docs. Shipping a dispatch target that fails on execution undermines trust in the entire action system. | Loses WhatsApp outreach capability. Mitigated by adding wacli to the dispatch mapping with a single SKILL.md edit once functionality is verified. |
| **Filesystem memory, no database** | The `2026-*.md` format is already established, human-readable, and backed up with the workspace. Adding a database for one consumer's diary entries violates P4 (speculative abstraction). File reads are fast enough for 180 entries per year. | No indexing, no full-text search, no relational queries. Pattern detection must read and parse files sequentially. Acceptable at current scale; revisit only if corpus exceeds 500+ entries. |
| **One orchestrating agent, not a skill-chain system** | The OpenClaw agent already decides which skills to invoke based on context. Building a separate orchestration layer (skill A calls skill B) adds complexity for a four-skill pipeline. The agent's session instructions are the orchestration config. | Orchestration logic is less explicit — it lives in natural-language agent instructions rather than structured skill dependencies. For four skills this is fine; would not scale to 20+ interdependent skills. |
| **Baseline stored as reference file, not memory entry** | The cold-start bootstrap produces metadata about patterns in memory, not a diary entry. Mixing metadata with memory entries pollutes the corpus that pattern detection reads, creating a feedback loop where the detector finds its own prior observations. | The baseline file must be maintained or aged out. Since it loses relevance as rolling detection accumulates history, this is a diminishing concern. |

## Risk Boundaries

**Timeout risk**: Pattern detection in deep mode against a growing corpus. Current headroom is large (20 entries vs. 3600s timeout), but at ~365 entries per year the context assembly could approach limits. Mitigation is the summarization threshold in the memory window strategy — a manual tuning knob, not an automated system, because premature automation for one user's growth curve violates P4.

**Tone risk**: The reality-check skill walks a narrow line between useful challenge and demoralizing criticism. The calibration guardrail (challenge rationalizations, preserve experiences) is necessary but not sufficient — the SOUL.md personality context must reinforce the sharp-friend tone. This is a prompt-tuning problem, not an architecture problem, but the architecture must ensure SOUL.md is always in context when reality-check runs.

**Trust risk**: Action dispatch touches external systems (email, reminders). A single misfired action erodes trust disproportionately. Confirm-before-execute is the architectural mitigation. If user testing reveals that confirmation fatigue leads to rubber-stamping, the fallback is to restrict auto-proposed actions to reminders only (low-consequence) and require explicit invocation for email.

## Workspace File Updates

The existing OpenClaw workspace files require targeted updates to support the new skills:

- **AGENTS.md** — Add orchestration instructions for the diary pipeline flow and `/reflect` command routing. This is where the composition model is declared.
- **MEMORY.md** — No structural changes. The diary-process skill writes to the established format. Pattern detection and reality check read from it.
- **SOUL.md** — May need a "reflection voice" section that defines the sharp-friend calibration for reality-check output. Keeps tone rules in one place per P6 (references as source of truth).
- **HEARTBEAT.md** — Evaluate whether the existing proactive-check schedule should trigger pattern detection on a cadence (e.g., weekly deep analysis). Deferred until the daily diary flow is proven.

## Related Documents

- [Analysis](./analysis.md) — Problems, constraints, and open questions driving this architecture
- [Epic](./epic.md) — Scope, tasks, success criteria, and exclusions
- [Timeline](./timeline.md) — Delivery milestones and status tracking