import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

@Component({
  selector: 'app-landing-cta-bar',
  standalone: true,
  imports: [],
  template: `
    <div class="cta-bar">
      <span class="cta-bar-text">Turn your braindump into a full spec set.</span>
      <button class="cta-bar-btn" (click)="goToSignup()" data-test="landing-cta-btn">
        Paste Your Brain Dump
      </button>
    </div>
  `,
  styles: [`
    .cta-bar {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 100;
      background: var(--ink);
      color: var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 20px;
      padding: 14px 24px;
      border-top: 2px solid var(--border-dark);
    }

    .cta-bar-text {
      font-family: var(--sans);
      font-size: 14px;
      color: var(--bg);
      opacity: 0.85;
    }

    .cta-bar-btn {
      font-family: var(--sans);
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      background: var(--bg);
      color: var(--ink);
      border: none;
      padding: 10px 24px;
      cursor: pointer;
      transition: opacity 0.15s;
      white-space: nowrap;
    }

    .cta-bar-btn:hover {
      opacity: 0.85;
    }

    @media (max-width: 640px) {
      .cta-bar {
        flex-direction: column;
        gap: 10px;
        padding: 16px;
      }

      .cta-bar-text {
        text-align: center;
      }

      .cta-bar-btn {
        width: 100%;
      }
    }
  `],
})
export class LandingCtaBarComponent {
  private router = inject(Router);

  goToSignup(): void {
    this.router.navigate(['/signup']);
  }
}
