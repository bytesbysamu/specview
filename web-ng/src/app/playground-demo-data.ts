/**
 * Hardcoded demo data for the live playground page.
 * No HTTP calls — all data is static and typed.
 */

import { Project } from './services/projects.service';
import { NavSection } from './section-nav.component';

// ── Demo Nav Sections ────────────────────────────────────────────────────────

export const DEMO_NAV_SECTIONS: NavSection[] = [
  { id: 'all',            label: 'All',            icon: '' },
  { id: 'Active',         label: 'Active',         icon: 'zap' },
  { id: 'Ready to build', label: 'Ready to build', icon: 'hammer' },
  { id: 'Specced',        label: 'Specced',        icon: 'check-circle' },
  { id: 'Braindumps',     label: 'Braindumps',     icon: 'brain' },
];

// ── Demo Spec Content ────────────────────────────────────────────────────────

/**
 * Raw braindump text for the Payment Gateway Redesign project.
 * Used by the Before/After section to show unprocessed input.
 */
export const PAYMENT_GATEWAY_BRAINDUMP = `ok so our checkout is a total mess. weve got like 4 different frontend codebases because of the two acquisitions we did in 2022 and 2023 and they all render different things on mobile vs desktop which is killing our conversion

the mobile checkout requires so many taps its ridiculous. i counted 11 steps on mobile to complete a payment. desktop is 6. industry standard is like 4-5 for both so were way off

also when cards decline we just show "payment error" which is useless. our support team gets like 340 tickets a week just for payment failures and most of them could be fixed with a better error message

pci compliance is a nightmare. currently 14 services are in scope because we handle card data in too many places. if we could get that down to 3 or so the audit cost alone would justify the rewrite

idea is to move to a unified checkout shell, probably react, and use stripe elements for the actual card capture so we never touch raw card data. progressive disclosure flow - address first then payment - makes more sense with how users think anyway

need to figure out the timeline. probably 6-7 weeks if we sequence it right. stripe integration first, then the shell, then address autocomplete and better error messages, then ab test and launch`;

export const ANALYSIS_CONTENT = `# Analysis — Payment Gateway Redesign

## Executive Summary

The existing payment gateway has accumulated significant technical debt over three years of incremental patching. Conversion rates have dropped 4.2% quarter-over-quarter, and checkout abandonment now exceeds 67% on mobile devices.

The root cause is a fragmented frontend built across four separate frameworks — an inheritance from two acquisitions — that renders a different experience depending on device type. Backend validation logic is duplicated in six places.

## Key Problems

The current checkout flow requires an average of 11 user interactions on mobile versus 6 on desktop. Industry benchmarks sit at 4–5 for both platforms. Every extra tap represents measurable drop-off.

Error messaging is generic. When a card declines, the user sees "Payment error" with no actionable guidance. Support ticket volume for payment failures runs at 340 tickets per week, of which 60% could be resolved by a clear error message.

PCI DSS scope currently touches 14 services. The redesign targets 3, dramatically reducing audit surface and annual compliance cost.

## Recommended Approach

Adopt a unified React-based checkout shell that delegates iframe-isolated card capture to Stripe Elements. This removes all raw card data from our servers, collapsing PCI scope immediately.

A progressive disclosure flow — shipping address first, then payment method — matches how users think about purchase completion and reduces perceived complexity.
`;

const EPIC_CONTENT = `# Epic — Unified Checkout v2

## Problem Statement

Checkout abandonment costs the business an estimated $2.1M in lost GMV per quarter. The mobile experience is the primary driver; secondary is confusing error recovery.

## Success Criteria

- Mobile checkout completion rate reaches 38% (from 24% baseline) within 60 days of launch
- Average checkout interactions drops below 6 on all device types
- PCI DSS scope reduced from 14 services to 3
- Support tickets for payment failures drop by 55% within 30 days

## Scope

**In scope:** New checkout shell, Stripe Elements integration, address autocomplete, error message taxonomy, webhook reliability.

**Out of scope:** Subscription billing, multi-currency display, B2B invoice flow.

## Milestones

1. Stripe Elements integration + PCI scope reduction — Week 1–2
2. Unified checkout shell (mobile-first) — Week 3–4
3. Address autocomplete + error taxonomy — Week 5
4. A/B test infrastructure + launch — Week 6–7
`;

