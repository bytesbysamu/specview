# CI & Test Quality

## What this is

Gaps in the test suite and CI pipeline identified during the ux-reader-textops epic. These are not new features — they are the quality floor that should exist before the SaaS launch. The CI pipeline exists but the coverage is thinner than it should be.

---

## Missing unit test files

Three services from exec-guide have no specs at all:

**`section-taxonomy.service.spec.ts`**
Tests for `sectionFor(project)` in `web-ng/src/app/services/section-taxonomy.service.ts`. Five branches to cover:
- Project with an active/running AI job → `active`
- Project with `implementation-guide.md` in files → `specced`
- Project with `architecture.md` or `epic.md` but no impl guide → `specced`
- Project with `braindump.md` only → `braindumps`
- Archived project → `archive`

**`project-teaser.spec.ts`**
Tests for `projectTeaser(project)` and `firstNonHeadingSentence(text)` in `web-ng/src/app/services/project-teaser.ts`. Cases: empty content, content with only headers, content with a sentence after a header, multi-sentence paragraph (should return only first).

**`ai.service.spec.ts`** (update, not create — likely exists but references deleted functions)
The service was rewritten to use the ng-openapi-gen generated client. Any existing spec that imports old interfaces (`TextOperationResponse`, direct `HttpClient.post()`) needs to be updated to test against the new client shape.

---

## E2E test coverage

The E2E framework is in place (`e2e/` directory, Playwright, `pytest-bdd`). The Phase 4 epic created the infrastructure but the actual feature scenarios are minimal.

`product-behavior.md` defines five core flows:
1. Create project + paste braindump
2. Run spec pipeline (bootstrap)
3. Open spec and run a text op
4. Apply text op result
5. View project list (grid + sections)

Each of these needs a passing BDD scenario in `e2e/features/`. Currently CI runs the E2E suite but it's unclear how many of these flows have real assertions vs. placeholder steps.

The goal: every flow in `product-behavior.md` has at least one Playwright scenario that passes in CI with `CHAIN_PROVIDER=mock`. Mock provider means specs generate immediately with deterministic output — E2E tests should be fast and reliable.

---

## Branch protection rules on master

`master` has no protection rules. This means:
- Direct pushes to master are allowed (only convention prevents it)
- No required status checks before merging PRs
- Auto-merge (`gh pr merge`) works without any required checks — CI passing is not enforced

Recommended rules:
- Require status checks: `backend`, `frontend`, `e2e`, `docker` must pass
- Require at least 1 approval (even if the only reviewer is the author — can be self-review)
- Prevent force pushes to master
- Require branches to be up to date before merging

With these in place, the auto-merge step in CI becomes meaningful: it only merges after required checks pass. Without them, it merges even if CI fails.

Branch protection is configured in GitHub repo settings > Branches > Add branch protection rule.

---

## Coverage thresholds

`pytest` runs with `--cov` but there's no threshold enforcement. A PR that drops coverage from 85% to 10% will still pass CI.

Add `--cov-fail-under=70` (or similar) to the pytest command in `ci.yml`. This makes CI fail if overall coverage drops below the threshold.

Starting at 70% is conservative enough to pass today while still catching major regressions. Raise to 80% once missing specs are written.

For frontend coverage: `ng test` doesn't currently report coverage in CI. Add `--code-coverage` to the test command and a coverage threshold in `karma.conf.js` (or `angular.json` coverage thresholds config).

---

## `app.component.ts` review warnings

Three issues from the dev-review pass that are clean-up candidates:

**`runOp(op as any)`** — should use an explicit union type for `op` instead of `as any`. Define `type TextOp = 'expand' | 'compress' | 'clarify' | 'simplify' | 'tldr' | 'bullets' | 'brainstorm' | 'rewrite' | 'undo'` and use it in the method signature.

**`[style.bottom]` inline binding in template** — should be a CSS class with `@HostBinding` or a data attribute. Inline style bindings are harder to override and harder to test.

**Missing `data-test` attributes** — E2E tests (Playwright) should target elements by `data-test` attr, not CSS classes or text. Currently missing on: status bar states, section group headers, file-dot elements, op chip buttons.

---

## `_syncElapsedTimer` setInterval not covered

The `_syncElapsedTimer` in `AppComponent` starts a 1-second interval while a gen job is running. It's cleared in the completion handlers. There's no `fakeAsync` + `tick` test that verifies the clearInterval path. This is the kind of timer leak that can cause test pollution.

Add a test in `app.component.spec.ts` using Angular's `fakeAsync` + `tick(N)` to verify that the elapsed timer stops when the job completes.

---

## CI: `ruff check` format flag

Currently `ruff check .` only lints, it doesn't check formatting. Add `ruff format --check .` as a second step in the backend job. This catches formatting inconsistencies (trailing commas, line length) that `check` alone misses.

---

## Implementation order

1. Branch protection rules — GitHub settings, 5 minutes, no code change
2. Missing unit test files (3 specs, ~3h total)
3. `ruff format --check` in CI (1-line change)
4. Coverage thresholds — `--cov-fail-under=70` (1-line change)
5. `runOp` type cast cleanup (define union type, ~30 min)
6. `data-test` attrs on key elements (template-only, ~1h)
7. `_syncElapsedTimer` fakeAsync spec (~1h)
8. E2E feature scenarios for the 5 product-behavior flows (~1 day)
