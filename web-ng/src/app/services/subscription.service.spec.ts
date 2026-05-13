import { TestBed } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';

import { SubscriptionService, Plan } from './subscription.service';

describe('SubscriptionService', () => {
  let service: SubscriptionService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        SubscriptionService,
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });

    // Flush the constructor refresh() call before each test
    httpMock = TestBed.inject(HttpTestingController);
    service = TestBed.inject(SubscriptionService);
    const initReq = httpMock.expectOne('/api/billing/status');
    initReq.flush({ plan: 'free' });
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should have initial plan state of "free"', () => {
    expect(service.plan()).toBe('free');
  });

  describe('isPro', () => {
    it('returns false when plan is "free"', () => {
      service.plan.set('free');
      expect(service.isPro()).toBeFalse();
    });

    it('returns false when plan is "lapsed"', () => {
      service.plan.set('lapsed');
      expect(service.isPro()).toBeFalse();
    });

    it('returns true when plan is "pro"', () => {
      service.plan.set('pro');
      expect(service.isPro()).toBeTrue();
    });
  });

  describe('refresh()', () => {
    it('updates plan signal from API response', async () => {
      const refreshPromise = service.refresh();
      const req = httpMock.expectOne('/api/billing/status');
      expect(req.request.method).toBe('GET');
      req.flush({ plan: 'pro' } satisfies { plan: Plan });
      await refreshPromise;
      expect(service.plan()).toBe('pro');
    });

    it('sets plan to "lapsed" when API returns lapsed', async () => {
      const refreshPromise = service.refresh();
      const req = httpMock.expectOne('/api/billing/status');
      req.flush({ plan: 'lapsed' } satisfies { plan: Plan });
      await refreshPromise;
      expect(service.plan()).toBe('lapsed');
    });
  });

  describe('verifySession()', () => {
    it('updates plan state on success', async () => {
      const verifyPromise = service.verifySession('cs_test_abc123');
      const req = httpMock.expectOne(r =>
        r.url === '/api/billing/verify-session' &&
        r.params.get('session_id') === 'cs_test_abc123'
      );
      expect(req.request.method).toBe('GET');
      req.flush({ plan: 'pro' } satisfies { plan: Plan });
      await verifyPromise;
      expect(service.plan()).toBe('pro');
    });

    it('keeps plan at current value if verify returns free', async () => {
      service.plan.set('pro');
      const verifyPromise = service.verifySession('cs_test_xyz');
      const req = httpMock.expectOne(r =>
        r.url === '/api/billing/verify-session' &&
        r.params.get('session_id') === 'cs_test_xyz'
      );
      req.flush({ plan: 'free' } satisfies { plan: Plan });
      await verifyPromise;
      expect(service.plan()).toBe('free');
    });
  });

  describe('startCheckout()', () => {
    it('calls POST /api/billing/create-checkout-session', async () => {
      // Intercept window.location.href assignment
      const originalDescriptor = Object.getOwnPropertyDescriptor(window, 'location');
      const locationMock = { href: '' };
      Object.defineProperty(window, 'location', {
        value: locationMock,
        writable: true,
        configurable: true,
      });

      const checkoutPromise = service.startCheckout();
      const req = httpMock.expectOne('/api/billing/create-checkout-session');
      expect(req.request.method).toBe('POST');
      req.flush({ url: 'https://checkout.stripe.com/pay/test_123' });
      await checkoutPromise;

      expect(locationMock.href).toBe('https://checkout.stripe.com/pay/test_123');

      // Restore window.location
      if (originalDescriptor) {
        Object.defineProperty(window, 'location', originalDescriptor);
      }
    });
  });
});
