# 🏗️ Solution Architecture: weekly-life-os-1779265846

## Architecture Overview

Specview already solves a hard problem: it takes an unstructured braindump and produces a sequenced, actionable document set through a multi-step AI chain. The pipeline — braindump → analysis → epic → architecture → implementation guide — works because each step narrows ambiguity and adds structure. The insight behind this epic is that the pipeline's power is domain-agnostic; the only thing that makes it "a dev tool" is the output shape. An architecture document makes sense for a software project. It makes no sense for a friendship investment strategy. The output templates are the coupling point, not the pipeline itself.

The architecture therefore changes exactly one thing: it makes the output shape configurable per domain. The chain adapter's prompt construction gains a domain detection step that reads the braindump content and selects a template set — either the existing engineering templates or a new life-domain template set. Everything upstream (braindump ingestion, project CRUD, background job runner, status polling) and everything downstream (file persistence, reader panel, Telegram delivery) remains untouched. This is a narrow intervention with maximum leverage: one new decision point in the pipeline enables an entire category of non-engineering output.

Telegram delivery is the second structural addition. A system-level cron job fires weekly, calls the existing Specview pipeline endpoint with a pre-composed prompt, and pushes the formatted result to Telegram via bot API. No OpenClaw, no VPS agent runtime, no new infrastructure. The "scheduled AI agent" that the original braindump imagined is actually just "run the pipeline on a timer" — a single cron line and a delivery adapter.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P1 — Adapter Boundary | Telegram delivery goes through a new delivery adapter module. No feature code imports the Telegram bot API directly. If delivery later expands to email or web push, only the adapter changes. |
| P2 — Thin HTTP Layer | No new routes required for domain detection — the existing braindump ingestion endpoint handles all domains. The Telegram cron caller uses the same endpoint as the Angular frontend. |
| P3 — Async 202 + Polling | Life-domain braindumps use the same background thread pattern as engineering specs. The cron job polls the existing status endpoint until `done: true`, then calls the delivery adapter. |
| P4 — No Speculative Abstractions | One life-domain template set, not a template registry. One delivery channel (Telegram), not a notification framework. One domain detector, not a classifier pipeline. Build for the social/people POC and nothing else. |
| P5 — OpenAPI-First | No new endpoints means no OpenAPI changes. The template selection is internal to the chain — the API contract is unchanged. If a template-selection parameter is later needed, it enters the contract via `openapi.yaml` first. |
| P7 — File Size & Structure | Life-domain templates are standalone files in the project data directory, following the same pattern as existing spec files. The domain detector is a function inside the existing prompt builder, not a new module. |

## Component Design

### Domain Detector

**Purpose**: Determines whether a braindump is engineering-shaped or life-domain-shaped, so the pipeline selects the correct output template set.

This is a prompt-level decision, not a code-level classifier. The chain adapter's prompt construction step already assembles context and instructions before calling the AI provider. The domain detector adds a lightweight classification preamble: given the braindump content, which domain does this belong to? The result selects a template set. For the POC, there are exactly two options — engineering (existing) and life-domain (new). No enum of twelve domains, no taxonomy service, no ML model. The AI provider that already processes the braindump is perfectly capable of recognizing "I haven't seen my friends" versus "I need a REST API for user auth."

The detector lives inside the existing prompt builder in `modules/ai/workflows/spec_gen/`, not as a separate module. It is a conditional branch in prompt assembly, not a new service.

### Life-Domain Template Set

**Purpose**: Defines the output shape for non-engineering braindumps — what sections get generated and in what order.

Engineering specs emit: analysis → epic → architecture → timeline → implementation guide. Each section assumes software context (code references, API contracts, deploy targets, task dependencies). A life-domain braindump needs fundamentally different sections:

- **Situation Analysis** — replaces engineering "analysis." What is the current state? What data do we have? What patterns emerge? (Equivalent depth, different vocabulary.)
- **Action Plan** — replaces "epic" and "architecture" combined. Named actions with owners, timeframes, and success criteria. No task dependency graphs — life actions are parallel by default.
- **Review Triggers** — replaces "timeline." When should you revisit this plan? What signals indicate it is working or failing? Not status tracking — trigger conditions.

Templates are stored as markdown files in the Specview data directory, alongside the existing prompt templates. They are static files checked into the repo, not database records. The chain reads them at generation time the same way it reads engineering templates today.

The template count is deliberately small. Two to three sections, not six. Life-domain output must be shorter and more direct than engineering output because the consumer (Sam on Telegram at 6pm Sunday) has less patience than the consumer (Sam at a desk implementing a feature). The constraint is not technical — it is attentional.

### Context Provider (Manual Paste, MVP)

**Purpose**: Feeds life-domain data into the braindump so the pipeline has material to work with.

For the POC, context injection is entirely manual. The user pastes relevant data — diary entries, people notes, calendar snippets — directly into the braindump text field alongside their unstructured thoughts. The pipeline processes everything as a single input block, the same way it processes an engineering braindump that includes code snippets or API docs.

This is a deliberate non-automation decision. Automated data ingestion (Google Calendar API, Strava, Apple Health, bank statements) is a separate capability with its own authentication flows, data format handling, and failure modes. Coupling it to the generalization POC creates two untested variables — "can the pipeline generalize?" and "can we reliably pull data from five external APIs?" — when the epic only needs to answer the first question.

The manual paste approach also validates a critical product hypothesis: does the pipeline produce good output from messy, incomplete, human-written context? If it requires perfectly structured API data to work, it is not a general-purpose thinking tool — it is an ETL pipeline with a nice frontend.

### Telegram Delivery Adapter

**Purpose**: Formats pipeline output for Telegram and sends it via bot API.

The delivery adapter is a thin module behind the P1 adapter boundary. It accepts structured pipeline output (the generated life-domain spec), compresses it to fit Telegram's 4096-character limit, and sends it via the Telegram Bot API's `sendMessage` endpoint. Compression is format-aware: it preserves action items and names while trimming analysis paragraphs, because the Sunday evening consumer needs "call Alex, suggest Thursday coffee" more than they need "your social engagement has declined 23% quarter-over-quarter."

The adapter lives in a new `modules/delivery/` directory under the API, with `adapter.py` as the boundary and `telegram.py` as the initial provider. This mirrors the chain adapter pattern — if email delivery is added later, it becomes another provider behind the same boundary. But per P4, we build only the Telegram provider now.

### Cron Trigger

**Purpose**: Fires the weekly pipeline run on schedule without requiring a running AI agent.

A system-level cron job (Sunday 18:00 CET) calls the Specview API's existing braindump ingestion endpoint with a pre-composed prompt. The prompt includes a standing instruction ("generate my weekly social pulse") and any manually-updated context files. The cron job then polls the status endpoint until generation completes, then calls the delivery adapter.

This is a shell script registered in the system crontab, not a Python scheduler, not an OpenClaw skill, not a long-running daemon. Cron is the correct tool for "do this thing once a week at a fixed time." It has been solving this problem since 1975. The cron script lives in the Specview repo so it is version-controlled, but it executes at the OS level.

The critical framing: the cron job is not "the AI agent." It is a timer that triggers the existing pipeline. The intelligence is in Specview's chain. The scheduling is in cron. Conflating these two concerns is what creates unnecessary OpenClaw coupling.

### Quality Rubric

**Purpose**: Provides a concrete, scorable evaluation of whether non-engineering pipeline output meets the same quality bar as software specs.

The rubric is a static markdown file with five binary criteria. Each criterion is testable by a reader who is not the author. The rubric is applied manually to the POC output — not automated, not integrated into the pipeline. It is a validation artifact, not a runtime component.

