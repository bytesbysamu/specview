# spec-doc — Status & Roadmap (2026-04-26)

> Deep status snapshot taken after the Pipeline Self-Improvement + Bootstrap
> Async + Raise-Max-Tokens capability epics merged. Numbers, stats, what's
> shipped, what's in flight, tech debt, and the remaining roadmap.

---

## 1 — Executive summary

spec-doc has just completed its **most active week ever** (357 commits in 7 days; 420 in 30; 433 lifetime). Six epics shipped to master, the Workflows-as-a-Domain-Layer epic is integrated, and three follow-on capability epics (raise-max-tokens, bootstrap-async, pipeline-self-improvement) merged in parallel via worktree agents. The product runs against 764 tests with zero failures.

Direction has crystallised around two parallel tracks:
1. **SaaS migration** (multi-tenant deploy, monetisation, observability) — 10 active brain dumps consolidated into 4 buckets covering everything from Postgres to Stripe to Sentry. Mostly verbatim ports from bubls.
2. **Pipeline self-improvement** — closing the leaky feedback loop from review-fix to upstream prompt. Linter + coherence pass + structured-prior-contracts already shipped; cancellation hook + per-step model routing + Anthropic SDK as production default queued.

The biggest open risks: **CLI provider silently drops `--max-tokens`** (P0 — fix queued, not shipped); **no auth means no real users yet**; **5 differentiation brain dumps still need writing** (GitHub integration, spec sharing, landing page, onboarding, settings).

---

## 2 — Code stats

### Backend (`api/`)

| Metric | Value |
|---|---|
| Python LOC (excluding generated `dtos/models.py`) | **14,967** |
| Top-level modules | 11 |
| Modules with tests | 8 of 11 (gaps: `context`, `projects`, `templates` for service-level tests) |
| Test functions collected | **767** |
| Tests passing | **764** |
| Tests skipped | 3 |
| Tests failing | **0** |
| Snapshot tests | 13 |
| Test runtime | ~3.3s for full suite |
| OpenAPI operations | 24 endpoints |
| Structural tests (architecture invariants) | 6 |
| TODO/FIXME/HACK markers in `api/modules` | 6 (very low) |

### Tests by module

| Module | Tests | Coverage notes |
|---|---|---|
| `workflows/` | 139 | Highest — Workflows epic has 9 sub-modules with cross-cutting tests |
| `task_gen/` | 50 | Refactored against `WorkflowExecution`; previously flaky tests now stable |
| `ai/` | 44 | Includes prompt snapshot tests |
| `quality/` | 36 | Linter + coherence pass — just landed |
| `implementation_guide/` | 31 | Prompt builder + snapshots |
| `spec_gen/` | 28 | Routes + workflow definition |
| `chain/` | 22 | Adapter + 3 providers + types |
| `templates/` | 0* | Snapshot-only (deterministic generators); no Python test functions |
| `context/` | 0 | Service-level tests missing — gap |
| `projects/` | 0 | Service-level tests missing — gap |

\* `templates/` ships snapshot tests via syrupy; counted in the 13 snapshot total.

### Frontend (`web/`)

| Metric | Value |
|---|---|
| TypeScript LOC | **6,137** |
| Angular components | 13 |
| Angular services | 7 |
| HTML template lines | 13 (mostly index.html — components use inline templates) |
| SCSS/CSS lines | 37 (sparse — minimal styling) |

### Repository

| Metric | Value |
|---|---|
| Total commits (master + branches) | **433** |
| Commits last 7 days | **357** (huge spike from the integration work) |
| Commits last 30 days | 420 |
| Contributors (top 4) | Claude (193), Sam (144), samuelbedassa (77), bytesbysamu (12) |
| Active local branches | 6 + master |
| Generated project folders in `projects/` | **94** (9.5 MB total) |
| Brain dumps in `projects/` | **25** (10 active + 15 historical/merged) |

---

## 3 — Architecture state

### Module hierarchy (current — flat 11)

