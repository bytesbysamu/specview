import { Injectable, computed, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export type Plan = 'free' | 'pro' | 'lapsed';

interface BillingStatusResponse {
  plan: 'free' | 'pro' | 'lapsed';
}

interface CheckoutSessionResponse {
  url: string;
}

@Injectable({ providedIn: 'root' })
export class SubscriptionService {
  readonly plan = signal<Plan>('free');
  readonly isPro = computed(() => this.plan() === 'pro');

  constructor(private http: HttpClient) {
    this.refresh();
  }

  async refresh(): Promise<void> {
    const res = await firstValueFrom(
      this.http.get<BillingStatusResponse>('/api/billing/status')
    );
    this.plan.set(res.plan);
  }

  async startCheckout(): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<CheckoutSessionResponse>('/api/billing/create-checkout-session', {})
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
