# spec-doc — Deployment Config Fragmentation Cleanup

> **Priority**: P2 — three bugs that would break the in-flight `aligning-spec-doc-deployment` epic if executed as written, plus three dead files that should be deleted before that epic starts.
> **Effort**: ~0.5 days as a pre-flight task, OR fold into existing epic's Task 1.
> **Blocks**: `projects/aligning-spec-doc-deployment-1777307253079/` — that epic's Task 3 only edits `api/docker-compose.yml`, but Coolify reads the *root* `docker-compose.yml`. Without resolving canonicality first, the epic ships and Coolify still runs the old monolith.
> **Depends on**: nothing.
> **Siblings**: `aligning-spec-doc-deployment` (in flight) — read its `architecture.md` first.
> **Status**: Found via filesystem audit on 2026-04-28 after reviewing the alignment epic.

## What

Three real bugs and three dead files in the current deployment surface. The alignment epic at `projects/aligning-spec-doc-deployment-1777307253079/` would partially fix #1 by accident but does not address #2–#6 at all. Either (a) revise that epic to absorb these, or (b) ship a small pre-flight cleanup first so the epic operates on a coherent baseline.

### 1. Three compose files, no canonical

- `/workspace/docker-compose.yml` — repo root. `api` service with `ports: 3101:3101`, full env (Stripe, Auth, DB, Sentry), `curl` healthcheck, named `spec-doc-data` volume. Added in commit `416e317 feat(deploy): add root-level docker-compose.yml for Coolify`.
- `/workspace/api/docker-compose.yml` — local dev. Bind mount `../spec-doc:ro`, python urllib healthcheck, minimal env, `PORT=3101` (gunicorn ignores it).
- `/workspace/api/docker-compose.coolify.yml` — Traefik labels (`Host(\`api.spec-doc.${DOMAIN}\`)`), no `ports:`, **missing Stripe / Auth / DB / Sentry env vars entirely**.

The epic's Task 3 edits only `api/docker-compose.yml`. After the epic ships, Coolify still runs whichever of the other two files is wired up at Coolify's end — not the new two-service split. Pick one canonical file (the root one is what `416e317` declares), retire the other two, and align the epic to edit *that*.

### 2. `curl` healthcheck against `python:3.11-slim` will fail

Both root `docker-compose.yml:25-29` and `api/docker-compose.coolify.yml:14-18` use:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3101/health"]
```

`python:3.11-slim` does not ship `curl`. The healthcheck silently fails on every interval, the container is marked unhealthy, and Coolify's `depends_on: condition: service_healthy` (from the epic's Task 3) never resolves.

**Fix**: either install curl in the Dockerfile (`apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*`), or use python urllib like `api/docker-compose.yml:15-23` already does. The python option keeps the image smaller; pick that.

### 3. Stripe var name in spec ≠ name in code

The alignment epic's Task 1 standardises on `STRIPE_PRO_PRICE_ID`. All three compose files in tree (and presumably the billing module) use `STRIPE_PRICE_ID_PRO`. The epic's deviations section anticipates this — but the executor hits a deviation on the very first var. Flip the canonical to `STRIPE_PRICE_ID_PRO` in Task 1's body so the executor doesn't have to.

### 4. `api/.github/workflows/deploy.yml` is dead but tracked

GitHub only reads `.github/workflows/` at the repo root. `api/.github/workflows/deploy.yml` is git-tracked (so it shows up in code review), targets `main` (the rest of the repo is `master`), references `make docker-build` / `make docker-up`, and **never runs**.

Same for `web/.github/workflows/test-frontend.yml` and `web/.github/workflows/ci.yml` — both git-tracked, both ignored by GitHub.

**Fix**: `git rm api/.github/workflows/deploy.yml web/.github/workflows/test-frontend.yml web/.github/workflows/ci.yml` and the empty parent dirs. The alignment epic's Task 4 mentions this in its "out of scope" section as deferred ops housekeeping — but it's a 30-second deletion, do it now. Otherwise these dead files keep showing up in PRs and confusing the next person who touches CI.

### 5. `api/.dockerignore` is dead since context moved to repo root

The Dockerfile header (`api/Dockerfile:3-5`) declares build context = repo root. Docker only honours a `.dockerignore` at the **build context root**. `api/.dockerignore` is therefore not consulted on any build today.

Effect: `web/node_modules/` (potentially hundreds of MB) and `web/.angular/cache/` are sent to the Docker daemon on every build. The `tests/`, `.env`, `.git/`, and `__pycache__/` exclusions also no longer apply.

**Fix**: create a `.dockerignore` at repo root that re-encodes the api/ excludes plus `web/node_modules/`, `web/.angular/`, `web/dist/`, `.claude/`, `projects/`. Then delete `api/.dockerignore`.

### 6. Soft-fail SPA smoke test in CI

`/workspace/.github/workflows/deploy.yml:128-143` curls Angular `/` and only `WARN`s on non-200 — never fails the job. The file's own comment notes this is a temporary seam. The alignment epic's Task 4 replaces this whole section, so this is fixed by inheritance — flagging it here so it doesn't get carried forward into the new `docker-integration` job's smoke test.

## Why now

The `aligning-spec-doc-deployment` epic is queued and ready to execute. It's well-structured but operates on a baseline assumption that's wrong: it treats `api/docker-compose.yml` as the production target. If the executor follows the epic literally, Coolify keeps running the old setup and the epic appears to ship without delivering its stated value. That's the worst failure mode — looks done, isn't done.

The dead workflow / dead .dockerignore / dead api/coolify file issues are also accumulating; every audit of CI from now on has to re-discover that 3 of 4 workflow files don't run.

## What's missing

Two open questions before this can become a spec:

- **Which compose file is canonical?** The recent commit `416e317` says root `docker-compose.yml` is for Coolify. Confirm Coolify's `Compose Path` setting actually points there, then delete `api/docker-compose.coolify.yml`. If Coolify points at `api/docker-compose.coolify.yml` instead, the inverse: keep that, delete the root one.
- **`api/docker-compose.yml` retention**: this is local dev only. Either (a) keep it as a documented dev-only file, or (b) collapse to one compose with a `docker-compose.override.yml` for dev. Lean toward (a) — overrides are a footgun for a solo project.

## Out of scope

- Rewriting the alignment epic from scratch — its dependency graph (T1 ∥ T2 → T3, T2 → T4 ∥ T3, T3-verified → T5) and rollback safety are correct. Only the baseline assumptions and a few specific paths need patching.
- Coolify dashboard configuration — UI clicks, not code. Note in the spec which Coolify settings need to change after the cleanup.
- Adding a root-level Makefile `docker-*` target set — `api/Makefile`'s `docker-up` already exists; just point it at the canonical compose with `-f`.
- Migrating to a different orchestrator (Kamal, Dokku, etc.) — Coolify works; don't churn.

## Open question for the alignment epic

If we adopt this cleanup as a pre-flight, the alignment epic's Task 3 changes shape: it edits the **root** `docker-compose.yml`, deletes `api/docker-compose.coolify.yml`, and leaves `api/docker-compose.yml` as the dev-only file. That's a less invasive Task 3 than what's currently written. Decide before starting.
