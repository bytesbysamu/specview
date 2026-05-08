# Specview — Self-Hosted Packaging

## What self-hosted means for specview

Specview is already deployable via Docker Compose. The DEPLOY.md explains the VPS setup. The docker-compose.yml has three services (web, api, landing). In theory, anyone with a server, Docker, an Anthropic key, and a Postgres database can run their own instance today.

In practice, the self-hosted experience is rough. There's no public Docker Hub image, so self-hosters have to clone the repo and build locally. The Anthropic CLI requirement (`CHAIN_PROVIDER=cli`) is a significant friction point. There's no proper documentation for self-hosters. There's no health check endpoint that tells you "this is working." The environment variable requirements aren't documented in a discoverable way.

The self-hosted audience is technical developers who don't want a SaaS subscription, want full data control, or want to customize the tool for their own stack. This audience is valuable for distribution (GitHub stars, word of mouth) even if they never pay. Making the self-hosted experience excellent is also what enables a credible "host it yourself" alternative to the SaaS, which some developers will pay the SaaS for just to avoid the ops burden.

## The Anthropic CLI problem

This is the biggest structural issue with self-hosted distribution.

`CHAIN_PROVIDER=cli` means the Flask API invokes the Claude CLI via subprocess to make AI calls. In the production Docker container on Coolify, this works because the container mounts `~/.claude` and `~/.claude-openclaw` from the host. The host has the CLI installed and authenticated.

For a self-hoster to replicate this, they need:
1. Claude CLI installed on their host system
2. Claude CLI authenticated (requires interactive login: `claude auth login`)
3. The `~/.claude` directory mounted into the API container

This is doable but it's an unusual requirement. Most self-hosted apps just need an API key as an environment variable. The CLI mount adds host-level coupling that breaks the "just run docker compose up" promise.

The alternative is `CHAIN_PROVIDER=sdk`, which uses the Anthropic Python SDK directly with `ANTHROPIC_API_KEY` as an environment variable. This is the standard self-hosted experience. However, CLAUDE.md says "CHAIN_PROVIDER=cli always — never use the SDK provider in Docker." This rule exists for the production environment (Coolify + CLI), not as a constraint on self-hosters.

For self-hosted packaging, we probably want to document two modes:
- **CLI mode** (production/Coolify): mounts `~/.claude`, requires CLI auth
- **SDK mode** (self-hosted): set `CHAIN_PROVIDER=sdk` and `ANTHROPIC_API_KEY`, no CLI required

The SDK provider path needs to be tested and documented for this to work. Right now it's technically present in the codebase but not validated as a first-class deployment target.

## Docker Hub image

Publishing a Docker image to Docker Hub makes the self-hosted install dramatically simpler. Instead of:

```bash
git clone ... && docker compose build && docker compose up
```

it becomes:

```bash
curl -O docker-compose.yml && docker compose up
```

The compose file references the published image by tag. Self-hosters pull and run without needing to build. This eliminates the build step, the clone step, and the NPM/Python dependency installation from the self-hoster's machine.

Publishing requires:
1. A Docker Hub account and repo (e.g., `samuelbedassa/specview` or `specviewio/specview`)
2. A GitHub Actions workflow that builds and pushes on tag push (`v*`)
3. A versioned tagging scheme: `latest`, `v1`, `v1.2`, `v1.2.3`
4. A separate image for the API and the frontend (or a single bundled image)

The single bundled image is simpler for self-hosters: one image, one container, Flask serves the Angular build as a static directory. The API Dockerfile already has a multi-stage pattern that could bundle the Angular dist into the Flask container. This collapses the compose file to: one service (api/frontend combined), one optional service (landing page), and a Postgres config that points to an external database.

The landing page container (`specviewio/landing`) can be a separate publish. Most self-hosters won't want the marketing landing page — they just want the app.

## One-click deploy targets

Modern cloud platforms offer "deploy to X" buttons that create an account, provision infrastructure, and deploy from a Docker image or repo in a few clicks. The target platforms and their tradeoffs:

### Railway

Railway has the best developer experience for one-click deploys. It supports Docker images directly, provisions Postgres on the same platform, and injects `DATABASE_URL` automatically. The monthly cost for a specview-sized deployment is roughly $5-10 for the Postgres + API container.

Railway's "Deploy on Railway" button goes in the README: a link that prefills the Railway dashboard with the repo. Self-hosters click, authenticate with GitHub, Railway clones the repo and runs it.

Railway limitation: it doesn't support mounting host directories into containers (no `~/.claude` mount). This means Railway deployments need SDK mode, not CLI mode.

### Render

Render is similar to Railway. It supports Docker, has a managed Postgres product, and has a "Deploy to Render" button. The pricing is comparable. Same limitation: no host volume mounts, so SDK mode only.

Render's advantage over Railway is more established brand recognition and better documentation. Many developers have existing Render accounts from other projects.

### Fly.io

Fly.io deploys Docker containers globally, has a Postgres product, and targets developers more explicitly than Railway or Render. Fly doesn't have a one-click deploy button but has a well-documented `fly.toml` config format that a self-hoster can copy.

Fly advantage: you can deploy to a specific region, which matters for latency if your users are in Europe. Fly also supports persistent volumes, which could be used for file storage if we move away from database-only storage.

### Coolify (self-hosted Coolify)

The production specview deployment uses Coolify on a VPS. Coolify is itself an open source self-hosted PaaS. Developers who are already using Coolify can deploy specview by pointing at the Docker Hub image and setting environment variables. This is worth documenting even if there's no button — Coolify users know what they're doing and just need the image name and env var list.

### DigitalOcean App Platform

