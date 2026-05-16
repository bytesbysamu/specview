import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

import { SectionNavComponent } from './section-nav.component';
import { DEMO_NAV_SECTIONS, DEMO_SECTION_COUNTS } from './playground-demo-data';

// ── Card config ───────────────────────────────────────────────────────────────

interface CardDemo {
  title: string;
  teaser: string;
  badge: string | number;
  sectionLabel: string;
  featured: boolean;
  label: string;
}

// ── File nav config ───────────────────────────────────────────────────────────

interface FileNavDemo {
  label: string;
  active: boolean;
  dotState: 'running' | 'success' | 'failure' | null;
  stateLabel: string;
}

// ── Section nav config ────────────────────────────────────────────────────────

interface SectionNavDemo {
  label: string;
  activeId: string;
  pulsing: boolean;
}

const DEMO_MD = `## Analysis\n\nThe existing payment gateway has accumulated significant **technical debt**.\n\n- Conversion rates dropped 4.2% QoQ\n- Checkout abandonment exceeds 67% on mobile\n- PCI scope touches 14 services`;

@Component({
  selector: 'app-pg-state-matrix',
  standalone: true,
  imports: [SectionNavComponent],
  templateUrl: './pg-state-matrix.component.html',
  styleUrl: './pg-state-matrix.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PgStateMatrixComponent {
  private sanitizer = inject(DomSanitizer);

  // ── Project cards ─────────────────────────────────────────────────────────

  readonly cards: CardDemo[] = [
    {
      label: 'featured (.featured)',
      title: 'Payment Gateway Redesign',
      teaser: 'Checkout rework with Stripe Elements, mobile-first progressive disclosure flow reducing interactions from 11 to 4.',
      badge: 4,
      sectionLabel: 'Ready to build',
      featured: true,
    },
    {
      label: 'normal card',
      title: 'Search & Discovery v3',
      teaser: 'Semantic search with vector embeddings and faceted filtering.',
      badge: 4,
      sectionLabel: 'Ready to build',
      featured: false,
    },
    {
      label: 'generating... teaser (Active)',
      title: 'Real-time Notification Engine',
      teaser: 'generating…',
      badge: 1,
      sectionLabel: 'Active',
      featured: false,
    },
    {
      label: 'Implementation guide ready (Specced)',
      title: 'Multi-tenant RBAC System',
      teaser: 'Implementation guide ready · 8 tasks',
      badge: 5,
      sectionLabel: 'Specced',
      featured: false,
    },
    {
      label: 'Braindump — ready to generate',
      title: 'AI Code Review Bot',
      teaser: 'Braindump — ready to generate',
      badge: 1,
      sectionLabel: 'Braindumps',
      featured: false,
    },
  ];

  // ── Sidebar file nav states ───────────────────────────────────────────────

  readonly fileNavItems: FileNavDemo[] = [
    { label: 'Braindump',    active: false, dotState: null,      stateLabel: 'idle (no dot)' },
    { label: 'Analysis',     active: true,  dotState: null,      stateLabel: 'active (highlighted)' },
    { label: 'Epic',         active: false, dotState: 'running', stateLabel: 'running dot' },
    { label: 'Architecture', active: false, dotState: 'success', stateLabel: 'success dot' },
    { label: 'Impl. Guide',  active: false, dotState: 'failure', stateLabel: 'failure dot' },
  ];

  // ── Section nav states ────────────────────────────────────────────────────

  readonly sectionNavDemos: SectionNavDemo[] = [
    { label: '"All" active',      activeId: 'all',     pulsing: false },
    { label: '"Specced" active',  activeId: 'Specced', pulsing: false },
    { label: 'Badge pulsing',     activeId: 'Active',  pulsing: true  },
  ];

  readonly demoSections = DEMO_NAV_SECTIONS;
  readonly demoCounts   = DEMO_SECTION_COUNTS;

  getPulsingSet(pulsing: boolean): Set<string> {
    return pulsing ? new Set(['Active']) : new Set<string>();
  }

  // ── Reader panel states ───────────────────────────────────────────────────

  readonly parsedSpec: SafeHtml = this.sanitizer.bypassSecurityTrustHtml(
    DOMPurify.sanitize(marked.parse(DEMO_MD) as string)
  );

  readonly diffBlocks = [
    { type: 'remove', text: 'PCI DSS scope touches 14 services, dramatically increasing audit surface.' },
    { type: 'add',    text: 'PCI DSS scope reduced to 3 services, collapsing compliance cost immediately.' },
    { type: 'add',    text: 'Stripe Elements iframe isolates card capture — no raw card data on our servers.' },
  ];
}
