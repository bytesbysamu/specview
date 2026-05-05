# spec-doc — SaaS Feature Roadmap (flat capability inventory)

Every capability spec-doc could use, sorted by SaaS deployment priority.
Stripped of "from app X" attribution — only the feature/capability matters.

**Status legend**:
- ✅ Already in spec-doc
- 🚧 In-flight or queued brain dump exists
- 🟢 Ready to port near-verbatim from sibling apps (bubls / humanize-me / trendfy)
- 🔵 Needs adapting (shape ports, body rewrites)
- ⚪ Net new

**Priority legend**:
- **P0** — Production deployment can't ship without these
- **P1** — Required for any multi-user use (internal beta)
- **P2** — Required for the public paid launch
- **P3** — Required for stable operations
- **P4** — Differentiation + scale
- **P5** — Nice-to-have / phase 5+

---

## P0 — Production deployment can't ship without these

| # | Capability | Status | Notes |
|---|---|---|---|
| 1 | App factory + Blueprint registration | ✅ | Done |
| 2 | CORS config | ✅ | Done |
| 3 | `/health` route + Docker healthcheck | ✅ | Epic 6 |
| 4 | Dockerfile (non-root, slim, gunicorn) | ✅ | Epic 6 |
| 5 | docker-compose for dev + Coolify prod | ✅ | Epic 6 |
| 6 | GitHub Actions CI (test → docker-build → deploy) | ✅ | Epic 6 |
| 7 | Dependabot weekly updates | ✅ | Epic 6 |
| 8 | `.env.example` documentation | ✅ | Epic 6 |
| 9 | Anthropic SDK provider as production default | 🚧 | `braindump-saas-anthropic-sdk-provider.md` — CLI doesn't run in container |
| 10 | CLI provider `--max-tokens` forward-fix | 🚧 | `braindump-raise-max-tokens.md` — silently truncating today |

## P1 — Required for any multi-user use (internal beta)

| # | Capability | Status | Notes |
|---|---|---|---|
| 11 | SQLModel + Alembic + SQLite/Postgres | 🟢 | bubls has the entire shape |
| 12 | User entity + repository | 🟢 | bubls auth module |
| 13 | **Git-backed markdown storage (per-project repo)** | ⚪ | net new — `braindump-saas-git-storage-layer.md` |
| 14 | Project entity (metadata only — git_repo_path + latest_commit_sha) | 🔵 | Adapt the Project shape to git-pointer model |
| 15 | Project ownership scoping (user_id FK on every query) | 🟢 | bubls pattern, generic |
| 16 | Supabase magic-link auth + JWKS validation + JWT middleware | 🟢 | bubls auth module |
| 17 | `g.current_user` injection + `@require_auth` decorator | 🟢 | bubls pattern |
| 18 | DEV_BYPASS_AUTH for local development | 🟢 | bubls convention |
| 19 | Centralised JSON error handler | 🔵 | bubls has it; ~50 LOC |
| 20 | Filesystem→git+DB one-shot migration script | ⚪ | spec-doc-specific (existing FS projects exist) |

## P2 — Required for the public paid launch

| # | Capability | Status | Notes |
|---|---|---|---|
| 21 | Stripe Checkout session + webhook + signature verification | 🟢 | bubls billing module |
| 22 | Subscription entity + 6 webhook event handlers | 🟢 | bubls verbatim |
| 23 | User.plan denormalisation (synced by webhook) | 🟢 | bubls pattern |
| 24 | Stripe Customer Portal link (self-service) | 🟢 | bubls helper |
| 25 | Lazy customer creation (first checkout, not signup) | 🟢 | bubls pattern |
| 26 | UsageCounter entity + atomic upsert | 🟢 | bubls usage module |
| 27 | `@check_usage_limit("feature")` decorator + 429 paywall payload | 🟢 | bubls verbatim |
| 28 | Per-feature daily caps + UTC reset | 🟢 | bubls config |
| 29 | Angular `AuthService` (Supabase JS) + Bearer interceptor | 🟢 | bubls verbatim |
| 30 | Angular `SubscriptionService` + plan signal | 🟢 | bubls verbatim |
| 31 | Angular `UsageMeterComponent` (X/N pill) | 🟢 | bubls near-verbatim |
| 32 | Angular `proGuard` route guard | 🟢 | bubls verbatim |
| 33 | Angular 429→/upgrade interceptor | 🟢 | bubls verbatim |
| 34 | Upgrade page (Stripe Checkout trigger + pricing) | 🔵 | bubls shape; copy + design product-specific |
| 35 | Login page (magic-link request form) | 🔵 | bubls shape; design product-specific |

## P3 — Required for stable operations (real users will hit these)

| # | Capability | Status | Notes |
|---|---|---|---|
| 36 | Bootstrap async (202 + polling, via WorkflowRuntime) | 🚧 | `braindump-bootstrap-async.md` — kills timeout class |
| 37 | Streaming partial output for long generations | 🚧 | `braindump-streaming-task-gen.md` |
| 38 | Truncation detection heuristic + warning badge | 🚧 | `braindump-raise-max-tokens.md` |
| 39 | Retry/regenerate failed tasks endpoint | 🚧 | `braindump-retry-recovery.md` |
| 40 | Pre-emit linter (preamble strip, etc.) | 🚧 | `braindump-pipeline-self-improvement.md` |
| 41 | Multi-doc coherence pass | 🚧 | same brain dump |
| 42 | Structured prior-task contracts (kill 60-line truncation) | 🚧 | same brain dump |
| 43 | Project repair endpoint (regen missing canonical files) | 🚧 | same brain dump |
| 44 | `versions.md` injection (kill stale Sonnet 4.6 attribution) | 🚧 | same brain dump |
| 45 | Sentry error tracking + DSN env wiring | ⚪ | bubls has it; ~10 LOC + project setup |
| 46 | structlog JSON output + request-ID propagation | ⚪ | bubls has it; ~20 LOC |
| 47 | Per-external-dep health checks (Anthropic, Supabase, Stripe) | 🔵 | bubls pattern via `@ConditionalOnProperty`-equivalent |
| 48 | Cancellation hook in WorkflowRuntime (cooperative) | ⚪ | T3 left a stub; ~30 LOC to wire up |

