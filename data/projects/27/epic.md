# 🎯 Epic: SaaS Phase 2a — Project Isolation & Multi-Tenancy

## Business Value

Specview cannot onboard a second paying user until project isolation exists. Today, every authenticated user sees all 41 projects — there is no ownership boundary. This is not a feature gap; it is a security defect that makes the product unsellable in any multi-user context. Billing (Phase 2b) and onboarding (Phase 4) both assume per-user project state. Without this epic, neither can ship, and specview remains a single-user tool indefinitely.

Project isolation is the gate between "Sam's personal tool" and "SaaS product with revenue potential." The engineering investment is small (~1.5 days) because every architectural seam — the `Project` model with `user_id`, the `ProjectRepository` protocol, the `@require_auth` middleware, the `current_app.project_repository` DI pattern — already exists. This is a wiring job that unlocks the entire monetization roadmap.

From a market standpoint, documentation-first development tools are a growing niche, but trust is table stakes. A user who discovers they can read or delete another user's projects will never return. Shipping isolation now — before the second user signs up — means the security boundary is battle-tested before it matters commercially.

## Scope

### What This Epic Covers

- **Per-user project listing** — `GET /api/projects` returns only projects owned by the authenticated user, scoped at both the query layer and the route layer
- **Ownership verification on all project routes** — every read, update, and delete route checks `project.user_id == g.current_user.id` and returns 403 on mismatch
- **SQL repository implementation** — a concrete `ProjectRepository` backed by the existing `project` table, wired into routes via the established `current_app.project_repository` DI seam
- **Dual-write project creation** — `POST /api/projects` creates both a filesystem directory and a DB row with the authenticated user's ID, using DB-first ordering with filesystem rollback on failure
- **Existing project migration** — a one-shot idempotent script that backfills DB rows for all 41 filesystem projects, assigning them to a user specified by email (not hardcoded ID)
- **Test coverage for new ownership logic** — pytest cases for the repository, ownership checks (403 on wrong user, 404 on missing project), and migration idempotency; no regression of the 146-test baseline

### What This Epic Does NOT Cover

- ❌ **`project_member` join table / sharing roles** — no second user exists yet; a join table for one `owner` role is speculative. Re-scope when collaboration is a real requirement
- ❌ **Admin/superuser bypass** — use direct DB access for admin needs now. Re-scope if a support workflow materializes
- ❌ **Per-user slug namespacing** — global slug uniqueness stays; filesystem restructuring to `data/projects/<user_id>/<slug>/` is too expensive for zero collision probability with one real user. Re-scope at Phase 4 onboarding
- ❌ **Feature flag for cutover** — with 1.5 days and one user, deploy-and-verify beats flag infrastructure. Re-scope if rollback risk increases with more users
- ❌ **Audit logging for denied access** — valuable but outside the 1.5-day budget. Re-scope at Phase 4 when multiple real users exist
- ❌ **New-user cold-start experience** — new users will see zero projects until Phase 4 ships onboarding. Accepted gap; specview has no signups before Phase 4

## Design Decisions Required

| Decision | Options | Recommendation | Rationale |
|----------|---------|----------------|-----------|
| Response code for unauthorized project access | 403 Forbidden vs 404 Not Found | **403** | Small user base, debuggability matters, frontend can show "access denied" vs "not found" distinctly |
| Slug uniqueness scope | Global (current) vs per-user | **Global — defer to Phase 4** | Zero collision probability with one user; per-user requires filesystem restructuring |
| Migration user lookup | Hardcoded `user_id=1` vs email parameter | **Email parameter** | 10 minutes of safety against DB rebuilds |
| Dual-write failure handling | DB-first vs filesystem-first | **DB-first, rollback on filesystem failure** | Clean failure mode (nothing created); no orphan directories |

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **SQL ProjectRepository implementation** — concrete class implementing the existing `ProjectRepository` protocol, wired into the app via `current_app.project_repository` following the file-history DI pattern | Phase 1 auth wired | — | 0.3 days | High |
| 2 | **Ownership-checking route layer** — ownership decorator on ALL project routes (CRUD + `repair` + `coherence` + 3 file-history routes); 403 on wrong user, scoped listing via `list_for_user()`, dual-write on create, ownership verification on delete | Task 1 | — | 0.4 days | High |
| 3 | **Filesystem-to-DB migration script** — one-shot idempotent script that backfills `project` rows for all 41 filesystem projects, with `--user-email` lookup and post-run count verification | Task 1 | ∥ with Task 2 | 0.3 days | High |
| 4 | **Test coverage for isolation logic** — pytest cases for repository methods, ownership enforcement (403/404), migration idempotency, and dual-write; verify 146-test baseline holds | Tasks 1–3 | — | 0.3 days | High |
| 5 | **Frontend 403 handling** — Angular services interpret 403 responses distinctly from 404; project list naturally scopes to authenticated user's projects with no UI changes beyond error handling | Task 2 | ∥ with Task 4 | 0.2 days | Low |

## Success Criteria

- ✅ `GET /api/projects` returns only projects owned by the authenticated user
- ✅ `GET /api/projects/<slug>` returns 403 when accessed by a non-owner
- ✅ `PUT /api/projects/<slug>` and `DELETE /api/projects/<slug>` return 403 for non-owners
- ✅ `POST /api/projects` creates both a DB row (with `user_id`) and a filesystem directory
- ✅ All 41 existing filesystem projects have corresponding rows in `project` table assigned to Sam's user record
- ✅ Migration script is idempotent — running it twice produces the same result
- ✅ 146-test baseline passes without regression
- ✅ New repository and ownership logic have dedicated pytest coverage
- ✅ Existing E2E feature files pass without modification

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Phase 1 auth not fully wired (`g.current_user` returns stub) | Every ownership check is meaningless — false sense of security | Verify `g.current_user.id` returns a real DB user ID before starting |
| Migration runs after route enforcement enabled | Sam locked out of all 41 projects | Migration script must run and verify BEFORE deploying ownership-enforced routes |
| Missed route — one endpoint skips ownership check | Data leak for that endpoint | Structural test asserting every slug-accepting route is decorated. Note: `repair`, `coherence`, and all 3 file-history routes need the decorator too |
| Dual-write partial failure on create | Orphan DB row or orphan filesystem directory | DB-first with explicit rollback; test both failure modes |

## Related Documents

- [Analysis](./analysis.md) — Problems and open questions driving this epic
- [Solution Architecture](./architecture.md) — Dual-store design, repository wiring, decorator pattern
- [Timeline](./timeline.md) — Execution status and delivery tracking
- [Implementation Guide](./implementation-guide.md) — Step-by-step build instructions