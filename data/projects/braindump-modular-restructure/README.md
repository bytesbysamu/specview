# spec-doc-api — Modular Restructure (10 modules → 4 packages, import-only)

> **Priority**: P3 — modularity + architecture clarity; lands before bucket 7's 5 new SaaS dumps
>                  so they have a clean home to land in.
> **Effort**: ~1 day (file moves + import-path updates + structural test).
> **Blocks**: nothing functionally; **enables** clean placement for bucket 7 (auth/billing/usage)
>             and the SaaS observability brain dump's `modules/observability/` package.
> **Depends on**: nothing — pure structural refactor.
> **Constraint**: **Import paths only.** No logic changes, no test reorganisation,
>                 no openapi changes, no Blueprint URL changes. The diff is mechanical.
> **Siblings**: every brain dump that adds a new module benefits from the cleaner shape.
> **Port from**: bubls package layout (already follows this hierarchy).

## What

Today `api/modules/` has **10 flat top-level packages**, three of which are tightly coupled (`spec_gen`, `task_gen`, `implementation_guide` all generate AI specs and call the chain adapter through the workflow runtime). The flat shape was right at 3 modules; at 10 it's noise. Every new SaaS feature (auth, billing, usage, observability) would add another top-level module — by Phase 2 we'd have 14+ flat modules.

This brain dump regroups the 10 existing modules into **4 cohesive packages** by domain, plus a slot for future SaaS modules. **The change is file moves + import path rewrites only.** No code logic changes, no test logic changes, no API URL changes, no Blueprint name changes.

### Current structure (10 flat modules)

```
api/modules/
├── ai/                     # text endpoints (rewrite, iterate, lint, review, generate-spec, bootstrap)
├── chain/                  # adapter + providers + types
├── context/                # read context files
├── implementation_guide/   # prompt builder for impl guides
├── projects/               # project CRUD (filesystem)
├── quality/                # pipeline self-improvement linter (just landed)
├── spec_gen/               # generate-spec endpoint (Workflows-backed)
├── task_gen/               # task generation endpoint
├── templates/              # deterministic generators (spec-index, timeline, README)
└── workflows/              # WorkflowRuntime + WorkflowExecution + steps + repository
```

### Proposed structure (4 packages + tests stays per-package)

```
api/modules/
├── ai/                              # All AI generation — was: ai + spec_gen + task_gen + implementation_guide
│   ├── routes/
│   │   ├── text.py                  # was modules/ai/routes.py
│   │   ├── spec_gen.py              # was modules/spec_gen/routes.py
│   │   └── task_gen.py              # was modules/task_gen/routes.py
│   ├── prompts/
│   │   ├── __init__.py              # was modules/ai/prompts/__init__.py
│   │   ├── builder.py               # was modules/ai/prompts/builder.py (PromptBuilder)
│   │   ├── spec_gen.py              # was modules/spec_gen/prompts.py
│   │   └── implementation_guide.py  # was modules/implementation_guide/prompts.py
│   ├── workflows/                   # AI-specific Workflow definitions
│   │   └── spec_gen/
│   │       └── generate_spec.py     # was modules/spec_gen/workflows/generate_spec.py
│   ├── services/
│   │   ├── spec_gen.py              # was modules/spec_gen/service.py
│   │   └── task_gen.py              # was modules/task_gen/service.py
│   └── tests/                       # AI-layer tests
│
├── runtime/                         # Generic execution infrastructure — was: chain + workflows
│   ├── chain/                       # was modules/chain/
│   │   ├── adapter.py
│   │   ├── providers/
│   │   ├── types.py
│   │   ├── context.py
│   │   └── errors.py
│   ├── workflows/                   # was modules/workflows/
│   │   ├── runtime.py
│   │   ├── execution.py
│   │   ├── workflow.py
│   │   ├── steps/
│   │   └── repository/
│   └── tests/
│
├── data/                            # Storage + content — was: projects + context + templates
│   ├── projects/                    # was modules/projects/
│   ├── context/                     # was modules/context/
│   ├── templates/                   # was modules/templates/
│   └── tests/
│
├── quality/                         # Pipeline self-improvement — UNCHANGED (already cohesive)
│   └── ...
│
└── (future SaaS modules land here, each as a top-level package)
    ├── auth/                        # braindump-saas-auth-magic-link
    ├── billing/                     # braindump-saas-stripe-billing
    ├── usage/                       # braindump-saas-usage-metering
    ├── observability/               # braindump-saas-observability
    └── ...
```