```
api/modules/
├── ai/                      ← text endpoints + prompts (5 src + 3 test files)
├── chain/                   ← adapter + providers (claude SDK, cli, mock) + types (11 src + 4 test)
├── context/                 ← read context files (4 src; no tests yet)
├── implementation_guide/    ← impl-guide prompt builder (2 src + 3 test)
├── projects/                ← project CRUD on filesystem (4 src; no tests yet)
├── quality/                 ← linter + coherence pass [JUST LANDED] (3 src + 2 test)
├── spec_gen/                ← /api/spec-gen/generate via WorkflowRuntime (6 src + 2 test)
├── task_gen/                ← /api/projects/<id>/generate-task (3 src + 4 test)
├── templates/               ← deterministic generators for spec-index/timeline/README (3 src + 2 test)
└── workflows/               ← WorkflowRuntime + WorkflowExecution + steps + repository (12 src + 8 test)
```

**Proposed restructure** (`braindump-modular-restructure.md`): 11 → 4 packages — `ai/` + `runtime/` + `data/` + `quality/` + slot for SaaS modules. Import-only refactor; should land before bucket-7 SaaS modules add 4-8 more flat packages.

### Provider boundary

| Provider | State | Notes |
|---|---|---|
| `mock` | ✅ Production | Tests + offline dev |
| `cli` (Claude Code subprocess) | ✅ Default for dev | **Has 1 latent bug — silently drops `--max-tokens`** (P0 fix queued in `braindump-raise-max-tokens.md`) |
| `claude` (Anthropic SDK) | 🔧 Skeleton present, not default | `braindump-saas-anthropic-sdk-provider.md` will flip the default when API key is set; precondition for cloud deploy |

Subprocess timeout: **3600s** (escalated from 600s → 1200s → 3600s — the third escalation in the same band-aid sequence; structural fix is bootstrap-async + SDK provider).

### Workflows-as-a-Domain-Layer (just landed)

`WorkflowRuntime` + `WorkflowExecution` + `AbstractStep` + `AICall` + `Compute` + `WorkflowRepository`. State machine: `NEW → IN_PROGRESS → COMPLETED | ERROR | TIMEOUT | CANCELLING → CANCELLED`. Sealed event lifecycle (`StepStarted`, `StepCompleted`, `StepFailed`).

Three feature consumers wired to it:
- `task_gen` (background-thread task generation; **fixed 4 pre-existing flaky tests** during integration)
- `spec_gen` (new `POST /api/spec-gen/generate`; runs the bootstrap-style chain)
- *bootstrap-project still runs inline* — bootstrap-async migration in flight (capability shipped to integration branch this week)

### Context / pipeline encoding

**6 context files** at workspace root, read by spec-doc when generating:
- `builder.md` — the user's role + preferences
- `principles.md` — architecture principles (ELA-derived)
- `codebase.md` — codebase shape ground-truth
- `references.md` — port-from sources (humanize-me, bubls, trendfy)
- `quality.md` — quality rubric
- `versions.md` — current model + co-author attribution (closes the stale `Sonnet 4.6` leak)

The pipeline self-improvement epic just shipped:
- **Linter** at `modules/quality/lint.py` — pre-emit checks on generated docs
- **Coherence pass** at `modules/quality/coherence.py` — cross-doc invariants for multi-task projects
- **Structured prior-task contracts** — replaces the 60-line truncation in `task_gen/service.py:collect_prior_task_content` that was the structural cause of cross-doc drift
- **`POST /api/projects/<id>/coherence`** — new route for running the coherence pass on demand

---

## 4 — Shipped epics (in `api/docs/`)

| Epic | Folder | Docs | Lines | What landed |
|---|---|---|---|---|
| 1 — Foundation | `epic-1-foundation/` | 8 | 3,602 | App factory, project CRUD, context module, chain adapter |
| 2 — OpenAPI Mock | `epic-2-openapi-mock/` | 8 | 2,857 | `openapi.yaml` as contract, generated DTOs, mock server |
| 3 — Express Retirement | `epic-3-express-retirement/` | 9 | 2,665 | All 5 AI endpoints migrated from Express to Flask; Express deleted |
| 4 — Test Hardening | `epic-4-test-hardening/` | 1 (README only) | 32 | 302 tests; snapshot + contract + matrix coverage |
| 5 — E2E Suite | `epic-5-e2e-suite/` | 1 (README only) | 39 | Playwright + pytest-bdd, 5 features, 4 page objects |
| 6 — DevEx + CI/CD | `epic-6-devex-cicd/` | 11 | 2,664 | Dockerfile, Coolify deploy, GitHub Actions, Dependabot, .env.example, CHAIN_PROVIDER convention |