// ── Pipeline Preview Content ─────────────────────────────────────────────────

export const PIPELINE_BRAINDUMP_PREVIEW = `ok so i want to build this thing where users can paste like a big messy brain dump of their idea — doesnt matter how rough, just stream of consciousness — and then the system figures out what theyre actually trying to build and spits out like a full spec document set.

analysis of the problem space first, then an epic with user stories, then a proper architecture doc with tech choices, and finally an impl guide that a dev could actually follow. it should work for any kind of software project, not just web apps.

also need auth so people cant just spam it, maybe usage limits too. and it needs to be fast — nobody wants to wait 10 minutes, should be under a minute ideally. the output should be structured enough that you could hand it to a junior dev and theyd know exactly what to build.

probably a flask backend and some kind of simple frontend. maybe a cli mode too for power users who want to pipe things in.`;

export const PIPELINE_ANALYSIS_PREVIEW = `## Executive Summary

The existing payment gateway has accumulated significant technical debt over three years of incremental patching. Conversion rates have dropped 4.2% quarter-over-quarter, and checkout abandonment now exceeds 67% on mobile devices.

The root cause is a fragmented frontend built across four separate frameworks — an inheritance from two acquisitions — that renders a different experience depending on device type. Backend validation logic is duplicated in six places, making bug fixes expensive and error-prone.

## Key Problems

The current checkout flow requires an average of 11 user interactions on mobile versus 6 on desktop. Industry benchmarks sit at 4–5 for both platforms. Every extra tap represents measurable drop-off.

PCI DSS scope currently touches 14 services. The redesign targets 3, dramatically reducing audit surface and annual compliance cost. Error messaging is generic — when a card declines, users see "Payment error" with no actionable guidance.`;

export const PIPELINE_EPIC_PREVIEW = `## Problem Statement

Checkout abandonment costs the business an estimated $2.1M in lost GMV per quarter. The mobile experience is the primary driver; secondary is confusing error recovery and a fragmented multi-framework frontend inherited from two acquisitions.

## Success Criteria

Mobile checkout completion rate reaches 38% (from 24% baseline) within 60 days of launch. Average checkout interactions drops below 6 on all device types. PCI DSS scope reduced from 14 services to 3. Support tickets for payment failures drop by 55% within 30 days.

## Scope

**In scope:** New checkout shell, Stripe Elements integration, address autocomplete, error message taxonomy, webhook reliability layer.

**Out of scope:** Subscription billing, multi-currency display, B2B invoice flow, saved payment methods (phase 2).`;

export const PIPELINE_ARCHITECTURE_PREVIEW = `## System Design

The checkout shell is a React single-page application hosted on a CDN edge network. Card capture delegates entirely to Stripe Elements iframes — no raw card data ever touches our servers, collapsing PCI DSS scope from 14 services to 3.

## Key Decisions

A progressive disclosure flow — shipping address first, then payment method — matches the mental model users bring from e-commerce and reduces perceived complexity. Address autocomplete via Google Places API eliminates the largest source of form abandonment.

## Data Flow

Order intent is created server-side before the payment sheet mounts. Stripe webhook events drive order state transitions; the frontend polls a lightweight status endpoint rather than holding a WebSocket connection. This keeps the reliability surface small and observable.`;

export const PIPELINE_GUIDE_PREVIEW = `## Implementation Order

Tasks are sequenced so that each unblocks the next. The Stripe integration must land before the checkout shell, because the shell renders Elements components. The error taxonomy must be defined before any form error states are implemented.

## Task 1: Stripe Elements Integration (Days 1–3)

Install \`@stripe/stripe-js\` and \`@stripe/react-stripe-js\`. Implement \`useStripeIntent\` hook that creates a PaymentIntent server-side and returns the client secret. Wrap the checkout tree in \`<Elements stripe={stripePromise} options={options}>\`.

## Task 2: Checkout Shell — Address Step (Days 4–6)

Build the address form using react-hook-form with zod validation. Wire Google Places autocomplete to the street-address field. On submit, persist to the order intent via PATCH and advance to the payment step.

## Task 3: Checkout Shell — Payment Step (Days 7–9)

Render \`<PaymentElement />\` with the appearance API configured to match the brand token set. Implement \`handleSubmit\` calling \`stripe.confirmPayment()\`. Map Stripe decline codes to the error taxonomy strings defined in the design doc.`;

