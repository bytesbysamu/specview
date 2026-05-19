/**
 * Curated demo fixtures for the unauthenticated app shell.
 *
 * These projects are optimised for persuasion — each one tells a complete,
 * credible product story. They are intentionally distinct from the playground
 * demo data in `playground-demo-data.ts`, which is optimised for feature
 * coverage of the pipeline UI.
 *
 * Shape matches the `Project` and `Spec` interfaces exported from
 * `services/projects.service.ts`.
 */

import { Project } from './projects.service';

// ── Fixture: Incident Response Platform ──────────────────────────────────────

const INCIDENT_BRAINDUMP = `we keep getting burned on incidents. last month we had three P1s that each took
over two hours to resolve because nobody could figure out who owned what service,
the runbook was three years old, and the on-call engineer had to dig through five
different slack channels to piece together what was happening.

want to build an internal incident command tool. something that auto-creates a
dedicated channel, pages the right people based on service ownership, and pulls
in the relevant runbook automatically. engineers should be able to declare an
incident, pick a severity, and get a structured war room in under 30 seconds.

also need post-mortems. right now nobody writes them because its too much friction.
if the tool captured the timeline automatically during the incident it would be
way easier. maybe a one-click post-mortem template that pre-fills from the
incident data.

stack is probably a go backend with postgres, slack api for the channel and
notifications, pagerduty for escalation. should integrate with our existing
service catalog so we know who to page automatically.

timeline probably 8 weeks if we do it right. biggest risk is the service catalog
integration — it's a mess.`;

const INCIDENT_ANALYSIS = `# Analysis — Incident Response Platform

## Executive Summary

Specview's incident response process is functionally broken. Three P1 incidents
last month averaged 127 minutes to resolve — more than double the industry
benchmark of 55 minutes. The root cause is not technical: it is a coordination
deficit. Engineers spend the first 30–40 minutes of every incident locating
owners, finding runbooks, and assembling context that should be pre-assembled.

## Key Problems

**Ownership opacity.** The service catalog exists but is not integrated into any
incident tooling. During incidents, engineers search Confluence and Slack history
to determine who owns a failing service. This adds 15–20 minutes of coordination
overhead per incident.

**Runbook decay.** Runbooks are stored as Confluence pages last updated an average
of 2.4 years ago. They reference infrastructure that no longer exists. Engineers
treat them as suggestions rather than procedures.

**Post-mortem avoidance.** Post-mortems are filed for fewer than 30% of P1
incidents. The primary reason cited in a recent team survey: writing them from
memory after the fact takes 2–3 hours and the timeline reconstruction is always
incomplete.

## Recommended Approach

Build a Slack-native incident command tool that treats the incident channel as the
primary coordination surface. Auto-creation, auto-paging, and auto-runbook
attachment remove the coordination overhead. Automated timeline capture during the
incident transforms post-mortem writing from a reconstruction exercise into an
editing exercise — reducing it to 20–30 minutes.

## Risk Assessment

The service catalog integration is the highest-risk element. If the catalog data is
too stale to be trusted, auto-paging will page the wrong people, which is worse
than the current state. A catalog audit gate should precede the incident tool
rollout.`;

const INCIDENT_EPIC = `# Epic — Incident Command Tool v1

## Problem Statement

Mean time to resolve P1 incidents exceeds two hours due to coordination overhead,
not technical complexity. Ownership lookup, runbook retrieval, and post-mortem
authoring are all manual and friction-heavy.

## Success Criteria

- MTTR for P1 incidents drops below 60 minutes within 90 days of launch
- 80% of incidents are followed by a filed post-mortem (from 30% baseline)
- War room setup time (channel + pages + runbook) drops below 30 seconds
- On-call engineers rate the tool 4+ out of 5 in the first monthly survey

## Scope

**In scope:** Incident declaration, severity triage, auto-channel creation, service
owner paging via PagerDuty, runbook attachment from service catalog, automated
timeline capture, post-mortem template generation.

**Out of scope:** Automated remediation actions, external status page integration,
SLA billing impact tracking (phase 2).

## Milestones

1. Service catalog integration + ownership lookup — Week 1–2
2. Incident declaration flow + Slack channel automation — Week 3–4
3. PagerDuty escalation integration — Week 5
4. Automated timeline capture — Week 6
5. Post-mortem template generation — Week 7
6. Beta rollout to on-call rotation + feedback loop — Week 8`;