## P4 — Differentiation + scale

| # | Capability | Status | Notes |
|---|---|---|---|
| 49 | Per-step model routing (Haiku/Sonnet/Opus) in workflows | 🟢 | bubls pattern; AICall already accepts `model=` |
| 50 | Token usage tracking + `/api/stats` cost dashboard | 🚧 | `braindump-multi-provider-cost-visibility.md` |
| 51 | File history endpoint (`git log`) | ⚪ | Free with git-storage layer |
| 52 | File diff endpoint (`git diff`) | ⚪ | Free with git-storage layer |
| 53 | File revert endpoint (`git checkout`) | ⚪ | Free with git-storage layer |
| 54 | "Connect GitHub" — OAuth + `git push` to user's repo | ⚪ | Net new — depends on git-storage |
| 55 | Read-only public share link to a project | 🔵 | Adapt bubls share-tracking |
| 56 | Share-event analytics endpoint | 🟢 | bubls verbatim (~50 LOC) |
| 57 | App-store-factory project templates (Ionic + Capacitor seed) | 🚧 | `braindump-app-store-factory-template.md` |
| 58 | Public landing page + signup CTA + pricing | ⚪ | Net new — marketing surface |
| 59 | Onboarding tour (first-run walkthrough) | 🔵 | Pattern from bubls; copy domain-specific |
| 60 | Settings page (profile, billing portal link, API key) | 🔵 | bubls shape |
| 61 | Anthropic SDK + multi-provider env switch | 🚧 | covered in #9 + #50 |
| 62 | Streaming via SSE for any long-running call | 🔵 | humanize-me pattern; covered in #37 |
| 63 | Monorepo structural cleanup (`projects/` → `api/resources/`) | 🚧 | `braindump-monorepo-refactor.md` |
| 64 | Frontend + backend unified CI (Angular build in CI) | 🚧 | `braindump-frontend-backend-cicd.md` |

## P5 — Nice-to-have / phase 5+ / explicitly deferred

| # | Capability | Status | Notes |
|---|---|---|---|
| 65 | Annual + team Stripe plans | 🔵 | Single Price ID more for now |
| 66 | Coupon / discount codes | 🔵 | Stripe supports; UI defers |
| 67 | Rate limiting per-IP (abuse) | ⚪ | Cloud LB or Cloudflare |
| 68 | nginx + Let's Encrypt SSL stack | 🚧 | `braindump-docker-compose-production.md` — partially redundant with Coolify Traefik |
| 69 | Email transactional (welcome, project shared) | ⚪ | Resend/Postmark; deferred |
| 70 | Web push notifications | ⚪ | No consumer named |
| 71 | Multi-region replication / read replicas | ⚪ | Single Postgres for v1 |
| 72 | Vector store / semantic search across projects | ⚪ | No consumer named |
| 73 | Soft delete + trash UI | ⚪ | No consumer named |
| 74 | Workspace / team / org primitives | ⚪ | No paying team customer yet |
| 75 | Admin / customer support tools | ⚪ | Phase 5+ |
| 76 | Per-tenant API keys (BYOK) | ⚪ | Enterprise feature; deferred |
| 77 | Composite workflows (workflow as step) | ⚪ | Workflows epic Phase 2 |
| 78 | Decorator step wrappers (Retry/Log/Cost step types) | ⚪ | Workflows epic Phase 2 |
| 79 | JSON workflow loader + GUI builder | ⚪ | Workflows epic Phase 3 |

## Skipped — not relevant to web SaaS

| Capability | Why |
|---|---|
| Capacitor plugins (share, speech-recognition, media, haptics) | spec-doc is web-only |
| Apple Sign-In | magic link covers it |
| Google OAuth | magic link covers it; defer until consumer ask |
| Stripe IAP / RevenueCat | mobile-only |
| Photo library save | image-output not in scope |
| Replicate image generation | no image consumer |
| Generated-images table + URL expiration | no image consumer |
| fastlane / TestFlight CI | no mobile app |
| Mobile push notifications | web-only product |
| i18n (database-driven translations) | English-only v1 |
| Hibernate Envers audit trail | git already provides this for content |
| Field injection style debates | Python + Flask, not Spring Boot |

---

## Summary

- **79 ranked capabilities total** (40 already shipped or queued + 40 explicit deferrals/skips).
- **Portable surface is huge**: P1+P2+P3 contains 30+ items marked 🟢 or 🔵 (port verbatim or near-verbatim).
- **Net-new code concentrated in two areas**: git-storage (the differentiating storage choice) and the marketing/onboarding surface.
- **Dependency chain**: P0 → P1 → P2; P3 (reliability + pipeline self-improvement) and P4 (differentiation) can run in parallel with launch work.

---

*Generated 2026-04-26 after the Workflows-as-a-Domain-Layer epic landed.
Cross-references all 13 brain dumps in `projects/braindump-*.md` and the
spec-doc-improvements report at `projects/spec-doc-improvements-report.md`.*
