# Reference Code — Patterns to Port

These are real working patterns from sibling projects. When architecture says "port from references.md",
describe the shape to port — not the implementation detail.

## financing-plugin — Claude Code Plugin Structure

The gold standard for a well-structured Claude Code plugin.
Location: `~/Projects/financing-plugin-extracted/`

### Plugin Layout Pattern
```
plugin-name/
├── .claude-plugin/plugin.json   # Plugin metadata + version
├── agents/                      # Specialised agents as flat .md files
├── hooks/                       # SessionStart hook (context injection)
├── references/                  # Convention references (single source of truth)
├── skills/                      # Skills — each a SKILL.md
│   ├── SKILL_MAP.md             # Master index of all skills
│   ├── feature-pipeline/SKILL.md   # Orchestrator skill
│   ├── feature-requirement/SKILL.md
│   └── dev-build/SKILL.md       # Dev tools
└── docs/                        # Spec-doc specs (Epic, Architecture)
```

Key rule: **references are the source of truth** — no rules duplicated inline in agents/skills.
Skills read from `references/*.md`, never inline the same constraint twice.

### SessionStart Hook Pattern
The hook fires on every session start and injects live context into the agent.
No heavy I/O — just read files and compute a snapshot. Fast and deterministic.

### Skill File Pattern (SKILL.md)
```markdown
# Skill Name

## When to use
[Trigger conditions]

## What I do
[Steps the agent takes]

## Tools available
[Bash, Read, Write, etc.]

## Examples
[Sample invocations]
```

## OpenClaw Workspace Files — Context Injection Pattern

The workspace files already loaded by OpenClaw every session:
- `AGENTS.md` — session instructions (auto-loaded)
- `USER.md` — who Sam is (auto-loaded)
- `MEMORY.md` — curated long-term memory (auto-loaded in main session)
- `TOOLS.md` — stack + environment (auto-loaded)

Port pattern: new skills should reference these files rather than duplicating their content.
`SOUL.md` defines agent identity — skills can refer to it for tone/style.

## spec-doc Bootstrap Adapter — Async 202 + Polling Pattern

Already shipping in spec-doc. Port this pattern for any long-running skill:
1. POST trigger → return 202 + job_id immediately
2. Background thread runs the work
3. GET /status/{job_id} polls until `done: true`
4. In-process dict keyed by project/job id — no Redis needed

Location: `~/Projects/2026/spec-doc/api/modules/ai/routes/text.py` (bootstrap)
and `~/Projects/2026/spec-doc/api/modules/ai/routes/task_gen.py` (generate-task)

## Trendfy — Docker + Deploy Pattern

gunicorn config for Flask with background threads:
```
gunicorn --bind 0.0.0.0:3101 --workers 1 --threads 4 --timeout 900 --worker-class gthread
```
`--workers 1` required when using in-process state dicts (no cross-worker sharing).
`gthread` allows daemon threads to coexist with gunicorn.

## humanize-me — Flask Thin Layer Pattern

Flask as a ~150 line AI service boundary:
- All routes: validate → call AI adapter → return streaming or JSON
- No business logic in routes
- Supabase accessed only through Flask, never from frontend directly

## Specview UX Lineage — Playground & Design System Projects

Prior UX work that feeds into Playground V3. Each project built on the last.

| Project | Focus |
|---------|-------|
| `ux-reader-textops-1778237000` | Reader view, text ops & navigation UX |
| `ux-polish-newspaper-1778238000` | Newspaper aesthetic, typographic rhythm |
| `ux-grid-polish-1778368175` | App grid layout & spacing system |
| `ux-landing-grid-polish-1778450371` | Landing page grid alignment |
| `landing-v2-playground-1778400000` | Landing V2 playground exploration |
| `unified-page-v3-1778873042014` | Unified single-page app + landing |
| `live-component-playground-1778879053` | Live component playground (design patterns demo) |
| `app-v3-state-extraction-1778916148` | App V3 state extraction + playground shell |
| `ux-audit-design-refs-1778945980` | Playground 2.0 — UX audit + design system refs |

Key decisions from this lineage:
- Newspaper-feel typography (large headlines, tight body, generous whitespace)
- Grid system with 12-col desktop / 4-col mobile
- Signal-based state, no heavy frameworks
- One long scroll > multi-page nav for showcase/onboarding flows
- Design patterns demonstrated in use, not documented in isolation