const INCIDENT_ARCHITECTURE = `# Architecture — Incident Command Tool

## System Design

The incident tool is a Go service that orchestrates three external systems: the
internal service catalog (PostgreSQL), Slack (channel management and messaging),
and PagerDuty (escalation). It exposes a REST API consumed by a Slack slash command
handler and a lightweight React admin UI for post-mortem review.

## Key Decisions

**Slack as the primary surface.** Incident coordination already happens in Slack.
Building a separate web UI as the primary surface would split attention. The slash
command (\`/incident declare\`) meets engineers where they already are.

**Timeline capture via Slack event streaming.** Rather than asking engineers to log
actions, the service subscribes to all messages in incident channels and persists
them with timestamps. Post-mortem timeline sections are auto-generated from this
stream, with engineers editing rather than writing from scratch.

**Service catalog as the ownership source of truth.** The catalog is queried at
incident declaration time for the affected service. If no owner is found, the
incident defaults to the platform team and triggers a catalog gap alert — fixing
ownership debt is a second-order benefit of the system.

## Data Flow

1. Engineer runs \`/incident declare service=payments severity=P1\`
2. Go service looks up the payment service owner in the catalog
3. Slack channel \`#inc-YYYYMMDD-payments\` is created with the runbook pinned
4. PagerDuty alert fires for the service owner
5. All channel activity is streamed to the timeline store
6. On \`/incident resolve\`, a post-mortem draft is generated from the timeline`;

const INCIDENT_GUIDE = `# Implementation Guide — Incident Command Tool

## Task 1: Service Catalog Integration (Days 1–4)

Connect the Go service to the existing PostgreSQL service catalog. Implement
\`OwnershipResolver\` that takes a service name and returns the on-call team and
current runbook URL. Add a health check that alerts on catalog staleness (no
updates in 90 days).

Write integration tests against a catalog fixture with 20 representative services,
including edge cases: services with no owner, services with multiple owners,
and services with expired runbook links.

## Task 2: Incident Declaration + Slack Automation (Days 5–9)

Implement the \`/incident declare\` slash command handler. On declaration:
create the Slack channel, invite the service owner and incident commander, pin
the runbook, and post the incident brief (service, severity, declared-at,
incident commander).

Slack channel names follow the pattern \`inc-YYYYMMDD-{service}-{seq}\` where
\`seq\` is a daily counter to handle multiple incidents per service per day.

## Task 3: PagerDuty Escalation (Days 10–12)

Integrate PagerDuty's Events API v2. Map Specview severity levels (P0–P3) to
PagerDuty urgency levels. Implement deduplication so a re-declaration of an
open incident updates the existing alert rather than creating a duplicate page.

## Task 4: Timeline Capture (Days 13–16)

Subscribe to Slack's Events API for \`message\` events in all channels matching
the \`inc-\` prefix. Persist each event to the \`incident_timeline\` table with
channel ID, user ID, timestamp, and message text.

Implement a \`/incident status\` command that posts a summarised timeline to the
channel on demand.

## Task 5: Post-Mortem Generation (Days 17–20)

On \`/incident resolve\`, generate a Confluence page from the post-mortem template.
Pre-fill: incident summary, timeline (from captured events), service owner, duration,
and five standard sections (What happened, Why it happened, How we detected it,
How we fixed it, Prevention).

Gate the resolve command: the post-mortem page URL must be posted to the channel
before the incident is marked closed in the system.`;

// ── Fixture: Internal Developer Platform ─────────────────────────────────────

const IDP_BRAINDUMP = `our platform team is drowning. we have 80 engineers and the platform team is
6 people. we're getting 20+ requests a week to provision new services, set up
CI pipelines, create staging environments, add monitoring dashboards. it takes
us 2-3 days per request because everything is manual and each one is slightly
different.

the dream is a self-service portal. engineer goes to a web app, picks a template
(python service, node service, go service, whatever), fills in a form, clicks
create — and 15 minutes later they have a running service with CI, staging env,
monitoring, pagerduty integration, the works.

underlying infra is kubernetes on AWS, github actions for CI, terraform for
infra-as-code, datadog for monitoring. we already have a service catalog in
postgres.

the hard part is we need to handle the state of all these resources. if someone
deletes their github repo the platform should know the service is gone. if CI
fails to set up, the engineer should see why and be able to retry.

probably build this on backstage or build our own. backstage is heavy. maybe just
a flask/react app with a job queue for the provisioning work.

goal: reduce time-to-running-service from 3 days to 15 minutes. reduce platform
team toil by 60%.`;