// ── Pipeline Stage Fixtures (V3 Section 2 — Kitchen) ─────────────────────────

export interface PipelineStageFixture {
  key: string;
  label: string;
  title: string;
  description: string;
  snippet: string;
}

/**
 * Four ordered stages of the Specview pipeline.
 * Reuses the existing PIPELINE_*_PREVIEW constants for representative snippets.
 */
export const PIPELINE_STAGES: PipelineStageFixture[] = [
  {
    key: 'braindump',
    label: 'Stage 01',
    title: 'Braindump',
    description:
      'Start with whatever you have — stream of consciousness, bullet points, half-formed ideas. ' +
      'Rough is fine. The pipeline reads intent, not polish.',
    snippet: PIPELINE_BRAINDUMP_PREVIEW,
  },
  {
    key: 'analysis',
    label: 'Stage 02',
    title: 'Analysis',
    description:
      'The AI distills the problem space: root causes, key metrics, recommended approach. ' +
      'One document you could hand to a stakeholder.',
    snippet: PIPELINE_ANALYSIS_PREVIEW,
  },
  {
    key: 'epic',
    label: 'Stage 03',
    title: 'Epic',
    description:
      'Success criteria, scope boundaries, and milestones — scoped tightly so the team ' +
      'knows exactly what is and is not on the table.',
    snippet: PIPELINE_EPIC_PREVIEW,
  },
  {
    key: 'architecture',
    label: 'Stage 04',
    title: 'Architecture',
    description:
      'System design, key decisions, and data flow. Enough detail to unblock technical ' +
      'planning without over-specifying implementation.',
    snippet: PIPELINE_ARCHITECTURE_PREVIEW,
  },
];

// ── Demo Projects ────────────────────────────────────────────────────────────

