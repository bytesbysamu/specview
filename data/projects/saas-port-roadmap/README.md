# spec-doc — SaaS Port Roadmap (bucketed)

> Combines the architectural shift (git for markdown, DB for metadata),
> the flat 79-item capability inventory, and the 18 brain dumps into
> **9 thematic buckets** plus an historical pile.
>
> Each bucket: theme → brain dumps in it → capabilities (#N from the
> flat roadmap) → port-from breakdown (🟢 verbatim / 🔵 adapt / ⚪ net new)
> → dependencies → effort.
>
> Read alongside `projects/saas-feature-roadmap.md` (the flat list) and
> the individual `projects/braindump-*.md` files.

---

## Architectural shift (load-bearing decision)

Markdown content lives in **git per-project repos**, not in SQL. The DB stores
metadata only (User, Project, Subscription, UsageCounter). Every `update_file()`
becomes a `git commit`. History (`git log`), diffs (`git diff`), revert
(`git checkout`) come free. "Connect GitHub" is a `git push` away in Phase 4.

This invalidates any pre-roadmap design that put markdown content in a SQL
column. `braindump-saas-data-layer.md` was revised to reflect this; the new
`braindump-saas-git-storage-layer.md` carries the storage layer itself.

---

## Bucket 1 — Provider & AI infrastructure

**Theme**: every AI call, what model, what tokens, what cost, what fails when.

**Brain dumps in this bucket:**
- `braindump-raise-max-tokens.md` (P0 — acute) — fix CLI provider's silent `--max-tokens` drop + truncation heuristic
- `braindump-saas-anthropic-sdk-provider.md` (P0 — deploy blocker) — SDK as production default, per-step model routing, cost accumulator + `/api/stats` endpoint (consolidates the former cost-visibility brain dump)

**Capabilities covered**: #9 SDK as default, #10 max_tokens fix, #38 truncation heuristic, #49 per-step model routing, #50 cost dashboard, #61 multi-provider env switch.

