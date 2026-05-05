# Task 4: Angular Auth Service + Interceptor + Login Flow

## 1. Context

Task 4 ships the client side of the magic-link flow. Five Angular files: `auth.service.ts` (signals + localStorage), `auth.interceptor.ts` (Bearer injection + 401 redirect), `login.component.ts` (email input + request button), `auth-callback.component.ts` (token exchange + redirect to `/projects`), and `auth.guard.ts` (canActivate that requires a session). Wire the interceptor in `app.config.ts`, add the new routes to the router, mount the guard on every protected route, and add `neonAuthProjectId` + `neonAuthAppOrigin` to `web/src/environments/environment.ts`.

Spec-doc's Angular app already calls `/api/projects`, `/api/context/*`, `/api/templates`, `/api/ai/text/*` from existing services. Once the interceptor lands, every call gains the `Authorization: Bearer <jwt>` header automatically — no per-service changes needed. The 401 branch in the interceptor catches the case where the JWT is expired or invalid; the user is signed out and routed to `/login`.

The login page is the simplest possible UX: one email input, one button, success/error states. Branded email templates and deep-link redirects after verify are out of scope for v1.

**Trade-offs considered:**
- **In-memory signal vs `localStorage` for the JWT** — `localStorage` chosen; survives reloads; matches Neon Auth SDK convention; interceptor stateless.
- **Single `/login` page vs hosted Neon Auth UI** — own page chosen; one extra route is cheaper than embedding a hosted iframe and styling it; we control the UX.
- **Guard on every protected route vs route-tree-level guard** — every-route chosen; explicit; avoids accidentally unprotecting a new route added to a parent.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
git status
cd {WORKSPACE}/web && npm test -- --watch=false 2>&1 | tail -10
```

Record the passing test count from the test output as **N**.

Confirm Task 2 endpoints are deployed (or stubbed) at `/api/auth/login`, `/api/auth/verify`, `/api/auth/me`. Without them, every Angular HTTP call returns 404 and the manual smoke test fails.

---

## 3. Files

### To Create (new)
- `{WORKSPACE}/web/src/app/services/auth.service.ts` (new) — `AuthService` with signals + localStorage
- `{WORKSPACE}/web/src/app/services/auth.service.spec.ts` (new) — 5 unit tests
- `{WORKSPACE}/web/src/app/interceptors/auth.interceptor.ts` (new) — `authInterceptor` function (Angular 17 functional interceptor)
- `{WORKSPACE}/web/src/app/interceptors/auth.interceptor.spec.ts` (new) — 4 unit tests
- `{WORKSPACE}/web/src/app/guards/auth.guard.ts` (new) — `authGuard` (functional CanActivateFn)
- `{WORKSPACE}/web/src/app/guards/auth.guard.spec.ts` (new) — 2 unit tests
- `{WORKSPACE}/web/src/app/components/login/login.component.ts` (new) — standalone component
- `{WORKSPACE}/web/src/app/components/login/login.component.spec.ts` (new) — 2 unit tests
- `{WORKSPACE}/web/src/app/components/auth-callback/auth-callback.component.ts` (new) — standalone component
- `{WORKSPACE}/web/src/app/components/auth-callback/auth-callback.component.spec.ts` (new) — 2 unit tests

### To Modify
- `{WORKSPACE}/web/src/app/app.config.ts` — register `authInterceptor` via `provideHttpClient(withInterceptors([authInterceptor]))`
- `{WORKSPACE}/web/src/app/app.routes.ts` (or wherever the router is configured) — add `/login`, `/auth/callback` routes; mount `authGuard` on every protected route
- `{WORKSPACE}/web/src/environments/environment.ts` — add `neonAuthProjectId: ''` and `neonAuthAppOrigin: 'https://auth.neon.tech'`
- `{WORKSPACE}/web/src/environments/environment.development.ts` (if present) — same additions for dev

### To Leave Alone
- Existing services (`projects.service.ts`, `ai.service.ts`, `context.service.ts`) — the interceptor handles header injection transparently; no per-service changes
- Existing components — the interceptor and guard are cross-cutting; components that consume protected routes need no edits

---

## 4. Implementation Steps

### Step 1: Add the Neon Auth env vars to `environment.ts`

**Action**: Append two properties. Dev defaults are empty strings — they get populated by the developer's local `.env` mirror or via `ng serve --configuration=...` overrides.

**File**: `{WORKSPACE}/web/src/environments/environment.ts` (modify)

Append to the exported object:

```typescript
export const environment = {
  // ... existing fields ...
  neonAuthProjectId: '',
  neonAuthAppOrigin: 'https://auth.neon.tech',
};
```

**File**: `{WORKSPACE}/web/src/environments/environment.development.ts` (modify if present)

Append the same two properties.

**Verify**:
```bash
cd {WORKSPACE}/web && npx tsc --noEmit
```
Expect zero TypeScript errors.

---

### Step 2: Write `AuthService`

**Action**: Create the service with `currentUser` signal, `requestMagicLink`, `verifyToken`, `signOut`, `getStoredJwt` methods.

**File**: `{WORKSPACE}/web/src/app/services/auth.service.ts` (new)

```typescript
import { HttpClient } from '@angular/common/http';
import { Injectable, WritableSignal, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

export interface AuthUser {
  id: number;
  email: string;
  auth_user_id: string;
}

interface VerifyResponse {
  jwt: string;
  user: AuthUser;
}

const STORAGE_KEY = 'spec_doc_jwt';
const USER_KEY = 'spec_doc_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);

  readonly currentUser: WritableSignal<AuthUser | null> = signal(this.loadUserFromStorage());
  readonly isAuthenticated = computed(() => this.currentUser() !== null);

  requestMagicLink(email: string): Observable<{ request_id: string }> {
    return this.http.post<{ request_id: string }>('/api/auth/login', { email });
  }

  verifyToken(token: string): Observable<VerifyResponse> {
    return this.http.post<VerifyResponse>('/api/auth/verify', { token }).pipe(
      tap((response) => {
        localStorage.setItem(STORAGE_KEY, response.jwt);
        localStorage.setItem(USER_KEY, JSON.stringify(response.user));
        this.currentUser.set(response.user);
      })
    );
  }

  signOut(): void {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(USER_KEY);
    this.currentUser.set(null);
    this.router.navigate(['/login']);
  }

  getStoredJwt(): string | null {
    return localStorage.getItem(STORAGE_KEY);
  }

  private loadUserFromStorage(): AuthUser | null {
    const raw = localStorage.getItem(USER_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as AuthUser;
    } catch {
      localStorage.removeItem(USER_KEY);
      return null;
    }
  }
}
```

**Verify**:
```bash
cd {WORKSPACE}/web && npx tsc --noEmit
```
Expect zero TypeScript errors.

---

### Step 3: Write the auth interceptor

**Action**: Functional interceptor (Angular 17 style). Adds `Authorization: Bearer <jwt>` to every outbound `/api/*` request when a session exists. On HTTP 401 from any `/api/*` route except `/api/auth/login` and `/api/auth/verify`, calls `signOut()` (which redirects).

**File**: `{WORKSPACE}/web/src/app/interceptors/auth.interceptor.ts` (new)

```typescript
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';

const PUBLIC_AUTH_PATHS = ['/api/auth/login', '/api/auth/verify', '/api/auth/logout'];

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const jwt = auth.getStoredJwt();

  let authedReq = req;
  if (jwt && req.url.startsWith('/api/')) {
    authedReq = req.clone({
      setHeaders: { Authorization: `Bearer ${jwt}` },
    });
  }

  return next(authedReq).pipe(
    catchError((err: unknown) => {
      if (
        err instanceof HttpErrorResponse &&
        err.status === 401 &&
        !PUBLIC_AUTH_PATHS.some((p) => req.url.startsWith(p))
      ) {
        auth.signOut();
      }
      return throwError(() => err);
    })
  );
};
```

**Verify**:
```bash
cd {WORKSPACE}/web && npx tsc --noEmit
```
Expect zero TypeScript errors.

---

### Step 4: Write the auth guard

**Action**: Functional `CanActivateFn`. If `authService.isAuthenticated()` is true, allow; otherwise redirect to `/login` and deny.

**File**: `{WORKSPACE}/web/src/app/guards/auth.guard.ts` (new)

```typescript
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isAuthenticated()) {
    return true;
  }
  router.navigate(['/login']);
  return false;
};
```

**Verify**:
```bash
cd {WORKSPACE}/web && npx tsc --noEmit
```
Expect zero TypeScript errors.

---

### Step 5: Write `LoginComponent` and `AuthCallbackComponent`

**Action**: Two standalone components.

**File**: `{WORKSPACE}/web/src/app/components/login/login.component.ts` (new)

```typescript
import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="login">
      <h1>Sign in</h1>
      <form (submit)="onSubmit($event)">
        <label>
          Email
          <input
            type="email"
            name="email"
            [(ngModel)]="email"
            required
            data-test="login-email"
          />
        </label>
        <button type="submit" [disabled]="state() === 'sending'" data-test="login-submit">
          {{ state() === 'sending' ? 'Sending…' : 'Send magic link' }}
        </button>
      </form>
      <p *ngIf="state() === 'sent'" data-test="login-success">
        Check your email for a sign-in link.
      </p>
      <p *ngIf="state() === 'error'" data-test="login-error">
        Couldn't send the link. Try again.
      </p>
    </section>
  `,
})
export class LoginComponent {
  private auth = inject(AuthService);
  email = '';
  state = signal<'idle' | 'sending' | 'sent' | 'error'>('idle');

  onSubmit(event: Event): void {
    event.preventDefault();
    if (!this.email) {
      return;
    }
    this.state.set('sending');
    this.auth.requestMagicLink(this.email).subscribe({
      next: () => this.state.set('sent'),
      error: () => this.state.set('error'),
    });
  }
}
```

**File**: `{WORKSPACE}/web/src/app/components/auth-callback/auth-callback.component.ts` (new)

```typescript
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="auth-callback">
      <p *ngIf="state() === 'verifying'" data-test="callback-verifying">Signing you in…</p>
      <p *ngIf="state() === 'error'" data-test="callback-error">
        Sign-in failed. <a routerLink="/login">Try again</a>.
      </p>
    </section>
  `,
})
export class AuthCallbackComponent implements OnInit {
  private auth = inject(AuthService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  state = signal<'verifying' | 'error'>('verifying');

  ngOnInit(): void {
    const token =
      this.route.snapshot.queryParamMap.get('token') ??
      new URLSearchParams(window.location.hash.slice(1)).get('token');
    if (!token) {
      this.state.set('error');
      return;
    }
    this.auth.verifyToken(token).subscribe({
      next: () => this.router.navigate(['/projects']),
      error: () => this.state.set('error'),
    });
  }
}
```

**Verify**:
```bash
cd {WORKSPACE}/web && npx tsc --noEmit
```
Expect zero TypeScript errors.

---

### Step 6: Wire the interceptor and routes

**Action**: Register the interceptor in `app.config.ts`. Add `/login` and `/auth/callback` routes; mount `authGuard` on every existing protected route.

**File**: `{WORKSPACE}/web/src/app/app.config.ts` (modify)

In the `providers` array, replace any existing `provideHttpClient(...)` with:

```typescript
provideHttpClient(withInterceptors([authInterceptor]))
```

Add the import at the top:

```typescript
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { authInterceptor } from './interceptors/auth.interceptor';
```

**File**: `{WORKSPACE}/web/src/app/app.routes.ts` (modify; or wherever routes are declared)

Add to the `routes` array:

```typescript
import { authGuard } from './guards/auth.guard';
import { LoginComponent } from './components/login/login.component';
import { AuthCallbackComponent } from './components/auth-callback/auth-callback.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'auth/callback', component: AuthCallbackComponent },
  // existing routes — add canActivate: [authGuard] to each
  { path: 'projects', loadComponent: () => import('./...').then(m => m.ProjectsComponent), canActivate: [authGuard] },
  // ... apply canActivate: [authGuard] to every other existing route
  { path: '', pathMatch: 'full', redirectTo: 'projects' },
];
```

**Verify**:
```bash
cd {WORKSPACE}/web && npx tsc --noEmit
cd {WORKSPACE}/web && npm run build 2>&1 | tail -5
```
Expect a successful build.

---

### Step 7: Write the unit tests

**Action**: Five tests for `AuthService`, four for the interceptor, two for the guard, two each for the two components.

**File**: `{WORKSPACE}/web/src/app/services/auth.service.spec.ts` (new)

```typescript
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

import { AuthService, AuthUser } from './auth.service';

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    localStorage.clear();
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
      ],
    });
    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('requestMagicLink_postsEmailToLoginEndpoint', () => {
    service.requestMagicLink('a@b.co').subscribe();
    const req = httpMock.expectOne('/api/auth/login');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ email: 'a@b.co' });
    req.flush({ request_id: 'req-1' });
  });

  it('verifyToken_persistsJwtAndUserToLocalStorage', () => {
    const user: AuthUser = { id: 1, email: 'a@b.co', auth_user_id: 'u-1' };
    service.verifyToken('one-time').subscribe();
    httpMock.expectOne('/api/auth/verify').flush({ jwt: 'jwt-abc', user });
    expect(localStorage.getItem('spec_doc_jwt')).toBe('jwt-abc');
    expect(JSON.parse(localStorage.getItem('spec_doc_user')!)).toEqual(user);
    expect(service.currentUser()).toEqual(user);
  });

  it('signOut_clearsStorageAndNavigatesToLogin', () => {
    localStorage.setItem('spec_doc_jwt', 'x');
    localStorage.setItem('spec_doc_user', JSON.stringify({ id: 1, email: 'a@b.co', auth_user_id: 'u-1' }));
    service.currentUser.set({ id: 1, email: 'a@b.co', auth_user_id: 'u-1' });
    service.signOut();
    expect(localStorage.getItem('spec_doc_jwt')).toBeNull();
    expect(localStorage.getItem('spec_doc_user')).toBeNull();
    expect(service.currentUser()).toBeNull();
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });

  it('isAuthenticated_isFalseWhenNoUser', () => {
    expect(service.isAuthenticated()).toBe(false);
  });

  it('isAuthenticated_isTrueAfterVerify', () => {
    service.currentUser.set({ id: 1, email: 'a@b.co', auth_user_id: 'u-1' });
    expect(service.isAuthenticated()).toBe(true);
  });
});
```

**File**: `{WORKSPACE}/web/src/app/interceptors/auth.interceptor.spec.ts` (new)

```typescript
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AuthService } from '../services/auth.service';
import { authInterceptor } from './auth.interceptor';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let auth: jasmine.SpyObj<AuthService>;

  beforeEach(() => {
    auth = jasmine.createSpyObj<AuthService>('AuthService', ['getStoredJwt', 'signOut']);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('addsBearerHeaderToApiRequestsWhenJwtPresent', () => {
    auth.getStoredJwt.and.returnValue('jwt-abc');
    http.get('/api/projects').subscribe();
    const req = httpMock.expectOne('/api/projects');
    expect(req.request.headers.get('Authorization')).toBe('Bearer jwt-abc');
    req.flush([]);
  });

  it('omitsBearerHeaderWhenNoJwt', () => {
    auth.getStoredJwt.and.returnValue(null);
    http.get('/api/projects').subscribe();
    const req = httpMock.expectOne('/api/projects');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush([]);
  });

  it('triggersSignOutOn401FromProtectedRoute', () => {
    auth.getStoredJwt.and.returnValue('expired-jwt');
    http.get('/api/projects').subscribe({ next: () => {}, error: () => {} });
    const req = httpMock.expectOne('/api/projects');
    req.flush({ error: 'expired' }, { status: 401, statusText: 'Unauthorized' });
    expect(auth.signOut).toHaveBeenCalled();
  });

  it('doesNotSignOutOn401FromAuthVerify', () => {
    auth.getStoredJwt.and.returnValue(null);
    http.post('/api/auth/verify', { token: 'bad' }).subscribe({ next: () => {}, error: () => {} });
    const req = httpMock.expectOne('/api/auth/verify');
    req.flush({ error: 'bad' }, { status: 400, statusText: 'Bad Request' });
    expect(auth.signOut).not.toHaveBeenCalled();
  });
});
```

**File**: `{WORKSPACE}/web/src/app/guards/auth.guard.spec.ts` (new)

```typescript
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { AuthService } from '../services/auth.service';
import { authGuard } from './auth.guard';

describe('authGuard', () => {
  let auth: jasmine.SpyObj<AuthService>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    auth = jasmine.createSpyObj<AuthService>('AuthService', [], { isAuthenticated: () => false });
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: Router, useValue: router },
      ],
    });
  });

  it('allowsActivationWhenAuthenticated', () => {
    (auth as any).isAuthenticated = () => true;
    const result = TestBed.runInInjectionContext(() => authGuard({} as any, {} as any));
    expect(result).toBe(true);
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('redirectsToLoginWhenNotAuthenticated', () => {
    (auth as any).isAuthenticated = () => false;
    const result = TestBed.runInInjectionContext(() => authGuard({} as any, {} as any));
    expect(result).toBe(false);
    expect(router.navigate).toHaveBeenCalledWith(['/login']);
  });
});
```

**File**: `{WORKSPACE}/web/src/app/components/login/login.component.spec.ts` (new)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { By } from '@angular/platform-browser';

import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    fixture = TestBed.createComponent(LoginComponent);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('postsEmailAndShowsSuccessMessage', () => {
    fixture.componentInstance.email = 'a@b.co';
    fixture.detectChanges();
    fixture.debugElement
      .query(By.css('[data-test="login-submit"]'))
      .nativeElement.click();
    httpMock.expectOne('/api/auth/login').flush({ request_id: 'req-1' });
    fixture.detectChanges();
    expect(
      fixture.debugElement.query(By.css('[data-test="login-success"]'))?.nativeElement.textContent
    ).toContain('Check your email');
  });

  it('showsErrorWhenNeonAuthRejects', () => {
    fixture.componentInstance.email = 'a@b.co';
    fixture.detectChanges();
    fixture.debugElement
      .query(By.css('[data-test="login-submit"]'))
      .nativeElement.click();
    httpMock
      .expectOne('/api/auth/login')
      .flush({ error: 'rate limited' }, { status: 502, statusText: 'Bad Gateway' });
    fixture.detectChanges();
    expect(
      fixture.debugElement.query(By.css('[data-test="login-error"]'))?.nativeElement.textContent
    ).toContain("Couldn't send the link");
  });
});
```

**File**: `{WORKSPACE}/web/src/app/components/auth-callback/auth-callback.component.spec.ts` (new)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { By } from '@angular/platform-browser';

import { AuthCallbackComponent } from './auth-callback.component';

describe('AuthCallbackComponent', () => {
  let fixture: ComponentFixture<AuthCallbackComponent>;
  let httpMock: HttpTestingController;
  let router: jasmine.SpyObj<Router>;

  function configure(token: string | null) {
    router = jasmine.createSpyObj<Router>('Router', ['navigate']);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [AuthCallbackComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              queryParamMap: convertToParamMap(token ? { token } : {}),
            },
          },
        },
      ],
    });
    fixture = TestBed.createComponent(AuthCallbackComponent);
    httpMock = TestBed.inject(HttpTestingController);
  }

  afterEach(() => httpMock.verify());

  it('verifiesTokenAndRedirectsToProjects', () => {
    configure('one-time');
    fixture.detectChanges();
    httpMock
      .expectOne('/api/auth/verify')
      .flush({ jwt: 'jwt-abc', user: { id: 1, email: 'a@b.co', auth_user_id: 'u-1' } });
    expect(router.navigate).toHaveBeenCalledWith(['/projects']);
  });

  it('showsErrorWhenTokenAbsent', () => {
    configure(null);
    fixture.detectChanges();
    expect(
      fixture.debugElement.query(By.css('[data-test="callback-error"]'))?.nativeElement.textContent
    ).toContain('Sign-in failed');
  });
});
```

**Verify**:
```bash
cd {WORKSPACE}/web && npm test -- --watch=false 2>&1 | tail -10
```
Expect 15 new tests passing (5 service + 4 interceptor + 2 guard + 2 login + 2 callback). Zero pre-existing tests broken.

---

## 5. Tests

15 new tests across the five spec files. Every assertion checks a concrete value or call:

- `AuthService` (5): magic-link POST shape, verify persists JWT, signOut clears, isAuthenticated false-default, true-after-verify
- `authInterceptor` (4): adds Bearer when JWT, omits Bearer when none, signOut on 401 from protected route, no signOut on 401 from `/api/auth/verify`
- `authGuard` (2): allow when authenticated, redirect when not
- `LoginComponent` (2): success branch, error branch
- `AuthCallbackComponent` (2): verify-and-redirect, missing-token error

No `expect(true).toBe(true)`; no empty test bodies.

---

## 6. Commit Plan

**Commit 1** — `feat(env): add neonAuthProjectId and neonAuthAppOrigin to Angular environment`
- Files: `web/src/environments/environment.ts`, `web/src/environments/environment.development.ts`
- What: two new properties

**Commit 2** — `feat(auth): add AuthService with signals + localStorage session`
- Files: `web/src/app/services/auth.service.ts`, `web/src/app/services/auth.service.spec.ts`
- What: service + 5 unit tests

**Commit 3** — `feat(auth): add authInterceptor for Bearer injection and 401 redirect`
- Files: `web/src/app/interceptors/auth.interceptor.ts`, `web/src/app/interceptors/auth.interceptor.spec.ts`, `web/src/app/app.config.ts`
- What: interceptor + 4 unit tests + app.config wiring

**Commit 4** — `feat(auth): add authGuard for protected routes`
- Files: `web/src/app/guards/auth.guard.ts`, `web/src/app/guards/auth.guard.spec.ts`
- What: guard + 2 unit tests

**Commit 5** — `feat(auth): add LoginComponent and AuthCallbackComponent`
- Files: `web/src/app/components/login/*`, `web/src/app/components/auth-callback/*`
- What: two standalone components + 4 unit tests

**Commit 6** — `feat(routes): mount login/callback routes and authGuard on protected routes`
- Files: `web/src/app/app.routes.ts`
- What: route additions + canActivate

**Co-Authored-By trailer** (verbatim, every commit):
```
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

**Deviation logging**: if any step deviates, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
cd {WORKSPACE}/web && npx tsc --noEmit
cd {WORKSPACE}/web && npm run build 2>&1 | tail -5
cd {WORKSPACE}/web && npm test -- --watch=false 2>&1 | tail -10
```

**Expected delta**: N → N+15 passing (5 service + 4 interceptor + 2 guard + 4 component tests). Zero pre-existing tests broken. Build succeeds. tsc reports zero errors.

Manual smoke (against the running backend from Tasks 1-3):
- Open `http://localhost:4201/login`, enter email, click Send. Expect 202 from `/api/auth/login` and the success message.
- Click the magic link in the email. Expect a redirect to `http://localhost:4201/auth/callback?token=...` followed by a redirect to `/projects` and a hydrated `currentUser`.
- Open devtools → Application → Local Storage. Expect `spec_doc_jwt` and `spec_doc_user` keys populated.
- Click an existing protected action (e.g. open a project). Expect the request to carry `Authorization: Bearer <jwt>` (visible in Network tab).

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>` in reverse order (commit 6 → 5 → 4 → 3 → 2 → 1).
- **Per-branch**: if verification fails, `git reset --hard <pre-task-sha>`. Removing the interceptor from `app.config.ts` instantly restores unauthenticated behaviour for testing.

---

## 9. Deviations Allowed

- **`environment.ts` already has the two properties** — skip Step 1; log in commit 1 body (no diff).
- **`provideHttpClient(withInterceptors([...]))` already wraps a different interceptor** — append `authInterceptor` to the existing array; log in commit 3 body.
- **App routes are not in `app.routes.ts`** — find the file that exports `Routes`; apply Step 6 there; log in commit 6 body.
- **A protected route uses `loadChildren` for a route module** — apply `canActivate: [authGuard]` at the parent route level; log in commit 6 body.
- **Side-effect required** (network call to a real Neon Auth project, schema change) — STOP, mark `[REQUIRES APPROVAL]`, ask before proceeding.

---

## 10. Out of Scope

Task 4 ships only the Angular auth surface. Branding, deep-linking, OAuth, and 2FA are explicitly deferred.

- **Branded email templates** — Neon Auth defaults; brand when marketing-page capability lands
- **Deep-link redirect after verify** (return to last opened project) — defaults to `/projects`; UX polish
- **Password / OAuth fallback** — magic-link is the only login surface
- **2FA / TOTP** — opt-in feature; future capability
- **Pre-flight email-validity check** before POSTing to `/api/auth/login` — Angular's `type="email"` and `required` are sufficient v1

**Rule for the executor**: if a change appears helpful but is listed above, STOP and flag it as a deviation rather than expanding this task.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale for this module
- [Epic](./epic.md) — Task scope and ordering
- [Task 1](./task-1-auth-service-jwt-verifier.md) — Backend service
- [Task 2](./task-2-require-auth-decorator-routes.md) — Backend routes this client consumes
- [Task 3](./task-3-protect-existing-routes.md) — Backend protection enforced for this client
- [Timeline](./timeline.md) — Update status to `done` after verification passes

---
Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
