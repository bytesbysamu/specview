# 🏗️ Solution Architecture: Sam's Studio Plugin

**Purpose**: Long-lived system design document.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

The plugin is a thin instrumentation layer over Sam's already-running local systems. Rather than introducing a new service, it creates named entry points that OpenClaw's agent can call to answer questions it would otherwise ask Sam. The mental model is an ambassador: the plugin knows Sam's topology and speaks on his behalf, so the agent never needs to re-establish context across conversations.

At v1, the three skill files (`sam-context`, `sam-specDoc`, `sam-projects`) are instruction-bearing SKILL.md documents loaded by OpenClaw at session start. They carry no compiled code and require no build step. This is a deliberate constraint: it makes each skill deployable in minutes and independently editable without breaking the others. The trade-off is that skills are instruction-interpreted rather than function-registered — sufficient until a specific capability ceiling is hit.

Channel awareness is not a separate component. Telegram constraints are behavioural rules embedded in the skill layer that the agent consults whenever it determines the active channel. This keeps the constraint close to the content it governs and avoids a hook dependency that would require intercepting the outbound message pipeline before v2.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Wire it up, don't describe it | Each gap in live-system awareness is closed by a callable tool, not a prompt instruction to "check localhost:8080" |
| One boundary per capability | Each skill file owns one domain; no skill bleeds into another's API surface |
| Defer graduation until constrained | SKILL.md files remain the implementation until a named capability is demonstrably blocked |
| Channel-first formatting | Telegram constraints are architectural, not stylistic — they determine whether the plugin delivers value on the primary interface |
| No placeholder entries | The project registry ships only confirmed, live projects; unresolved paths and dead projects are excluded |

---

## System Boundaries

### What This System Includes

- `sam-context/SKILL.md` — session-start snapshot and Telegram formatting rules, consumed by the agent on every conversation open
- `sam-specDoc/SKILL.md` — six core API operations against `host.docker.internal:8080`, consumed by the agent whenever Sam asks anything spec-doc-related
- `sam-projects/SKILL.md` — project registry and `sam_git_status()` tool, consumed by the agent when Sam references a project by name
- Plugin graduation path — `openclaw.plugin.json` package structure with MCP tool registration, activated only when a v1 skill limitation is demonstrated

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| `sam_docker_ps()` | Docker socket mount inside OpenClaw container is unconfirmed; inclusion now generates a silently-failing tool |
| `sam_specDoc_braindump()` | Template source file is unidentified; tool cannot be specced without a concrete file path |
| Bubls data access | No confirmed local URL; API surface unknown |
| Proactive Telegram push | Heartbeat behaviour belongs to a dedicated heartbeat plugin |
| `humaniz.me` registry entry | Canonical local path unconfirmed; added when path is resolved |
| Trendfy registry entry | Post-May 1 live-or-dead status unknown; a dead project must not appear in active registry |
| Calendar, email, web | External integrations outside this plugin's scope |
| Trendfy pipeline control | Replicate and Stripe are production systems; agent control requires explicit re-scoping |

---

## Component Design

### Session Context Component

**Purpose**: Eliminates the "what are you working on?" opening by making the agent aware of date, live services, spec-doc project count, and active project git state before Sam types a word.

**Key Parts**:
- `sam-context/SKILL.md` — carries the boot snapshot definition and Telegram formatting constraints; consumed by OpenClaw on session start and by the agent on every response when the active channel is Telegram
- Boot snapshot definition — specifies which systems to query (date, spec-doc health, git state per active project) and the compact output format surfaced to Sam

**Patterns**: The boot mechanism decision — live per-session compute versus cron-written daily file — is unresolved and determines the snapshot's freshness guarantee and per-session token cost. See Open Questions. The two options produce different skill designs and cannot both be accommodated in a single file.

---

### Spec-Doc Bridge Component

**Purpose**: Makes the spec-doc API callable by name rather than requiring Sam to supply endpoint paths or auth tokens in conversation.

**Key Parts**:
- `sam-specDoc/SKILL.md` — defines six operations (`listProjects`, `getProject`, `createProject`, `readFile`, `writeFile`, `runCoherence`) against `host.docker.internal:8080`; consumed by the agent whenever Sam references spec-doc activity
- Auth handling — localhost calls from inside OpenClaw may bypass RS256 JWT enforcement; if they do, tools are unconditional HTTP calls; if they do not, tools require a stored dev token at a known path; the auth behaviour determines whether this component is five lines or twenty per tool

**Patterns**: Thin one-to-one HTTP wrapper. No aggregation, no caching, no retry logic at v1. The bridge is intentionally minimal so that when spec-doc's API changes, only the SKILL.md needs updating. Multi-step queries are composed by the agent, not pre-baked into the bridge.

---

### Project Registry Component

**Purpose**: Gives the agent a stable, named reference to Sam's active projects so it can resolve a project name to a local path, stack, and URL without asking.

**Key Parts**:
- `sam-projects/SKILL.md` — carries the project map (confirmed entries only) and the `sam_git_status(project)` tool definition; consumed by the agent when Sam names a project in any context
- Project map — a flat, hand-maintained keyed list; each entry requires a confirmed local path, stack, and live-or-dead status before inclusion; no entry ships with a placeholder
- `sam_git_status(project)` — resolves a project name to its local path via the map, then reads branch and last commit via the mounted filesystem; direct consumer is the agent answering any git-state or project-awareness question