**10 → 4 packages**. Future SaaS modules are independent capabilities (each is a top-level package); they don't get jammed into one of the four core domains.

### File-by-file mapping

| Old path | New path |
|---|---|
| `modules/ai/routes.py` | `modules/ai/routes/text.py` |
| `modules/ai/prompts/__init__.py` | `modules/ai/prompts/__init__.py` (in place) |
| `modules/ai/prompts/builder.py` | `modules/ai/prompts/builder.py` (in place) |
| `modules/ai/errors.py` | `modules/ai/errors.py` (in place) |
| `modules/spec_gen/routes.py` | `modules/ai/routes/spec_gen.py` |
| `modules/spec_gen/prompts.py` | `modules/ai/prompts/spec_gen.py` |
| `modules/spec_gen/service.py` | `modules/ai/services/spec_gen.py` |
| `modules/spec_gen/workflows/generate_spec.py` | `modules/ai/workflows/spec_gen/generate_spec.py` |
| `modules/task_gen/routes.py` | `modules/ai/routes/task_gen.py` |
| `modules/task_gen/service.py` | `modules/ai/services/task_gen.py` |
| `modules/implementation_guide/prompts.py` | `modules/ai/prompts/implementation_guide.py` |
| `modules/chain/*` | `modules/runtime/chain/*` (no internal change) |
| `modules/workflows/*` | `modules/runtime/workflows/*` (no internal change) |
| `modules/projects/*` | `modules/data/projects/*` |
| `modules/context/*` | `modules/data/context/*` |
| `modules/templates/*` | `modules/data/templates/*` |
| `modules/quality/*` | `modules/quality/*` (in place) |

### Import path changes

Every `from modules.X import Y` becomes `from modules.<package>.X import Y`. ~50 such lines across the codebase, all mechanical:

| Old import | New import |
|---|---|
| `from modules.chain import adapter` | `from modules.runtime.chain import adapter` |
| `from modules.chain.adapter import generate` | `from modules.runtime.chain.adapter import generate` |
| `from modules.workflows.runtime import WorkflowRuntime` | `from modules.runtime.workflows.runtime import WorkflowRuntime` |
| `from modules.workflows.steps.ai_call import AICall` | `from modules.runtime.workflows.steps.ai_call import AICall` |
| `from modules.projects.service import get_project` | `from modules.data.projects.service import get_project` |
| `from modules.context.service import read_context` | `from modules.data.context.service import read_context` |
| `from modules.templates.generators import generate_spec_index` | `from modules.data.templates.generators import generate_spec_index` |
| `from modules.ai.prompts import bootstrap_extract_tasks` | (unchanged — in place) |
| `from modules.implementation_guide.prompts import build_implementation_guide_prompt` | `from modules.ai.prompts.implementation_guide import build_implementation_guide_prompt` |

A single `git grep "from modules\." | sed -e 's|modules\.chain|modules.runtime.chain|g' ...` pass + manual review covers the lot.

### `create_app.py` changes

Two lines change:

```python
# Before
ENABLED_MODULES = [
    ('modules.projects.routes',  'projects_bp'),
    ('modules.context.routes',   'context_bp'),
    ('modules.ai.routes',        'ai_bp'),
    ('modules.templates.routes', 'templates_bp'),
    ('modules.task_gen.routes',  'task_gen_bp'),
    ('modules.spec_gen.routes',  'spec_gen_bp'),
]

# After
ENABLED_MODULES = [
    ('modules.data.projects.routes',     'projects_bp'),
    ('modules.data.context.routes',      'context_bp'),
    ('modules.data.templates.routes',    'templates_bp'),
    ('modules.ai.routes.text',           'ai_bp'),
    ('modules.ai.routes.spec_gen',       'spec_gen_bp'),
    ('modules.ai.routes.task_gen',       'task_gen_bp'),
]
```

