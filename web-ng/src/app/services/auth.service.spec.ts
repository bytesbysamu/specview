import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
import { TokenLifecycleService } from './token-lifecycle.service';
import { createTokenLifecycleServiceMock } from './token-lifecycle.service.mock';

// ---------------------------------------------------------------------------
// Factory helpers
// ---------------------------------------------------------------------------

function makeAuthResponse(overrides: Partial<{ token: string; email: string }> = {}) {
  return { token: 'test.jwt.token', email: 'user@example.com', ...overrides };
}

// ---------------------------------------------------------------------------
// AuthService
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
  // login
  // -------------------------------------------------------------------------

  describe('login', () => {
    it('POSTs to /api/auth/login with email and password', async () => {
      const promise = service.login('user@example.com', 'secret');

      const req = httpController.expectOne('/api/auth/login');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'user@example.com', password: 'secret' });
      req.flush(makeAuthResponse());

      await promise;
    });

    it('calls storeToken with the token from the response', async () => {
      const promise = service.login('user@example.com', 'secret');

      const req = httpController.expectOne('/api/auth/login');
      req.flush(makeAuthResponse({ token: 'returned.jwt' }));

      await promise;

      expect(lifecycleMock.storeToken).toHaveBeenCalledWith('returned.jwt');
    });

    it('propagates HTTP errors to the caller', async () => {
      const promise = service.login('bad@example.com', 'wrong');

      const req = httpController.expectOne('/api/auth/login');
      req.flush({ error: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' });

      await expectAsync(promise).toBeRejected();
    });
  });

  // -------------------------------------------------------------------------
  // register
  // -------------------------------------------------------------------------

  describe('register', () => {
    it('POSTs to /api/auth/register with email and password', async () => {
      const promise = service.register('new@example.com', 'pass123');

      const req = httpController.expectOne('/api/auth/register');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ email: 'new@example.com', password: 'pass123' });
      req.flush(makeAuthResponse({ email: 'new@example.com' }));

      await promise;
    });

    it('calls storeToken with the token from the registration response', async () => {
      const promise = service.register('new@example.com', 'pass123');

      const req = httpController.expectOne('/api/auth/register');
      req.flush(makeAuthResponse({ token: 'reg.jwt' }));

      await promise;

      expect(lifecycleMock.storeToken).toHaveBeenCalledWith('reg.jwt');
    });

    it('propagates HTTP errors to the caller', async () => {
      const promise = service.register('existing@example.com', 'pass');

      const req = httpController.expectOne('/api/auth/register');
      req.flush({ error: 'Email already registered' }, { status: 409, statusText: 'Conflict' });

      await expectAsync(promise).toBeRejected();
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