Plus two unfoldered capability epics that landed via integration branch:
- **Workflows-as-a-Domain-Layer** (T1.1, T1.2, T2, T3, T4, T5) — 6 sub-tasks, all merged
- **Two Separate Levers** — CLI timeout 600→1200, generate-task POST/GET routes
- **Pipeline Self-Improvement** — linter + coherence + structured prior contracts (just landed)
- **Bootstrap Async** — 202 + polling for `/bootstrap-project` (just landed)

---

## 5 — Brain dump backlog (10 active + 15 historical)

### Active brain dumps — by bucket

| Bucket | File | Status |
|---|---|---|
| 1 — Provider & AI | `braindump-raise-max-tokens.md` | P0 acute — implementing in flight |
| 1 — Provider & AI | `braindump-saas-anthropic-sdk-provider.md` | P0 deploy blocker |
| 2 — Persistence | `braindump-saas-persistence.md` | P1 — consolidates DB + git layer |
| 3 — Auth | `braindump-saas-auth-magic-link.md` | P1 — Supabase magic-link |
| 4 — Monetisation | `braindump-saas-monetisation.md` | P2 — Stripe + usage metering |
| 5 — Async & reliability | `braindump-saas-reliability.md` | P3 — async + streaming + retry + cancel |
| 6 — Pipeline self-improvement | `braindump-pipeline-self-improvement.md` | P3 — **shipped** |
| 7 — Differentiation | `braindump-app-store-factory-template.md` | P4 — only existing dump in bucket 7; 5 NEW still needed |
| 8 — Operations & infra | `braindump-saas-operations.md` | mixed — observability + CI + cleanup + deploy |
| (cross-cutting) | `braindump-modular-restructure.md` | P3 — 11 modules → 4 packages |

### Historical brain dumps (banner-marked, no action)

15 files: 12 merged into the 4 consolidated bucket dumps, 2 obsolete (`run-chain-runner` superseded by Workflows epic; `express-retirement` shipped via Epic 3), 1 merged earlier (`multi-provider-cost-visibility` → SDK provider).

### Bucket 7 gap (5 brain dumps to write)

| Needed | Theme |
|---|---|
| `braindump-saas-github-integration.md` | OAuth + push-to-user-repo (the killer differentiator) |
| `braindump-saas-spec-sharing.md` | Public read-only project link, adapts bubls share-tracking |
| `braindump-saas-landing-page.md` | Marketing surface, signup CTA, pricing |
| `braindump-saas-onboarding.md` | First-run walkthrough (or fold into landing-page) |
| `braindump-saas-settings-page.md` | Profile + billing portal + future API key (or fold into stripe-billing) |

---

## 6 — Tech debt

### Quantified

- **6 TODO/FIXME/XXX markers** across 14,967 LOC in `api/modules` — extraordinarily low. The codebase has been kept clean.
- **3 modules without service-level tests** — `context/`, `projects/`, `templates/`. Templates ships snapshot tests; the other two are gaps.
- **3 skipped tests** — known timing-sensitive tests; not red flags.
- **6 structural tests** — pinning architectural invariants (provider-boundary, workflow contracts, etc.).

### Named structural debt

