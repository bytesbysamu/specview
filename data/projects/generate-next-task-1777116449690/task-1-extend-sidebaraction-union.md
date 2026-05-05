I'm restricted from reading the Angular frontend files directly (session is scoped to `spec-doc/api`). I'll produce the guide using the architecture and epic docs — all uncertain paths are marked `(verify)` with a resolution instruction.

---

# Task 1: Extend SidebarAction Union — Implementation Guide

## 1. Context

`SidebarAction` is the discriminated string union in `sidebar.component.ts` that `AppComponent`'s action-router switch pattern-matches against. Right now the union does not include `'generate-task'`, so TypeScript will reject that literal at both the emission site (Task 2's button) and the consumption site (Task 3's `case` branch). Adding it here — a single line — establishes the shared type boundary that unblocks both tasks to proceed in parallel. This is the only deliverable; no logic, no template, no inputs belong to this task.

**Trade-offs considered:**
- **Separate `GenerateAction` sub-union** — rejected because it introduces an unnecessary indirection layer; the existing union is flat and the new action fits the established pattern without a wrapper.
- **Enum instead of string literal union** — rejected because the rest of the codebase uses string literal unions; switching one action to an enum creates an inconsistency with no benefit at this scope.
- **String literal added to the existing union** — preferred because it is the exact pattern used by `'implement'`, `'copy'`, `'new-project'`, and every other existing action; zero structural disruption, one-line diff, immediately enforced by the TypeScript compiler.

---

## 2. Pre-flight

Run **before** editing any file:

```bash
# Confirm working tree state
git -C {WORKSPACE}/spec-doc status

# Confirm the target file is clean (no uncommitted edits)
git -C {WORKSPACE}/spec-doc diff HEAD -- src/app/sidebar/sidebar.component.ts

# Record baseline test count
cd {WORKSPACE}/spec-doc && npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -20
```

> **`{WORKSPACE}`** = the absolute path to your local `spec-doc` repo root (the directory that contains `package.json` and `proxy.conf.json`). Resolve this once before starting; all paths below use it as the anchor.

**If the target file is dirty**: stash or commit the unrelated changes before proceeding.

**Baseline recorded**: note the passing test count from the `npm test` output — you will need it for §7 Verification.

---

## 3. Files

### To Create
*(none — this task adds no new files)*

### To Modify
- `{WORKSPACE}/spec-doc/src/app/sidebar/sidebar.component.ts` *(verify path)* — adds `'generate-task'` as one new member to the existing `SidebarAction` string literal union; no other edits.

### To Leave Alone
- `{WORKSPACE}/spec-doc/src/app/app.component.ts` — handler switch lives here; Task 3 owns it.
- `{WORKSPACE}/spec-doc/src/app/sidebar/sidebar.component.html` *(verify path)* — template changes belong to Task 2.
- `{WORKSPACE}/spec-doc/src/app/sidebar/sidebar.component.spec.ts` *(verify path)* — spec additions belong to Task 4; do not touch here.
- `{WORKSPACE}/spec-doc/api/**` — entirely separate Flask service; no changes.

---

## 4. Implementation Steps

### Step 1: Locate and read the `SidebarAction` union

**Action**: Open `sidebar.component.ts` and find the `SidebarAction` type alias. Confirm its exact current form — member count, formatting, and whether it is exported — before editing.

**File**: `{WORKSPACE}/spec-doc/src/app/sidebar/sidebar.component.ts` *(verify)*

**Pattern** (expected shape, verify against actual):
```typescript
// Current — look for this declaration near the top of the file
export type SidebarAction =
  | 'implement'
  | 'copy'
  | 'new-project'
  | '<other-member>'
  // ... remaining existing members
  ;
```

**Verify**: `grep -n "SidebarAction" {WORKSPACE}/spec-doc/src/app/sidebar/sidebar.component.ts` — expect one `type SidebarAction = ...` declaration plus any usage references.

---

### Step 2: Add `'generate-task'` to the union

**Action**: Append `| 'generate-task'` to the `SidebarAction` type alias, preserving the existing formatting exactly (pipe-per-line vs. inline — match what is already there).

**File**: `{WORKSPACE}/spec-doc/src/app/sidebar/sidebar.component.ts`

**Pattern** (pipe-per-line format — adapt to match actual file style):
```typescript
export type SidebarAction =
  | 'implement'
  | 'copy'
  | 'new-project'
  | '<other-existing-member-1>'
  | '<other-existing-member-2>'
  | '<other-existing-member-3>'
  | '<other-existing-member-4>'
  | '<other-existing-member-5>'
  | 'generate-task'   // ← only this line is new
  ;
```

> **If the union is inline** (single line): append ` | 'generate-task'` before the closing semicolon, matching the surrounding spacing.

**Verify**:
```bash
grep -n "generate-task" {WORKSPACE}/spec-doc/src/app/sidebar/sidebar.component.ts
# Expect: exactly one match on the SidebarAction type line/block
```

Then do a TypeScript compilation dry-run to confirm no type errors were introduced:
```bash
cd {WORKSPACE}/spec-doc && npx tsc --noEmit
# Expect: zero errors (Tasks 2 and 3 are not yet present, so the new member
# will be unused — tsc will not error on an unused union member)
```

---

## 5. Tests

This task makes a one-line type change. The type system itself is the test: `tsc --noEmit` passing with the new member present — and no existing tests broken — is the full verification. **No new spec file is created here.** Behavioral unit tests for the button and the handler belong to Task 4.

However, if the repo has an existing structural/lint test that validates the `SidebarAction` union (e.g., an exhaustiveness check), run it now and confirm it still passes:

```bash
cd {WORKSPACE}/spec-doc && npm test -- --watch=false --browsers=ChromeHeadless --include="**/sidebar.component.spec.ts"
# Expect: same number of passing specs as baseline; zero failures
```

If the project uses ESLint with `@typescript-eslint`:
```bash
cd {WORKSPACE}/spec-doc && npx eslint src/app/sidebar/sidebar.component.ts
# Expect: zero new warnings or errors
```

---

## 6. Commit Plan

**Executor instruction**: run the commit below immediately after Step 2 passes both verify commands — do not wait until Task 2 or 3 is complete.

```
1. feat(sidebar): add 'generate-task' to SidebarAction union
```

**After Step 2 + both verify commands pass**, commit only the single modified file:

```bash
cd {WORKSPACE}/spec-doc

git add src/app/sidebar/sidebar.component.ts

git commit -m "$(cat <<'EOF'
feat(sidebar): add 'generate-task' to SidebarAction union

Extends the SidebarAction discriminated union with the 'generate-task'
literal. This is the shared type boundary that unblocks Task 2 (sidebar
button) and Task 3 (AppComponent handler) to proceed in parallel.
No logic, template, or input changes — type only.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

**Deviation logging**: if the union was not in `sidebar.component.ts` (e.g., it lives in a separate `sidebar.types.ts`), prefix the commit body with:
```
Deviations: SidebarAction found in <actual-path>, not sidebar.component.ts — edited that file instead.
```

---

## 7. Verification

```bash
cd {WORKSPACE}/spec-doc && npm test -- --watch=false --browsers=ChromeHeadless
```

**Expected delta**: N → N+0 passing (this task adds no new tests). Zero pre-existing tests broken.

Additionally:
```bash
cd {WORKSPACE}/spec-doc && npx tsc --noEmit
# Expect: zero errors
```

---

## 8. Rollback

- **Per-step**: the single commit is independently revertible:
  ```bash
  git -C {WORKSPACE}/spec-doc revert <sha-of-task1-commit>
  ```
  This restores `sidebar.component.ts` to its pre-task state without touching any other file.

- **Per-branch**: if working on a feature branch and verification fails catastrophically:
  ```bash
  git -C {WORKSPACE}/spec-doc reset --hard <pre-task1-sha>
  # or, if on a dedicated branch:
  git -C {WORKSPACE}/spec-doc checkout main && git branch -D feature/task1-sidebar-action
  ```

---

## 9. Deviations Allowed

- **`SidebarAction` is not in `sidebar.component.ts`** → search for it with `grep -r "SidebarAction" {WORKSPACE}/spec-doc/src/` and edit whichever file owns the declaration; do not duplicate the type. Log the actual path in the commit body.
- **Union is formatted inline, not pipe-per-line** → match the inline style; do not reformat the existing members. Log the style in the commit body only if you were tempted to reformat.
- **`tsc --noEmit` reveals pre-existing errors** → STOP. Do not proceed until baseline errors are understood. The pre-existing errors are not this task's responsibility, but adding to a broken type graph masks regressions.
- **Side-effect required** (push to remote, merge to main) → **[REQUIRES APPROVAL]** — stop and ask.
- **Step 2 reveals the union already contains `'generate-task'`** → the task is already done; run verification, confirm tests pass, and close the task without a new commit.

---

## 10. Out of Scope

This task is intentionally constrained to the single type addition that unblocks parallel work. Every adjacent change that "seems natural" here belongs to a later task and must not be absorbed by the executor.

- **`@Input() canGenerateTask` and `@Input() generatingTask`** — Task 2 owns these; adding them here, even as stubs, changes the component's public API before the template is ready and creates a merge conflict surface with Task 2.
- **`case 'generate-task'` in `AppComponent`'s switch** — Task 3 owns this; adding a partial case here leaves the switch in a broken state between tasks.
- **"Generate Next Task" button in the sidebar template** — Task 2 owns this entirely.
- **Karma spec for the new action** — Task 4 owns this; the component shape must be stabilised by Tasks 2 and 3 before a meaningful spec can be written.
- **`ImplementationGuideService.generateNextTask()` call** — Task 3 owns the handler; the service is already implemented and must not be modified here.
- **Reformatting or tidying other union members** — no cosmetic changes; a reformat produces a noisy diff that obscures the one meaningful line.

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for the full four-task epic
- [Epic](./epic.md) — Task scope and execution graph
- [Timeline](./timeline.md) — Status tracking (mark Task 1 done after the commit in §6 lands)