export const DEMO_PROJECTS: Project[] = [
  // Active (simulated — has braindump only, section assigned externally)
  {
    id: 'demo-active-1',
    name: 'Real-time Notification Engine',
    createdAt: '2026-05-10T09:00:00Z',
    specs: [
      { filename: 'braindump.md', label: 'Braindump', teaser: 'WebSocket-based notification system with offline queuing and device targeting' },
    ],
  },

  // Ready to build
  {
    id: 'demo-ready-1',
    name: 'Payment Gateway Redesign',
    createdAt: '2026-05-08T14:30:00Z',
    specs: [
      { filename: 'braindump.md', label: 'Braindump', teaser: 'Checkout rework with Stripe Elements, mobile-first flow' },
      { filename: 'analysis.md',  label: 'Analysis',  content: ANALYSIS_CONTENT },
      { filename: 'epic.md',      label: 'Epic',      content: EPIC_CONTENT },
      { filename: 'architecture.md', label: 'Architecture', teaser: 'React checkout shell, Stripe Elements iframe, webhook reliability layer' },
    ],
  },
  {
    id: 'demo-ready-2',
    name: 'Search & Discovery v3',
    createdAt: '2026-05-06T11:00:00Z',
    specs: [
      { filename: 'braindump.md',    label: 'Braindump',    teaser: 'Semantic search with vector embeddings and faceted filtering' },
      { filename: 'analysis.md',     label: 'Analysis',     teaser: 'Current full-text search misses 40% of relevant results on long-tail queries' },
      { filename: 'epic.md',         label: 'Epic',         teaser: 'Hybrid BM25 + vector retrieval replacing Elasticsearch text-only index' },
      { filename: 'architecture.md', label: 'Architecture', teaser: 'Pinecone vector store, FastAPI retrieval service, React search shell' },
    ],
  },

  // Specced
  {
    id: 'demo-specced-1',
    name: 'Multi-tenant RBAC System',
    createdAt: '2026-04-28T08:00:00Z',
    specs: [
      { filename: 'braindump.md',         label: 'Braindump',         teaser: 'Role-based access with org hierarchy and resource-level permissions' },
      { filename: 'analysis.md',          label: 'Analysis',          teaser: 'Current flat permission model blocks enterprise deals worth $4M ARR' },
      { filename: 'epic.md',              label: 'Epic',              teaser: 'Hierarchical org model with fine-grained resource policies' },
      { filename: 'architecture.md',      label: 'Architecture',      teaser: 'Casbin policy engine, PostgreSQL RLS, React permission provider' },
      { filename: 'implementation-guide.md', label: 'Implementation Guide', teaser: 'Implementation guide ready · 8 tasks' },
    ],
  },
  {
    id: 'demo-specced-2',
    name: 'Analytics Dashboard',
    createdAt: '2026-04-15T16:00:00Z',
    specs: [
      { filename: 'braindump.md',         label: 'Braindump',         teaser: 'Self-serve analytics with cohort analysis and funnel visualization' },
      { filename: 'analysis.md',          label: 'Analysis',          teaser: 'Product team spends 6h/week exporting CSVs to answer routine questions' },
      { filename: 'epic.md',              label: 'Epic',              teaser: 'Embedded analytics with pre-built charts and custom query builder' },
      { filename: 'architecture.md',      label: 'Architecture',      teaser: 'ClickHouse OLAP, dbt transforms, Recharts frontend' },
      { filename: 'implementation-guide.md', label: 'Implementation Guide', teaser: 'Implementation guide ready · 12 tasks' },
    ],
  },

  // Braindumps
  {
    id: 'demo-braindump-1',
    name: 'AI Code Review Bot',
    createdAt: '2026-05-14T13:00:00Z',
    specs: [
      { filename: 'braindump.md', label: 'Braindump', teaser: 'PR review automation with context-aware suggestions and style enforcement' },
    ],
  },
  {
    id: 'demo-braindump-2',
    name: 'Developer Onboarding Portal',
    createdAt: '2026-05-12T10:00:00Z',
    specs: [
      { filename: 'braindump.md', label: 'Braindump', teaser: 'Self-service onboarding reducing time-to-first-commit from 3 days to 4 hours' },
    ],
  },
  {
    id: 'demo-braindump-3',
    name: 'Feature Flag Service',
    createdAt: '2026-05-11T07:30:00Z',
    specs: [
      { filename: 'braindump.md', label: 'Braindump', teaser: 'Gradual rollout infrastructure with targeting rules and kill switches' },
    ],
  },

  // Active — generation in progress (ninth project)
  {
    id: 'demo-active-2',
    name: 'API Platform Spec',
    createdAt: '2026-05-16T08:45:00Z',
    specs: [
      {
        filename: 'braindump.md',
        label: 'Braindump',
        content: `We need a unified API platform that acts as a gateway for all internal services. Right now every team publishes their own endpoints with different auth schemes, rate limiting strategies, and versioning conventions. It's a mess.

The platform should handle auth (OAuth2 + API keys), rate limiting per consumer tier, request/response logging, and automatic SDK generation from OpenAPI specs. We want teams to register their services via a manifest file and the platform handles the rest.

Probably built on Kong or a custom Go service sitting in front of everything. Need to support REST and gRPC, maybe GraphQL federation later. Key metric: reduce integration time for a new service consumer from 2 weeks to 1 day.`,
      },
      {
        filename: 'analysis.md',
        label: 'Analysis',
        content: `# Analysis — API Platform Spec

## Executive Summary

Internal service proliferation has reached an inflection point. Fourteen distinct authentication schemes are in production, three of which are deprecated but still serving traffic. Consumer onboarding averages 11 business days — largely spent navigating undocumented auth flows and per-service rate limit semantics.

## Key Problems

**Authentication fragmentation**: OAuth2, API keys, mutual TLS, and three legacy session-cookie schemes coexist without a unified revocation surface. A compromised credential in one service cannot be invalidated globally.

**Observability gaps**: Request tracing stops at service boundaries. Cross-service latency attribution is manual and unreliable, delaying incident response by an average of 47 minutes.

**Onboarding friction**: New consumers must read four separate runbooks to integrate a single upstream service. SDK generation is ad-hoc — some teams publish SDKs, most do not.

## Recommended Approach

A centralized API gateway (Kong Enterprise or custom Go service) registered as the single ingress point for all internal APIs. Services publish an OpenAPI 3.1 manifest; the platform derives auth policy, rate limits, and SDK stubs automatically.`,
      },
      {
        filename: 'epic.md',
        label: 'Epic',
        teaser: 'Unified gateway with OAuth2, per-tier rate limiting, and automatic SDK generation — still generating…',
      },
    ],
  },
];

