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
import { PgNarrativeDesignComponent } from './pg-narrative-design.component';
import { PgNarrativeScreensComponent } from './pg-narrative-screens.component';
import { PgNarrativePatternsComponent } from './pg-narrative-patterns.component';
import { PgNarrativeDarkComponent } from './pg-narrative-dark.component';
import { PgJourneyComponent } from './pg-journey.component';

interface NavItem {
  id: string;
  label: string;
}

@Component({
  selector: 'app-pg-case-study',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    PgHeroComponent,
    PgPipelineComponent,
    PgNarrativeDesignComponent,
    PgNarrativeScreensComponent,
    PgNarrativePatternsComponent,
    PgNarrativeDarkComponent,
    PgJourneyComponent,
  ],
  template: `
    <!-- ── Section nav bar ──────────────────────────────────────────────────── -->
    <nav class="cs-nav">
      @for (item of navItems; track item.id) {
        <a
          class="cs-nav__item"
          [class.cs-nav__item--active]="activeSection() === item.id"
          [href]="'#' + item.id"
        >{{ item.label }}</a>
      }
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

      <!-- Pipeline ─────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="pipeline" #sectionEl>
        <h2 class="section-heading">The Pipeline</h2>
        <app-pg-pipeline />
      </section>

      <!-- Design Language ──────────────────────────────────────────────────── -->
      <section class="cs-section" id="design" #sectionEl>
        <app-pg-narrative-design />
      </section>

      <!-- Screen Gallery ───────────────────────────────────────────────────── -->
      <section class="cs-section" id="screens" #sectionEl>
        <app-pg-narrative-screens />
      </section>

      <!-- Patterns ─────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="patterns" #sectionEl>
        <app-pg-narrative-patterns />
      </section>

      <!-- Dark Mode ────────────────────────────────────────────────────────── -->
      <section class="cs-section" id="dark" #sectionEl>
        <app-pg-narrative-dark />
      </section>

      <!-- Journey Map ──────────────────────────────────────────────────────── -->
      <section class="cs-section" id="journey" #sectionEl>
        <h2 class="section-heading">The Journey</h2>
        <app-pg-journey />
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
      align-items: center;
      gap: 0;
      padding: 0 24px;
      background: var(--bg, #fff);
      border-bottom: 1px solid var(--border, #e5e7eb);
    }

    .cs-nav__item {
      display: inline-flex;
      align-items: center;
      padding: 12px 16px;
      font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-muted, #6b7280);
      text-decoration: none;
      border-bottom: 2px solid transparent;
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
      padding: 6px 14px;
      font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif;
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

    /* ── Page ────────────────────────────────────────────────────────────────── */
    .cs-page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 24px 80px;
    }

    .cs-section {
      padding: 64px 0 32px;
    }

    /* ── Section heading ────────────────────────────────────────────────────── */
    .section-heading {
      font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif;
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

  readonly navItems: NavItem[] = [
    { id: 'hero',     label: 'The Pitch' },
    { id: 'pipeline', label: 'The Pipeline' },
    { id: 'design',   label: 'Design Language' },
    { id: 'screens',  label: 'Screen Gallery' },
    { id: 'patterns', label: 'Patterns' },
    { id: 'dark',     label: 'Dark Mode' },
    { id: 'journey',  label: 'The Journey' },
  ];

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
