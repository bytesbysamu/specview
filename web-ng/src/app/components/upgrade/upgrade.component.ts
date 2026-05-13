import { Component, OnInit, signal, computed, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { SubscriptionService } from '../../services/subscription.service';

type UpgradeReason = 'limit_reached' | 'payment_lapsed' | 'direct';

@Component({
  selector: 'app-upgrade',
  standalone: true,
  templateUrl: './upgrade.component.html',
  styleUrl: './upgrade.component.scss',
})
export class UpgradeComponent implements OnInit {
  private route = inject(ActivatedRoute);
  protected subscription = inject(SubscriptionService);

  readonly reason = signal<UpgradeReason>('direct');
  readonly feature = signal<string>('');
  readonly sessionId = signal<string | null>(null);

  readonly loading = signal(false);
  readonly verified = signal(false);
  readonly error = signal<string | null>(null);

  readonly plan = computed(() => this.subscription.plan());
  readonly isPro = computed(() => this.subscription.isPro());

  readonly headingText = computed(() => {
    if (this.verified()) return 'Welcome to Pro';
    if (this.isPro()) return 'You are on Pro';
    if (this.reason() === 'payment_lapsed') return 'Update Your Payment Method';
    if (this.reason() === 'limit_reached') return 'Usage Limit Reached';
    return 'Upgrade to Pro';
  });

  async ngOnInit(): Promise<void> {
    const params = this.route.snapshot.queryParamMap;
    const reason = params.get('reason') as UpgradeReason | null;
    const feature = params.get('feature') ?? '';
    const sessionId = params.get('session_id');

    this.reason.set(reason ?? 'direct');
    this.feature.set(feature);
    this.sessionId.set(sessionId);

    if (sessionId) {
      await this.handleVerifySession(sessionId);
    }
  }

  private async handleVerifySession(sessionId: string): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.subscription.verifySession(sessionId);
      this.verified.set(true);
    } catch {
      this.error.set('Could not confirm your subscription. Please refresh or contact support.');
    } finally {
      this.loading.set(false);
    }
  }

  async upgrade(): Promise<void> {
    this.loading.set(true);
    this.error.set(null);
    try {
      await this.subscription.startCheckout();
    } catch {
      this.error.set('Could not start checkout. Please try again.');
      this.loading.set(false);
    }
  }
}
