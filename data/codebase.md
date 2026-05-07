# Codebase Context — specview

specview is a self-hosted spec generation tool. Users paste a braindump; an AI chain
generates analysis, epic, architecture, timeline, and implementation guide.

## Project Layout

```
/Users/sam/Projects/specview/
├── api/                            Flask API (Python 3.11)
│   ├── app.py                      App entry point (python app.py → port 5001)
│   ├── config.py                   SPEC_DOC_DIR, PROJECTS_DIR, CONTEXT_PATHS
│   └── modules/
│       ├── ai/                     Spec generation routes + services
│       │   ├── prompts/            Python prompt builders (being migrated out)
│       │   ├── services/           epic_guide.py, task_gen.py
│       │   ├── workflows/spec_gen/ bootstrap.py (4-step chain)
│       │   └── routes/             spec_gen.py, task_gen.py, text.py, stats.py
│       ├── runtime/chain/          AI adapter layer (only AI call boundary)
│       │   ├── adapter.py          generate(), stream(), rewrite(), stream_generate()
│       │   └── providers/          cli.py, claude.py, mock.py
│       ├── auth/                   JWT auth (require_auth decorator)
│       ├── data/                   Projects CRUD, context file service
│       └── quality/                lint_task_guide() — pre-write lint gate
├── web-ng/                         Angular 17 SPA (signals, no NgRx)
│   └── src/app/                    Components, services, routing
├── landing/                        Static marketing page (nginx:alpine)
├── plugin/                         Claude Code plugin
│   ├── agents/                     chain-agent, spec-backend, spec-frontend, chain-developer
│   ├── references/                 chain-conventions.md, flask-conventions.md, angular-conventions.md
│   └── skills/                     dev-build, dev-test, dev-migrate, dev-review,
│                                   spec-pipeline, impl-guide, exec-guide
├── .claude/                        Active plugin wiring (agents, skills, settings)
└── data/                           Runtime data (SPEC_DOC_DIR)
    ├── builder.md                  Builder profile context
    ├── principles.md               Engineering principles
    ├── codebase.md                 This file
    ├── references.md               Reference code patterns
    ├── quality.md                  Lint + coherence rules
    ├── versions.md                 Deployment versions fact sheet
    └── projects/                   Per-project spec files
        └── <project-id>/
            ├── project.json        { name, createdAt }
            ├── braindump.md
            ├── analysis.md
            ├── epic.md
            ├── architecture.md
            ├── timeline.md
            └── implementation-guide.md
```

## Key URLs (local dev, no Docker)

| Service | URL |
|---------|-----|
| Flask API | http://localhost:5001 |
| Angular SPA | http://localhost:4201 |

## Chain Adapter

All AI calls go through `modules/runtime/chain/adapter.py` only. Never import from `providers/*` directly.

- `CHAIN_PROVIDER=cli` → subprocess `claude -p` (local dev + Docker)
- `CHAIN_AGENT=chain-agent` → routes through `claude --agent chain-agent -p`
- `CHAIN_PROVIDER=mock` → deterministic fixture output (tests only)

## Background Jobs

Long AI generation runs in `threading.Thread`. State in module-level dict.
`snapshot(job_id)` → `{ running, done, error?, files? }`.

## Test Suite

```bash
cd /Users/sam/Projects/specview/api
pytest -q          # full suite
pytest modules/ai/ # AI module only
```
