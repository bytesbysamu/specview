# 📖 SaaS Auth — Magic Link

> Overview and quick start for this capability.

---

## What This Is

SaaS Auth — Magic Link is a capability defined by the following documents:

| Document | Purpose |
|----------|---------|
| [Spec Index](./spec-index.md) | Entry point for Claude Code |
| [Analysis](./analysis.md) | Problems we're solving |
| [Epic](./epic.md) | Scope, tasks, success criteria |
| [Architecture](./architecture.md) | System design |
| [Timeline](./timeline.md) | Status tracking |
| [Task 1](./task-1-auth-service-jwt-verifier.md) | Auth service + JWT verifier |
| [Task 2](./task-2-require-auth-decorator-routes.md) | `@require_auth` decorator + `auth_bp` routes |
| [Task 3](./task-3-protect-existing-routes.md) | Protect existing routes with `@require_auth` |
| [Task 4](./task-4-angular-auth-service-interceptor.md) | Angular auth service + interceptor + login flow |

---

## Quick Start

1. Read [Analysis](./analysis.md) to understand the problems
2. Read [Epic](./epic.md) to understand scope and tasks
3. Read [Architecture](./architecture.md) before implementing
4. Track progress in [Timeline](./timeline.md)

---

## For Claude Code

```
Read this capability's docs and implement the next task:

@spec-index.md
@epic.md
@architecture.md

Implement Task 1 from the backlog. Follow architecture patterns.
```

---

## Document Guidelines

- **Status** belongs ONLY in [Timeline](./timeline.md)
- **Reference, don't duplicate** — link to other docs
- **Each doc has ONE job** — don't mix concerns

---

**Created**: 2026-04-26
