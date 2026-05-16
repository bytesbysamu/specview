import { Component } from '@angular/core';

interface JourneyStation {
  number: string;
  name: string;
  description: string;
}

@Component({
  selector: 'app-pg-journey',
  standalone: true,
  imports: [],
  template: `
    <div class="journey">
      @for (station of stations; track station.number; let last = $last) {
        <div class="journey__station" [class.journey__station--last]="last">
          <span class="journey__number">{{ station.number }}</span>
          <h3 class="journey__name">{{ station.name }}</h3>
          <p class="journey__description">{{ station.description }}</p>
          @if (last) {
            <button class="journey__cta" type="button">Try it free</button>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    /* ── Journey timeline container ────────────────────────────────────────────── */
    .journey {
      display: flex;
      flex-direction: row;
      align-items: stretch;
      width: 100%;
    }

    /* ── Individual station ─────────────────────────────────────────────────────── */
    .journey__station {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 24px 20px;
      border-right: 1px solid var(--border, #e5e7eb);
    }

    .journey__station--last {
      border-right: none;
    }

    /* ── Station number ─────────────────────────────────────────────────────────── */
    .journey__number {
      font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ink-muted, #6b7280);
    }

    /* ── Station name ───────────────────────────────────────────────────────────── */
    .journey__name {
      font-family: 'Playfair Display', serif;
      font-size: 17px;
      font-weight: 700;
      color: var(--ink, #111827);
      margin: 0;
      line-height: 1.25;
    }

    /* ── Station description ────────────────────────────────────────────────────── */
    .journey__description {
      font-family: 'Source Serif 4', 'Georgia', serif;
      font-size: 13px;
      color: var(--ink-muted, #6b7280);
      margin: 0;
      line-height: 1.5;
      flex: 1;
    }

    /* ── CTA button ─────────────────────────────────────────────────────────────── */
    .journey__cta {
      display: inline-block;
      margin-top: 12px;
      padding: 10px 16px;
      font-family: 'Source Sans 3', 'Source Sans Pro', sans-serif;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--bg, #ffffff);
      background: var(--ink, #111827);
      border: none;
      border-radius: 0;
      cursor: pointer;
      transition: opacity 0.15s;
    }

    .journey__cta:hover {
      opacity: 0.85;
    }

    /* ── Mobile: vertical stack ─────────────────────────────────────────────────── */
    @media (max-width: 768px) {
      .journey {
        flex-direction: column;
      }

      .journey__station {
        width: 100%;
        border-right: none;
        border-bottom: 1px solid var(--border, #e5e7eb);
      }

      .journey__station--last {
        border-bottom: none;
      }
    }
  `],
})
export class PgJourneyComponent {
  readonly stations: JourneyStation[] = [
    {
      number: '01',
      name: 'Land on page',
      description: 'First impressions in under 3 seconds',
    },
    {
      number: '02',
      name: 'See the pitch',
      description: 'Write messy. Ship clean.',
    },
    {
      number: '03',
      name: 'Explore playground',
      description: 'Live components, real data, no signup wall',
    },
    {
      number: '04',
      name: 'Sign up',
      description: 'Email and password — 30 seconds',
    },
    {
      number: '05',
      name: 'Generate specs',
      description: 'Paste braindump, get five documents in 45 seconds',
    },
    {
      number: '06',
      name: 'Iterate',
      description: 'AI-powered text operations refine each spec',
    },
    {
      number: '07',
      name: 'Ship',
      description: 'Share specs publicly or export to your workflow',
    },
  ];
}