const IDP_ANALYSIS = `# Analysis — Internal Developer Platform

## Executive Summary

The platform team's 6:80 engineer ratio creates a structural bottleneck. At the
current rate of 20+ manual provisioning requests per week, each taking 2–3 days,
the platform team spends more than 50% of its capacity on undifferentiated toil.
As engineering headcount grows, this ratio worsens — the platform team is on a
path to becoming a hard ceiling on engineering velocity.

## Key Problems

**Manual provisioning is unscalable.** Every new service requires the platform team
to manually create a GitHub repository, configure Actions workflows, provision a
Kubernetes namespace, apply Terraform modules, and wire Datadog dashboards. Each
step is documented in a runbook but requires human judgment for edge cases.

**No state visibility.** Once a service is provisioned, the platform team has no
automated view of whether it is healthy. Deleted repositories and failed CI
pipelines go undetected until an engineer raises a ticket.

**Template drift.** Service templates diverge over time as engineers make ad-hoc
changes to their provisioned setups. There is no mechanism to propagate template
updates to existing services, so the fleet becomes increasingly heterogeneous.

## Recommended Approach

A self-service provisioning portal backed by a job queue. Engineers select a
language template, fill a structured form (service name, team, tier, dependencies),
and submit. A background worker runs the provisioning steps in sequence, updating
a state machine that the portal polls. Engineers can see live step progress and
retry failed steps without platform team involvement.

Backstage is evaluated and rejected: it is operationally heavy, requires
significant customisation to match the existing stack, and adds a Kubernetes
operator dependency. A purpose-built Flask/React app with Celery for job
orchestration is more maintainable given current team size.`;

const IDP_EPIC = `# Epic — Internal Developer Platform v1

## Problem Statement

Platform team capacity is a hard ceiling on engineering velocity. 50% of platform
team time is spent on manual provisioning requests that take 2–3 days each and
could be automated.

## Success Criteria

- Median time-to-running-service drops from 3 days to under 20 minutes
- Platform team toil (defined as manual provisioning work) drops by 60%
- 90% of provisioning requests complete without platform team intervention
- Engineers rate the portal experience 4+ out of 5 in the first quarterly survey

## Scope

**In scope:** Self-service provisioning portal, service template library (Python,
Node, Go), GitHub repository + Actions setup, Kubernetes namespace provisioning,
Terraform module execution, Datadog dashboard creation, PagerDuty service creation,
service catalog registration.

**Out of scope:** Secret management automation (phase 2), cost attribution
dashboards, multi-cloud support.

## Milestones

1. Job queue infrastructure + provisioning state machine — Week 1–2
2. GitHub + CI provisioning worker — Week 3–4
3. Kubernetes + Terraform worker — Week 5–6
4. Datadog + PagerDuty worker — Week 7
5. Self-service portal UI — Week 8–9
6. Service catalog integration + beta rollout — Week 10`;

// ── Fixture: API Rate Limiting Service ───────────────────────────────────────

const RATELIMIT_BRAINDUMP = `we're a platform that other companies build on top of. right now we have a single
global rate limit of 1000 req/min per API key. this is causing two problems:
(1) some customers who need more are getting blocked and churning to competitors,
(2) some customers are hammering specific endpoints and degrading the experience
for everyone else.

need to move to tiered, per-endpoint rate limiting. free tier gets lower limits,
pro tier gets higher limits, enterprise tier gets configurable limits. also need
to rate limit differently by endpoint category — search endpoints are expensive
so they should count more toward the limit than read endpoints.

we also need better observability. customers currently have no idea they're being
rate limited until they get a 429. need a rate limit header, a rate limit dashboard
in the customer portal, and ideally email alerts when they're regularly hitting 80%
of their limit.

technically: we're on fastapi, redis for rate limit state, postgres for customer
data. we have about 200 API customers, 40 of which are on pro or enterprise plans.

i want this done in 5-6 weeks. biggest concern is backwards compatibility — any
change to the rate limit system breaks customers who have hardcoded retry logic
for the current 429 shape.`;

