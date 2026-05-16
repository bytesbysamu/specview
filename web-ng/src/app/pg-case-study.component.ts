import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  QueryList,
  ViewChildren,
  signal,
} from '@angular/core';

import { PgHeroComponent } from './pg-hero.component';
import { PgPipelineComponent } from './pg-pipeline.component';
import { PgLiveDemoComponent } from './pg-live-demo.component';
import { PgNarrativeDesignComponent } from './pg-narrative-design.component';
import { PgNarrativeScreensComponent } from './pg-narrative-screens.component';
import { PgNarrativePatternsComponent } from './pg-narrative-patterns.component';
import { PgNarrativeDarkComponent } from './pg-narrative-dark.component';
import { PgJourneyV2Component } from './pg-journey-v2.component';
import { PgProblemComponent } from './pg-problem.component';
import { PgLandingShowcaseComponent } from './pg-landing-showcase.component';
import { DEMO_CASE_STUDY_ACTS, CaseStudyAct } from './playground-demo-data';

@Component({
  selector: 'app-pg-case-study',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    PgHeroComponent,
    PgProblemComponent,
    PgPipelineComponent,
    PgLiveDemoComponent,
    PgNarrativeDesignComponent,
    PgNarrativeScreensComponent,
    PgNarrativePatternsComponent,
    PgNarrativeDarkComponent,
    PgJourneyV2Component,
    PgLandingShowcaseComponent,
  ],
  template: `
    <!-- ── Section nav bar ──────────────────────────────────────────────────── -->
    <nav class="cs-nav">
      <div class="cs-nav__acts">
        @for (act of navActs; track act.label) {
          <div class="cs-nav__act">
            <span class="cs-nav__act-label">{{ act.label }}</span>
            <div class="cs-nav__act-items">
              @for (item of act.sections; track item.id) {
                <a
                  class="cs-nav__item"
                  [class.cs-nav__item--active]="activeSection() === item.id"
                  [href]="'#' + item.id"
                >{{ item.label }}</a>
              }
            </div>
          </div>
        }
      </div>
      <button class="cs-nav__theme" (click)="toggleTheme()">
        {{ isDark() ? 'Light' : 'Dark' }}
      </button>
    </nav>

    <!-- ── Main page wrapper ────────────────────────────────────────────────── -->
    <div class="cs-page">

      <!-- Hero ─────────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="hero" #sectionEl>
        <h2 class="section-heading">The Pitch</h2>
        <app-pg-hero />
      </section>

      <!-- Problem Statement ───────────────────────────────────────────────── -->
      <section class="cs-section" id="problem" #sectionEl>
        <app-pg-problem />
      </section>

      <!-- Pipeline ─────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="pipeline" #sectionEl>
        <h2 class="section-heading">The Pipeline</h2>
        <app-pg-pipeline />
      </section>

      <!-- Live Demo ────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="live-demo" #sectionEl>
        <app-pg-live-demo />
      </section>

      <!-- Landing Showcase ────────────────────────────────────────────────── -->
      <section class="cs-section" id="landing-showcase" #sectionEl>
        <h2 class="section-heading">The Landing Page</h2>
        <app-pg-landing-showcase />
      </section>

      <!-- Design Language ──────────────────────────────────────────────────── -->
      <section class="cs-section" id="design-language" #sectionEl>
        <app-pg-narrative-design />
      </section>

      <!-- Screen Gallery ───────────────────────────────────────────────────── -->
      <section class="cs-section" id="screen-gallery" #sectionEl>
        <app-pg-narrative-screens />
      </section>

      <!-- Patterns ─────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="patterns" #sectionEl>
        <app-pg-narrative-patterns />
      </section>

      <!-- Dark Mode ────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="dark-mode" #sectionEl>
        <app-pg-narrative-dark />
      </section>

      <!-- Journey Map — #journey-map alias scrolls here via hidden anchor ──── -->
      <span id="journey-map" aria-hidden="true"></span>
      <section class="cs-section" id="journey" #sectionEl>
        <app-pg-journey-v2 />
      </section>

      <!-- CTA ──────────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="cta" #sectionEl>
        <p class="nw-overline">Get Started</p>
        <h2 class="nw-headline cta-headline">Ready to spec your next project?</h2>
        <p class="nw-deck">Paste a braindump. Get analysis, epic, architecture, timeline, and implementation guide — in minutes.</p>
        <a class="cta-btn" href="https://specview.dev">Start Free →</a>
      </section>

    </div>
  `,
  styles: [`
    /* ── Nav bar ─────────────────────────────────────────────────────────────── */
    .cs-nav {
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      align-items: stretch;
      padding: 0 24px;
      background: var(--bg, #fff);
      border-bottom: 1px solid var(--border, #e5e7eb);
      overflow: hidden;
    }

    /* Acts row — flex container holding each act group */
    .cs-nav__acts {
      display: flex;
      align-items: stretch;
      flex: 1;
      min-width: 0;
      gap: 0;
    }

    /* Single act column — act label above its section links */
    .cs-nav__act {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      justify-content: center;
      padding: 6px 12px 0;
      border-right: 1px solid var(--border, #e5e7eb);
      min-width: 0;
    }

    .cs-nav__act:first-child {
      padding-left: 0;
    }

    .cs-nav__act:last-child {
      border-right: none;
    }

    /* Act label — low-weight organiser text */
    .cs-nav__act-label {
      font-family: var(--sans, 'Source Sans 3', 'Source Sans Pro', sans-serif);
      font-size: 9px;
      font-weight: 500;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink-muted, #6b7280);
      opacity: 0.65;
      margin-bottom: 2px;
      white-space: nowrap;
    }

    /* Section links inside an act */
    .cs-nav__act-items {
      display: flex;
      align-items: center;
      flex-wrap: nowrap;
      gap: 0;
    }

    .cs-nav__item {
      display: inline-flex;
      align-items: center;
      padding: 6px 10px 10px;
      font-family: var(--sans, 'Source Sans 3', 'Source Sans Pro', sans-serif);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink-muted, #6b7280);
      text-decoration: none;
      border-bottom: 2px solid transparent;
      white-space: nowrap;
      transition: color 0.15s, border-color 0.15s;
    }

    .cs-nav__item:hover {
      color: var(--ink, #111827);
    }

    .cs-nav__item--active {
      color: var(--accent, #6366f1);
      border-bottom-color: var(--accent, #6366f1);
    }

    .cs-nav__theme {
      margin-left: auto;
      align-self: center;
      flex-shrink: 0;
      padding: 6px 14px;
      font-family: var(--sans, 'Source Sans 3', 'Source Sans Pro', sans-serif);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: transparent;
      border: 1px solid var(--border, #e5e7eb);
      border-radius: 4px;
      color: var(--ink-muted, #6b7280);
      cursor: pointer;
      transition: color 0.15s, border-color 0.15s;
    }

    .cs-nav__theme:hover {
      color: var(--ink, #111827);
      border-color: var(--ink-muted, #6b7280);
    }

    /* ── Responsive — viewport < 1024px ─────────────────────────────────────── */
    @media (max-width: 1023px) {
      .cs-nav {
        overflow-x: auto;
        overflow-y: hidden;
        /* Smooth momentum scroll on iOS */
        -webkit-overflow-scrolling: touch;
      }

      /* Keep act columns side-by-side but allow horizontal scroll on the row */
      .cs-nav__acts {
        flex-shrink: 0;
      }

      .cs-nav__act {
        flex-shrink: 0;
      }

      /* Section items inside each act scroll independently when the act overflows */
      .cs-nav__act-items {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
      }
    }

    /* ── Page ────────────────────────────────────────────────────────────────── */
    .cs-page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 24px 80px;
    }

    .cs-section {
      padding: 64px 0 32px;
    }

    .cta-headline {
      font-size: clamp(28px, 4vw, 42px);
    }

    .cta-btn {
      display: inline-block;
      margin-top: 24px;
      padding: 12px 32px;
      font-family: var(--sans, 'Source Sans 3', sans-serif);
      font-size: 16px;
      font-weight: 600;
      color: var(--bg, #fff);
      background: var(--ink, #111827);
      text-decoration: none;
      letter-spacing: 0.02em;
    }

    /* ── Section heading ────────────────────────────────────────────────────── */
    .section-heading {
      font-family: var(--sans, 'Source Sans 3', 'Source Sans Pro', sans-serif);
      font-size: 28px;
      font-weight: 700;
      color: var(--ink, #111827);
      margin: 0 0 32px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border, #e5e7eb);
    }

  `],
})
export class PgCaseStudyComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChildren('sectionEl') sectionEls!: QueryList<ElementRef<HTMLElement>>;

  readonly navActs: CaseStudyAct[] = DEMO_CASE_STUDY_ACTS;

  activeSection = signal<string>('hero');
  isDark        = signal<boolean>(false);

  private observer: IntersectionObserver | null = null;

  // ── Lifecycle ────────────────────────────────────────────────────────────────

  ngOnInit(): void {
    const saved = localStorage.getItem('theme') ?? 'light';
    this.isDark.set(saved === 'dark');
  }

  ngAfterViewInit(): void {
    this.observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            this.activeSection.set(entry.target.id);
            break;
          }
        }
      },
      { rootMargin: '-20% 0px -80% 0px', threshold: 0 },
    );

    this.sectionEls.forEach((ref) => {
      this.observer!.observe(ref.nativeElement);
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.observer = null;
  }

  // ── Methods ──────────────────────────────────────────────────────────────────

  toggleTheme(): void {
    const next = this.isDark() ? 'light' : 'dark';
    this.isDark.set(next === 'dark');
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  }
}
