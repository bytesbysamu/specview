# 🎯 Epic: Sam's Studio Plugin

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

Sam runs OpenClaw locally so the agent acts as a real co-pilot, not a generic chat window. The current setup has static context (MEMORY.md, USER.md, claude.ai export) and generic tools. Every session starts with the agent asking "what are you working on?" — wasted time and friction that compounds across every Telegram DM sent. The gap is not memory; it is live tooling. The agent can read about Sam's projects but cannot query them.

Wiring Sam's live systems into the agent's tooling closes that gap. When the agent can query spec-doc directly, read git state on any project, and inject a live context snapshot at session start, it stops being a chat assistant and starts being a system that knows its operator. This follows the same principle as the financing plugin: don't describe the system in text, make it callable. The productivity return is immediate — every interaction that currently opens with re-establishing context becomes an interaction that opens with actual work.

The primary interface is Telegram on mobile. A capable agent that produces unreadable walls of markdown on a phone screen is a failed agent. Telegram-aware behaviour is not optional polish; it determines whether the plugin is actually usable day-to-day. Both dimensions — live system awareness and channel-appropriate output — must ship together for the plugin to deliver its stated value.

**Value Proposition**: An agent that knows Sam's live systems and speaks the right language for the right channel, without being told each session.

---

## Scope

### What This Epic Covers

- **Boot context injection** — live snapshot of running services, spec-doc project count, and active project git state, delivered at session start without prompting
- **Telegram behaviour constraints** — message-length ceiling, formatting restrictions, and response tone calibrated for mobile, enforced when the active channel is Telegram
- **Spec-doc bridge** — callable tools covering the core spec-doc operations against the local API at `host.docker.internal:8080`
- **Project registry** — curated map of Sam's active projects keyed by name, with confirmed local paths, stack, URL, and git awareness
- **Plugin graduation** — promotion from SKILL.md files to a proper plugin package with real MCP tool registration, gated on the skill shape proving sufficient in practice

### What This Epic Does NOT Cover

- ❌ **Proactive Telegram push** — heartbeat config belongs to a dedicated heartbeat plugin, not sam-plugin
- ❌ **`sam_docker_ps()`** — Docker socket access inside the OpenClaw container is unconfirmed; deferred until socket mount is verified
- ❌ **Bubls data access** — Bubls is not running locally; deferred until a local URL and confirmed stack exist
- ❌ **`sam_specDoc_braindump()` scaffolding** — template source file is unresolved; deferred until the concrete file is identified
- ❌ **Calendar, email, or web access** — external integrations; out of scope for this plugin
- ❌ **Trendfy AI pipeline control** — Replicate and Stripe are production systems; no direct agent control without explicit re-scoping
- ❌ **ClawHub publishing** — this plugin is private and local; distribution is never a goal

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Boot Context Skill** | Boot hook mechanism decision | Tasks 2, 3 | 1 day | High |
| 2 | **Telegram Behaviour Constraints** | None | Tasks 1, 3 | 0.5 days | High |
| 3 | **Spec-Doc Bridge** | Localhost auth behaviour confirmed | Tasks 1, 2 | 2 days | High |
| 4 | **Project Registry** | Project map gaps resolved | — | 1 day | High |
| 5 | **Plugin Graduation** | Tasks 1–4 complete | — | 2 days | Low |

### Task 1: Boot Context Skill

Delivers a session-start snapshot covering date, running services, spec-doc project count, and active project git state — so the agent begins every conversation informed rather than asking. Blocked on the boot hook mechanism decision identified in [Analysis](./analysis.md): live compute per session burns tokens on every Telegram DM; a cron-written daily file risks stale data. That decision must be made before this task can be specced, because the two options produce different skill designs.

See [Solution Architecture](./architecture.md) for skill file placement and session startup sequence.

**Port budget**: Core snapshot only. `sam_docker_ps()` excluded pending Docker socket confirmation. `sam_memory_append()` excluded until daily note path is made explicit in AGENTS.md.

---

### Task 2: Telegram Behaviour Constraints

Defines the rules the agent applies when the active channel is Telegram: a hard 4096-character ceiling, formatting restrictions (no markdown tables, no unsolicited long code blocks), and response tone calibrated for mobile. Has no external dependencies and can begin immediately; the only open question from [Analysis](./analysis.md) — hook vs. skill instruction — is resolved in favour of skill instruction for v1, with hook-based enforcement deferred to plugin graduation if self-limiting proves insufficient.

See [Solution Architecture](./architecture.md) for channel detection approach and formatting rule placement.

**Port budget**: Skill instruction only in v1. Hook enforcement deferred to Task 5 if needed.

---

### Task 3: Spec-Doc Bridge

Gives the agent callable tools for the core spec-doc operations: listing projects, reading and writing files, and triggering coherence checks against `host.docker.internal:8080`. Blocked on the localhost auth question identified in [Analysis](./analysis.md): calls from inside OpenClaw may skip RS256 JWT enforcement, or may require a stored dev token — that answer determines whether each tool is five lines or twenty. The braindump scaffolding tool is excluded from this task until the template source file is confirmed.

See [Solution Architecture](./architecture.md) for API surface design and auth handling.

**Port budget**: Six core API operations for v1. `sam_specDoc_braindump()` added as a follow-on once the template file is identified.

---

### Task 4: Project Registry

Registers Sam's active projects by name so the agent can look up path, stack, URL, and git state without asking. Blocked on three open items from [Analysis](./analysis.md): `humaniz.me` is absent from the current map and must be added; `clawboi` and `openclaw` appear at conflicting paths and the canonical path must be confirmed; Trendfy's post-May 1 status is unknown and a dead project must not appear in the registry. All three gaps must close before this task ships a correct registry.

See [Solution Architecture](./architecture.md) for registry format and `sam_git_status()` tool design.

**Port budget**: Registry entries limited to projects with confirmed local paths and live/dead status. `sam_docker_ps()` excluded from this task.

---

### Task 5: Plugin Graduation

Promotes the three SKILL.md files to a proper plugin package with real MCP tool registration, enabling callable functions rather than skill instructions. Gated on Tasks 1–4 demonstrating that the skill shape works in practice. If SKILL.md files prove sufficient and no capability ceiling is hit, this task may be indefinitely deferred without loss of value.

See [Solution Architecture](./architecture.md) for plugin package structure and MCP registration requirements.

**Port budget**: Promotion only — no new capabilities added at graduation. New tools added only if a specific skill limitation is hit during Tasks 1–4.

---

## Success Criteria

- ✅ Agent session starts with a live context snapshot requiring zero input from Sam
- ✅ `sam_specDoc_listProjects()` returns current projects from the spec-doc API without Sam supplying credentials
- ✅ `sam_git_status()` returns current branch and last commit for any project in the registry, called by project name
- ✅ All Telegram responses stay under 4096 characters without truncation or mid-sentence cuts, across at least ten consecutive sessions
- ✅ Every project in the registry has a confirmed local path, stack, and live-or-dead status — no placeholder entries
- ✅ `humaniz.me` is present in the registry with a confirmed path and URL

---

## Non-Goals

- ❌ **Generalisability** — this plugin is explicitly Sam's world; making it reusable for other users is not a design concern and would actively harm specificity
- ❌ **Proactive push notifications** — the agent responds; it does not initiate without an explicit heartbeat plugin in place
- ❌ **External service integrations** — calendar, email, Replicate, and Stripe are out of scope for this plugin's lifetime
- ❌ **Abstracting the project map** — the registry is a curated, hand-maintained list; auto-discovery of projects is not a goal

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview