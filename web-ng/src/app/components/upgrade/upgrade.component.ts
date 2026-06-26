import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { SubscriptionService } from '../../services/subscription.service';

/**
 * Stripe Checkout return target: the backend sets success_url and cancel_url to
 * FRONTEND_URL/upgrade, so Stripe redirects here after the hosted payment page.
 *
 *   success → /upgrade?session_id=cs_...  → verify the session, show the plan
 *   cancel  → /upgrade                    → friendly "no charge" message
 *
 * Verification calls GET /api/billing/verify-session (the webhook is still the
 * source of truth for plan state; this just confirms and refreshes the UI).
 */
@Component({
  selector: 'app-upgrade',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="upgrade-wrap">
      <div class="upgrade-card">
        <div class="upgrade-title">Specview</div>

        @switch (state()) {
          @case ('verifying') {
            <p class="upgrade-msg" data-test="upgrade-verifying">Confirming your payment…</p>
          }
          @case ('success') {
            <div class="upgrade-badge" data-test="upgrade-success">✓</div>
            <h2 class="upgrade-heading">You're on {{ planLabel() }}</h2>
            <p class="upgrade-msg">Thanks — your account has been upgraded. Every Pro feature is unlocked.</p>
            <a class="upgrade-cta" routerLink="/" data-test="upgrade-home">Back to your specs</a>
          }
          @case ('pending') {
            <h2 class="upgrade-heading">Payment received</h2>
            <p class="upgrade-msg" data-test="upgrade-pending">
              We're still finalising your upgrade. It usually lands within a few seconds —
              refresh, or head back and it'll be active shortly.
            </p>
            <a class="upgrade-cta" routerLink="/" data-test="upgrade-home">Back to your specs</a>
          }
          @case ('cancelled') {
            <h2 class="upgrade-heading">No charge made</h2>
            <p class="upgrade-msg" data-test="upgrade-cancelled">
              Your checkout was cancelled and you have not been charged.
              You can upgrade any time from the menu.
            </p>
            <a class="upgrade-cta" routerLink="/" data-test="upgrade-home">Back to your specs</a>
          }
        }
      </div>
    </div>
  `,
  styles: [`
    .upgrade-wrap {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg);
    }
    .upgrade-card {
      width: 360px;
      border: 1px solid var(--border);
      padding: 44px 36px;
      text-align: center;
    }
    .upgrade-title {
      font-family: 'Playfair Display', serif;
      font-size: 32px;
      font-weight: 700;
      margin-bottom: 24px;
    }
    .upgrade-badge {
      font-size: 28px;
      line-height: 1;
      width: 52px;
      height: 52px;
      margin: 0 auto 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 50%;
      color: #fff;
      background: var(--accent, #567B95);
    }
    .upgrade-heading {
      font-family: 'Playfair Display', serif;
      font-size: 22px;
      font-weight: 700;
      margin: 0 0 12px;
    }
    .upgrade-msg {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 14px;
      line-height: 1.55;
      color: var(--ink);
      margin: 0 0 24px;
    }
    .upgrade-cta {
      font-family: 'Source Sans 3', sans-serif;
      font-size: 13px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      display: inline-block;
      padding: 11px 20px;
      background: var(--ink);
      color: var(--bg);
      text-decoration: none;
    }
  `]
})
export class UpgradeComponent implements OnInit {
  state = signal<'verifying' | 'success' | 'pending' | 'cancelled'>('verifying');
  planLabel = signal('Pro');

  private route = inject(ActivatedRoute);
  private subscription = inject(SubscriptionService);

  async ngOnInit() {
    const sessionId = this.route.snapshot.queryParamMap.get('session_id');
    if (!sessionId) {
      // Stripe's cancel_url has no session_id; treat as a cancelled checkout.
      this.state.set('cancelled');
      return;
    }
    try {
      await this.subscription.verifySession(sessionId);
      if (this.subscription.isPro()) {
        this.planLabel.set('Specview Pro');
        this.state.set('success');
      } else {
        // Session is valid but the webhook hasn't flipped the plan yet.
        this.state.set('pending');
      }
    } catch {
      this.state.set('pending');
    }
  }
}