const RATELIMIT_ANALYSIS = `# Analysis — API Rate Limiting Service

## Executive Summary

The current flat rate limiting model is simultaneously too permissive for some
endpoints and too restrictive for high-growth customers. The mismatch is causing
churn at the top of the customer tier (enterprise prospects blocked by limits
they cannot negotiate) and performance degradation for the majority (caused by a
minority of customers saturating expensive endpoints).

## Key Problems

**Single-tier limits block enterprise conversion.** Four known enterprise prospects
have cited the inability to negotiate custom rate limits as a blocking reason for
not signing. Estimated ARR impact: $380K annually.

**Endpoint-agnostic counting penalises good actors.** A customer running analytics
on the search endpoint (10x more expensive than read endpoints in compute cost)
consumes the same quota as a customer making lightweight read calls. This creates
cross-customer interference with no incentive gradient to use the cheaper paths.

**Zero observability until failure.** Customers have no advance warning they are
approaching their limit. The first signal is a 429 response, which they discover
in production. This leads to reactive escalations that consume support capacity.

## Recommended Approach

A tiered rate limiting layer built on Redis, with per-endpoint weight coefficients
that reflect backend compute cost. Rate limit state is tracked at the API key level
with a sliding window algorithm. Response headers (\`X-RateLimit-Remaining\`,
\`X-RateLimit-Reset\`) are added to every response. A webhook fires when an API key
crosses 80% utilisation within a rolling window.

Backwards compatibility is maintained by keeping the 429 response body shape
identical to today and adding new fields (not removing or renaming existing ones).`;

const RATELIMIT_EPIC = `# Epic — Tiered Rate Limiting Service

## Problem Statement

Flat rate limiting blocks enterprise conversion and creates cross-customer
interference. The system needs per-tier limits, per-endpoint weights, and
customer-facing observability before the next enterprise sales cycle.

## Success Criteria

- Enterprise prospects can configure custom limits without platform team involvement
- Search endpoint abuse no longer degrades performance for read-only customers
- Customers receive rate limit headers on every response
- Rate limit dashboard in customer portal live within 6 weeks
- Zero breaking changes to existing 429 response shape

## Scope

**In scope:** Tiered rate limits (free/pro/enterprise), per-endpoint weight
coefficients, sliding window algorithm, rate limit response headers, customer
portal dashboard, 80%-utilisation webhook alerts, admin UI for setting enterprise
custom limits.

**Out of scope:** Real-time rate limit negotiation via API, IP-level rate limiting,
GraphQL query complexity scoring.

## Milestones

1. Redis sliding window rate limiter with tier support — Week 1–2
2. Per-endpoint weight coefficients + FastAPI middleware — Week 3
3. Rate limit response headers + backwards-compatible 429 shape — Week 4
4. Customer portal dashboard — Week 5
5. Utilisation webhook + email alerts — Week 6`;

const IDP_ARCHITECTURE = `# Architecture — Internal Developer Platform

## System Design

The IDP is a Flask application with a React frontend and Celery worker pool for
asynchronous provisioning jobs. All provisioning state is stored in PostgreSQL.
The system orchestrates four external providers: GitHub (repository + Actions),
AWS EKS (Kubernetes namespaces), Terraform Cloud (infrastructure modules), and
Datadog (monitoring dashboards + alerts).

## Key Decisions

**Flask + Celery over Backstage.** Backstage was evaluated and rejected. It
requires a Kubernetes operator, has a steep plugin authoring curve, and its
catalog model does not map cleanly to the existing service catalog schema.
Flask + Celery is operationally simpler: the platform team already runs both
in production.

**State machine per provisioning job.** Each job progresses through a defined
sequence of states: \`pending → github → kubernetes → terraform → monitoring →
complete\`. Each state transition is idempotent — a failed step can be retried
without re-running prior steps. The state machine is stored as a JSON column
on the \`provisioning_job\` table.

**Template registry as code.** Service templates are YAML files in a Git
repository. Each template declares a language runtime, default resource
limits, required Terraform modules, and Datadog dashboard JSON. Template
updates are versioned — existing services are not retroactively modified, but
a drift report identifies services running on outdated templates.

## Data Flow

1. Engineer selects a template and fills the service form in the React UI
2. Flask API validates the form and creates a \`provisioning_job\` row
3. Celery picks up the job and runs steps sequentially
4. Each step calls the relevant provider API and updates the job state
5. The React UI polls the job status endpoint for live progress
6. On completion, the service is registered in the service catalog`;

