import { signal, computed } from '@angular/core';
import { SubscriptionService, Plan } from './subscription.service';

export function createMockSubscriptionService(): jasmine.SpyObj<SubscriptionService> {
  const mock = jasmine.createSpyObj<SubscriptionService>('SubscriptionService', [
    'refresh',
    'startCheckout',
    'verifySession',
  ]);

  const planSignal = signal<Plan>('free');
  Object.defineProperty(mock, 'plan', { get: () => planSignal, configurable: true });
  Object.defineProperty(mock, 'isPro', { get: () => computed(() => planSignal() === 'pro'), configurable: true });

  mock.refresh.and.returnValue(Promise.resolve());
  mock.startCheckout.and.returnValue(Promise.resolve());
  mock.verifySession.and.returnValue(Promise.resolve());

  return mock;
}
