# 🏗️ Solution Architecture: ex-girlfriend

## Architecture Overview

This is a **decision architecture**, not a software architecture. The system under design is Sam's reasoning process between today (2026-05-09) and Wednesday (2026-05-13). The mental model: treat the decision as a four-stage pipeline — **Diagnose → Delta → Signal → Decide** — where each stage produces a written artifact that feeds the next, and the final stage emits one of three outputs (yes / no / defer-30-days).

The key insight is that the dominant failure mode is **anniversary-anchored reasoning**: the May 13 four-year date creates symbolic gravity that can override evidence. The architecture's primary job is to isolate evidence inputs from symbolic inputs so the decision is auditable. Every stage produces a written one-liner; if the final reason cannot be stated without referencing the date, the system must default to "defer."

The components fit as a thin sequential chain — no parallel branches except Stage 1 and Stage 3, which are independent (past cause vs. present signal). Stage 4 is the gate. Stage 5 (Wednesday script) is a **prep artifact**, not a decision input — it executes the decision rather than producing it.

## Design Principles

| Principle | Application |
|-----------|-------------|
| Evidence over symbolism | Anniversary date is excluded from decision criteria; if it surfaces as the deciding factor, the architecture forces "defer" |
| Written artifacts at each stage | Every stage emits one written sentence; verbal-only reasoning is rejected because it drifts |
| Single decision-maker, single beneficiary | No consensus-building layer, no stakeholder review — Sam is the only node |
| Asymmetric error cost weighting | A wrong "yes" costs months; a wrong "no" costs a relationship that may have matured. Defer is cheaper than either wrong answer when signal is ambiguous |
| Questions over statements (Wednesday) | Wednesday's session is an information-gathering interface, not a verdict-delivery interface |
| Hard deadline, soft outcome | EOD May 13 is fixed; the outcome space includes "defer," so the deadline doesn't force a binary |

## Component Design

### Stage 1 — Breakup Cause Diagnoser
**Purpose**: Categorize the December 2025 split into one of three buckets — resolvable conflict, structural incompatibility, or external circumstance. This determines whether a restart is even coherent. A structural-incompatibility cause cannot be resolved by time alone; a resolvable-conflict cause can; an external-circumstance cause may already be moot.

**Input**: Sam's recollection of the December breakup, unfiltered.
**Output**: One sentence — `cause = <category>` plus a one-line justification.
**Boundary**: Does not relitigate the fight. Categorizes only.

### Stage 3 — Sunday Signal Reader
**Purpose**: Convert the two post-breakup meetings (most recently last Sunday) into a classified signal — mutual interest / one-sided interest / ambiguous. Runs in parallel with Stage 1 because past cause and present signal are independent variables.

**Input**: What she said, what she did, what she did not say or do.
**Output**: `signal = <class>` + the specific behaviors that justify the classification.
**Boundary**: Cannot include projection. If a behavior is ambiguous, it must be classified as ambiguous, not resolved by hopeful interpretation.

### Stage 2 — Five-Month Delta Assessor
**Purpose**: Identify what concretely changed during the break. The output names the person(s) who changed (her / Sam / both / neither) and the specific behavior or circumstance that shifted. "Neither changed" is a valid and important output.

**Input**: Stage 1 cause + observable evidence from the two meetings + Sam's own change log over 5 months.
**Output**: `delta = <who> changed <what>` or `delta = none`.
**Trade-off accepted**: Sam can only observe her change indirectly; the assessor must mark her-side claims as low-confidence until Wednesday's conversation verifies them.

### Stage 4 — Decision Gate
**Purpose**: Combine cause + delta + signal into one of three outputs. This is the architectural choke point — all evidence converges here, and the symbolic input (anniversary date) is explicitly excluded.

**Decision rules** (declarative, written before Wednesday):
- **YES** requires: cause is resolvable OR external; delta names a concrete change in the relevant party; signal is mutual.
- **NO** requires: cause is structural incompatibility AND delta = none; OR signal is one-sided.
- **DEFER 30 days** is the default when any input is ambiguous, when the only "yes" reason references the anniversary, or when Wednesday's conversation reveals a mismatch with Stage 3's signal read.

**Boundary**: The gate runs once on Wednesday after the conversation, not before. Pre-Wednesday output is a **provisional** decision that the conversation can confirm, downgrade, or invert.

### Stage 5 — Wednesday Conversation Script
**Purpose**: Translate the decision criteria into 3–5 questions to ask her. Not statements. Questions are designed to surface evidence that confirms or contradicts the provisional Stage 4 output.

**Input**: Stage 4 decision rules + open uncertainties from Stages 1–3.
**Output**: A written question list, ordered from least to most loaded.
**Boundary**: No prepared statements, no rehearsed declarations, no "if she says X then I say Y" branches deeper than one level — over-scripting prevents listening.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Reasoning surface | Plain written notes (one document, five sections) | Single decision-maker; written form forces clarity and survives the 4-day window without drift |
| Storage | Local file or notebook page | No collaboration layer needed — Sam is sole reader and writer |
| Time budget | 0.5 days × 4 stages + 0.25 day signal review = ~2.25 working days | Fits inside the May 9 → May 13 window with slack for Wednesday itself |
| Decision protocol | Three-outcome gate (yes / no / defer) | Two-outcome forces false binary on a date-coincidence deadline |
| Verification interface | Wednesday in-person conversation | Highest-bandwidth channel available; questions over statements |
| Symbolic-input filter | Explicit exclusion rule in Stage 4 | Anniversary date is the predicted dominant bias; must be filtered architecturally, not by willpower |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Three outcomes, not two | A binary forced by a symbolic date produces noise; "defer 30 days" is a real third option that respects ambiguity | Defer can become indefinite avoidance — mitigated by the explicit 30-day clock |
| Sequential pipeline with one parallel branch | Stages 1 and 3 are independent (past vs. present); chaining everything serially wastes the 4-day window | Slight cognitive overhead from running two threads at once; acceptable for one person on two artifacts |
| Stage 4 runs twice (provisional pre-Wed, final post-Wed) | A pre-Wednesday position prevents being talked into something live; a post-Wednesday rerun prevents ignoring new evidence | Risk of locking in too early — mitigated by explicitly labeling the first run "provisional" |
| Exclude anniversary date from decision inputs | Identified failure mode is anniversary-anchored reasoning; the only architectural defence is to forbid the input | Loses any genuine signal embedded in the timing — accepted as cost; if timing matters, it will surface via signal class instead |
| Questions to her, not statements | The information gap is on her side (intent, what changed); statements close the channel, questions open it | Sam may want closure or to deliver a position — deferred to a follow-up conversation if Stage 4 outputs YES |
| Written one-sentence outputs at every stage | Verbal reasoning drifts over 4 days; one written sentence is auditable on Wednesday morning | Feels heavy for a personal decision — accepted because the cost of a wrong yes is months |
| No relitigating old fights in scope | Belongs in the Wednesday conversation itself, not the planning system | Pushes ambiguity into the live conversation; mitigated by question prep |
| Sam's own delta included in Stage 2 | A symmetric break can produce asymmetric change; "she didn't change but I did" is a real and important output | Self-assessment is the lowest-reliability input — accepted, marked as such |
| Defer is the safe default | When inputs conflict or signal is ambiguous, neither yes nor no is supported by evidence | Defer can be read as cowardice or stringing along — mitigated by communicating it explicitly on Wednesday with a 30-day clock |

## Related Documents
- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking