import { Component, computed, inject } from '@angular/core';
import { usageRemaining } from '../../state/usage.state';
import { SubscriptionService } from '../../services/subscription.service';

@Component({
  selector: 'app-usage-meter',
  standalone: true,
  templateUrl: './usage-meter.component.html',
  styleUrl: './usage-meter.component.scss',
})
export class UsageMeterComponent {
  private subscription = inject(SubscriptionService);

  protected readonly usage = usageRemaining;
  protected readonly isPro = computed(() => this.subscription.isPro());
  protected readonly isWarning = computed(() => {
    const u = this.usage();
    return u !== null && u.remaining <= 1;
  });
  protected readonly isVisible = computed(() => {
    return !this.isPro() && this.usage() !== null;
  });
}
