/**
 * pg-section-patterns.component.ts
 *
 * Playground V3 — Section 4 "Presentation".
 *
 * EXTRACTION API
 * ──────────────
 * This component is fully extractable for landing page consumption.
 * All content is hardcoded in the template — there are no input signals,
 * no constructor-injected dependencies, no references to
 * PgScrollShellComponent's internal signals, and no coupling to the
 * gating state machine.
 *
 * Named export: PgSectionPatternsComponent
 *
 * Input contract:  none
 * Output contract: none
 *
 * Transitive dependencies (must be available in the landing page build):
 *   - PgTokensComponent    (pg-tokens.component.ts)
 *   - PgBordersComponent   (pg-borders.component.ts)
 *   - PgAnimationsComponent (pg-animations.component.ts)
 *
 * These are already declared in this component's `imports` array; Angular's
 * standalone component model means a landing page consumer does NOT need to
 * declare them separately — they are pulled in automatically when this
 * component is imported.
 *
 * Usage outside the scroll shell:
 *   <app-pg-section-patterns />
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { PgTokensComponent } from './pg-tokens.component';
import { PgBordersComponent } from './pg-borders.component';
import { PgAnimationsComponent } from './pg-animations.component';

@Component({
  selector: 'app-pg-section-patterns',
  standalone: true,
  imports: [PgTokensComponent, PgBordersComponent, PgAnimationsComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .patterns {
      padding: 40px 0 40px;
      height: 100%;
      box-sizing: border-box;
      overflow-y: auto;
    }

    .patterns__overline {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 32px;
      display: block;
    }

    .patterns__headline {
      font-family: var(--serif);
      font-size: 48px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.1;
      color: var(--ink);
      max-width: 640px;
      margin-bottom: 16px;
    }

    .patterns__subhead {
      font-family: var(--body);
      font-size: 15px;
      line-height: 1.65;
      color: var(--ink-light);
      max-width: 480px;
      margin-bottom: 64px;
    }

    /* Three editorial vignettes: 2-col asymmetric on desktop */
    .vignette-spread {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 0;
      border-top: 3px solid var(--ink);
      margin-bottom: 48px;
    }

    .vignette-spread--reversed {
      grid-template-columns: 1fr 2fr;
    }

    .vignette-spread--full {
      grid-template-columns: 1fr;
    }

    .vignette-pane {
      border-right: 1px solid var(--border);
      padding: 40px 32px 48px;
    }

    .vignette-pane:last-child {
      border-right: none;
    }

    .vignette-pane__label {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 24px;
      padding-bottom: 12px;
      border-bottom: 2px solid var(--ink);
      display: block;
    }

    .vignette-pane__caption {
      font-family: var(--body);
      font-size: 13px;
      font-style: italic;
      color: var(--ink-muted);
      line-height: 1.55;
      margin-top: 24px;
    }

    @media (max-width: 768px) {
      .patterns {
        padding: 48px 0 80px;
      }

      .patterns__headline {
        font-size: 32px;
        margin-bottom: 12px;
      }

      .patterns__subhead {
        margin-bottom: 40px;
      }

      .vignette-spread,
      .vignette-spread--reversed {
        grid-template-columns: 1fr;
      }

      .vignette-pane {
        border-right: none;
        border-bottom: 1px solid var(--border);
        padding: 32px 0 36px;
      }

      .vignette-pane:last-child {
        border-bottom: none;
      }
    }
  `],
  template: `
    <div class="patterns">
      <span class="patterns__overline">Presentation</span>

      <h2 class="patterns__headline">A design language built for reading.</h2>

      <p class="patterns__subhead">
        Ink on cream. Playfair headlines. Source Serif body copy. Every token
        chosen to make long-form spec documents feel like considered documents,
        not generated artifacts.
      </p>

      <!-- Vignette 1: Tokens (wide left) -->
      <div class="vignette-spread">
        <div class="vignette-pane">
          <span class="vignette-pane__label">Color &amp; Typography Tokens</span>
          <app-pg-tokens />
          <p class="vignette-pane__caption">
            Every color is a CSS custom property — dark mode is a single
            <code>[data-theme]</code> swap, no duplication.
          </p>
        </div>
        <div class="vignette-pane">
          <span class="vignette-pane__label">Borders &amp; Rules</span>
          <app-pg-borders />
          <p class="vignette-pane__caption">
            Borders carry semantic weight: 1px divides, 2px titles, 3px sections.
          </p>
        </div>
      </div>

      <!-- Vignette 2: Animations (full width) -->
      <div class="vignette-spread vignette-spread--full">
        <div class="vignette-pane">
          <span class="vignette-pane__label">Motion &amp; Interactions</span>
          <app-pg-animations />
          <p class="vignette-pane__caption">
            Animations are purposeful — each maps to a specific product moment.
            No decoration for its own sake.
          </p>
        </div>
      </div>
    </div>
  `,
})
export class PgSectionPatternsComponent {}
