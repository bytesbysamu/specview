---
name: dev-migrate
description: "Use this skill when the user wants to add a column, create a table, change the database schema, or mentions a migration. Scaffolds an Alembic migration, reviews it, applies it, and verifies the schema."
---

# /dev-migrate — Alembic migration

Scaffold, review, apply, and verify an Alembic migration.

## Parameters

- `$ARGUMENTS` — migration description (snake_case, e.g. `add_project_tags`)

## Procedure

### Step 1 — Auto-generate

```bash
cd /path/to/specview/api
alembic revision --autogenerate -m "$ARGUMENTS"
```

Open the generated file at `api/migrations/versions/`.

### Step 2 — Review gate

Read the generated migration. Verify:
- Only the intended tables/columns are affected.
- `downgrade()` is implemented (not `pass`).
- No combined schema + data changes.
- No column drops that break running application code.

If the migration is unsafe: report the issue and stop. Do not apply.

### Step 3 — Apply

```bash
cd /path/to/specview/api
alembic upgrade head
```

### Step 4 — Verify

```bash
cd /path/to/specview/api
alembic current
```

Confirm the head revision matches the new migration.

## Output Format

**Success:**
```
Migration: applied (add_project_tags)
Revision: abc123def456 (head)
Changes: +2 columns on projects table
```

**Failure (unsafe):**
```
Migration: BLOCKED
Reason: downgrade() is empty — implement rollback before applying.
```

## Abort Conditions

- `downgrade()` is `pass` or missing.
- Migration drops a column still referenced in application code.
- More than one concern in a single migration.

## Allowed Tools

Bash, Read, Glob, Grep, Write, Edit