**Port-from breakdown**:
- 🟢 SDK provider shape (humanize-me's `claude.py` is the original; spec-doc has it skeleton-only)
- 🔵 Cost accumulator pattern (bubls has `_USAGE` dict)
- ⚪ Per-step model routing in workflows (uses existing `AICall.model` field)

**Depends on**: nothing — this bucket is independent.

**Effort**: ~1 day (CLI fix is 30 min; SDK + cost + startup gate is ~1 day).

---

## Bucket 2 — Persistence: DB metadata + git content

**Theme**: where state lives. SQL for what changes by row; git for what changes by line.

**Brain dumps in this bucket:**
- `braindump-saas-data-layer.md` (P1) — SQLModel + Alembic + Project entity (metadata pointer to git)
- `braindump-saas-git-storage-layer.md` (P1) — pygit2 wrapper, per-project repo, six public ops, three free endpoints (history/diff/revert)

**Capabilities covered**: #11 SQLModel/Alembic, #13 git storage, #14 Project entity, #15 user_id scoping, #20 FS→git+DB migration, #51–53 git endpoints, plus #54 GitHub integration depends on this layer.

**Port-from breakdown**:
- 🟢 SQLModel + Alembic + table-prefix convention (bubls verbatim)
- 🔵 Project entity adaptation (drop file content column, add git pointer)
- ⚪ Git storage layer itself (net-new architecture; bubls/trendfy don't have it)

**Depends on**: nothing — paired internally; ships as one Phase 1 unit.

**Effort**: ~2 days combined (1 day data-layer + 1 day git-store).

---

## Bucket 3 — Auth & multi-tenant primitives

**Theme**: identity. Who is making this call, and what can they touch.

**Brain dumps in this bucket:**
- `braindump-saas-auth-magic-link.md` (P1) — Supabase magic-link, JWT validation, `@require_auth`, User entity, dev-bypass

**Capabilities covered**: #12 User entity, #16 magic-link auth + JWKS + JWT, #17 `g.current_user` injection + decorator, #18 DEV_BYPASS_AUTH, #29 Angular AuthService + Bearer interceptor, #35 login page.

**Port-from breakdown**:
- 🟢 JWKS validation + JWT decode (bubls verbatim, generic pattern)
- 🟢 `@require_auth` decorator + `g.current_user` injection (bubls pattern)
- 🔵 Login page UI (bubls shape; design product-specific)

**Depends on**: Bucket 2 (User entity sits in the SQL store).

**Effort**: ~1 day.

---

## Bucket 4 — Monetisation

**Theme**: take money + meter usage. Free tier vs pro plan. The actual SaaS economics.

**Brain dumps in this bucket:**
- `braindump-saas-stripe-billing.md` (P2) — Stripe Checkout + webhook + Subscription + Customer Portal
- `braindump-saas-usage-metering.md` (P2) — UsageCounter + decorator + 429 paywall

**Capabilities covered**: #21–28 (all billing + metering DB/server side), #30–34 (Angular billing/usage UI), #65 annual plans (deferred), #66 coupons (deferred).

**Port-from breakdown**:
- 🟢 Almost everything (bubls has the full stack — billing module + usage module are the closest-to-verbatim ports in the project)
- 🔵 Upgrade page copy + pricing (product-specific)

**Depends on**: Bucket 2 (Subscription + UsageCounter need user_id FKs), Bucket 3 (auth populates user.id and user.plan).

**Effort**: ~2 days combined.

---

## Bucket 5 — Async & reliability

**Theme**: long-running operations. Bootstraps that take 25 minutes. Tasks that fail mid-stream. Users staring at a spinner.

**Brain dumps in this bucket:**
- `braindump-bootstrap-async.md` (P3) — 202 + polling for bootstrap; uses WorkflowRuntime + WorkflowExecution
- `braindump-streaming-task-gen.md` (P3) — partial buffer in polling response + optional SSE
- `braindump-retry-recovery.md` (P3) — regenerate failed/truncated task endpoint

**Capabilities covered**: #36 bootstrap async, #37 streaming, #39 retry/regenerate, #48 cancellation hook (NO BRAIN DUMP — small), #62 SSE for any long-running call.

**Port-from breakdown**:
- 🔵 Polling pattern (already shipped in `task_gen` from the Workflows epic; pattern reapplies)
- 🔵 SSE generator response (humanize-me pattern)
- ⚪ Cancellation hook (T3 left a stub; ~30 LOC to wire up)

**Depends on**: Workflows-as-a-Domain-Layer epic (already shipped). Internally these three brain dumps share polling/SSE plumbing but each is its own task — don't merge.

**Effort**: ~2 days combined.

---

## Bucket 6 — Pipeline self-improvement

**Theme**: making the pipeline that produces specs better at producing specs. Catches the bugs the executor currently fixes by hand.

**Brain dumps in this bucket:**
- `braindump-pipeline-self-improvement.md` (P3) — pre-emit linter + multi-doc coherence pass + structured prior-task contracts (kills the 60-line truncation root cause) + versions.md injection + project repair endpoint

**Capabilities covered**: #40 linter, #41 coherence pass, #42 structured contracts, #43 repair endpoint, #44 versions.md injection.

**Port-from breakdown**:
- ⚪ All of it — net-new infrastructure for spec-doc itself (bubls/trendfy don't generate specs of specs)

**Depends on**: nothing — independent track. Compounds because every encoded bug is one fewer hand-fix forever.

**Effort**: ~1.5 days.

---

## Bucket 7 — Differentiation features

**Theme**: what spec-doc does that nothing else does. The reasons users pay for the pro tier and tell their friends.

**Brain dumps in this bucket (existing):**
- `braindump-app-store-factory-template.md` (P4) — Ionic + Capacitor template seed

**Brain dumps NEEDED in this bucket (write):**
- `braindump-saas-github-integration.md` — OAuth + push internal repo to user's GitHub ("your data, your repo")
- `braindump-saas-spec-sharing.md` — read-only public link to a project, adapts bubls share-tracking
- `braindump-saas-landing-page.md` — marketing site, signup CTA, pricing
- `braindump-saas-onboarding.md` — first-run walkthrough (or fold into landing-page)
- `braindump-saas-settings-page.md` — profile + billing portal link + future API key (or fold into stripe-billing)

**Capabilities covered**: #54 GitHub integration, #55 share link, #56 share-event endpoint, #57 templates, #58 landing page, #59 onboarding, #60 settings page.

**Port-from breakdown**:
- 🟢 Share-event endpoint (bubls verbatim, ~50 LOC)
- 🔵 Onboarding tour pattern (bubls shape; copy domain-specific)
- 🔵 Settings page shape (bubls shape)
- ⚪ GitHub integration (net-new — depends on git-storage)
- ⚪ Landing page (net-new — marketing surface)

**Depends on**: Bucket 2 (git-storage for GitHub integration), Bucket 3 (auth for sharing/settings), Bucket 4 (Stripe portal link in settings).

**Effort**: ~3 days combined for the existing + 5 NEW brain dumps. Each is small; the cluster is the work.

---

## Bucket 8 — Operations & infra

**Theme**: when things break in production, can the team see, debug, and recover.

**Brain dumps in this bucket (existing):**
- `braindump-monorepo-refactor.md` (P4) — restructure `projects/` → `api/resources/`
- `braindump-frontend-backend-cicd.md` (P4) — Angular build in CI, multi-stage Docker
- `braindump-docker-compose-production.md` (P5) — nginx + SSL (partly redundant with Coolify Traefik from Epic 6)

**Brain dumps NEEDED in this bucket (write):**
- `braindump-saas-observability.md` — Sentry error tracking + structlog JSON + per-external-dep health checks (Anthropic, Supabase, Stripe). Bundles capabilities #19, #45, #46, #47.

**Capabilities covered**: #19 JSON error handler, #45 Sentry, #46 structlog, #47 per-dep health checks, #63 monorepo refactor, #64 frontend-backend CI, #67 rate limiting (deferred), #68 nginx + SSL (deferred).

**Port-from breakdown**:
- 🔵 Sentry wiring (~10 LOC + project setup; bubls has it)
- 🔵 structlog config (~20 LOC; bubls has it)
- 🔵 Per-dep health checks (bubls pattern via `@ConditionalOnProperty`-equivalent)
- ⚪ Rate limiting (cloud LB or Cloudflare; defer)

**Depends on**: nothing operational; observability brain dump should ship around Phase 1 so the rest is debuggable.

**Effort**: ~1.5 days for observability; rest are P4/P5 backlog.

---

## Bucket 9 — Workflows Phase 2 + 3 (deferred)

**Theme**: extending the Workflows-as-a-Domain-Layer epic that just landed.

**Brain dumps**: NONE — explicitly deferred until Phase 2 triggers fire.

**Capabilities covered**: #77 Composite workflows, #78 Decorator step wrappers, #79 JSON workflow loader + GUI.

**Port-from breakdown**: ⚪ all net-new (Workflows epic v3 brain dump is the design source).

**Triggers to fire each item**:
- #77 Composite — when a workflow needs to call another workflow as a sub-step
- #78 Decorators — when a real retry/cost/log concern shows up across multiple steps
- #79 JSON loader + GUI — when a non-developer consumer is named for the workflow builder

**Effort**: ~3 days each when triggered (out of current scope).

---

## Historical / inactive brain dumps

These exist as files but are NOT actionable. Banner-marked at the top of each file.

| File | Why |
|---|---|
| `braindump-multi-provider-cost-visibility.md` | **MERGED** into `braindump-saas-anthropic-sdk-provider.md` §5. Original kept for git history. |
| `braindump-run-chain-runner.md` | **OBSOLETE** — Workflows-as-a-Domain-Layer epic supersedes (sequential runner is `WorkflowRuntime`). |
| `braindump-express-retirement.md` | **DONE** — shipped via Epic 3. |

---

## Phasing across buckets

```
Phase 0 (now)        Bucket 1 (P0 acute fix only)          ~30 min
                     ├─ Fix CLI --max-tokens drop
                     └─ Pre-condition for everything else

Phase 1 (parallel)   Bucket 1 (rest)  +  Bucket 2  +  Bucket 8 (observability only)
                     ├─ SDK provider as default               ~1 day
                     ├─ Data-layer + git-storage              ~2 days
                     ├─ Sentry + structlog + health checks    ~1.5 days
                     └─ End: spec-doc runs in production multi-tenant

Phase 1.5            Bucket 3 (auth)                          ~1 day
                     └─ End: real users can log in

Phase 2              Bucket 4 (billing + metering)            ~2 days
                     └─ End: spec-doc charges money — public launch possible

Phase 3 (parallel)   Bucket 5 (async + reliability)  +  Bucket 6 (pipeline self-improvement)
                     ├─ Bootstrap async + streaming + retry   ~2 days
                     └─ Linter + coherence + contracts        ~1.5 days

Phase 4              Bucket 7 (differentiation)               ~3 days
                     ├─ Write 5 NEW brain dumps
                     ├─ GitHub integration (the killer feature)
                     ├─ Share link + share-event
                     ├─ Landing page + onboarding
                     └─ Settings page + templates

Phase 5+             Bucket 9 (Workflows Phase 2/3) — when triggered
                     Bucket 8 (P5 items: nginx, rate limit, monorepo refactor)
```

**Total active build effort**: ~14 days end-to-end if executed serially. Phase 1
work can parallelise across three independent tracks.

---

## What this bucketing buys

- **Read order is buckets, not files**: 9 themes vs 18 files; fewer mental moves.
- **Dependency graph is now per-bucket**: e.g., "Bucket 4 needs Buckets 2+3" is one sentence; chasing per-file deps is brittle.
- **Net-new vs port-from is per-bucket**: Buckets 1, 2 (partly), 5, 6 are mostly net-new; Buckets 3, 4 are mostly verbatim port. Lets you decide where to use port-time vs design-time.
- **Missing brain dumps cluster in Bucket 7 + 8**: 6 dumps to write, all in two themes. Cleaner than spotting them across the flat list.
- **Historical pile is named**: 3 files explicitly inactive; future readers don't waste time on them.

---

*Generated 2026-04-26 after the Workflows-as-a-Domain-Layer epic landed.
Companion to `projects/saas-feature-roadmap.md` (the flat 79-item list)
and the 18 `projects/braindump-*.md` files (the actionable backlog).*
