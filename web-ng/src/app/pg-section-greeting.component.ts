/**
 * pg-section-greeting.component.ts
 *
 * Playground V3 — Section 1 "Greeting".
 *
 * EXTRACTION API
 * ──────────────
 * This component is fully extractable for landing page consumption.
 * All content is hardcoded in the template — there are no input signals,
 * no constructor-injected dependencies, no references to
 * PgScrollShellComponent's internal signals, and no coupling to the
 * gating state machine.
 *
 * Named export: PgSectionGreetingComponent
 *
 * Input contract:  none
 * Output contract: none
 *
 * Usage outside the scroll shell:
 *   <app-pg-section-greeting />
 *
 * Zero transitive playground dependencies.
 * The "Scroll to explore" cue in the footer rule is cosmetic;
 * it carries no functional behaviour that requires the scroll shell.
 */
import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-pg-section-greeting',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .greeting {
      padding: 80px 0 40px;
      display: flex;
      flex-direction: column;
      height: 100%;
      box-sizing: border-box;
    }

    .greeting__overline {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 32px;
      display: block;
    }

    .greeting__headline {
      font-family: var(--serif);
      font-size: 64px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.08;
      color: var(--ink);
      max-width: 880px;
      margin-bottom: 40px;
    }

    .greeting__body {
      font-family: var(--body);
      font-size: 17px;
      line-height: 1.7;
      color: var(--ink-light);
      max-width: 540px;
      margin-bottom: 40px;
    }

    .greeting__cta {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
      margin-bottom: 0;
    }

    .greeting__cta-btn {
      font-family: var(--sans);
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      background: var(--accent);
      color: var(--bg);
      border: 2px solid var(--accent);
      padding: 14px 36px;
      text-decoration: none;
      cursor: pointer;
      transition: opacity 0.18s ease, transform 0.18s ease;
    }

    .greeting__cta-btn:hover {
      opacity: 0.88;
      transform: translateY(-1px);
    }

    .greeting__cta-link {
      font-family: var(--sans);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.04em;
      color: var(--ink);
      text-decoration: underline;
      text-underline-offset: 3px;
    }

    .greeting__cta-link:hover {
      opacity: 0.7;
    }

    .greeting__rule {
      margin-top: auto;
      padding-top: 80px;
      border-top: 1px solid var(--border);
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .greeting__scroll-label {
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }

    .greeting__scroll-line {
      height: 1px;
      width: 48px;
      background: var(--border);
    }

    @media (max-width: 768px) {
      .greeting {
        padding: 48px 0 80px;
      }

      .greeting__headline {
        font-size: 40px;
      }

      .greeting__body {
        font-size: 15px;
      }
    }
  `],
  template: `
    <div class="greeting">
      <span class="greeting__overline">Specview — Playground</span>

      <h1 class="greeting__headline">
        From braindump<br>to spec set.
      </h1>

      <p class="greeting__body">
        Paste a rough idea — a stream of consciousness, a half-formed thought —
        and the AI pipeline turns it into analysis, epic, architecture, and an
        implementation guide a developer can act on.
      </p>

      <div class="greeting__cta">
        <a routerLink="/signup" class="greeting__cta-btn">Try it free</a>
        <a routerLink="/login" class="greeting__cta-link">Sign in</a>
      </div>

      <div class="greeting__rule">
        <span class="greeting__scroll-line"></span>
        <span class="greeting__scroll-label">Scroll to explore</span>
      </div>
    </div>
  `,
})
export class PgSectionGreetingComponent {}
