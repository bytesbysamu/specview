import { Component, ChangeDetectionStrategy } from '@angular/core';
import { PgComponentsAppComponent } from './pg-components-app.component';
import { PgComponentsUiComponent } from './pg-components-ui.component';

@Component({
  selector: 'app-pg-narrative-screens',
  standalone: true,
  imports: [PgComponentsAppComponent, PgComponentsUiComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="nw-intro">
      <p class="nw-overline">SCREEN GALLERY</p>
      <h2 class="nw-headline">Live components, not static screenshots</h2>
      <p class="nw-deck">
        Every screen in this gallery is rendered by the same Angular components running in
        production. Nothing is mocked, proxied, or frozen for presentation. The application
        states you see here — loading, success, empty, error — are the real states specview
        enters during a spec generation run. Hover, click, and inspect them as you would in
        the live product.
      </p>
    </div>

    <app-pg-components-app />
    <app-pg-components-ui />

    <div class="nw-pullquote-row">
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          Every component you see here is the same one running in production.
        </p>
        <p class="nw-pullquote-attr">On zero-gap design fidelity</p>
      </div>
      <div class="nw-pullquote-divider"></div>
      <div class="nw-pullquote">
        <p class="nw-pullquote-mark">"</p>
        <p class="nw-pullquote-text">
          Static mockups lie. Live components don't.
        </p>
        <p class="nw-pullquote-attr">On honest presentation</p>
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
export class PgNarrativeScreensComponent {}