Less developer-adjacent than Railway/Render but has broad name recognition. Same Docker-based deploy, same SDK-mode requirement. Worth a "Deploy to DigitalOcean" button in the README if we're going broad.

## Environment variables documentation

This is the most important piece of documentation for self-hosters. Every required env var, what it's for, and what happens if it's missing.

```
Required:
ANTHROPIC_API_KEY=sk-ant-...    # Anthropic API key (SDK mode only)
DATABASE_URL=postgresql://...    # Neon, Railway, Render, or self-hosted Postgres
JWT_SECRET=...                   # Random string, used for token signing
CHAIN_PROVIDER=sdk               # Use 'sdk' for self-hosted; 'cli' requires CLI mount

Optional:
STRIPE_SECRET_KEY=sk_...         # Required for Pro tier billing
STRIPE_WEBHOOK_SECRET=whsec_...  # Required for Stripe webhook verification
STRIPE_PRICE_ID=price_...        # Stripe price ID for Pro subscription
SENTRY_DSN=...                   # Error tracking (optional but recommended)
LOG_LEVEL=INFO                   # Default: INFO
```

The `.env.example` file in the repo root should contain exactly this, with placeholder values and comments.

## Quickstart guide

The target experience: a developer reads the README, runs three commands, and has a working specview instance in under 10 minutes.

```bash
# 1. Create a .env file from the example
cp .env.example .env
# (edit .env with your API key, database URL, JWT secret)

# 2. Start the stack
docker compose -f docker-compose.self-hosted.yml up -d

# 3. Create the first user
open http://localhost:8095/signup
```

The `docker-compose.self-hosted.yml` file is a self-hosted-specific compose file that:
- References the Docker Hub image (no local build needed)
- Omits the landing page service (not needed for self-hosting)
- Includes a local Postgres service as the default (so DATABASE_URL defaults to localhost)
- Sets CHAIN_PROVIDER=sdk

The distinction between the development compose file and the self-hosted compose file matters. Self-hosters shouldn't be running the development override.

## Health checks

A self-hosted deployment needs observable health checks. The current API has no `/api/health` endpoint. Self-hosters need a way to verify:

1. The API is up and reachable
2. The database connection is working
3. The Anthropic API key is valid (can make a test call)

`GET /api/health` should return:

```json
{
  "status": "ok",
  "database": "connected",
  "chain": "available",
  "version": "1.2.3"
}
```

If any check fails, return a non-200 status so load balancers and uptime monitors can detect it. The saas-operations-infra project already documents health checks (`/api/health/anthropic`, `/api/health/neon`, `/api/health/stripe`). These should be implemented as part of the self-hosted packaging work.

## Upgrade path

Once someone is running a self-hosted instance, how do they upgrade? With a Docker Hub image and a compose file, the upgrade path is:

```bash
docker compose pull && docker compose up -d
```

But database migrations need to run too. The Alembic migration needs to run as part of the container startup, not as a manual step. The `api/` Dockerfile entrypoint should run `alembic upgrade head` before starting gunicorn. This is the standard pattern for containerized Flask apps.

Migration safety: Alembic migrations should be forwards-compatible. A migration that drops a column or renames a table is dangerous during a rolling upgrade. For self-hosted deployments running on a single container, this matters less. But documenting the "backup your database before upgrading" recommendation is still important.

## What version control looks like for self-hosted users

When a self-hosted user pulls the latest Docker image, they get the latest production build. If a breaking change is introduced, they might get broken without warning.

The solution is semantic versioning plus a CHANGELOG.md. Tag each Docker image with the version. Let self-hosters pin to a major version (`samuelbedassa/specview:v1`) or a minor version (`samuelbedassa/specview:v1.2`). The `latest` tag always follows main.

CHANGELOG.md with upgrade notes for each version. Migrations that require manual action should be called out explicitly.

## What the self-hosted audience wants that the SaaS doesn't offer

Understanding this shapes what to build:

1. **Data sovereignty**: All spec data stays on their own server. Nothing is sent to a third-party database. This is important for users who are speccing sensitive projects.

2. **Unlimited usage without subscription**: They pay for the Anthropic API directly, no monthly SaaS fee. For heavy users, this might be cheaper.

3. **Customization**: They want to add their own skills, modify prompts, integrate with their own tooling. The plugin system and SKILL.md format are the right surface for this.

4. **Airgap / private network**: Some developers want to run AI tools that don't make outbound calls to third-party services. With CHAIN_PROVIDER=sdk, the only outbound call is to the Anthropic API, which they control via their own key.

These are all valid reasons that won't be addressed by the SaaS. The self-hosted distribution is complementary to the SaaS, not competing with it. It serves the long tail of developers who will never pay for a hosted service but who might refer paying users, contribute to the codebase, or evangelize the tool in their communities.

## Open questions

Should the SDK provider path be validated in CI? Right now CI only tests with CHAIN_PROVIDER=mock. Adding a test with CHAIN_PROVIDER=sdk would require a real Anthropic API key in CI, which has cost and secret-management implications.

Is a bundled (single Docker image for API + frontend) better for self-hosters than separate images? The compose file with two images is more flexible, but the single image is simpler. The answer depends on what fraction of self-hosters want to run the frontend separately.

Should specview support Sqlite as an alternative to Postgres for local/small installs? Sqlite would eliminate the DATABASE_URL requirement entirely for developers just trying the tool. Alembic supports Sqlite. The tradeoff is limited concurrent writes and no hosted option. This might be worth doing as a "trial mode" for the first run.

What's the minimum resource requirement to run specview? The API container needs to run the Flask app and the Claude CLI (or SDK). Memory: probably 256MB–512MB. The Angular frontend is static files. Total cost on Railway/Render is roughly $5-10/month. This should be documented so self-hosters can size their deployment.
