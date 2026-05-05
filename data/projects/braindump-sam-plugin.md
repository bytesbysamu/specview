# sam-plugin — OpenClaw Personal Life OS Plugin

> **Priority**: P0 — this is the core reason OpenClaw is running locally.
> **Effort**: iterative — starts thin, grows as Sam's world is wired in.
> **Blocks**: nothing external — self-contained plugin.
> **Depends on**: OpenClaw gateway running locally, ~/Projects mounted at /home/node/Projects, spec-doc API at host.docker.internal:8080.
> **Inspired by**: `braindump-saas-monetisation.md` — same rigour, same structure, different domain.
> **Lives at**: `~/.openclaw/workspace/` (workspace plugin, not a published extension).

---

## What

A personal OpenClaw plugin that makes the agent deeply aware of Sam's world — his projects, their real-time status, his spec-doc workflow, his daily context, and his preferences. Not a generic assistant plugin. Specifically Sam's.

The agent already has `MEMORY.md`, `USER.md`, and the claude.ai history import. This plugin goes further: it gives the agent **live tools** to interact with Sam's actual running systems, not just static files.

### Core capabilities

**1. Spec-Doc bridge**

The agent can read, create, and drive spec-doc projects via the local API at `http://host.docker.internal:8080`.

```
sam_specDoc_listProjects()         → GET /api/projects
sam_specDoc_getProject(id)         → GET /api/projects/{id}
sam_specDoc_createProject(name)    → POST /api/projects
sam_specDoc_readFile(id, file)     → GET /api/projects/{id}/files/{file}
sam_specDoc_writeFile(id, file, content)  → PUT /api/projects/{id}/files/{file}
sam_specDoc_runCoherence(id)       → POST /api/projects/{id}/coherence
```

The agent can now say: *"Let me pull your current spec-doc projects and see what needs work."*

**2. Projects filesystem awareness**

`~/Projects` is mounted at `/home/node/Projects`. The agent has Read/Bash/Glob tools. Sam's full codebase is live. The plugin registers a curated project map so the agent knows what matters:

```json
{
  "projects": {
    "spec-doc":     { "path": "/home/node/Projects/2026/spec-doc",     "stack": "Flask+Angular", "url": "http://localhost:8080" },
    "bubls":        { "path": "/home/node/Projects/bubls",              "stack": "Ionic+Flask",   "url": null },
    "trendfy":      { "path": "/home/node/Projects/2026/wardrobai",     "stack": "Flask+Angular", "url": "https://trendfy.me" },
    "openclaw":     { "path": "/home/node/Projects/openclaw",           "stack": "Node/TS",       "url": "http://localhost:18789" },
    "constellation":{ "path": "/home/node/Projects/2026/constellation", "stack": "Flask+Next.js", "url": null }
  }
}
```

**3. Daily context injection (boot hook)**

On session start, the plugin auto-injects a live context snapshot:

```
- Date: 2026-05-04 (Sunday)
- Spec-doc: running @ localhost:8080 (N projects)
- OpenClaw: healthy, Telegram connected
- Active projects: [list with git status]
- Last memory update: [timestamp]
```

No more "what are you working on?" — the agent already knows.

**4. Sam's personal tools**

Thin wrappers for the things Sam actually uses:

- `sam_git_status(project)` — git status + last commit for any project
- `sam_docker_ps()` — what containers are running
- `sam_specDoc_braindump(topic)` — scaffold a new braindump file from a template
- `sam_memory_append(content)` — write to today's daily memory file

**5. Telegram-aware behaviour**

When the agent is responding via Telegram (channel = telegram):
- Keep responses under 4096 chars (Telegram hard limit)
- No markdown tables → use bullet lists
- Proactive check-ins are short: one-liners, not essays
- Never send code blocks longer than 30 lines without asking

---

## Why

Sam runs OpenClaw locally so the agent can be a real co-pilot, not a chat window. The current setup has memory (static files) and tools (generic Claude Code). What's missing is **domain knowledge about Sam's specific world** baked into the agent's tooling — not as prompts it reads, but as callable tools that return live state.

The financing plugin (Stripe + metering) is the template because it follows the same principle: don't just describe the system in text, wire it up so the code speaks for itself. Same here: don't just tell the agent "Sam has a spec-doc at localhost:8080" — give it `sam_specDoc_listProjects()` and let it find out for itself.

