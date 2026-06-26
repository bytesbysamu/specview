import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from './auth.service';

export type Plan = 'free' | 'pro' | 'lapsed';

/** Stripe billing-interval / variant accepted by the checkout endpoint. */
export type CheckoutPlan = 'monthly' | 'yearly' | 'one_time';

interface BillingStatusResponse {
  plan: 'free' | 'pro' | 'lapsed';
  status?: 'active' | 'past_due' | 'canceled' | null;
  current_period_end?: string | null;
  manage_url?: string | null;
}

interface CheckoutSessionResponse {
  url: string;
}

@Injectable({ providedIn: 'root' })
export class SubscriptionService {
  readonly plan = signal<Plan>('free');
  readonly isPro = computed(() => this.plan() === 'pro');
  private auth = inject(AuthService);

  constructor(private http: HttpClient) {
    if (this.auth.isLoggedIn()) {
      this.refresh();
    }
  }

  async refresh(): Promise<void> {
    const res = await firstValueFrom(
      this.http.get<BillingStatusResponse>('/api/billing/status')
    );
    this.plan.set(res.plan);
  }

  /**
   * Start a Stripe Checkout session and redirect the browser to the hosted
   * payment page. Defaults match the backend convention (oll_pro / monthly);
   * each (product, plan) pair resolves server-side to a Stripe price.
   */
  async startCheckout(product = 'oll_pro', plan: CheckoutPlan = 'monthly'): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<CheckoutSessionResponse>(
        '/api/billing/create-checkout-session',
        { product, plan }
      )
    );
    this.redirect(res.url);
  }

  /** Extracted for testability — overridden in specs to prevent page reload. */
  protected redirect(url: string): void {
    window.location.href = url;
  }

  async verifySession(sessionId: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.get<BillingStatusResponse>('/api/billing/verify-session', {
        params: { session_id: sessionId },
      })
    );
    this.plan.set(res.plan);
  }
}