const IDP_GUIDE = `# Implementation Guide — Internal Developer Platform

## Task 1: Job Queue Infrastructure (Days 1–5)

Set up the Celery worker pool with Redis as the broker. Define the
\`ProvisioningJob\` SQLAlchemy model with columns for job ID, template slug,
service name, team, current state, step results (JSON), and timestamps.

Implement the state machine: each step is a Celery task that reads the
current state, executes the provider call, writes the result, and advances
to the next state. Failed steps set the state to \`{step}_failed\` and
include the error in \`step_results\`.

Write integration tests with mocked provider calls for the full happy path
and each failure mode (GitHub 422, Kubernetes quota exceeded, Terraform
plan error).

## Task 2: GitHub + CI Provisioning (Days 6–10)

Implement the GitHub provisioning step. Using the GitHub API: create a
repository from the template's cookiecutter archive, configure branch
protection rules, and commit the initial Actions workflow YAML.

The Actions workflow is generated from the template — Python templates get
pytest + ruff, Node templates get vitest + eslint, Go templates get
go test + golangci-lint.

## Task 3: Kubernetes + Terraform Provisioning (Days 11–16)

Implement the Kubernetes step: create a namespace, apply resource quotas
from the template, and create the service account. Use the Kubernetes
Python client against the EKS cluster.

Implement the Terraform step: trigger a Terraform Cloud run with the
template's module, passing the service name and namespace as variables.
Poll the run until it reaches \`applied\` or \`errored\` state.

## Task 4: Monitoring + Catalog Registration (Days 17–20)

Implement the Datadog step: create a dashboard from the template's JSON
definition, substituting the service name and namespace. Create a monitor
for the service's health endpoint with PagerDuty routing.

Implement catalog registration: insert a row in the service catalog with
the service name, team, template version, and links to the GitHub repo,
dashboard, and PagerDuty service.

## Task 5: Self-Service Portal UI (Days 21–28)

Build the React frontend. Three views: template picker (card grid),
service creation form (dynamic fields per template), and job status
(polling progress bar with per-step status). The form validates service
name uniqueness against the catalog before submission.`;

const RATELIMIT_ARCHITECTURE = `# Architecture — API Rate Limiting Service

## System Design

The rate limiter is a FastAPI middleware that intercepts every request before
it reaches the route handler. Rate limit state is stored in Redis using a
sliding window counter. The middleware reads the API key from the request
header, resolves the customer's tier from a local cache (refreshed every 60s
from PostgreSQL), and evaluates the request against the tier's limits.

## Key Decisions

**Sliding window over fixed window.** Fixed windows create burst problems at
window boundaries — a customer can send 2x their limit by timing requests
across a boundary. The sliding window algorithm uses two Redis keys per API
key (current and previous window) with a weighted average, eliminating the
burst problem with minimal additional complexity.

**Per-endpoint weight coefficients.** Each endpoint category (read, write,
search, bulk) has a weight multiplier stored in a configuration table. A
search request with weight 5 consumes 5 units of the customer's quota while
a read request consumes 1. Weights are adjustable without code deploys.

**Rate limit headers on every response.** Three headers are added to every
response: \`X-RateLimit-Limit\` (tier maximum), \`X-RateLimit-Remaining\`
(units left in the current window), and \`X-RateLimit-Reset\` (Unix timestamp
when the window resets). This gives customers real-time visibility without
polling a separate endpoint.

## Data Flow

1. Request arrives → middleware extracts API key from \`Authorization\` header
2. Tier lookup: check local cache → miss: query PostgreSQL, populate cache
3. Endpoint weight: resolve the route's category and multiply by its weight
4. Redis EVAL: atomic sliding window check + increment
5. If under limit: add headers, pass to route handler
6. If over limit: return 429 with \`Retry-After\` header and unchanged body shape

## Failure Modes

**Redis unavailable:** Fail open — allow the request and log the error. Rate
limiting is a protection mechanism, not a correctness requirement. Failing
closed on Redis downtime would create a self-inflicted outage.

**Tier cache stale:** A 60-second TTL means a customer who upgrades from free
to pro may wait up to 60 seconds for the new limits to apply. This is
acceptable — upgrades are rare events and 60 seconds is imperceptible.`;

