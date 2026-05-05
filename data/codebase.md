# Codebase Context — Current Target: OpenClaw Workspace (sam-plugin)

The sam-plugin lives in the OpenClaw workspace. This file describes the target environment
where generated tasks will be executed.

## OpenClaw Workspace Layout
```
~/.openclaw/workspace/           # mounted at /home/node/.openclaw/workspace in container
├── AGENTS.md                    # session startup instructions (auto-loaded)
├── MEMORY.md                    # long-term curated memory (auto-loaded in main session)
├── USER.md                      # Sam's profile and projects
├── TOOLS.md                     # stack, GitHub, environment details
├── SOUL.md                      # agent identity and values
├── IDENTITY.md                  # agent self-description
├── HEARTBEAT.md                 # proactive check-in config
├── anchor.md                    # session anchor context
├── skills/                      # workspace skills (SKILL.md files, auto-discovered)
│   ├── sam-context/
│   │   └── SKILL.md             # [TO BUILD] boot hook + live snapshot
│   ├── sam-specDoc/
│   │   └── SKILL.md             # [TO BUILD] spec-doc bridge tools
│   └── sam-projects/
│       └── SKILL.md             # [TO BUILD] project registry + git tools
└── memory/                      # daily notes + claude-ai export
    ├── YYYY-MM-DD.md            # daily logs (today + yesterday auto-loaded)
    └── claude-ai/               # searchable conversation history
```

## OpenClaw Container Environment
```
Container: openclaw-openclaw-cli-1 / openclaw-openclaw-gateway-1
Image: ghcr.io/openclaw/openclaw:latest
Node user: /home/node
Mounts:
  /home/node/.openclaw           → ~/.openclaw (config, workspace)
  /home/node/.claude             → ~/.claude   (claude CLI auth)
  /home/node/.claude.json        → ~/.claude.json
  /home/node/Projects            → ~/Projects  (all Sam's projects)
  /home/node/spec-doc-data       → ~/Projects/spec-doc-data (generated specs)
Ports: 18789 (gateway), 18790 (bridge)
Channels: Telegram (@ClawBoiSamBot), web UI
Provider: claude-cli (claude-sonnet-4-6 via Claude Code CLI)
```

## Sam's Projects on Disk (visible at /home/node/Projects)
```
~/Projects/
├── 2026/
│   ├── spec-doc/               Flask :3101 + Angular :4201
│   ├── constellation/          Next.js 15 + Flask
│   └── wardrobai/              Trendfy (Ionic + Flask)
├── bubls/                      Ionic + Angular + Capacitor
├── humanize-me/                Next.js 15 + Flask (production)
├── openclaw/                   OpenClaw gateway (Node/TS, docker-compose)
└── spec-doc-data/              Generated spec-doc project data
    └── projects/
        └── sam-s-studio-*/     Sam's Studio project (this project's output)
```

## spec-doc API Layout (secondary context)
```
~/Projects/2026/spec-doc/api/
├── create_app.py               App factory
├── config.py                   SPEC_DOC_DIR, CONTEXT_PATHS
├── openapi.yaml                API contract (source of truth)
├── dtos/models.py              Generated DTOs — never hand-edit
└── modules/
    ├── ai/                     Bootstrap + generate-task routes
    ├── chain/adapter.py        ONLY import point for AI calls
    ├── context/                Read/write builder.md, principles.md, etc.
    ├── data/projects/          Project CRUD, file read/write
    └── ai/routes/task_gen.py  POST /generate-task (async 202 + polling)
```

## Key URLs (local dev)
| Service | URL |
|---------|-----|
| spec-doc web | http://localhost:8080 |
| spec-doc API | http://localhost:3101 |
| OpenClaw gateway | http://localhost:18789 |
| Telegram bot | @ClawBoiSamBot |
