import { Component, ChangeDetectionStrategy } from '@angular/core';
import { PgAnimationsComponent } from './pg-animations.component';
import { PgStateMatrixComponent } from './pg-state-matrix.component';

@Component({
  selector: 'app-pg-narrative-patterns',
  standalone: true,
  imports: [PgAnimationsComponent, PgStateMatrixComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="nw-intro">
      <p class="nw-overline">DESIGN PATTERNS</p>
      <h2 class="nw-headline">Motion and state, choreographed</h2>
      <p class="nw-deck">
        Perceived quality is built on two invisible pillars: animation and state management.
        Transitions signal intent — they tell users what just happened and what comes next.
        A complete state matrix eliminates entire classes of bugs by making every possible
        condition explicit before a single line of logic is written. The patterns below are
        not decorative; they are the load-bearing structure of the specview experience.
      </p>
    </div>

    <app-pg-animations />
    <app-pg-state-matrix />

    <div class="nw-pullquote-row">
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          Animation isn't polish — it's communication.
        </p>
        <p class="nw-pullquote-attr">On motion as meaning</p>
      </div>
      <div class="nw-pullquote-divider"></div>
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          A state matrix is a contract with every possible future.
        </p>
        <p class="nw-pullquote-attr">On exhaustive state design</p>
      </div>
    </div>
  `,
  styles: [`
    .nw-intro {
      margin-bottom: 40px;
    }

    .nw-overline {
      font-family: var(--sans);
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--red);
      margin-bottom: 14px;
    }

    .nw-headline {
      font-family: 'Playfair Display', Georgia, serif;
      font-size: 44px;
      font-weight: 700;
      line-height: 1.15;
      color: var(--ink);
      margin: 0 0 20px;
    }

    .nw-deck {
      font-family: 'Source Serif 4', 'Source Serif Pro', Georgia, serif;
      font-size: 18px;
      line-height: 1.6;
      color: var(--ink);
      max-width: 680px;
      margin: 0;
    }

    .nw-pullquote-row {
      display: grid;
      grid-template-columns: 1fr 1px 1fr;
      border-bottom: 1px solid var(--border);
      margin-top: 48px;
    }

    .nw-pullquote {
      padding: 36px 40px;
    }

    .nw-pullquote-divider {
      background: var(--border);
    }

    .nw-pullquote-mark {
      font-family: var(--serif);
      font-size: 56px;
      font-weight: 700;
      color: var(--border);
      line-height: 0.8;
      margin-bottom: 8px;
    }

    .nw-pullquote-text {
      font-family: var(--serif);
      font-size: 22px;
      font-style: italic;
      line-height: 1.45;
      color: var(--ink);
      margin-bottom: 16px;
    }

    .nw-pullquote-attr {
      font-family: var(--sans);
      font-size: 11px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin: 0;
    }
  `],
})
export class PgNarrativePatternsComponent {}
