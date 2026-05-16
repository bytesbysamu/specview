import { Component, ChangeDetectionStrategy, signal, OnInit, OnDestroy } from '@angular/core';

interface TokenRow {
  token: string;
  light: string;
  dark: string;
}

@Component({
  selector: 'app-pg-narrative-dark',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="nw-intro">
      <p class="nw-overline">DARK MODE</p>
      <h2 class="nw-headline">Two themes, one source of truth</h2>
      <p class="nw-deck">
        Specview's dark mode is not a second stylesheet — it is a single set of CSS custom
        properties whose values swap under the <code class="nw-code">[data-theme="dark"]</code>
        attribute on <code class="nw-code">&lt;html&gt;</code>. Every color in the product
        is expressed as a token; no raw hex value appears in component CSS. The result is
        a theme switch that costs one attribute write and persists across sessions via
        <code class="nw-code">localStorage</code>.
      </p>
    </div>

    <div class="nw-toggle-row">
      <button class="nw-toggle-btn" (click)="toggleTheme()">
        Toggle theme (currently {{ isDark() ? 'dark' : 'light' }})
      </button>
    </div>

    <div class="nw-table-wrapper">
      <table class="nw-token-table">
        <thead>
          <tr>
            <th class="nw-th">Token</th>
            <th class="nw-th">Light</th>
            <th class="nw-th">Dark</th>
          </tr>
        </thead>
        <tbody>
          @for (row of tokenRows; track row.token) {
            <tr class="nw-tr">
              <td class="nw-td nw-td--token">{{ row.token }}</td>
              <td class="nw-td">
                <span class="nw-swatch" [style.background]="row.light"></span>
                {{ row.light }}
              </td>
              <td class="nw-td">
                <span class="nw-swatch" [style.background]="row.dark"></span>
                {{ row.dark }}
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>

    <div class="nw-pullquote-row nw-pullquote-row--centered">
      <div class="nw-pullquote nw-pullquote--single">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          Ship dark mode on day one — not as a feature request six months later.
        </p>
        <p class="nw-pullquote-attr">On designing for both themes from the start</p>
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

    .nw-code {
      font-family: monospace;
      font-size: 15px;
      background: var(--code-bg, rgba(0, 0, 0, 0.05));
      padding: 1px 5px;
      border-radius: 2px;
    }

    /* ── Toggle ─────────────────────────────────────────────────────────────── */
    .nw-toggle-row {
      margin: 32px 0;
    }

    .nw-toggle-btn {
      padding: 10px 20px;
      font-family: var(--sans);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0.04em;
      background: var(--ink);
      color: var(--bg);
      border: none;
      cursor: pointer;
      transition: opacity 0.15s;
    }

    .nw-toggle-btn:hover {
      opacity: 0.82;
    }

    /* ── Token table ────────────────────────────────────────────────────────── */
    .nw-table-wrapper {
      overflow-x: auto;
      margin-bottom: 48px;
    }

    .nw-token-table {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--sans);
    }

    .nw-th {
      font-family: var(--sans);
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink-muted);
      text-align: left;
      padding: 10px 16px;
      border: 1px solid var(--border);
      background: transparent;
    }

    .nw-td {
      font-family: var(--sans);
      font-size: 14px;
      color: var(--ink);
      padding: 10px 16px;
      border: 1px solid var(--border);
      vertical-align: middle;
    }

    .nw-td--token {
      font-family: monospace;
      font-size: 13px;
      color: var(--ink-muted);
    }

    .nw-tr:hover .nw-td {
      background: rgba(0, 0, 0, 0.02);
    }

    .nw-swatch {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 1px solid var(--border);
      border-radius: 2px;
      vertical-align: middle;
      margin-right: 6px;
    }

    /* ── Pullquote ──────────────────────────────────────────────────────────── */
    .nw-pullquote-row {
      display: grid;
      grid-template-columns: 1fr 1px 1fr;
      border-bottom: 1px solid var(--border);
      margin-top: 48px;
    }

    .nw-pullquote-row--centered {
      grid-template-columns: 1fr;
      max-width: 680px;
    }

    .nw-pullquote {
      padding: 36px 40px;
    }

    .nw-pullquote--single {
      padding: 36px 0;
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
export class PgNarrativeDarkComponent implements OnInit, OnDestroy {
  isDark = signal<boolean>(false);
  private themeObserver: MutationObserver | null = null;

  readonly tokenRows: TokenRow[] = [
    { token: '--ink',       light: '#1a1a1a', dark: '#e8e6e1' },
    { token: '--bg',        light: '#faf9f6', dark: '#1a1a1a' },
    { token: '--border',    light: '#d4d0c8', dark: '#3a3a3a' },
    { token: '--red',       light: '#c0392b', dark: '#e74c3c' },
    { token: '--ink-muted', light: '#6b6b6b', dark: '#8a8a8a' },
  ];

  ngOnInit(): void {
    this.syncDark();
    this.themeObserver = new MutationObserver(() => this.syncDark());
    this.themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });
  }

  ngOnDestroy(): void {
    this.themeObserver?.disconnect();
    this.themeObserver = null;
  }

  toggleTheme(): void {
    const next = this.isDark() ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    this.isDark.set(next === 'dark');
  }

  /** Read current theme from DOM — stays in sync with shell's toggle. */
  private syncDark(): void {
    const current = document.documentElement.getAttribute('data-theme')
      ?? localStorage.getItem('theme')
      ?? 'light';
    this.isDark.set(current === 'dark');
  }
}
