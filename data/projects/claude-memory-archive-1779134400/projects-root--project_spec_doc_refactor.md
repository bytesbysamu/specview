---
name: spec-doc monorepo pending refactors
description: Planned structural refactors for bytesbysamu/spec-doc monorepo
type: project
---

Two pending refactors (deferred, not blocking):

1. **Lift docs/ to root** — move `api/docs/` → `docs/` so it sits at same level as `api/` and `web/`
2. **Move projects/ into api/** — `projects/` (currently at monorepo root) → `api/resources/projects/` since Flask owns it; update `config.py` PROJECTS_DIR accordingly

Target structure:
```
spec-doc/
├── api/
│   └── resources/projects/
├── web/
├── docs/
├── specs/
└── Makefile
```

**Why:** docs belong to the product, not the API module. projects/ is Flask data, not root-level content.
**How to apply:** Do as a single refactor commit — update config.py BASE_DIR → resources path, move dirs, update CLAUDE.md.