Secondary reason: Sam uses Telegram as his primary interface. The agent needs to know it's talking to Sam on mobile and adjust — short, actionable, no markdown soup.

---

## Architecture

OpenClaw workspace plugins live in `~/.openclaw/workspace/skills/` as skill files, or as a proper plugin package. For v1, we start with **skills** (faster iteration, no build step):

```
~/.openclaw/workspace/
├── skills/
│   ├── sam-context/
│   │   └── SKILL.md          ← boot hook + context snapshot
│   ├── sam-specDoc/
│   │   └── SKILL.md          ← spec-doc bridge tools
│   └── sam-projects/
│       └── SKILL.md          ← project map + git tools
├── MEMORY.md                 ← already seeded from claude.ai export
├── USER.md                   ← already populated
└── AGENTS.md                 ← already has session startup instructions
```

Each SKILL.md defines:
- When the agent uses this skill
- What tools/commands are available
- Examples

For v2, if the skill approach hits limits (no custom MCP tools, can't register real functions), graduate to a proper `openclaw.plugin.json` package compiled to a dist bundle. But v1 skills are enough to start.

---

## Session startup sequence (target state)

```
1. Agent wakes up
2. Boot hook fires → sam-context skill injects live snapshot
3. Agent reads MEMORY.md + USER.md + today's daily note
4. Agent is now aware of:
   - Who Sam is (USER.md)
   - What's been happening (MEMORY.md + daily notes)
   - What's running right now (context snapshot)
5. Sam says "check on spec-doc" → agent calls sam_specDoc_listProjects()
6. Sam says "make a braindump for X" → agent calls sam_specDoc_braindump("X")
7. Sam says "what's the git status of bubls?" → agent calls sam_git_status("bubls")
```

---

## What's missing (open decisions)

1. **Skill vs full plugin** — Do we start with SKILL.md files (no build, works now) or build a proper `openclaw.plugin.json` package (real MCP tools, more powerful)?  
   → Proposed: start with skills, graduate to plugin when we hit a wall.

2. **Telegram message length guard** — Hard-limit in the skill or via a hook? Hook is cleaner (fires on every outbound Telegram message automatically).

3. **Context snapshot on every session or on demand?** — Boot hook fires every session start. If sessions are frequent and cheap (Telegram DMs), this might burn tokens. Alternative: only inject on first message of the day.

4. **Which projects go in the map?** — Current proposal: spec-doc, bubls, trendfy, openclaw, constellation. What else? `clawboi`? `SamBoi`?

5. **Second account import** — The claude.ai export was Sam's account. The "two accounts" from earlier session — what's the second one? Lea's? A work account? Affects what gets imported into memory.

---

## Explicitly out of scope (v1)

- **Proactive Telegram push** (agent messages Sam without being asked) — that's heartbeat config, not sam-plugin.
- **Calendar / email / web access** — external integrations, separate plugins.
- **Trendfy AI pipeline control** — Replicate/Stripe are prod systems; no direct control from agent without explicit ask.
- **Multi-agent orchestration** — one main agent for now; subagents per task are fine but sam-plugin doesn't manage them.
- **Published to ClawHub** — this is private, stays local.
- **Voice** — `talk-voice` plugin handles that separately.
- **Bubls data access** — Bubls is not running locally yet; defer until it is.

---

## Build order

```
Phase 1 — Context (today)
  [ ] sam-context skill: boot hook + live snapshot (date, running containers, spec-doc status)
  [ ] Telegram message-length hook

Phase 2 — Spec-Doc bridge (this week)
  [ ] sam-specDoc skill: list/read/create projects via host.docker.internal:8080
  [ ] sam_specDoc_braindump(): scaffold new braindump files from template

Phase 3 — Projects map (this week)
  [ ] sam-projects skill: project registry + sam_git_status()
  [ ] sam_docker_ps() wrapper

Phase 4 — Promote to plugin (when Phase 1-3 prove the shape)
  [ ] openclaw.plugin.json + proper MCP tool registration
  [ ] Real tool calls (not just skill instructions)
```

---

## Open questions for Sam

1. What is the second Claude.ai account — whose is it, and what context should come from it?
2. Is Trendfy still alive post-May 1st or has the pivot happened?
3. What does the Bubls local setup look like — is it worth wiring in now?
4. For the Telegram hook — short responses only, or should the agent be allowed to send long responses when Sam explicitly asks for depth?