The rubric answers the business question directly: "Did Specview generalize?" If the POC output scores 5/5, the answer is yes and the next braindump domain is greenlit. If it scores below 3/5, the pipeline needs template or prompt changes before expanding further.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Pipeline engine | Existing Specview chain (`modules/runtime/chain/adapter.py`) | Already proven for multi-step AI generation. No new runtime needed — the generalization is in templates, not infrastructure. |
| Template storage | Markdown files in `data/` directory | Matches existing spec file storage. No database, no CMS. Templates are code-reviewed artifacts, not user-editable content. |
| Domain detection | Prompt-level classification in existing workflow | The AI provider already reads the braindump — adding a domain classification instruction costs one prompt paragraph, not a new service. |
| Delivery | New `modules/delivery/adapter.py` + `telegram.py` provider | P1-compliant adapter boundary. Telegram Bot API is a single HTTPS POST — no SDK, no webhook server, no long-polling. |
| Scheduling | System crontab + shell script | Zero-dependency scheduling. No Python scheduler library, no OpenClaw, no always-on process. Matches P4 — cron is the one concrete case. |
| Frontend | Existing Angular SPA (`web-ng/`) | Life-domain specs render in the same reader panel as engineering specs. The reader does not care about domain — it renders markdown. No new components. |
| Background processing | Existing `threading.Thread` + in-process state dict | Same 202 + polling pattern already shipping for engineering specs. No Redis, no Celery, no new job infrastructure. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| No OpenClaw dependency | The epic's intelligence comes from the Specview pipeline, not from an agent runtime. OpenClaw's only contribution would be scheduled triggers, which cron handles without a VPS agent. Removing this dependency makes the feature portable and validates Specview as a standalone product. | Loses future OpenClaw integration benefits (conversational trigger, multi-step agent workflows). Acceptable because those benefits are speculative and the POC needs to prove pipeline generalization, not agent orchestration. |
| Manual data input only | Automated ingestion (Google Calendar, Strava, bank APIs) creates authentication complexity, data format variability, and failure modes that are orthogonal to the generalization question. Manual paste isolates the variable under test. | Higher friction per use. Users must copy-paste diary entries and calendar data. Acceptable for a weekly cadence with one user — 5 minutes of paste vs. 5 days of API integration. |
| Life-domain templates as a second template set, not a template engine | Two template sets (engineering, life-domain) is the minimum intervention. A generic template engine with variable section counts, conditional blocks, and user-defined fields is a product, not a POC. | Cannot support arbitrary new domains without adding another template file. Acceptable because P4 says build for the one concrete case. If three more domains prove the pattern, then consider templating infrastructure. |
| Telegram-only delivery for MVP | Sam's primary mobile interface is Telegram. Building a web dashboard, email digest, or push notification system serves zero additional users and delays the POC. | No persistent web view of weekly output. Acceptable because the generated spec files are already viewable in Specview's reader panel — Telegram is the push notification, not the archive. |
| Domain detection via prompt, not classifier | Adding a classification model or rules engine for two domains is over-engineering. The AI provider that generates the spec can trivially distinguish "friendship strategy" from "REST API design" as part of its existing prompt processing. | Less deterministic than a rules-based classifier. The AI might misclassify an edge case. Acceptable because edge cases between "engineering" and "life" are rare in practice, and misclassification produces a usable-but-awkward output, not a failure. |
| Weekly cadence only, no daily check-ins | The epic scope explicitly excludes daily cadence. Daily check-ins add operational burden that historically kills adoption within two weeks for solo developers. Weekly is the atomic unit — prove it works before adding frequency. | Misses the "morning briefing" use case from the original braindump. Acceptable because the braindump's ambition exceeds the epic's scope by design — the additional context notes explicitly deprioritize daily cadence. |
| Quality rubric as static file, not automated scoring | Automated quality scoring requires defining "actionable" in machine-readable terms — a research problem, not an engineering task. A human-scored rubric with five binary criteria answers the business question in 10 minutes. | Requires manual evaluation effort each time. Acceptable for a one-time POC validation. If Specview generalizes to many domains, automated scoring becomes a separate epic. |
| Delivery adapter as new module, not extension of chain adapter | The chain adapter handles AI generation. Delivery (formatting + sending to Telegram) is a different concern with a different failure mode — a Telegram API outage should not affect spec generation. Separate modules, separate adapter boundaries. | Two adapter modules to maintain instead of one. Acceptable because P1 says each external service gets its own boundary, and Telegram Bot API is a distinct external service from the AI provider. |

## Risk Assessment

**Highest risk: Template quality determines everything.** If the life-domain template sections produce vague, generic output ("invest more in friendships," "exercise regularly"), the entire generalization thesis fails regardless of infrastructure quality. Mitigation: validate templates against real braindumps on paper before any pipeline integration. Task 1 exists precisely for this reason.

**Medium risk: Telegram's 4096-character limit forces lossy compression.** A well-structured weekly action plan might naturally exceed this limit. The delivery adapter must make intelligent compression choices — which sections to keep, which to truncate. Bad compression destroys the output's value. Mitigation: design the life-domain template to produce concise output by default, treating the character limit as a design constraint rather than a post-processing problem.

**Low risk: Cron reliability.** System cron on a single server has no redundancy. If the server reboots during the Sunday 18:00 window, the weekly delivery is missed. Mitigation: acceptable for a single-user POC. If this becomes a multi-user feature, scheduling moves to a managed service.

## Related Documents

- [Analysis](./analysis.md) – Problems driving this design
- [Epic](./epic.md) – Scope, tasks, and success criteria
- [Timeline](./timeline.md) – Status tracking