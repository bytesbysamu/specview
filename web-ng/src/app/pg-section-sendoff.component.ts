/**
 * pg-section-sendoff.component.ts
 *
 * Playground V3 — Section 5 "Send-Off".
 *
 * EXTRACTION API
 * ──────────────
 * This component is fully extractable for landing page consumption.
 * All data flows through Angular input signals — no constructor-injected
 * dependencies, no references to PgScrollShellComponent's internal signals,
 * and no coupling to the gating state machine.
 *
 * Named export: PgSectionSendoffComponent
 *
 * Input contract:
 *   headline  input<string>  — Main headline text. Default: 'Your turn.'
 *   bodyText  input<string>  — Body paragraph copy.
 *   ctaLabel  input<string>  — Primary CTA button label. Default: 'Try the live demo'
 *
 * Output contract:
 *   ctaClick  output<void>   — Emitted when the primary CTA button is clicked.
 *
 * Usage outside the scroll shell:
 *   <app-pg-section-sendoff
 *     [headline]="'Ready to write your spec?'"
 *     [bodyText]="'Start with a braindump.'"
 *     [ctaLabel]="'Get started'"
 *     (ctaClick)="onSignup()"
 *   />
 *
 * Zero transitive playground dependencies — no shared tokens, no fixture data.
 * The three footer stats (pipeline stages, median latency, output format) are
 * static values embedded in the template and are not configurable inputs.
 */
import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-pg-section-sendoff',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .sendoff {
      padding: 80px 0 80px;
      height: 100%;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
    }

    .sendoff__overline {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 32px;
      display: block;
    }

    .sendoff__headline {
      font-family: var(--serif);
      font-size: 64px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.08;
      color: var(--ink);
      max-width: 880px;
      margin-bottom: 24px;
    }

    .sendoff__body {
      font-family: var(--body);
      font-size: 17px;
      line-height: 1.7;
      color: var(--ink-light);
      max-width: 540px;
      margin-bottom: 56px;
    }

    .sendoff__cta {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
      margin-bottom: auto;
    }

    .sendoff__cta-btn {
      font-family: var(--sans);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: var(--accent);
      color: var(--bg);
      border: 2px solid var(--accent);
      padding: 14px 36px;
      cursor: pointer;
      transition: opacity 0.18s ease, transform 0.18s ease;
    }

    .sendoff__cta-btn:hover {
      opacity: 0.88;
      transform: translateY(-1px);
    }

    .sendoff__cta-sub {
      font-family: var(--body);
      font-size: 14px;
      color: var(--ink-muted);
      font-style: italic;
    }

    .sendoff__signin-link {
      color: var(--ink);
      text-decoration: underline;
      font-style: normal;
      font-weight: 600;
    }

    .sendoff__signin-link:hover {
      opacity: 0.7;
    }

    .sendoff__footer {
      margin-top: 120px;
      padding-top: 32px;
      border-top: 3px solid var(--ink);
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0;
    }

    .sendoff__footer-cell {
      border-right: 1px solid var(--border);
      padding: 24px 28px 24px 0;
    }

    .sendoff__footer-cell:last-child {
      border-right: none;
      padding-right: 0;
      padding-left: 28px;
    }

    .sendoff__footer-cell:nth-child(2) {
      padding-left: 28px;
    }

    .sendoff__footer-label {
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--ink-muted);
      display: block;
      margin-bottom: 8px;
    }

    .sendoff__footer-value {
      font-family: var(--serif);
      font-size: 20px;
      font-weight: 700;
      color: var(--ink);
    }

    @media (max-width: 768px) {
      .sendoff {
        padding: 48px 0 100px;
      }

      .sendoff__headline {
        font-size: 40px;
      }

      .sendoff__body {
        font-size: 15px;
        margin-bottom: 40px;
      }

      .sendoff__footer {
        grid-template-columns: 1fr;
        margin-top: 64px;
      }

      .sendoff__footer-cell,
      .sendoff__footer-cell:last-child,
      .sendoff__footer-cell:nth-child(2) {
        border-right: none;
        border-bottom: 1px solid var(--border);
        padding: 20px 0;
      }

      .sendoff__footer-cell:last-child {
        border-bottom: none;
      }
    }
  `],
  template: `
    <div class="sendoff">
      <span class="sendoff__overline">Send-Off</span>

      <h2 class="sendoff__headline">{{ headline() }}</h2>

      <p class="sendoff__body">{{ bodyText() }}</p>

      <div class="sendoff__cta">
        <button class="sendoff__cta-btn" (click)="ctaClick.emit()">
          {{ ctaLabel() }}
        </button>
        <span class="sendoff__cta-sub">Already have an account? <a routerLink="/login" class="sendoff__signin-link">Sign in</a></span>
      </div>

      <footer class="sendoff__footer">
        <div class="sendoff__footer-cell">
          <span class="sendoff__footer-label">Pipeline stages</span>
          <span class="sendoff__footer-value">4</span>
        </div>
        <div class="sendoff__footer-cell">
          <span class="sendoff__footer-label">Median latency</span>
          <span class="sendoff__footer-value">&lt; 60s</span>
        </div>
        <div class="sendoff__footer-cell">
          <span class="sendoff__footer-label">Output format</span>
          <span class="sendoff__footer-value">Markdown</span>
        </div>
      </footer>
    </div>
  `,
})
export class PgSectionSendoffComponent {
  readonly headline = input<string>('Your turn.');
  readonly bodyText = input<string>(
    'Paste a rough idea — any shape, any length — and the pipeline does the rest. ' +
    'Analysis, epic, architecture, implementation guide. All in under a minute.'
  );
  readonly ctaLabel = input<string>('Try the live demo');

  readonly ctaClick = output<void>();
}
