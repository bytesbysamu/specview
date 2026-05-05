# 🔍 Sam's Studio — Analysis

## The Problem
Sam's OpenClaw agent starts every session with only static context (MEMORY.md, USER.md, claude.ai export) and generic tools. His live systems — spec-doc, git repos, Docker containers — are reachable but unwired. The agent asks "what are you working on?" instead of knowing.

## Hard Constraints
- spec-doc API at `host.docker.internal:8080` must be reachable; all bridge tools fail if it's not
- `~/Projects` must be mounted at `/home/node/Projects` before any filesystem tool works
- v1 is SKILL.md only — no build step, no compiled plugin, no real MCP tool registration
- Plugin stays local (`~/.openclaw/workspace/`); never published to ClawHub
- Telegram hard limit is 4096 chars — platform constraint, not a preference

## Open Questions
- **Boot hook mechanism**: live compute each session (docker ps + git + curl) or cron writes `daily-context.md` once per morning the agent reads? — Option A burns tokens on every Telegram DM; Option B risks stale data
- **Telegram length guard**: the brain dump says hook (fires automatically); the appended analysis says skill instruction (agent self-limits) — contradicted within the same document; must be resolved before Phase 1 is specced
- **spec-doc localhost auth**: do calls from inside OpenClaw skip RS256 JWT enforcement, or does the bridge need a stored dev token? Determines whether tools are 5 lines or 20
- **`sam_specDoc_braindump` template**: which file — `braindump-saas-monetisation.md`, a generic skeleton, or something else? No scaffolding tool can be specced without a concrete answer
- **Second Claude.ai account**: whose is it (Lea's? work?)? Affects what gets seeded into MEMORY.md before any memory import work starts
- **Project map gaps**: `humaniz.me` (primary revenue project) is absent; `clawboi` and `openclaw` appear at conflicting paths — which is canonical?
- **Trendfy post-May 1**: still live or pivoted? Dead projects shouldn't be in the registry; live ones need a confirmed URL

## Dependencies & Sequencing
- Boot hook mechanism decision blocks Phase 1 — context skill can't be specced without knowing live vs. file-read
- spec-doc auth answer blocks Phase 2 — bridge tools can't be written until localhost auth behaviour is confirmed
- Project map completeness blocks Phase 3 — `humaniz.me` and Trendfy gaps must close before the registry is finalised
- Phase 1–3 completion blocks Phase 4 — plugin graduation is explicitly gated on proving the skill shape works

## Explicitly Out of Scope
- Architecture section, file tree, code blocks → route to architecture.md; pulled from this document
- Session startup sequence diagram → route to implementation guide
- Build phases with task checkboxes → route to epic.md
- Proactive Telegram push — heartbeat config, not sam-plugin; re-scope only when a dedicated heartbeat plugin exists
- `sam_docker_ps()` — Docker socket access inside the OpenClaw container is unconfirmed; defer until socket mount is verified
- Bubls data access — Bubls not running locally; re-scope when it has a local URL and confirmed stack