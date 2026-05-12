import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { Router } from '@angular/router';

import { TokenLifecycleService } from './token-lifecycle.service';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a syntactically valid JWT string with the given payload.
 * Signature is intentionally fake — the service only decodes, never verifies.
 */
function makeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `${header}.${body}.fake-signature`;
}

const TOKEN_KEY = 'specview_jwt';
const NOW_SECONDS = Math.floor(Date.now() / 1000);
const REFRESH_WINDOW = 3600; // seconds — mirrors service constant

// ---------------------------------------------------------------------------
// Existing tests (preserved)
// ---------------------------------------------------------------------------

describe('TokenLifecycleService', () => {
  let service: TokenLifecycleService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
    service = TestBed.inject(TokenLifecycleService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('creates successfully', () => {
    expect(service).toBeTruthy();
  });

  it('isLoggedIn is false when localStorage has no token', () => {
    expect(service.isLoggedIn()).toBeFalse();
  });

  it('storeToken sets isLoggedIn to true', () => {
    service.storeToken('fake.jwt.token');
    expect(service.isLoggedIn()).toBeTrue();
  });

  it('getRawToken returns null when no token stored', () => {
    expect(service.getRawToken()).toBeNull();
  });

  it('getRawToken returns stored token after storeToken', () => {
    service.storeToken('fake.jwt.token');
    expect(service.getRawToken()).toBe('fake.jwt.token');
  });
});

// ---------------------------------------------------------------------------
// _decodeExp — private, tested indirectly via getToken branches
// ---------------------------------------------------------------------------

describe('TokenLifecycleService — _decodeExp (via getToken)', () => {
  let service: TokenLifecycleService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
    service = TestBed.inject(TokenLifecycleService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('getToken returns the raw token when it has no exp claim (non-expiring token)', async () => {
    const token = makeJwt({ sub: 'user@example.com' }); // no exp field
    localStorage.setItem(TOKEN_KEY, token);

    const result = await service.getToken();

    expect(result).toBe(token);
  });

  it('getToken returns null when no token in localStorage', async () => {
    const result = await service.getToken();
    expect(result).toBeNull();
  });

  it('getToken returns the raw token when exp is malformed (not a number)', async () => {
    const token = makeJwt({ exp: 'not-a-number' });
    localStorage.setItem(TOKEN_KEY, token);

    const result = await service.getToken();

    expect(result).toBe(token);
  });

  it('getToken returns the raw token when JWT has wrong segment count (not 3 parts)', async () => {
    const malformed = 'only.two';
    localStorage.setItem(TOKEN_KEY, malformed);

    const result = await service.getToken();

    // _decodeExp returns null for malformed JWT → token returned as-is
    expect(result).toBe(malformed);
  });

  it('getToken returns the raw token when JWT payload is not valid JSON', async () => {
    const badPayload = btoa('not-json');
    const token = `header.${badPayload}.sig`;
    localStorage.setItem(TOKEN_KEY, token);

    const result = await service.getToken();

    expect(result).toBe(token);
  });
});

// ---------------------------------------------------------------------------
// getToken — branch: fresh token (expiry > REFRESH_WINDOW_SECONDS from now)
// ---------------------------------------------------------------------------

describe('TokenLifecycleService — getToken fresh path', () => {
  let service: TokenLifecycleService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
    service = TestBed.inject(TokenLifecycleService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('returns the token directly when expiry is well beyond the refresh window', async () => {
    const freshToken = makeJwt({ exp: NOW_SECONDS + REFRESH_WINDOW + 3600 }); // 2 hours from now
    localStorage.setItem(TOKEN_KEY, freshToken);

    const result = await service.getToken();

    expect(result).toBe(freshToken);
  });
});

// ---------------------------------------------------------------------------
// getToken — branch: expired token → handleAuthFailure
// ---------------------------------------------------------------------------

describe('TokenLifecycleService — getToken expired path', () => {
  let service: TokenLifecycleService;
  let router: Router;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
    service = TestBed.inject(TokenLifecycleService);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.returnValue(Promise.resolve(true));
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('returns null and calls handleAuthFailure when token is expired', async () => {
    const expiredToken = makeJwt({ exp: NOW_SECONDS - 60 }); // expired 1 minute ago
    localStorage.setItem(TOKEN_KEY, expiredToken);

    const result = await service.getToken();

    expect(result).toBeNull();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(service.isLoggedIn()).toBeFalse();
  });
});

// ---------------------------------------------------------------------------
// getToken — branch: within refresh window → _doRefresh
// ---------------------------------------------------------------------------

describe('TokenLifecycleService — getToken refresh path', () => {
  let service: TokenLifecycleService;
  let httpController: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
    service = TestBed.inject(TokenLifecycleService);
    httpController = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.returnValue(Promise.resolve(true));
  });

  afterEach(() => {
    localStorage.clear();
    httpController.verify();
  });

  it('calls /api/auth/refresh and stores the new token when within refresh window', async () => {
    // Token expires in 30 minutes — inside the 1-hour refresh window
    const nearExpiry = makeJwt({ exp: NOW_SECONDS + 1800 });
    localStorage.setItem(TOKEN_KEY, nearExpiry);
    const newToken = makeJwt({ exp: NOW_SECONDS + REFRESH_WINDOW * 2 });

    const promise = service.getToken();

    const req = httpController.expectOne('/api/auth/refresh');
    expect(req.request.method).toBe('POST');
    req.flush({ token: newToken, email: 'user@example.com' });

    const result = await promise;

    expect(result).toBe(newToken);
    expect(localStorage.getItem(TOKEN_KEY)).toBe(newToken);
    expect(service.isLoggedIn()).toBeTrue();
  });

  it('concurrent getToken calls share one in-flight refresh (mutex)', async () => {
    const nearExpiry = makeJwt({ exp: NOW_SECONDS + 1800 });
    localStorage.setItem(TOKEN_KEY, nearExpiry);
    const newToken = makeJwt({ exp: NOW_SECONDS + REFRESH_WINDOW * 2 });

    const promise1 = service.getToken();
    const promise2 = service.getToken();

    // Only one HTTP call should be made (the mutex prevents a second refresh)
    const req = httpController.expectOne('/api/auth/refresh');
    req.flush({ token: newToken, email: 'user@example.com' });

    const [r1, r2] = await Promise.all([promise1, promise2]);
    expect(r1).toBe(newToken);
    expect(r2).toBe(newToken);
  });

  it('returns null and calls handleAuthFailure when refresh HTTP call fails', async () => {
    const nearExpiry = makeJwt({ exp: NOW_SECONDS + 1800 });
    localStorage.setItem(TOKEN_KEY, nearExpiry);

    const promise = service.getToken();

    const req = httpController.expectOne('/api/auth/refresh');
    req.flush({ error: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' });

    const result = await promise;

    expect(result).toBeNull();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(service.isLoggedIn()).toBeFalse();
  });
});

// ---------------------------------------------------------------------------
// handleAuthFailure
// ---------------------------------------------------------------------------

describe('TokenLifecycleService — handleAuthFailure', () => {
  let service: TokenLifecycleService;
  let router: Router;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule, RouterTestingModule],
    });
    service = TestBed.inject(TokenLifecycleService);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.returnValue(Promise.resolve(true));
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('removes token from localStorage', async () => {
    service.storeToken('some.jwt');
    await service.handleAuthFailure();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it('sets isLoggedIn to false', async () => {
    service.storeToken('some.jwt');
    await service.handleAuthFailure();
    expect(service.isLoggedIn()).toBeFalse();
  });

  it('navigates to /login', async () => {
    await service.handleAuthFailure();
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });
});
