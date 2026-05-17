/**
 * pg-scroll-shell.component.ts
 *
 * Playground V3 scroll shell — full implementation (Task 2).
 *
 * Locks the five-section inventory and gating model agreed in Task 1.
 * Downstream tasks (3–5) import `SCROLL_SECTIONS` and `SectionState` from here.
 *
 * Section inventory (V3 → Phase 2 source mapping):
 *   1. Greeting     ← hero section
 *   2. Kitchen      ← pipeline + user journey
 *   3. Main Course  ← live app demo + screen gallery
 *   4. Presentation ← design language + patterns + dark-mode toggle
 *   5. Send-Off     ← new (no Phase 2 source)
 *
 * Cut from Phase 2:
 *   - Landing showcase → deferred to landing page epic
 *   - Before/after transformation → redundant with live demo
 *   - Screen annotations → replaced by the live app itself
 *   - Component-by-component catalog → replaced by composed vignettes
 *
 * Gating mechanism: IntersectionObserver-based scroll-reveal.
 *   - Sentinel divs at section boundaries.
 *   - Threshold: 0.6 on desktop, 0.4 on viewports < 768 px.
 *
 * Locked section behaviour:
 *   - Full-height container.
 *   - Content at opacity 0, pointer-events none.
 *   - Faint newspaper rule at boundary.
 *   - Single-line uppercase label teaser.
 *
 * Reveal transition (CSS-only):
 *   - Desktop: fade-in + 24 px upward shift over 400 ms.
 *   - Mobile: opacity-only (no translate).
 *
 * Dark-mode toggle: whole-page scope.
 *   Toggle in Section 3 applies [data-theme="dark"] on the .pg-shell wrapper,
 *   affecting all sections uniformly.
 *
 * Section nav: renders inside Section 3 as part of the embedded app demo.
 *   NOT used as scroll-level navigation.
 */

import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  QueryList,
  ViewChildren,
  computed,
  signal,
} from '@angular/core';
import { PgSectionGreetingComponent } from './pg-section-greeting.component';
import { PgSectionKitchenComponent } from './pg-section-kitchen.component';
import { PgSectionPatternsComponent } from './pg-section-patterns.component';
import { PgSectionSendoffComponent } from './pg-section-sendoff.component';
import { PgSectionLiveAppComponent } from './pg-section-live-app.component';
import { DEMO_MODE } from './tokens/demo-mode.token';
import { PIPELINE_STAGES } from './playground-demo-data';

// ── Section State ─────────────────────────────────────────────────────────────

/** The lifecycle state of a scroll-gated section. */
export type SectionState = 'locked' | 'revealing' | 'unlocked';

// ── Section Inventory ─────────────────────────────────────────────────────────

/** A single entry in the V3 scroll shell section inventory. */
export interface ScrollSection {
  /** Stable machine identifier used for IntersectionObserver sentinels and CSS hooks. */
  id: string;

  /** Display title shown in the teaser label while the section is locked. */
  label: string;

  /**
   * Phase 2 source sections this V3 section absorbs.
   * Empty for sections with no Phase 2 counterpart.
   */
  phase2Sources: string[];

  /**
   * Initial gate state.  All sections except Greeting start locked
   * so the IntersectionObserver controls progressive reveal.
   */
  initialState: SectionState;

  /**
   * IntersectionObserver threshold.
   * The runtime replaces this with the responsive override (0.4 below 768 px).
   */
  threshold: number;
}

/**
 * Ordered five-section inventory for the V3 playground scroll shell.
 *
 * Import this constant in downstream task components to drive
 * the IntersectionObserver setup, sentinel placement, and locked-state UI.
 */
export const SCROLL_SECTIONS: ScrollSection[] = [
  {
    id: 'greeting',
    label: 'Greeting',
    phase2Sources: ['hero'],
    initialState: 'unlocked',
    threshold: 0.6,
  },
  {
    id: 'kitchen',
    label: 'Kitchen',
    phase2Sources: ['pipeline', 'journey'],
    initialState: 'locked',
    threshold: 0.6,
  },
  {
    id: 'main-course',
    label: 'Main Course',
    phase2Sources: ['live-demo', 'screen-gallery'],
    initialState: 'locked',
    threshold: 0.6,
  },
  {
    id: 'presentation',
    label: 'Presentation',
    phase2Sources: ['design-language', 'patterns', 'dark-mode'],
    initialState: 'locked',
    threshold: 0.6,
  },
  {
    id: 'send-off',
    label: 'Send-Off',
    phase2Sources: [],
    initialState: 'locked',
    threshold: 0.6,
  },
];

