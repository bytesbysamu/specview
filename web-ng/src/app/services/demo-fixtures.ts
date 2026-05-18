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

// ── Exported Fixtures ────────────────────────────────────────────────────────

export const DEMO_FIXTURE_PROJECTS: Project[] = [
  {
    id: 'fixture-incident-platform',
    name: 'Incident Response Platform',
    createdAt: '2026-05-01T09:00:00Z',
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
      { filename: 'braindump.md', label: 'Braindump', content: IDP_BRAINDUMP },
      { filename: 'analysis.md',  label: 'Analysis',  content: IDP_ANALYSIS },
      { filename: 'epic.md',      label: 'Epic',      content: IDP_EPIC },
    ],
  },
  {
    id: 'fixture-api-rate-limiting',
    name: 'API Rate Limiting Service',
    createdAt: '2026-05-10T11:30:00Z',
    specs: [
      { filename: 'braindump.md', label: 'Braindump', content: RATELIMIT_BRAINDUMP },
      { filename: 'analysis.md',  label: 'Analysis',  content: RATELIMIT_ANALYSIS },
      { filename: 'epic.md',      label: 'Epic',      content: RATELIMIT_EPIC },
    ],
  },
];
