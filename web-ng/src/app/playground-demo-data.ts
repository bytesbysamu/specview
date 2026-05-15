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

const ANALYSIS_CONTENT = `# Analysis — Payment Gateway Redesign

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
];

// ── Demo Section Counts ──────────────────────────────────────────────────────

export const DEMO_SECTION_COUNTS: Record<string, number> = {
  all:              8,
  Active:           1,
  'Ready to build': 2,
  Specced:          2,
  Braindumps:       3,
};
