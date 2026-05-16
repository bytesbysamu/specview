import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import {
  FAQ_ITEMS,
  HOW_IT_WORKS_STEPS,
  OUTPUT_CARDS,
  COMPARISON_ROWS,
  PRICING_TIERS,
  PULL_QUOTES,
  type FaqItem,
  type HowItWorksStep,
  type OutputCard,
  type ComparisonRow,
  type PricingTier,
  type PullQuote,
} from './pg-landing-data';

@Component({
  selector: 'app-pg-landing-showcase',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- ── Editorial framing ─────────────────────────────────────────────────── -->
    <div class="ls-intro">
      <p class="ls-overline">THE LANDING PAGE</p>
      <h2 class="ls-headline">Every pattern, in one place</h2>
      <p class="ls-deck">
        The playground is the superset. Every pattern that appears on the public
        landing page lives here first as an interactive Angular component — masthead,
        output cards, how-it-works steps, comparison table, pricing tiers, FAQ, and
        pull quotes. Phase 3 will extract these directly to static HTML.
      </p>
    </div>

    <!-- ── 1. Masthead ────────────────────────────────────────────────────────── -->
    <section class="ls-section" id="ls-masthead">
      <p class="ls-section-label">Pattern 1 — Masthead</p>

      <div class="ls-masthead">
        <div class="ls-masthead__top">
          <div class="ls-masthead__edition">
            <span class="ls-masthead__edition-label">Vol. II</span>
            <span class="ls-masthead__edition-sep">&nbsp;&middot;&nbsp;</span>
            <span class="ls-masthead__edition-label">The Spec Issue</span>
          </div>
          <div class="ls-masthead__center">
            <h1 class="ls-masthead__title">Specview</h1>
            <p class="ls-masthead__tagline">All the Specs Fit to Build</p>
          </div>
          <div class="ls-masthead__meta">
            <button class="ls-masthead__theme-btn" (click)="toggleTheme()">
              {{ isDark() ? 'Light mode' : 'Dark mode' }}
            </button>
          </div>
        </div>
        <div class="ls-masthead__rule"></div>
        <div class="ls-masthead__subhead">
          <span>Braindump → Spec → Ship</span>
          <span class="ls-masthead__subhead-sep">|</span>
          <span>44.5s avg generation</span>
          <span class="ls-masthead__subhead-sep">|</span>
          <span>Free tier available</span>
        </div>
      </div>
    </section>

    <!-- ── 2. Output Cards ────────────────────────────────────────────────────── -->
    <section class="ls-section" id="ls-output-cards">
      <p class="ls-section-label">Pattern 2 — Output Cards</p>
      <h3 class="ls-section-heading">Five documents. One braindump.</h3>
      <p class="ls-section-subhead">
        Every generation produces this complete set — interlocking, ordered, and
        ready to act on.
      </p>

      <div class="ls-card-grid">
        @for (card of outputCards; track card.filename) {
          <div class="ls-card">
            <span class="ls-card__icon">{{ card.icon }}</span>
            <span class="ls-card__filename">{{ card.filename }}</span>
            <p class="ls-card__desc">{{ card.description }}</p>
          </div>
        }
      </div>
    </section>

    <!-- ── 3. How It Works ────────────────────────────────────────────────────── -->
    <section class="ls-section" id="ls-how-it-works">
      <p class="ls-section-label">Pattern 3 — How It Works</p>
      <h3 class="ls-section-heading">Three steps to a complete spec</h3>

      <div class="ls-steps">
        @for (step of howItWorksSteps; track step.number) {
          <div class="ls-step">
            <div class="ls-step__number">{{ step.number }}</div>
            <div class="ls-step__body">
              <h4 class="ls-step__title">{{ step.title }}</h4>
              <p class="ls-step__text">{{ step.body }}</p>
              <div class="ls-step__excerpt">
                <p class="ls-step__excerpt-label">{{ step.excerptLabel }}</p>
                <p class="ls-step__excerpt-text">{{ step.excerpt }}</p>
              </div>
            </div>
          </div>
        }
      </div>
    </section>

    <!-- ── 4. Comparison Table ────────────────────────────────────────────────── -->
    <section class="ls-section" id="ls-comparison">
      <p class="ls-section-label">Pattern 4 — Comparison Table</p>
      <h3 class="ls-section-heading">Specview vs. the alternatives</h3>
      <p class="ls-section-subhead">
        Lovable, Bolt, and Kiro generate code. Specview generates the spec that
        makes the code worth writing.
      </p>

      <div class="ls-table-wrap">
        <table class="ls-table">
          <thead>
            <tr>
              <th class="ls-table__th ls-table__th--dim">Dimension</th>
              <th class="ls-table__th ls-table__th--competitor">Lovable / Bolt / Kiro</th>
              <th class="ls-table__th ls-table__th--specview">Specview</th>
            </tr>
          </thead>
          <tbody>
            @for (row of comparisonRows; track row.dimension) {
              <tr class="ls-table__row">
                <td class="ls-table__td ls-table__td--dim">{{ row.dimension }}</td>
                <td class="ls-table__td ls-table__td--competitor">{{ row.competitor }}</td>
                <td class="ls-table__td ls-table__td--specview">{{ row.specview }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>

    <!-- ── 5. Pricing ─────────────────────────────────────────────────────────── -->
    <section class="ls-section" id="ls-pricing">
      <p class="ls-section-label">Pattern 5 — Pricing</p>
      <h3 class="ls-section-heading">Simple, honest pricing</h3>

      <div class="ls-pricing-grid">
        @for (tier of pricingTiers; track tier.name; let last = $last) {
          <div class="ls-tier" [class.ls-tier--primary]="tier.isPrimary">
            <p class="ls-tier__name">{{ tier.name }}</p>
            <p class="ls-tier__price">
              <span class="ls-tier__price-amount">{{ tier.price }}</span>
              <span class="ls-tier__price-suffix">{{ tier.priceSuffix }}</span>
            </p>
            <p class="ls-tier__desc">{{ tier.description }}</p>
            <ul class="ls-tier__features">
              @for (feature of tier.features; track feature) {
                <li class="ls-tier__feature">— {{ feature }}</li>
              }
            </ul>
            <button
              class="ls-tier__cta"
              [class.ls-tier__cta--primary]="tier.isPrimary"
            >{{ tier.ctaLabel }}</button>
          </div>
          @if (!last) {
            <div class="ls-pricing-divider"></div>
          }
        }
      </div>
    </section>

    <!-- ── 6. FAQ Accordion ───────────────────────────────────────────────────── -->
    <section class="ls-section" id="ls-faq">
      <p class="ls-section-label">Pattern 6 — FAQ Accordion</p>
      <h3 class="ls-section-heading">Common questions</h3>

      <div class="ls-faq">
        @for (item of faqItems; track item.question) {
          <details class="ls-faq__item">
            <summary class="ls-faq__question">{{ item.question }}</summary>
            <p class="ls-faq__answer">{{ item.answer }}</p>
          </details>
        }
      </div>
    </section>

    <!-- ── 7. Pull Quotes ─────────────────────────────────────────────────────── -->
    <section class="ls-section" id="ls-pullquotes">
      <p class="ls-section-label">Pattern 7 — Pull Quotes</p>
      <h3 class="ls-section-heading">From the field</h3>

      <div class="ls-pullquote-row">
        @for (quote of pullQuotesPair1; track quote.text) {
          <div class="ls-pullquote">
            <p class="ls-pullquote__mark">"</p>
            <p class="ls-pullquote__text">{{ quote.text }}</p>
            <p class="ls-pullquote__attr">{{ quote.attribution }}</p>
          </div>
          @if ($index === 0) {
            <div class="ls-pullquote-divider"></div>
          }
        }
      </div>

      <div class="ls-pullquote-row ls-pullquote-row--bordered">
        @for (quote of pullQuotesPair2; track quote.text) {
          <div class="ls-pullquote">
            <p class="ls-pullquote__mark">"</p>
            <p class="ls-pullquote__text">{{ quote.text }}</p>
            <p class="ls-pullquote__attr">{{ quote.attribution }}</p>
          </div>
          @if ($index === 0) {
            <div class="ls-pullquote-divider"></div>
          }
        }
      </div>
    </section>
  `,
  styles: [`
    .ls-intro { margin-bottom: 56px; }

    .ls-overline {
      font-family: var(--sans);
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--red);
      margin-bottom: 14px;
    }

    .ls-headline {
      font-family: var(--serif);
      font-size: 44px;
      font-weight: 700;
      line-height: 1.15;
      color: var(--ink);
      margin: 0 0 20px;
    }

    .ls-deck {
      font-family: var(--body);
      font-size: 18px;
      line-height: 1.6;
      color: var(--ink);
      max-width: 680px;
    }

    .ls-section {
      padding: 48px 0 40px;
      border-top: 1px solid var(--border);
    }

    .ls-section-label {
      font-family: var(--sans);
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 20px;
    }

    .ls-section-heading {
      font-family: var(--serif);
      font-size: 32px;
      font-weight: 700;
      line-height: 1.2;
      color: var(--ink);
      margin: 0 0 12px;
    }

    .ls-section-subhead {
      font-family: var(--body);
      font-size: 16px;
      line-height: 1.6;
      color: var(--ink-light);
      max-width: 600px;
      margin-bottom: 32px;
    }

    .ls-masthead { border: 1px solid var(--border-dark); padding: 32px 40px 24px; }

    .ls-masthead__top {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: flex-end;
      gap: 24px;
      margin-bottom: 20px;
    }

    .ls-masthead__edition {
      display: flex;
      align-items: center;
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--ink-muted);
      padding-bottom: 8px;
    }

    .ls-masthead__edition-label { white-space: nowrap; }
    .ls-masthead__edition-sep { opacity: 0.5; }
    .ls-masthead__center { text-align: center; }

    .ls-masthead__title {
      font-family: var(--serif);
      font-size: 64px;
      font-weight: 700;
      line-height: 1;
      letter-spacing: -0.02em;
      color: var(--ink);
    }

    .ls-masthead__tagline {
      font-family: var(--body);
      font-size: 15px;
      font-style: italic;
      color: var(--ink-light);
      margin-top: 8px;
      letter-spacing: 0.02em;
    }

    .ls-masthead__meta {
      display: flex;
      justify-content: flex-end;
      align-items: flex-end;
      padding-bottom: 8px;
    }

    .ls-masthead__theme-btn {
      font-family: var(--sans);
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: transparent;
      border: 1px solid var(--border);
      color: var(--ink-muted);
      padding: 6px 12px;
      cursor: pointer;
      transition: color 0.15s, border-color 0.15s;
    }

    .ls-masthead__theme-btn:hover { color: var(--ink); border-color: var(--ink-muted); }
    .ls-masthead__rule { height: 3px; background: var(--border-dark); margin-bottom: 8px; }
    .ls-masthead__subhead { display: flex; align-items: center; justify-content: center; gap: 12px; font-family: var(--sans); font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-muted); padding: 6px 0; }
    .ls-masthead__subhead-sep { opacity: 0.4; }

    .ls-card-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0;
      border: 1px solid var(--border);
      margin-top: 32px;
    }

    @media (max-width: 768px) {
      .ls-card-grid { grid-template-columns: repeat(2, 1fr); }
      .ls-card:nth-child(even) { border-right: none; }
      .ls-card:nth-child(4n) { border-right: 1px solid var(--border); }
      .ls-card:nth-child(odd):nth-child(n+3),
      .ls-card:nth-child(even):nth-child(n+4) { border-top: 1px solid var(--border); }
    }

    .ls-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 24px 20px;
      border-right: 1px solid var(--border);
    }

    .ls-card:nth-child(4n) { border-right: none; }
    .ls-card:nth-child(n+5) { border-top: 1px solid var(--border); }
    .ls-card__icon { font-size: 20px; color: var(--accent); line-height: 1; }

    .ls-card__filename {
      font-family: 'Source Code Pro', 'Fira Code', monospace;
      font-size: 12px;
      font-weight: 600;
      color: var(--ink);
      letter-spacing: 0.02em;
    }

    .ls-card__desc { font-family: var(--sans); font-size: 12px; line-height: 1.55; color: var(--ink-light); }

    .ls-steps { display: flex; flex-direction: column; gap: 0; margin-top: 32px; }

    .ls-step {
      display: grid;
      grid-template-columns: 140px 1fr;
      gap: 0;
      padding: 40px 0;
      border-top: 1px solid var(--border);
    }

    .ls-step:first-child { border-top: none; }

    .ls-step__number {
      font-family: var(--serif);
      font-size: 96px;
      font-weight: 700;
      line-height: 0.85;
      color: var(--border);
      letter-spacing: -0.04em;
      padding-right: 32px;
    }

    .ls-step__body { display: flex; flex-direction: column; gap: 12px; padding-top: 8px; }
    .ls-step__title { font-family: var(--serif); font-size: 28px; font-weight: 700; color: var(--ink); margin: 0; }
    .ls-step__text { font-family: var(--body); font-size: 16px; line-height: 1.65; color: var(--ink-light); max-width: 560px; }
    .ls-step__excerpt { border-left: 3px solid var(--accent); padding: 12px 16px; background: var(--code-bg); margin-top: 4px; }
    .ls-step__excerpt-label { font-family: var(--sans); font-size: 9px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--ink-muted); margin-bottom: 8px; }
    .ls-step__excerpt-text { font-family: var(--body); font-size: 13px; font-style: italic; line-height: 1.7; color: var(--ink-light); white-space: pre-line; }

    .ls-table-wrap { overflow-x: auto; margin-top: 32px; }
    .ls-table { width: 100%; border-collapse: collapse; border: 1px solid var(--border); }

    .ls-table__th {
      font-family: var(--serif);
      font-size: 15px;
      font-weight: 700;
      text-align: left;
      padding: 14px 20px;
      border-bottom: 2px solid var(--border-dark);
      color: var(--ink);
    }

    .ls-table__th--dim { width: 160px; }
    .ls-table__th--competitor,
    .ls-table__td--competitor { color: var(--ink-muted); }
    .ls-table__row { border-bottom: 1px solid var(--border); }
    .ls-table__row:last-child { border-bottom: none; }
    .ls-table__row:nth-child(even) { background: var(--code-bg); }
    .ls-table__td { font-family: var(--sans); font-size: 13px; line-height: 1.5; padding: 14px 20px; vertical-align: top; color: var(--ink); }
    .ls-table__td--dim { font-weight: 700; font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; color: var(--ink-muted); white-space: nowrap; }

    .ls-pricing-grid { display: grid; grid-template-columns: 1fr 1px 1fr; border: 1px solid var(--border); margin-top: 32px; }
    .ls-pricing-divider { background: var(--border); }
    .ls-tier { padding: 40px 36px; }
    .ls-tier__name { font-family: var(--serif); font-size: 28px; font-weight: 700; color: var(--ink); margin-bottom: 16px; }
    .ls-tier__price { display: flex; align-items: baseline; gap: 8px; margin-bottom: 12px; }
    .ls-tier__price-amount { font-family: var(--serif); font-size: 48px; font-weight: 700; color: var(--ink); line-height: 1; letter-spacing: -0.02em; }
    .ls-tier__price-suffix { font-family: var(--sans); font-size: 12px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: var(--ink-muted); }
    .ls-tier__desc { font-family: var(--body); font-size: 14px; line-height: 1.6; color: var(--ink-light); margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 24px; }
    .ls-tier__features { list-style: none; display: flex; flex-direction: column; gap: 10px; margin-bottom: 32px; }
    .ls-tier__feature { font-family: var(--sans); font-size: 13px; line-height: 1.4; color: var(--ink-light); }

    .ls-tier__cta {
      font-family: var(--sans);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      border: 1px solid var(--border-dark);
      background: transparent;
      color: var(--ink);
      padding: 12px 28px;
      cursor: pointer;
      transition: background 0.15s, color 0.15s;
      display: block;
      width: 100%;
      text-align: center;
    }

    .ls-tier__cta:hover { background: var(--ink); color: var(--bg); }
    .ls-tier__cta--primary { background: var(--ink); color: var(--bg); }
    .ls-tier__cta--primary:hover { opacity: 0.82; }

    .ls-faq { margin-top: 32px; border-top: 1px solid var(--border); }
    .ls-faq__item { border-bottom: 1px solid var(--border); }

    .ls-faq__question { font-family: var(--serif); font-size: 18px; font-weight: 700; color: var(--ink); padding: 20px 0; cursor: pointer; list-style: none; display: flex; align-items: center; justify-content: space-between; user-select: none; }
    .ls-faq__question::-webkit-details-marker { display: none; }
    .ls-faq__question::after { content: '+'; font-family: var(--sans); font-size: 20px; font-weight: 300; color: var(--ink-muted); flex-shrink: 0; margin-left: 16px; transition: transform 0.2s; }
    .ls-faq__item[open] .ls-faq__question::after { transform: rotate(45deg); }
    .ls-faq__answer { font-family: var(--body); font-size: 16px; line-height: 1.65; color: var(--ink-light); padding: 0 0 24px; max-width: 680px; }

    .ls-pullquote-row { display: grid; grid-template-columns: 1fr 1px 1fr; border-bottom: 1px solid var(--border); margin-top: 32px; }
    .ls-pullquote-row--bordered { border-top: 1px solid var(--border); margin-top: 0; }
    .ls-pullquote-divider { background: var(--border); }
    .ls-pullquote { padding: 36px 40px; }
    .ls-pullquote__mark { font-family: var(--serif); font-size: 56px; font-weight: 700; color: var(--border); line-height: 0.8; margin-bottom: 8px; }
    .ls-pullquote__text { font-family: var(--body); font-size: 20px; font-style: italic; line-height: 1.45; color: var(--ink); margin-bottom: 16px; }
    .ls-pullquote__attr { font-family: var(--sans); font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--ink-muted); }
  `],
})
export class PgLandingShowcaseComponent {
  readonly outputCards: OutputCard[]        = OUTPUT_CARDS;
  readonly howItWorksSteps: HowItWorksStep[] = HOW_IT_WORKS_STEPS;
  readonly comparisonRows: ComparisonRow[]   = COMPARISON_ROWS;
  readonly pricingTiers: PricingTier[]       = PRICING_TIERS;
  readonly faqItems: FaqItem[]               = FAQ_ITEMS;

  readonly pullQuotesPair1: PullQuote[] = PULL_QUOTES.slice(0, 2);
  readonly pullQuotesPair2: PullQuote[] = PULL_QUOTES.slice(2, 4);

  isDark = signal<boolean>(false);

  toggleTheme(): void {
    const next = this.isDark() ? 'light' : 'dark';
    this.isDark.set(next === 'dark');
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  }
}