**Patterns**: Registry over discovery. Auto-discovery of projects from the filesystem is a non-goal; the registry is curated to reflect only what Sam actively works on, preventing noise from archived or experimental directories.

---

### Plugin Graduation Component

**Purpose**: Provides a defined promotion path from instruction-based skills to compiled MCP tools when a specific capability is blocked at the skill layer.

**Key Parts**:
- `openclaw.plugin.json` — plugin manifest defining MCP tool registrations; activated only after Tasks 1–4 demonstrate the skill shape is insufficient for a named capability
- MCP tool wrappers — promote each `sam_*` skill operation to a registered function call; no new capabilities added at graduation, only promotion of the existing three skills

**Patterns**: Graduation is triggered by evidence of a skill-layer ceiling, not by a timeline or preference. The external interface — tool names and call signatures — is preserved across the promotion; only the execution mechanism changes from instruction-interpreted to function-registered.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Skill format | SKILL.md (instruction-based) | Zero build step; independently editable; sufficient until a specific MCP capability is demonstrably blocked |
| API target | Flask spec-doc at `host.docker.internal:8080` | Already running; six confirmed endpoints; no new service introduced |
| Auth | Localhost bypass (assumed) / stored dev token (fallback) | Unconfirmed; see Open Questions — this single decision determines tool complexity across the entire bridge |
| Filesystem access | `/home/node/Projects` via Bash and Read tools | Already mounted; `sam_git_status()` reads directly without additional tooling |
| Future plugin | `openclaw.plugin.json` + MCP registration | Standard OpenClaw plugin format; real function calls replace skill instructions when the ceiling is hit |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| SKILL.md over plugin package at v1 | Removes build step and deployment risk from the learning path; skills are editable live without a compilation cycle | Skills are instruction-interpreted; no hard type guarantees on tool inputs or outputs |
| Telegram constraints in skill layer, not hook | Hook enforcement requires intercepting the outbound message pipeline, which is unavailable before plugin graduation; skill instruction is available immediately | Agent can exceed 4096 chars if it misidentifies the channel; hook enforcement deferred to graduation if self-limiting fails in practice |
| Hand-curated project registry | Auto-discovery surfaces archived and dead directories alongside active ones, introducing noise into every project-name resolution | Registry requires manual updates when projects are added or retired; gaps (humaniz.me, path conflicts) must be resolved before the registry ships |
| One-to-one spec-doc bridge | Each tool maps to a single confirmed API endpoint; aggregation is application logic, not bridge logic | Agent must compose multi-step queries itself; the bridge does not short-circuit common patterns |
| `sam_docker_ps()` deferred | Socket access inside OpenClaw is unconfirmed; a tool that silently fails on every call is worse than no tool | Container visibility is absent from the plugin until the socket mount is verified |

---

## Execution Flow

**Session startup**: OpenClaw loads the three skill files; the boot hook fires and injects the live context snapshot; the agent reads MEMORY.md, USER.md, and the current daily note. By the time Sam sends his first message, the agent holds date, service health, spec-doc project count, and git state for active projects.

**Tool invocation**: When Sam names a project or a spec-doc operation, the agent resolves the name through `sam-projects/SKILL.md`, constructs the appropriate call (HTTP for spec-doc, Bash/Read for git state), and returns the result. No intermediate orchestration layer; each skill is consulted directly by the agent.

**Telegram gate**: Before composing any response when the active channel is Telegram, the agent applies constraints from `sam-context/SKILL.md` — 4096-character ceiling, bullet lists over tables, no unsolicited long code blocks. Enforced by skill instruction at v1; promoted to hook enforcement at graduation if self-limiting proves insufficient.

**Plugin graduation**: When a specific capability is blocked at the skill layer — named, evidenced, and confirmed — the three SKILL.md files are promoted to MCP tool registrations. Tool names and call signatures are preserved; only the execution mechanism changes.

---

## Open Questions

- **Boot hook mechanism** — Option A: a cron job writes a daily context file once per morning; the agent reads it at session start (zero per-session compute, risk of intra-day staleness). Option B: the agent runs live queries on every session start (always current, burns tokens on every Telegram DM). These produce different SKILL.md designs; the decision must be made before Task 1 is specced. Re-decision trigger: if daily session count exceeds ten, Option A becomes the correct default regardless of freshness preference.

- **Spec-doc localhost auth** — Calls from inside OpenClaw to `host.docker.internal:8080` may bypass RS256 JWT enforcement entirely, or may require a stored dev token. This determines whether each bridge tool is an unconditional HTTP call or requires a credential-lookup step. Re-decision trigger: confirmed by running a raw unauthenticated request from inside the OpenClaw container against a protected spec-doc endpoint.

- **`sam_specDoc_braindump()` template source** — The scaffolding tool requires a concrete template file path. `braindump-saas-monetisation.md` is a reference example, not a generic skeleton. Re-decision trigger: Sam identifies the canonical template file or confirms a new generic skeleton should be authored.

- **Project path conflicts** — `clawboi` and `openclaw` appear at conflicting paths in prior context; `humaniz.me` has no confirmed local path. The registry cannot include these entries until canonical paths are confirmed. Re-decision trigger: Sam confirms the canonical path for each conflicted or absent entry.

- **Trendfy live-or-dead status** — Post-May 1 pivot status is unknown. A dead project in the registry introduces noise into every project-name resolution. Re-decision trigger: Sam confirms whether Trendfy remains an active local project.

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview