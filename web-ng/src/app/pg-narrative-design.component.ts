import { Component, ChangeDetectionStrategy } from '@angular/core';
import { PgTokensComponent } from './pg-tokens.component';
import { PgBordersComponent } from './pg-borders.component';

@Component({
  selector: 'app-pg-narrative-design',
  standalone: true,
  imports: [PgTokensComponent, PgBordersComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="nw-intro">
      <p class="nw-overline">DESIGN LANGUAGE</p>
      <h2 class="nw-headline">Every pixel earns its place</h2>
      <p class="nw-deck">
        A consistent design language is the invisible infrastructure of trust. The tokens
        below define every color, spacing step, and typographic scale used across specview.
        Borders codify exactly when and how surfaces divide — so no designer ever debates
        "1px or 2px" again. Together they form a system where decisions are made once and
        applied everywhere.
      </p>
    </div>

    <app-pg-tokens />
    <app-pg-borders />

    <div class="nw-pullquote-row">
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          The best interface is the one you don't notice — until you try to use anything else.
        </p>
        <p class="nw-pullquote-attr">On invisible consistency</p>
      </div>
      <div class="nw-pullquote-divider"></div>
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          Tokens aren't decoration. They're promises.
        </p>
        <p class="nw-pullquote-attr">On design contracts</p>
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
export class PgNarrativeDesignComponent {}
