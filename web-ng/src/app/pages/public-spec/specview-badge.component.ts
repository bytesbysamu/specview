import { Component } from '@angular/core';

@Component({
  selector: 'app-specview-badge',
  standalone: true,
  imports: [],
  template: `
    <footer class="badge-footer">
      <a
        class="badge-link"
        href="/"
        target="_blank"
        rel="noopener noreferrer"
        data-test="specview-badge">
        Generated with Specview
      </a>
    </footer>
  `,
  styles: [`
    .badge-footer {
      padding: 16px 24px 24px;
      text-align: center;
    }

    .badge-link {
      font-family: var(--sans);
      font-size: 11px;
      color: var(--ink-muted);
      text-decoration: none;
      letter-spacing: 0.03em;
      opacity: 0.75;
      transition: opacity 0.15s;
      padding: 6px 10px;
      border-radius: 4px;
      display: inline-block;
      min-height: 44px;
      line-height: 44px;
      padding-top: 0;
      padding-bottom: 0;
    }

    .badge-link:hover {
      opacity: 1;
      color: var(--ink-light);
    }

    @media (max-width: 640px) {
      .badge-footer {
        padding: 12px 16px 20px;
      }
    }
  `],
})
export class SpecviewBadgeComponent {}
