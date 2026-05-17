/**
 * pg-scroll-shell.component.ts
 *
 * Playground V4 scroll shell — CSS-only section reveals (Task 4).
 *
 * Replaces the V3 high-threshold gating observer with a single lightweight
 * IntersectionObserver at threshold 0.1.  When a section's edge enters the
 * viewport the observer adds the `revealed` CSS class to that element and
 * immediately stops observing it — sections stay visible permanently.
 *
 * All JavaScript content-gating logic (sectionStates signal, locked/revealing/
 * unlocked state machine, MOBILE_BREAKPOINT override, setTimeout transitions)
 * has been removed.  Visibility is now a pure CSS concern.
 *
 * Section inventory (five sections):
 *   0. Greeting     ← hero
 *   1. Before/After ← transformation moment (not gated in V3 inventory)
 *   2. Kitchen      ← pipeline + user journey
 *   3. Main Course  ← live app demo
 *   4. Presentation ← design language + patterns
 *   5. Send-Off     ← new section
 *
 * Downstream tasks import `SCROLL_SECTIONS` and `SectionState` from here.
 * Both are kept for compatibility; `SectionState` is now unused at runtime.
 */

import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  QueryList,
  ViewChild,
  ViewChildren,
  signal,
} from '@angular/core';
import { PgSectionGreetingComponent } from './pg-section-greeting.component';
import { PgSectionKitchenComponent } from './pg-section-kitchen.component';
import { PgSectionPatternsComponent } from './pg-section-patterns.component';
import { PgSectionSendoffComponent } from './pg-section-sendoff.component';
import { PgSectionLiveAppComponent, LiveAppActivation } from './pg-section-live-app.component';
import { PgSectionBeforeAfterComponent } from './pg-section-before-after.component';
import { DEMO_MODE } from './tokens/demo-mode.token';

// ── Section State (kept for downstream compatibility) ─────────────────────────

/** The lifecycle state of a scroll-gated section. No longer used at runtime. */
export type SectionState = 'locked' | 'revealing' | 'unlocked';

// ── Section Inventory ─────────────────────────────────────────────────────────

/** A single entry in the V4 scroll shell section inventory. */
export interface ScrollSection {
  /** Stable machine identifier used for CSS hooks. */
  id: string;

  /** Display title. */
  label: string;

  /**
   * Phase 2 source sections this V4 section absorbs.
   * Empty for sections with no Phase 2 counterpart.
   */
  phase2Sources: string[];

  /**
   * Initial gate state — retained for interface compatibility.
   * No longer drives any runtime behaviour; CSS handles reveal.
   */
  initialState: SectionState;

  /**
   * Observer threshold — retained for interface compatibility.
   * Runtime always uses 0.1.
   */
  threshold: number;
}

/**
 * Ordered section inventory for the V4 playground scroll shell.
 *
 * Import this constant in downstream task components.
 */
export const SCROLL_SECTIONS: ScrollSection[] = [
  {
    id: 'greeting',
    label: 'Greeting',
    phase2Sources: ['hero'],
    initialState: 'unlocked',
    threshold: 0.1,
  },
  {
    id: 'kitchen',
    label: 'Kitchen',
    phase2Sources: ['pipeline', 'journey'],
    initialState: 'locked',
    threshold: 0.1,
  },
  {
    id: 'main-course',
    label: 'Main Course',
    phase2Sources: ['live-demo', 'screen-gallery'],
    initialState: 'locked',
    threshold: 0.1,
  },
  {
    id: 'presentation',
    label: 'Presentation',
    phase2Sources: ['design-language', 'patterns', 'dark-mode'],
    initialState: 'locked',
    threshold: 0.1,
  },
  {
    id: 'send-off',
    label: 'Send-Off',
    phase2Sources: [],
    initialState: 'locked',
    threshold: 0.1,
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
    PgSectionBeforeAfterComponent,
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

  // ── Live-app activation (Task 3 — "See it live" handoff) ──────────────────

  /**
   * Passed to the live-app section's `activation` input signal.
   * Task 3 (the Kitchen section's "See it live" CTA) sets this to
   * programmatically switch the Main Course section to detail view
   * with a specific tab selected.
   */
  readonly liveAppActivation = signal<LiveAppActivation | null>(null);

  // ── "See it live" handler (Task 3) ────────────────────────────────────────

  @ViewChild('mainCourseSection') private mainCourseSectionRef!: ElementRef<HTMLDivElement>;

  /**
   * Called when the Kitchen section's pipeline emits the "See it live" event.
   * Scrolls the Main Course section into view and activates detail view with
   * the architecture tab selected.
   */
  onKitchenSeeItLive(): void {
    this.liveAppActivation.set({ view: 'detail', tab: 'architecture.md' });

    if (this.mainCourseSectionRef?.nativeElement) {
      this.mainCourseSectionRef.nativeElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start',
      });
    }
  }

  // ── IntersectionObserver — CSS-only reveal ────────────────────────────────

  /**
   * References to every section wrapper element.
   * The observer adds `revealed` to each when it enters the viewport at 0.1.
   */
  @ViewChildren('sectionEl') private sectionEls!: QueryList<ElementRef<HTMLDivElement>>;

  private observer: IntersectionObserver | null = null;

  ngAfterViewInit(): void {
    this.observer = new IntersectionObserver(
      (entries) => this.onIntersection(entries),
      { threshold: 0.1 }
    );

    this.sectionEls.forEach(ref => {
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
   * When a section enters the viewport, add the `revealed` CSS class and
   * stop observing it — sections are permanently revealed once triggered.
   */
  private onIntersection(entries: IntersectionObserverEntry[]): void {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;

      const el = entry.target as HTMLElement;
      el.classList.add('revealed');
      this.observer?.unobserve(el);
    });
  }
}