Blueprint variable names (`projects_bp`, `ai_bp`, etc.) are unchanged — they're the registered name on the app, not the import path. Route URLs are unchanged — those live in the Blueprint definition, not the file path.

### Tests

Tests stay co-located with their package. `modules/spec_gen/tests/test_routes.py` becomes `modules/ai/tests/test_spec_gen_routes.py` (rename to avoid collisions when tests merge into one folder per package). Test logic unchanged. The import-path fixes apply to test imports too.

### Structural test — pin the new shape

```python
# tests/test_structural.py
def packages_areInExpectedHierarchy():
    """The 4-package structure is the canonical shape; new code goes into one of them."""
    expected = {"ai", "data", "runtime", "quality"}
    # SaaS modules added later (auth, billing, usage, observability) are also legal
    saas_optional = {"auth", "billing", "usage", "observability"}

    actual = {
        p.name for p in (Path(__file__).parent.parent / "modules").iterdir()
        if p.is_dir() and not p.name.startswith("_")
    }
    extra = actual - expected - saas_optional
    assert not extra, (
        f"Unexpected top-level package(s): {extra}. "
        "Add to expected/saas_optional in this test, OR re-place the module under one of the existing packages."
    )
```

Locks the structure: any new top-level module must be either an SaaS capability (auth/billing/usage/observability) or accepted into the structural test's allowlist via PR. Stops the 10-module sprawl from re-emerging.

## Why now

The Workflows epic just landed. Five SaaS brain dumps queue 4 new top-level modules (`auth`, `billing`, `usage`, `observability`). Five differentiation brain dumps in bucket 7 (github-integration, spec-sharing, landing-page, onboarding, settings-page) will add another ~3–4 modules. Without a restructure, `api/modules/` reaches **17–20 flat top-level packages** by Phase 4 — actively hostile to navigation.

Doing the restructure now, before any SaaS module is written, means each new module lands in its proper place from day one. Doing it after means re-shuffling 4–8 freshly-added modules retroactively.

The bubls codebase ships this shape (per Lesson 1 architecture: `kw-customer/`, `kw-loan/`, `kw-billing/`, etc., all top-level peer packages with internal sub-domains). spec-doc grew flat because it started as 3 modules and never got pruned.

## What's missing

One decision: **flatten or nest the four packages?**
- (a) **Nest** under `modules/{ai,runtime,data,quality}/` (proposed) — clear hierarchy, one extra import segment, ~50 import-path changes
- (b) **Flatten** with naming convention (`modules/ai_routes/`, `modules/data_projects/`, etc.) — no nesting, but the prefix is just a faux-namespace
- (c) Leave as-is — 10 (then 17-20) flat modules

(a) is right. The package boundary is a real conceptual boundary; the import path should reflect it.

## Explicitly out of scope

- **Logic changes** — no function bodies modified. Pure file moves + import path updates.
- **Test logic changes** — tests move with their package; assertions unchanged.
- **API URL changes** — Blueprint URL prefixes are owned by the Blueprint declaration, not the file path. `/api/spec-gen/generate` stays `/api/spec-gen/generate`.
- **Blueprint name changes** — `spec_gen_bp`, `task_gen_bp`, etc. unchanged; only the dotted import path that resolves them changes.
- **openapi.yaml changes** — none. The route shape is independent of the package.
- **Splitting tests across packages** — tests stay co-located with their module. The `modules/X/tests/` convention is preserved.
- **Renaming `quality/` to `pipeline/`** — kept as-is; renaming is a separate concern.
- **Moving `dtos/`** — generated artifact at the api root; stays where datamodel-codegen writes it.
- **Moving `tests/` (top-level)** — root-level tests (`test_health.py`, `test_structural.py`) stay at api/tests/.
- **Splitting `chain/` into `chain_provider/` and `chain_adapter/`** — already cohesive; one package internally.
- **Migrating Workflows steps from `runtime/workflows/steps/` into the AI prompts namespace** — `AICall` is generic infrastructure; it stays in runtime/. Spec-gen-specific step kinds (none today) would land in `modules/ai/workflows/steps/`.
- **Per-feature CLAUDE.md files** — `api/CLAUDE.md` is the single source; per-package docs add maintenance burden without payoff yet.
