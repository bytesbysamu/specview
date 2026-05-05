# Builder Profile — Sam

## Role
Solo founder and full-stack engineer. Building across multiple projects simultaneously.
Primary consumer of all generated specs — implementation guides must be self-contained.

## Active Projects (2026)
- **sam-plugin** — personal OpenClaw plugin (this project); wires agent to Sam's live systems
- **spec-doc** — this tool (Flask :3101 + Angular :4201); documentation-first dev methodology
- **humanize-me** — live Flask + Next.js AI humanizer; production at humaniz.me
- **Bubls** — Ionic + Capacitor mobile app (event discovery, Zürich); Angular + Flask
- **Trendfy** — wardrobai/trendfy.me; AI fashion photoshoot; kill date passed, status TBD
- **OpenClaw** — local AI agent gateway; runs claude-cli provider, Telegram-connected

## Stack Preferences
- **Backend**: Python / Flask (thin, ~150 lines, Blueprints, openapi.yaml-first)
- **Frontend (web)**: Angular (standalone components, signals) or Next.js 15 + shadcn/ui
- **Frontend (mobile)**: Ionic + Capacitor (iOS 16+, Angular)
- **AI**: Claude CLI (dev) → Anthropic SDK (prod); chain adapter pattern
- **Deploy**: Docker Compose → Coolify; single gunicorn + nginx pattern
- **Agent platform**: OpenClaw (local gateway, claude-cli provider, Telegram channel)

## Engineering Preferences
- Brain dump → AI structures it → ship. Minimal viable shape, not maximum abstraction
- Small focused modules with clear boundaries — no god classes, no god files
- Adapter pattern for all external services (AI, DB, storage)
- In-process state (module-level dict + threading.Lock) is fine for single-consumer async
- No speculative abstractions — build for the one concrete case that exists now
- Files under 200 lines; named exports; one component per file
- Build order: frontend with mock data first → Flask built to match the UI's API contract

## Known Constraints
- Solo developer — no handoff; guides must be runnable by one person end-to-end
- No Redis, no Postgres (unless Supabase via Flask), no external queue
- Claude CLI subprocess timeout: 3600s; Anthropic SDK: no practical ceiling
- OpenClaw workspace plugin system: skills first (SKILL.md files), graduate to full plugin when needed
- Telegram is the primary mobile interface — responses must stay under 4096 chars