// ── Component ─────────────────────────────────────────────────────────────────

@Component({
  selector: 'app-pg-scroll-shell',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './pg-scroll-shell.component.html',
  imports: [
    PgSectionGreetingComponent,
    PgSectionKitchenComponent,
    PgSectionLiveAppComponent,
    PgSectionPatternsComponent,
    PgSectionSendoffComponent,
  ],
  providers: [
    { provide: DEMO_MODE, useValue: true },
  ],
})
export class PgScrollShellComponent implements AfterViewInit, OnDestroy {

  // ── Dark mode (whole-page) ─────────────────────────────────────────────────

  readonly isDark = signal(false);

  toggleTheme(): void {
    this.isDark.update(v => !v);
  }

  // ── Demo data ──────────────────────────────────────────────────────────────

  readonly pipelineStages = PIPELINE_STAGES;

  // ── Section state machine ──────────────────────────────────────────────────

  /** Current gating state for each section, indexed to match SCROLL_SECTIONS. */
  readonly sectionStates = signal<SectionState[]>(
    SCROLL_SECTIONS.map(s => s.initialState)
  );

  /** Section 1 (index 0) is always unlocked on load. */
  readonly section1InView = computed(() => this.sectionStates()[0] === 'unlocked');

  /** Expose sections array to the template. */
  readonly sections = SCROLL_SECTIONS;

  // ── IntersectionObserver ───────────────────────────────────────────────────

  @ViewChildren('sentinel') private sentinelRefs!: QueryList<ElementRef<HTMLDivElement>>;

  private observer: IntersectionObserver | null = null;

  /** Mobile breakpoint — matches styles.css @media (max-width: 768px). */
  private readonly MOBILE_BREAKPOINT = 768;

  /** Transition duration matches the CSS .pg-section--revealing class (400ms). */
  private readonly REVEAL_DURATION_MS = 400;

  ngAfterViewInit(): void {
    const isMobile = window.innerWidth < this.MOBILE_BREAKPOINT;
    const threshold = isMobile ? 0.4 : 0.6;

    this.observer = new IntersectionObserver(
      (entries) => this.onIntersection(entries),
      { threshold }
    );

    this.sentinelRefs.forEach(ref => {
      this.observer!.observe(ref.nativeElement);
    });
  }

  ngOnDestroy(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  }

  // ── Intersection callback ──────────────────────────────────────────────────

  /**
   * When sentinel N becomes visible and section N is already unlocked,
   * transition section N+1 from locked → revealing → unlocked.
   *
   * Each sentinel element carries a data-sentinel-index attribute
   * indicating which BOUNDARY it sits after (0-based: sentinel 0 is between
   * section 0 and section 1, etc.).
   */
  private onIntersection(entries: IntersectionObserverEntry[]): void {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;

      const boundaryIndex = Number(
        (entry.target as HTMLElement).dataset['sentinelIndex']
      );
      if (isNaN(boundaryIndex)) return;

      const nextSectionIndex = boundaryIndex + 1;
      if (nextSectionIndex >= SCROLL_SECTIONS.length) return;

      const states = this.sectionStates();

      // Gating condition: current section (the one before this sentinel) must be unlocked.
      const currentSectionIndex = boundaryIndex;
      if (states[currentSectionIndex] !== 'unlocked') return;

      // Next section must still be locked to trigger the reveal.
      if (states[nextSectionIndex] !== 'locked') return;

      // Transition: locked → revealing
      this.updateSectionState(nextSectionIndex, 'revealing');

      // Transition: revealing → unlocked after CSS animation completes.
      setTimeout(() => {
        this.updateSectionState(nextSectionIndex, 'unlocked');
      }, this.REVEAL_DURATION_MS);
    });
  }

  private updateSectionState(index: number, state: SectionState): void {
    const current = [...this.sectionStates()];
    current[index] = state;
    this.sectionStates.set(current);
  }

  // ── Template helpers ───────────────────────────────────────────────────────

  /** Returns the CSS class for a section wrapper based on its current state. */
  sectionClass(index: number): string {
    const state = this.sectionStates()[index];
    return `pg-section pg-section--${state}`;
  }
}
