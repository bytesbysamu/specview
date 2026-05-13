# 🔍 SaaS Phase 2a: Project Isolation & Multi-Tenancy — Analysis

## The Problem
Every authenticated user sees all 41 projects because routes delegate to a filesystem-only `service.py` that ignores `g.current_user`. The DB model, repository protocol, migration FK, and auth middleware all exist — none are wired together. This is a connection job, not a design job.

## Hard Constraints
- Phase 1 auth (`@require_auth` + `g.current_user`) must be fully wired before this starts
- 146-test baseline (39% statement, 21% branch) must not regress
- `current_app.project_repository` DI seam already established by file history routes — must follow the same pattern
- Dual-store split is locked: DB owns identity/ownership, filesystem owns markdown content
- ~1.5 day budget — no room for speculative abstractions

## Open Questions
- **403 or 404 for "not your project"?** — 403 is debuggable and honest (good for small user base now), 404 hides project existence (good for public SaaS later). Pick one; it touches every route.
- **Slug uniqueness: global or per-user?** — Global is current schema and keeps filesystem flat, but two users can never share a slug. Per-user requires composite constraint + filesystem restructuring (`data/projects/<user_id>/<slug>/`). The braindump says "keep global, decide at Phase 4" but the migration script bakes this assumption into real data.
- **Migration script: hardcoded `user_id=1` or lookup by email?** — Hardcoding assumes Sam is always ID 1. Email lookup (`--user-email`) is 10 minutes of safety against DB rebuilds.
- **Dual-write failure order?** — DB-first then filesystem (rollback = delete row) is cleanest. Needs an explicit decision because the braindump mentions it but doesn't commit.

## Dependencies & Sequencing
- **Phase 1 → 2a**: `g.current_user` must return a real user object with `.id` — if it's still a stub, every ownership check is meaningless
- **Migration script → flag flip**: The 41 projects must have DB rows BEFORE routes start enforcing ownership, or Sam gets locked out of everything
- **2a → 2b**: Billing UI assumes per-user project state; can't scope billing without ownership
- **2a → Phase 4 (cold-start gap)**: New users post-2a see zero projects. If Phase 4 ships weeks later, specview is useless for signups in between. Either ship a stopgap (sample project?) with 2a, or accept no new-user onboarding until Phase 4

## Explicitly Out of Scope
- **`project_member` join table / sharing roles** — no second user exists yet; adding a join table for one `owner` role is speculative. Re-scope when sharing or collaboration appears in a real requirement
- **Admin/superuser bypass** — use direct DB access for admin needs now. Re-scope if a support workflow materializes
- **Feature flag for cutover** — with 1.5 days and one user, deploy-and-verify beats flag infrastructure. Re-scope if rollback risk increases with more users
- **Audit logging for denied access** — nice but not in the 1.5-day budget. Re-scope at Phase 4 when multiple real users exist
- **Per-user slug namespacing / filesystem restructuring** — too expensive now, and the collision probability is zero with one real user. Re-scope at Phase 4 onboarding

---
*Cross-references: [Solution Architecture](./architecture.md) · [Epic](./epic.md) · [Implementation Guide](./implementation-guide.md)*