// ── Case Study Acts ──────────────────────────────────────────────────────────
//
// The case study sticky nav is structured into four narrative acts.
// Each act has a display label and the ordered list of section IDs it contains.
// These IDs must match the `id` attributes on the <section> elements in
// PgCaseStudyComponent.

export interface CaseStudyAct {
  label: string;
  sections: CaseStudyNavItem[];
}

export interface CaseStudyNavItem {
  id: string;
  label: string;
}

/** Full ordered list of section IDs in narrative sequence. */
export const DEMO_CASE_STUDY_SECTION_IDS: string[] = [
  'hero',
  'problem',
  'pipeline',
  'live-demo',
  'landing-showcase',
  'design-language',
  'screen-gallery',
  'patterns',
  'dark-mode',
  'journey',
  'cta',
];

/** Four narrative acts grouping the 11 case study sections. */
export const DEMO_CASE_STUDY_ACTS: CaseStudyAct[] = [
  {
    label: 'The Problem',
    sections: [
      { id: 'hero',    label: 'The Pitch' },
      { id: 'problem', label: 'The Problem' },
    ],
  },
  {
    label: 'The Product',
    sections: [
      { id: 'pipeline',          label: 'The Pipeline' },
      { id: 'live-demo',         label: 'Live Demo' },
      { id: 'landing-showcase',  label: 'The Landing' },
    ],
  },
  {
    label: 'The Craft',
    sections: [
      { id: 'design-language', label: 'Design Language' },
      { id: 'screen-gallery',  label: 'Screen Gallery' },
      { id: 'patterns',        label: 'Patterns' },
      { id: 'dark-mode',       label: 'Dark Mode' },
    ],
  },
  {
    label: 'The Journey',
    sections: [
      { id: 'journey', label: 'The Journey' },
      { id: 'cta',     label: 'Get Started' },
    ],
  },
];

// ── Demo Section Counts ──────────────────────────────────────────────────────

export const DEMO_SECTION_COUNTS: Record<string, number> = {
  all:              9,
  Active:           2,
  'Ready to build': 2,
  Specced:          2,
  Braindumps:       3,
};

/** Set of project IDs that should be treated as "Active" (generation in progress). */
export const DEMO_ACTIVE_IDS = new Set<string>(['demo-active-1', 'demo-active-2']);

// ── V3 Extended Demo Data Interfaces ─────────────────────────────────────────
//
// These interfaces support the five-section scroll-shell introduced in
// Playground V3 (Task 1).  Downstream tasks (2–5) import these types to
// drive per-section content rendering.

/**
 * A single entry in the V3 section taxonomy.
 * Maps a scroll-shell section to its display metadata and Phase 2 sources.
 */
export interface SectionTaxonomyEntry {
  /** Stable machine identifier matching `ScrollSection.id` in pg-scroll-shell.component.ts. */
  id: string;

  /** Human-readable section title used in teaser labels and headings. */
  label: string;

  /**
   * Short descriptor of the section's narrative purpose.
   * Rendered as the locked-state teaser line (uppercase, single line).
   */
  teaser: string;

  /**
   * Phase 2 source section IDs absorbed into this V3 section.
   * Empty for sections with no Phase 2 counterpart (e.g. Send-Off).
   */
  phase2Sources: string[];
}