const RATELIMIT_GUIDE = `# Implementation Guide — Tiered Rate Limiting Service

## Task 1: Redis Sliding Window Limiter (Days 1–5)

Implement the sliding window algorithm as a Redis Lua script. The script
takes three arguments: the API key, the window size in seconds, and the
maximum allowed requests. It maintains two sorted sets (current window
and previous window) and returns the remaining quota.

Write the \`RateLimiter\` class in Python that wraps the Lua script. It
should expose \`check_and_increment(api_key, weight) -> RateLimitResult\`
where \`RateLimitResult\` contains \`allowed: bool\`, \`remaining: int\`,
\`reset_at: int\`, and \`limit: int\`.

Add tier configuration: create the \`rate_limit_tier\` table in PostgreSQL
with columns for tier name, requests per minute, and burst allowance.
Seed with three tiers: free (100/min), pro (1000/min), enterprise (custom).

## Task 2: FastAPI Middleware + Endpoint Weights (Days 6–10)

Implement the rate limit middleware as a Starlette middleware class.
On each request: extract the API key, resolve the tier, look up the
endpoint weight, call \`check_and_increment\`, and either pass through
or return 429.

Create the \`endpoint_weight\` configuration table with endpoint pattern
and weight columns. Seed with defaults: read=1, write=2, search=5, bulk=10.
The middleware resolves the weight by matching the request path against
the pattern list.

Add the three rate limit headers to every response, including 429 responses.
The 429 response body must be identical to the current shape — add new fields
but never remove or rename existing ones.

## Task 3: Customer Portal Dashboard (Days 11–16)

Add a \`/api/rate-limits/usage\` endpoint that returns the customer's current
utilisation: requests made, quota remaining, reset timestamp, and a 24-hour
histogram of usage by endpoint category.

Build the dashboard component in the customer portal React app. Show a
real-time gauge (current usage vs limit), a 24-hour usage chart broken
down by endpoint category, and the current tier with an upgrade CTA for
free-tier customers.

## Task 4: Utilisation Alerts (Days 17–20)

Implement a background Celery task that runs every 5 minutes. For each
API key that has exceeded 80% of its limit in the current window, enqueue
a webhook event to the customer's configured webhook URL.

Send an email alert (via SendGrid) on the first 80% crossing per 24-hour
period — do not spam on repeated crossings. Track the last alert timestamp
per API key in Redis with a 24-hour TTL.

Create an admin UI page for setting enterprise custom limits. The form
takes an API key, a new requests-per-minute limit, and an optional burst
override. Changes take effect on the next tier cache refresh (≤60s).`;

// ── Exported Fixtures ────────────────────────────────────────────────────────

export const DEMO_FIXTURE_PROJECTS: Project[] = [
  {
    id: 'fixture-incident-platform',
    name: 'Incident Response Platform',
    createdAt: '2026-05-19T09:00:00Z',
    specs: [
      { filename: 'braindump.md',         label: 'Braindump',         content: INCIDENT_BRAINDUMP },
      { filename: 'analysis.md',          label: 'Analysis',          content: INCIDENT_ANALYSIS },
      { filename: 'epic.md',              label: 'Epic',              content: INCIDENT_EPIC },
      { filename: 'architecture.md',      label: 'Architecture',      content: INCIDENT_ARCHITECTURE },
      { filename: 'implementation-guide.md', label: 'Implementation Guide', content: INCIDENT_GUIDE },
    ],
  },
  {
    id: 'fixture-internal-dev-platform',
    name: 'Internal Developer Platform',
    createdAt: '2026-04-22T14:00:00Z',
    specs: [
      { filename: 'braindump.md',            label: 'Braindump',            content: IDP_BRAINDUMP },
      { filename: 'analysis.md',             label: 'Analysis',             content: IDP_ANALYSIS },
      { filename: 'epic.md',                 label: 'Epic',                 content: IDP_EPIC },
      { filename: 'architecture.md',         label: 'Architecture',         content: IDP_ARCHITECTURE },
      { filename: 'implementation-guide.md', label: 'Implementation Guide', content: IDP_GUIDE },
    ],
  },
  {
    id: 'fixture-api-rate-limiting',
    name: 'API Rate Limiting Service',
    createdAt: '2026-05-10T11:30:00Z',
    specs: [
      { filename: 'braindump.md',            label: 'Braindump',            content: RATELIMIT_BRAINDUMP },
      { filename: 'analysis.md',             label: 'Analysis',             content: RATELIMIT_ANALYSIS },
      { filename: 'epic.md',                 label: 'Epic',                 content: RATELIMIT_EPIC },
      { filename: 'architecture.md',         label: 'Architecture',         content: RATELIMIT_ARCHITECTURE },
      { filename: 'implementation-guide.md', label: 'Implementation Guide', content: RATELIMIT_GUIDE },
    ],
  },
];
