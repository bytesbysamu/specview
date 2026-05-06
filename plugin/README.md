# chain-agent-plugin

Claude Code plugin for spec-doc / specview. Encodes Flask/Angular/chain conventions
once so sessions never re-establish context. Routes backend CLI calls through
`chain-agent` instead of raw system prompts.

## Structure

```
plugin/
├── .claude-plugin/plugin.json     — plugin metadata
├── agents/                        — 4 domain agents
│   ├── chain-agent.md             — primary backend agent (CLI-routed)
│   ├── spec-backend.md            — Flask/SQLModel specialist
│   ├── spec-frontend.md           — Angular specialist
│   └── chain-developer.md        — full-stack coordinator
├── skills/                        — 5 skills
│   ├── SKILL_MAP.md               — master index
│   ├── dev-build/SKILL.md         — build check
│   ├── dev-test/SKILL.md          — test runner
│   ├── dev-migrate/SKILL.md       — Alembic migration
│   ├── dev-review/SKILL.md        — 3-agent code review
│   └── spec-pipeline/SKILL.md    — braindump → spec set
├── references/                    — convention source-of-truth
│   ├── chain-conventions.md       — adapter, providers, SQLModel, Alembic
│   ├── flask-conventions.md       — blueprints, services, auth, background jobs
│   └── angular-conventions.md    — signals, services, templates, polling
└── hooks/
    ├── hooks.json                 — SessionStart registration
    └── session-start.mjs          — stack detection, reference selection
```

## Quick Reference

```bash
/dev-build                    # build check
/dev-test                     # run tests (module-scoped)
/dev-migrate add_column       # Alembic scaffold + apply
/dev-review                   # 3-agent code review
/spec-pipeline my-project     # braindump → full spec set
```

## Backend Integration

Set `CHAIN_AGENT=chain-agent` in `docker-compose.override.yml` to route all
`providers/cli.py` calls through the agent:

```yaml
api:
  environment:
    CHAIN_AGENT: chain-agent
```

Without this variable, cli.py falls back to the original `--system-prompt` path.

## Conventions Rule

All rules live in `references/*.md`. Agents and skills load from there.
Never duplicate a convention rule inside an agent or skill body.