/**
 * Generation status shape for a spec document being produced by the AI chain.
 * Mirrors the backend job-status payload consumed by the polling pattern.
 */
export interface GenerationStatus {
  /** The spec document type being generated. */
  docType: 'analysis' | 'epic' | 'architecture' | 'implementation-guide';

  /** Whether the generation job has finished (success or error). */
  done: boolean;

  /** True when the job completed without error and content is available. */
  success: boolean;

  /** Error message if `done` is true and `success` is false. */
  errorMessage: string | null;

  /**
   * Approximate completion fraction in [0, 1].
   * Used to animate the progress indicator while streaming.
   */
  progress: number;
}

/**
 * A markdown content fixture used to pre-populate demo sections
 * without making live HTTP calls.
 */
export interface MarkdownContentFixture {
  /** Identifier for the fixture, typically matching the spec filename (without extension). */
  key: string;

  /** The full markdown string. */
  content: string;

  /**
   * Display label shown in tabs and headings.
   * Matches the `label` field on the corresponding `Spec` entry.
   */
  label: string;
}

// ── Section Taxonomy Fixtures ─────────────────────────────────────────────────

/** Ordered five-section taxonomy for the V3 scroll shell. */
export const DEMO_SECTION_TAXONOMY: SectionTaxonomyEntry[] = [
  {
    id: 'greeting',
    label: 'Greeting',
    teaser: 'Where it all begins',
    phase2Sources: ['hero'],
  },
  {
    id: 'kitchen',
    label: 'Kitchen',
    teaser: 'Watch the pipeline cook',
    phase2Sources: ['pipeline', 'journey'],
  },
  {
    id: 'main-course',
    label: 'Main Course',
    teaser: 'The live app, in full',
    phase2Sources: ['live-demo', 'screen-gallery'],
  },
  {
    id: 'presentation',
    label: 'Presentation',
    teaser: 'Design language and dark mode',
    phase2Sources: ['design-language', 'patterns', 'dark-mode'],
  },
  {
    id: 'send-off',
    label: 'Send-Off',
    teaser: 'Your turn',
    phase2Sources: [],
  },
];

// ── Generation Status Fixtures ────────────────────────────────────────────────

/** Demo generation status for a project where analysis is complete and epic is in-progress. */
export const DEMO_GENERATION_STATUS_IN_PROGRESS: GenerationStatus[] = [
  { docType: 'analysis',            done: true,  success: true,  errorMessage: null, progress: 1 },
  { docType: 'epic',                done: false, success: false, errorMessage: null, progress: 0.6 },
  { docType: 'architecture',        done: false, success: false, errorMessage: null, progress: 0 },
  { docType: 'implementation-guide', done: false, success: false, errorMessage: null, progress: 0 },
];

/** Demo generation status for a fully completed project. */
export const DEMO_GENERATION_STATUS_COMPLETE: GenerationStatus[] = [
  { docType: 'analysis',            done: true, success: true, errorMessage: null, progress: 1 },
  { docType: 'epic',                done: true, success: true, errorMessage: null, progress: 1 },
  { docType: 'architecture',        done: true, success: true, errorMessage: null, progress: 1 },
  { docType: 'implementation-guide', done: true, success: true, errorMessage: null, progress: 1 },
];

// ── Markdown Content Fixtures ─────────────────────────────────────────────────

/** Pre-populated markdown fixtures for the V3 demo sections. */
export const DEMO_MARKDOWN_FIXTURES: MarkdownContentFixture[] = [
  {
    key: 'analysis',
    label: 'Analysis',
    content: PIPELINE_ANALYSIS_PREVIEW,
  },
  {
    key: 'epic',
    label: 'Epic',
    content: PIPELINE_EPIC_PREVIEW,
  },
  {
    key: 'architecture',
    label: 'Architecture',
    content: PIPELINE_ARCHITECTURE_PREVIEW,
  },
  {
    key: 'implementation-guide',
    label: 'Implementation Guide',
    content: PIPELINE_GUIDE_PREVIEW,
  },
];