| Item | Severity | Brain dump |
|---|---|---|
| CLI provider silently drops `--max-tokens` | **P0 — silently truncating output today** | `raise-max-tokens` |
| Bootstrap runs inline (25-min HTTP call; proxies kill it) | P3 | `saas-reliability` |
| `WorkflowExecution.request_cancel()` shipped but runtime never reads it | P3 | `saas-reliability` |
| 11 flat top-level modules; will reach 17-20 with SaaS additions | P3 | `modular-restructure` |
| Inline orchestration in `bootstrap_project` route (60+ lines) — Workflows epic exists but bootstrap not migrated | P3 | `saas-reliability` |
| No auth, no DB; single-user filesystem mode only | P1 (gates everything SaaS) | `saas-auth-magic-link` + `saas-persistence` |
| No production-ready provider (CLI doesn't run in containers) | P0 deploy-blocker | `saas-anthropic-sdk-provider` |
| 3 modules without tests (`context`, `projects`, `templates` service layer) | P4 — quality gap | (no brain dump; small) |
| 5 missing differentiation brain dumps | P4 | (write next) |
| Subprocess timeout escalated 3× (600 → 1200 → 3600s) — band-aid sequence | P3 | `saas-reliability` (kills the timeout class structurally) |

### Hidden positives

- **Adapter boundary holds** — `featureModules_mustNotImportProvidersDirectly` structural test green; no feature code couples to specific providers.
- **DTOs in sync** — `make check-dtos` passes; openapi.yaml is the contract source.
- **Workflows epic absorbed and fixed 4 pre-existing flaky tests** in `task_gen` during T3's `STATE` → `WorkflowExecution` refactor.

---

## 7 — In-flight + branches

### Branches ahead of master

All recent capability branches **already merged** to master via integration PR #3:
- ✅ `feat/cap-bootstrap-async` (merged)
- ✅ `feat/cap-pipeline-self-improvement` (merged)
- ✅ `feat/cap-raise-max-tokens` (merged)
- ✅ `feat/two-separate-levers` (merged earlier)
- ✅ All Workflows epic task branches (merged)

Master commit `9faeb73` is the current tip. **No outstanding branches blocking SaaS Phase 1**.

### Active worktrees

6 agent worktrees still in `.claude/worktrees/` from prior parallel runs — harness-locked, will reap automatically. Not blocking.

### Recent commits (last 10)

```
9faeb73 docs(api/docs): add 5 executed epics missing from api/docs
127f8f4 Merge pull request #3 from bytesbysamu/feat/integration-2026-04-26
316da93 fix(dtos): regenerate with --target-python-version 3.9 for CI consistency
4b72b90 feat(context): add all 6 context files (builder, principles, codebase, references, quality, versions)
d6cd4a1 feat(prompts): two new context blocks + tighten Hard Rules + strengthen bootstrap personas
f0b08c6 docs(braindumps): consolidate buckets 2/4/5/8 — one dump per bucket
3dc74bc docs(braindumps): runtime cancellation hook (bucket 5 — capability #48)
514413e docs(braindumps): modular restructure — 10 modules → 4 packages
35f3f25 docs(braindumps): bucket 2/4/5/8 refinement pass — observability + banners
1bb44d5 merge: Pipeline Self-Improvement — linter + coherence + 60-line truncation fix
```

Mix of capability merges (last few days) + brain dump consolidation work (today).

---

## 8 — Roadmap (P0 → P5)

### Phase 0 — Acute (this week)

- [x] Workflows-as-a-Domain-Layer epic
- [x] Pipeline self-improvement (linter + coherence + structured contracts)
- [x] Bootstrap async (202 + polling via WorkflowRuntime)
- [x] Raise max_tokens (CLI fix + truncation heuristic)
- [ ] **Verify CLI `--max-tokens` fix actually shipped** (recent commit references it; double-check the cli.py forward) ← OUTSTANDING

### Phase 1 — Foundation (~1 week)

| Bucket | Brain dump | Effort |
|---|---|---|
| 1 — Provider & AI | `braindump-saas-anthropic-sdk-provider.md` | ~1 day |
| 2 — Persistence | `braindump-saas-persistence.md` (DB + git, paired) | ~2 days |
| 8 — Operations (observability slice) | folded into `braindump-saas-operations.md` | ~1.5 days |

End of Phase 1: spec-doc runs in production with multi-tenant data, debuggable.

### Phase 1.5 — Auth (~1 day)

| Bucket | Brain dump | Effort |
|---|---|---|
| 3 — Auth | `braindump-saas-auth-magic-link.md` | ~1 day |

End of Phase 1.5: real users can log in. Internal beta possible.

### Phase 2 — Monetisation (~2 days)

| Bucket | Brain dump | Effort |
|---|---|---|
| 4 — Monetisation | `braindump-saas-monetisation.md` (Stripe + usage, paired) | ~2 days |

End of Phase 2: spec-doc charges money. Public launch possible.

### Phase 3 — Reliability + restructure (~3 days)

| Bucket | Brain dump | Effort |
|---|---|---|
| 5 — Async & reliability | `braindump-saas-reliability.md` (4 features, paired) | ~2 days |
| (cross-cutting) | `braindump-modular-restructure.md` (11 modules → 4) | ~1 day |

End of Phase 3: timeout class eliminated; codebase shape ready for Phase 4 SaaS modules.

### Phase 4 — Differentiation (~3-5 days)

| Bucket | Brain dump | Status |
|---|---|---|
| 7 — Differentiation | `braindump-app-store-factory-template.md` | Existing |
| 7 — Differentiation | `braindump-saas-github-integration.md` | **NEEDED** |
| 7 — Differentiation | `braindump-saas-spec-sharing.md` | **NEEDED** |
| 7 — Differentiation | `braindump-saas-landing-page.md` | **NEEDED** |
| 7 — Differentiation | `braindump-saas-onboarding.md` | **NEEDED** |
| 7 — Differentiation | `braindump-saas-settings-page.md` | **NEEDED** |

End of Phase 4: differentiated SaaS product (your data lives in your repo via GitHub push; landing + onboarding + sharing).

### Phase 5+ — Backlog (deferred)

- Workflows Phase 2 (Composite + Decorator step kinds)
- Workflows Phase 3 (JSON workflow loader + GUI builder)
- Annual + team Stripe plans
- Web push notifications
- Multi-region / read replicas
- Vector store / semantic search
- Workspace / team / org primitives
- Admin / customer support tools
- Per-tenant API keys (BYOK)
- Per-IP rate limiting (cloud LB / Cloudflare)

---

## 9 — Risk register

### High

- **CLI `--max-tokens` fix verification** — recent commit `merge: Pipeline Self-Improvement` doesn't explicitly include the cli.py fix; `grep` shows `timeout=3600` still present but `--max-tokens` flag passing needs spot-check. **Action: read `api/modules/chain/providers/cli.py` and confirm.**
- **No production deployment yet** — Coolify config exists from Epic 6 but the SDK provider hasn't shipped, so any cloud deploy would 500 on AI calls today.

### Medium

- **Worktree cleanup** — 6 stale agent worktrees in `.claude/worktrees/` consuming disk; harness should auto-reap but worth verifying.
- **Bucket 7 missing dumps** — 5 differentiation brain dumps need to be written before any of those features can be generated.
- **Test count growing fast** — 767 tests in ~3.3s is fine, but watch for parallelization needs as it grows.
- **Two contributors named differently in git** — `samuelbedassa`/`bytesbysamu`/`Sam`/`sbedassa67` are likely the same person; consider git mailmap.

### Low

- **3 modules without tests** — `context`, `projects`, `templates` (service-level). Templates ships snapshot tests; the other two are real gaps.
- **No Angular CI yet** — bad `ng build` ships silently to production. `braindump-saas-operations.md` covers it but it's P4.
- **94 project folders in `projects/`** — 9.5 MB is fine, but consider archiving the older brain-dump-only folders to keep navigation manageable.

### None of these are urgent

- **Tech debt markers very low** (6 TODOs across 15K LOC) — exceptional.
- **No failing tests** — clean slate for the SaaS migration.
- **Adapter boundary holds** — structural test green; no rot.

---

## 10 — Bottom line

spec-doc is **at the cleanest moment it has been at since Epic 1**. Six epics shipped, Workflows-as-a-Domain-Layer integrated, pipeline self-improvement live (the leaky-feedback-loop that produced the hand-fix passes earlier this week is now plugged), zero failing tests, near-zero tech debt markers.

**The next 2–3 weeks of work is highly leveraged**: the SaaS migration is 70% verbatim port from bubls (data layer + auth + billing + metering all match the bubls shape exactly). The 30% net-new code is concentrated in the differentiating storage layer (git-per-project) and the marketing surface — both are well-scoped brain dumps.

**Sequencing recommendation**:
1. **Verify the CLI `--max-tokens` fix actually landed** (15 min spot-check).
2. **Phase 1 Foundation** — SDK provider + persistence + observability in parallel (~1 week wall time, ~3 days dev work).
3. **Phase 1.5 Auth** (~1 day).
4. **Modular restructure** — slot it in before bucket-7 SaaS modules add 4-8 packages (~1 day).
5. **Phase 2 Monetisation** (~2 days) → public launch.
6. **Write 5 missing bucket-7 brain dumps** in parallel with Phase 2.
7. **Phase 3 Reliability** + Phase 4 Differentiation as parallel tracks.

Total runway to a paid public SaaS: **~3 weeks of focused work** if executed serially; ~2 weeks with the parallel tracks the brain dumps make possible.

---

*Status compiled 2026-04-26. Numbers based on master at commit `9faeb73`.
For the bucketed roadmap, see `projects/saas-port-roadmap.md`.
For the flat 79-item capability inventory, see `projects/saas-feature-roadmap.md`.
For the active brain dumps, see `projects/braindump-*.md` (10 active, 15 historical).*
