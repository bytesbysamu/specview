import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
import { TokenLifecycleService } from './token-lifecycle.service';
import { createTokenLifecycleServiceMock } from './token-lifecycle.service.mock';

// ---------------------------------------------------------------------------
// AuthService — passwordless magic-link flow
// ---------------------------------------------------------------------------

describe('AuthService', () => {
  let service: AuthService;
  let lifecycleMock: jasmine.SpyObj<TokenLifecycleService>;
  let httpController: HttpTestingController;

  beforeEach(() => {
    lifecycleMock = createTokenLifecycleServiceMock();

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [
        { provide: TokenLifecycleService, useValue: lifecycleMock },
      ],
    });

    service = TestBed.inject(AuthService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpController.verify();
  });

  // -------------------------------------------------------------------------
  // isLoggedIn — delegates to lifecycle signal
  // -------------------------------------------------------------------------

  describe('isLoggedIn', () => {
    it('returns false when lifecycle signal is false', () => {
      (lifecycleMock as any).isLoggedIn.set(false);
      expect(service.isLoggedIn()).toBeFalse();
    });

    it('returns true when lifecycle signal is true', () => {
      (lifecycleMock as any).isLoggedIn.set(true);
      expect(service.isLoggedIn()).toBeTrue();
    });
  });

  // -------------------------------------------------------------------------
  // requestMagicLink
  // -------------------------------------------------------------------------

  describe('requestMagicLink', () => {
    it('POSTs to /api/auth/magic-link with the email', async () => {
      const promise = service.requestMagicLink('user@example.com');

      const req = httpController.expectOne('/api/auth/magic-link');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'user@example.com' });
      req.flush({ sent: true });

      await promise;
    });

    it('does not store a token (none is returned yet)', async () => {
      const promise = service.requestMagicLink('user@example.com');
      httpController.expectOne('/api/auth/magic-link').flush({ sent: true });
      await promise;
      expect(lifecycleMock.storeToken).not.toHaveBeenCalled();
    });

    it('propagates HTTP errors to the caller', async () => {
      const promise = service.requestMagicLink('user@example.com');
      httpController
        .expectOne('/api/auth/magic-link')
        .flush({ error: 'rate limited' }, { status: 429, statusText: 'Too Many Requests' });
      await expectAsync(promise).toBeRejected();
    });
  });

  // -------------------------------------------------------------------------
  // verifyToken
  // -------------------------------------------------------------------------

  describe('verifyToken', () => {
    it('POSTs to /api/auth/verify with the token', async () => {
      const promise = service.verifyToken('magic-token-123');

      const req = httpController.expectOne('/api/auth/verify');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ token: 'magic-token-123' });
      req.flush({ token: 'returned.jwt', email: 'user@example.com' });

      await promise;
    });

    it('stores the JWT and returns the email on success', async () => {
      const promise = service.verifyToken('magic-token-123');
      httpController
        .expectOne('/api/auth/verify')
        .flush({ token: 'returned.jwt', email: 'user@example.com' });

      const email = await promise;

      expect(lifecycleMock.storeToken).toHaveBeenCalledWith('returned.jwt');
      expect(email).toBe('user@example.com');
    });

    it('propagates errors and does not store a token on an invalid token', async () => {
      const promise = service.verifyToken('bad-token');
      httpController
        .expectOne('/api/auth/verify')
        .flush({ error: 'invalid token' }, { status: 401, statusText: 'Unauthorized' });

      await expectAsync(promise).toBeRejected();
      expect(lifecycleMock.storeToken).not.toHaveBeenCalled();
    });
  });

  // -------------------------------------------------------------------------
  // signOut
  // -------------------------------------------------------------------------

  describe('signOut', () => {
    it('delegates to lifecycle.handleAuthFailure', () => {
      service.signOut();
      expect(lifecycleMock.handleAuthFailure).toHaveBeenCalledTimes(1);
    });
  });

  // -------------------------------------------------------------------------
  // getStoredJwt
  // -------------------------------------------------------------------------

  describe('getStoredJwt', () => {
    it('returns null when lifecycle.getRawToken returns null', () => {
      lifecycleMock.getRawToken.and.returnValue(null);
      expect(service.getStoredJwt()).toBeNull();
    });

    it('returns the token when lifecycle.getRawToken returns a string', () => {
      lifecycleMock.getRawToken.and.returnValue('stored.jwt');
      expect(service.getStoredJwt()).toBe('stored.jwt');
    });
  });
});
