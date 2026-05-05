I don't have read access to `web/` from this session. I'll write the guide based on Angular 17 standalone conventions and direct the executor to verify structural paths before each step.

---

# Task 4: Angular Billing Surface — Implementation Guide

## 1. Context

This task wires the five Angular pieces that make plan state visible and actionable: a signals-based `SubscriptionService` that owns plan state and initiates Stripe Checkout, a functional `proGuard` that gates pro-only routes, a `UsageMeterComponent` pill for the app shell, a functional `usageLimitInterceptor` that catches 429s globally and routes to `/upgrade`, and an `UpgradePage` with pricing copy and the Pro CTA. Together these close the user-facing loop: a free user who hits a usage cap sees a pill turn red, is intercepted into the upgrade flow, and is handed off to Stripe Checkout with one click. No billing logic runs in the browser — the Angular surface is a thin reactive skin over the three API endpoints delivered in Tasks 1–3.

**Trade-offs considered:**

- **NgRx / RxJS BehaviorSubject for plan state** — rejected because Angular 17 signals are already stable and eliminate the Subject+async-pipe boilerplate; consistent with existing spec-doc signal patterns and the bubls port source.
- **Class-based guard and interceptor** — rejected because Angular 14+ functional form (`CanActivateFn`, `HttpInterceptorFn`) removes the need for `@Injectable` plumbing, is the Angular team's current recommendation, and matches what bubls ships.
- **Signals + `inject()` in functional guard/interceptor (chosen)** — reads `isPro()` signal directly with no Subject subscription; zero RxJS in the guard/interceptor path; compatible with Angular 17's `provideHttpClient(withInterceptors([...]))` API.

---

## 2. Pre-flight

Run **before editing any file**:

```bash
# 1. Confirm clean working tree on target area
git status
git diff HEAD -- web/src/app/

# 2. Record Angular version — must be 17+ for stable signals
grep '"@angular/core"' web/package.json

# 3. Confirm test framework (Jasmine/Karma vs Jest)
grep -E '"jest"|"karma"|"@jest"' web/package.json

# 4. Run current Angular test suite; record pass count
cd web && ng test --watch=false --browsers=ChromeHeadless 2>&1 | tail -5

# 5. Confirm billing status endpoint is live (Tasks 1–3 prerequisite)
curl -s -o /dev/null -w "%{http_code}" http://localhost:3101/api/billing/status
# Expect 401 (auth-gated, not 404) — if 404, Tasks 1–3 are not complete; STOP.

# 6. Locate the app shell template (router-outlet host)
grep -rl "router-outlet" web/src/app/ --include="*.html"
# Note the path — used in Step 7 to add <app-usage-meter>

# 7. Confirm app.config.ts and app.routes.ts exist at expected paths
ls web/src/app/app.config.ts web/src/app/app.routes.ts

# 8. Confirm bubls billing surface is accessible for porting
ls {BUBLS_WORKSPACE}/src/app/core/services/subscription.service.ts 2>/dev/null \
  || echo "bubls unavailable — implement from patterns in this guide"
```

**If working tree is dirty on `web/src/app/`**: stash or commit unrelated changes before starting.

**Baseline recorded**: `___` Angular tests passing. Record this number; verification targets baseline + 14.

---

## 3. Files

### To Create (new)

- `web/src/app/core/services/subscription.service.ts` — signals-based plan state, `refresh()`, `startCheckout()`; sole HTTP consumer of `GET /api/billing/status` and `POST /api/billing/create-checkout-session`
- `web/src/app/core/services/subscription.service.spec.ts` — unit tests for service
- `web/src/app/core/guards/pro.guard.ts` — functional `CanActivateFn`; reads `isPro()` signal; redirects to `/upgrade?returnUrl=` when false
- `web/src/app/core/guards/pro.guard.spec.ts` — unit tests for guard
- `web/src/app/shared/components/usage-meter/usage-meter.component.ts` — standalone pill; hidden when pro; red highlight at ≤ 1 remaining; accepts `@Input() feature: string`
- `web/src/app/shared/components/usage-meter/usage-meter.component.spec.ts` — unit tests for component
- `web/src/app/core/interceptors/usage-limit.interceptor.ts` — functional `HttpInterceptorFn`; catches 429; navigates to `/upgrade`
- `web/src/app/core/interceptors/usage-limit.interceptor.spec.ts` — unit tests for interceptor
- `web/src/app/pages/upgrade/upgrade.page.ts` — standalone component; pricing copy; Pro CTA calls `startCheckout()`
- `web/src/app/pages/upgrade/upgrade.page.spec.ts` — unit tests for page

### To Modify (cite CODEBASE CONTEXT)

- `web/src/app/app.routes.ts` — add `/upgrade` route pointing to `UpgradePage`; apply `proGuard` to any existing pro-only routes (none yet, but pattern is established)
- `web/src/app/app.config.ts` — register `usageLimitInterceptor` via `withInterceptors([usageLimitInterceptor])` in `provideHttpClient(...)`, and add `APP_INITIALIZER` to call `SubscriptionService.refresh()` before first render
- **Shell component** (executor: use path found in pre-flight step 6) — add `<app-usage-meter feature="task_gen" />` to the header/nav area

### To Leave Alone

- `web/src/app/app.component.ts` — modify only if it IS the shell (pre-flight step 6 decides); otherwise untouched
- `api/` — all API modules; Tasks 1–3 own those; this task is Angular-only
- `api/openapi.yaml` — contract is already set by Task 1; do not re-open it here
- `api/dtos/models.py` — generated; never hand-edit; not touched by this task

---

## 4. Implementation Steps

### Step 1: Verify Angular version and signal API compatibility

**Action**: Confirm `@angular/core` ≥ 17.0.0, that `signal` and `computed` are importable from `@angular/core` (not a polyfill), and that the project uses `provideHttpClient(withInterceptors([...]))` rather than the legacy `HTTP_INTERCEPTORS` multi-token. If bubls is accessible, diff its Angular version against spec-doc's. If both are 17+, proceed. If bubls is 16 with `Signal` in preview, the port is still valid — signal API didn't change between 16 and 17 beyond stabilisation.

**File**: `web/package.json` (read-only audit)

**Pattern**:
```bash
# Confirm signals import resolves
node -e "const a = require('@angular/core'); console.log(typeof a.signal)"
# Expect: function

# Confirm functional interceptor API
grep "withInterceptors\|provideHttpClient" web/src/app/app.config.ts
# If provideHttpClient(...withInterceptors) is already present, Step 7 is additive.
# If HTTP_INTERCEPTORS multi-token is used, executor must migrate — flag as deviation.
```

**Verify**: Both checks return non-error; no deviation flag raised. If Angular < 17, STOP and raise [REQUIRES APPROVAL] — this is a prerequisite version constraint.

---

### Step 2: Create `SubscriptionService`

**Action**: Create the service with two private signals (`_plan`, `_remaining`), two public readonly projections (`plan`, `isPro`), `refresh()` (hydrates from billing status; fails silently for unauthenticated users so `APP_INITIALIZER` never blocks the app), and `startCheckout()` (POSTs then redirects). Port from `bubls/src/app/core/services/subscription.service.ts` if available — the only delta is the API path (`/api/billing/` prefix) and the `remaining: Record<string, number>` shape instead of a single counter.

**File**: `web/src/app/core/services/subscription.service.ts` (new)

**Pattern**:
```typescript
import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

export interface BillingStatus {
  plan: 'free' | 'pro';
  status: string | null;
  period_end: string | null;
  manage_url: string | null;
  remaining: Record<string, number> | null;  // null for pro users
}

@Injectable({ providedIn: 'root' })
export class SubscriptionService {
  private readonly http = inject(HttpClient);

  private readonly _plan = signal<'free' | 'pro'>('free');
  private readonly _remaining = signal<Record<string, number> | null>(null);

  readonly plan = this._plan.asReadonly();
  readonly isPro = computed(() => this._plan() === 'pro');
  readonly remaining = this._remaining.asReadonly();

  remainingFor(feature: string): number | null {
    const r = this._remaining();
    return r != null ? (r[feature] ?? null) : null;
  }

  refresh(): Observable<void> {
    return this.http.get<BillingStatus>('/api/billing/status').pipe(
      tap(status => {
        this._plan.set(status.plan);
        this._remaining.set(status.remaining);
      }),
      map(() => void 0 as void),
      catchError(() => of(void 0 as void))  // 401 / network — stay as free, never block init
    );
  }

  startCheckout(): void {
    this.http
      .post<{ checkout_url: string }>('/api/billing/create-checkout-session', {})
      .subscribe({
        next: (res) => { window.location.href = res.checkout_url; },
        error: (err) => console.error('Checkout failed', err),
      });
  }
}
```

**Verify**:
```bash
cd web && npx tsc --noEmit
# Expect: 0 errors
```

---

### Step 3: Create `pro.guard.ts`

**Action**: Implement a functional `CanActivateFn` that reads `isPro()` from `SubscriptionService`. If true, allow navigation. If false, redirect to `/upgrade` with `returnUrl` query param so the upgrade page can redirect back after checkout success. Port from `bubls/src/app/core/guards/pro.guard.ts` — the redirect path is the only expected delta.

**File**: `web/src/app/core/guards/pro.guard.ts` (new)

**Pattern**:
```typescript
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SubscriptionService } from '../services/subscription.service';

export const proGuard: CanActivateFn = (_route, state) => {
  const sub = inject(SubscriptionService);
  const router = inject(Router);

  if (sub.isPro()) {
    return true;
  }

  return router.createUrlTree(['/upgrade'], {
    queryParams: { returnUrl: state.url },
  });
};
```

**Verify**:
```bash
cd web && npx tsc --noEmit
# Expect: 0 errors
```

---

### Step 4: Create `UsageMeterComponent`

**Action**: Create a standalone component that displays a remaining-count pill for a given `feature` input. Hidden entirely when `isPro()` is true. Highlighted with the `danger` CSS class when remaining ≤ 1. The `feature` input defaults to `'task_gen'` (most frequent operation in spec-doc). Port from `bubls/src/app/shared/components/usage-meter/` — adapt template syntax from Ionic/Capacitor markup to plain Angular if needed, and switch from Angular 16's `*ngIf` to Angular 17 `@if` control flow.

**File**: `web/src/app/shared/components/usage-meter/usage-meter.component.ts` (new)

**Pattern**:
```typescript
import { Component, Input, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SubscriptionService } from '../../../core/services/subscription.service';

@Component({
  selector: 'app-usage-meter',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (!sub.isPro() && count() !== null) {
      <span class="usage-pill" [class.danger]="count()! <= 1">
        {{ count() }} left today
      </span>
    }
  `,
  styles: [`
    .usage-pill {
      font-size: 0.75rem;
      padding: 2px 8px;
      border-radius: 12px;
      background: var(--color-surface-alt, #f3f4f6);
      color: var(--color-text-secondary, #6b7280);
    }
    .usage-pill.danger {
      background: var(--color-danger-bg, #fee2e2);
      color: var(--color-danger, #dc2626);
      font-weight: 600;
    }
  `],
})
export class UsageMeterComponent {
  @Input() feature = 'task_gen';

  protected readonly sub = inject(SubscriptionService);
  protected readonly count = computed(() => this.sub.remainingFor(this.feature));
}
```

**Verify**:
```bash
cd web && npx tsc --noEmit
# Expect: 0 errors
```

---

### Step 5: Create `usage-limit.interceptor.ts`

**Action**: Implement a functional `HttpInterceptorFn` that catches `HttpErrorResponse` with status 429 and navigates to `/upgrade`. All other errors are re-thrown unchanged. Port from `bubls/src/app/core/interceptors/usage-limit.interceptor.ts` — the navigation target is the only expected delta. The interceptor must NOT swallow non-429 errors; callers rely on propagated errors for their own error handling.

**File**: `web/src/app/core/interceptors/usage-limit.interceptor.ts` (new)

**Pattern**:
```typescript
import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

export const usageLimitInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 429) {
        router.navigate(['/upgrade']);
      }
      return throwError(() => error);
    })
  );
};
```

**Verify**:
```bash
cd web && npx tsc --noEmit
# Expect: 0 errors
```

---

### Step 6: Create `UpgradePage`

**Action**: Create a standalone component with pricing copy and a single Pro CTA button that calls `SubscriptionService.startCheckout()`. Show `manage_url` as a "Manage subscription" link if the user already has a Stripe customer record (billing status has a non-null `manage_url`). The page is reachable via direct navigation and via the 429 interceptor redirect. Port page structure from `bubls/src/app/pages/upgrade/` — adapt to Angular Router `ActivatedRoute` for reading `returnUrl` query param (unused in v1 but preserved for future success-page redirect).

**File**: `web/src/app/pages/upgrade/upgrade.page.ts` (new)

**Pattern**:
```typescript
import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SubscriptionService } from '../../core/services/subscription.service';

@Component({
  selector: 'app-upgrade',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="upgrade-container">
      <h1>Upgrade to Pro</h1>
      <p class="subtitle">Remove daily limits and unlock unlimited AI generation.</p>

      <div class="plan-card">
        <div class="plan-name">Pro</div>
        <div class="plan-price">$X<span>/mo</span></div>
        <ul class="plan-features">
          <li>Unlimited project bootstraps</li>
          <li>Unlimited task generation</li>
          <li>Unlimited spec generation</li>
          <li>Priority AI processing</li>
        </ul>
        <button class="cta-btn" (click)="checkout()" [disabled]="loading()">
          {{ loading() ? 'Redirecting…' : 'Upgrade to Pro' }}
        </button>
      </div>

      @if (sub.plan() === 'pro') {
        <p class="already-pro">You're already on Pro. 🎉</p>
      }
    </div>
  `,
})
export class UpgradePage {
  protected readonly sub = inject(SubscriptionService);
  protected readonly loading = signal(false);

  checkout(): void {
    this.loading.set(true);
    this.sub.startCheckout();
    // loading stays true — browser navigates away to Stripe
  }
}
```

**Verify**:
```bash
cd web && npx tsc --noEmit
# Expect: 0 errors
```

---

### Step 7: Wire routes, interceptor, `APP_INITIALIZER`, and shell

**Action — 7a (routes)**: Open `web/src/app/app.routes.ts` and add the `/upgrade` route. Apply `proGuard` to any route that must be pro-only (none today, but declare the guard import so future use is one line).

**File**: `web/src/app/app.routes.ts`

**Pattern**:
```typescript
import { Routes } from '@angular/router';
import { UpgradePage } from './pages/upgrade/upgrade.page';
// import { proGuard } from './core/guards/pro.guard';  // ready for pro routes

export const routes: Routes = [
  // ... existing routes unchanged ...
  {
    path: 'upgrade',
    component: UpgradePage,
  },
  // Example of future pro-only route (DO NOT add yet — Out of Scope):
  // { path: 'pro-feature', component: ProFeaturePage, canActivate: [proGuard] },
];
```

**Action — 7b (config)**: Open `web/src/app/app.config.ts`. Add `usageLimitInterceptor` to `provideHttpClient(...)` and add an `APP_INITIALIZER` that calls `SubscriptionService.refresh()` once at startup.

**File**: `web/src/app/app.config.ts`

**Pattern**:
```typescript
import { APP_INITIALIZER, ApplicationConfig } from '@angular/core';
import {
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { usageLimitInterceptor } from './core/interceptors/usage-limit.interceptor';
import { SubscriptionService } from './core/services/subscription.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([usageLimitInterceptor])),
    {
      provide: APP_INITIALIZER,
      useFactory: (sub: SubscriptionService) => () => sub.refresh(),
      deps: [SubscriptionService],
      multi: true,
    },
    // ... existing providers unchanged ...
  ],
};
```

**Action — 7c (shell)**: Using the path found in pre-flight step 6, add `<app-usage-meter />` (and its import) to the header or navigation area of the shell component.

**File**: Shell component identified in pre-flight (likely `web/src/app/app.component.ts`)

**Pattern**:
```typescript
// In the @Component imports array:
imports: [RouterOutlet, UsageMeterComponent, /* existing */],

// In the template, inside the header/nav element:
// <app-usage-meter feature="task_gen" />
```

**Verify**:
```bash
cd web && ng build --configuration=development 2>&1 | tail -10
# Expect: Build successful with 0 errors
# If "Cannot find module" errors appear, check import paths against actual directory structure
```

---

## 5. Tests

All tests use Jasmine + `TestBed` (Angular CLI default). If the repo uses Jest, translate `jasmine.createSpy` → `jest.fn()` and `expect(...).toBeTruthy()` remains valid; note translation in commit body.

**`subscription.service.spec.ts`**:
```typescript
import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { SubscriptionService } from './subscription.service';

describe('SubscriptionService', () => {
  let service: SubscriptionService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });
    service = TestBed.inject(SubscriptionService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('initialises plan as free', () => {
    expect(service.plan()).toBe('free');
  });

  it('isPro is false when plan is free', () => {
    expect(service.isPro()).toBeFalse();
  });

  it('refresh() sets plan to pro and clears remaining', () => {
    service.refresh().subscribe();
    const req = httpMock.expectOne('/api/billing/status');
    req.flush({ plan: 'pro', status: 'active', period_end: null, manage_url: null, remaining: null });
    expect(service.plan()).toBe('pro');
    expect(service.isPro()).toBeTrue();
    expect(service.remaining()).toBeNull();
  });

  it('refresh() sets remaining counts for free plan', () => {
    service.refresh().subscribe();
    const req = httpMock.expectOne('/api/billing/status');
    req.flush({ plan: 'free', status: null, period_end: null, manage_url: null, remaining: { task_gen: 18, bootstrap: 2, spec_gen: 10 } });
    expect(service.remainingFor('task_gen')).toBe(18);
    expect(service.remainingFor('bootstrap')).toBe(2);
  });

  it('refresh() completes without error on 401', () => {
    let completed = false;
    service.refresh().subscribe({ complete: () => { completed = true; } });
    const req = httpMock.expectOne('/api/billing/status');
    req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });
    expect(completed).toBeTrue();
    expect(service.plan()).toBe('free');  // stays free, does not crash
  });
});
```

**`pro.guard.spec.ts`**:
```typescript
import { TestBed } from '@angular/core/testing';
import { Router, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { proGuard } from './pro.guard';
import { SubscriptionService } from '../services/subscription.service';
import { signal } from '@angular/core';

describe('proGuard', () => {
  let router: jasmine.SpyObj<Router>;
  let sub: jasmine.SpyObj<SubscriptionService>;

  const fakeRoute = {} as ActivatedRouteSnapshot;
  const fakeState = { url: '/some-pro-route' } as RouterStateSnapshot;

  beforeEach(() => {
    router = jasmine.createSpyObj('Router', ['createUrlTree']);
    sub = jasmine.createSpyObj('SubscriptionService', [], { isPro: signal(false) });

    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: router },
        { provide: SubscriptionService, useValue: sub },
      ],
    });
  });

  it('returns true when user is pro', () => {
    // Override isPro to return true
    Object.defineProperty(sub, 'isPro', { get: () => signal(true) });
    const result = TestBed.runInInjectionContext(() =>
      proGuard(fakeRoute, fakeState)
    );
    expect(result).toBeTrue();
    expect(router.createUrlTree).not.toHaveBeenCalled();
  });

  it('calls createUrlTree to /upgrade with returnUrl when not pro', () => {
    router.createUrlTree.and.returnValue({} as any);
    const result = TestBed.runInInjectionContext(() =>
      proGuard(fakeRoute, fakeState)
    );
    expect(router.createUrlTree).toHaveBeenCalledWith(
      ['/upgrade'],
      { queryParams: { returnUrl: '/some-pro-route' } }
    );
    expect(result).toBeDefined();
  });
});
```

**`usage-meter.component.spec.ts`**:
```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UsageMeterComponent } from './usage-meter.component';
import { SubscriptionService } from '../../../core/services/subscription.service';
import { signal, computed } from '@angular/core';

describe('UsageMeterComponent', () => {
  let fixture: ComponentFixture<UsageMeterComponent>;
  let subStub: Partial<SubscriptionService>;

  function buildStub(isPro: boolean, remaining: Record<string, number> | null) {
    subStub = {
      isPro: computed(() => isPro),
      remaining: signal(remaining).asReadonly(),
      remainingFor: (feature: string) => remaining?.[feature] ?? null,
    } as any;
  }

  function createComponent(feature = 'task_gen') {
    TestBed.configureTestingModule({
      imports: [UsageMeterComponent],
      providers: [{ provide: SubscriptionService, useValue: subStub }],
    });
    fixture = TestBed.createComponent(UsageMeterComponent);
    fixture.componentInstance.feature = feature;
    fixture.detectChanges();
  }

  it('hides pill when user is pro', () => {
    buildStub(true, null);
    createComponent();
    const pill = fixture.nativeElement.querySelector('.usage-pill');
    expect(pill).toBeNull();
  });

  it('shows remaining count for free user', () => {
    buildStub(false, { task_gen: 5 });
    createComponent('task_gen');
    const pill = fixture.nativeElement.querySelector('.usage-pill');
    expect(pill).not.toBeNull();
    expect(pill.textContent).toContain('5');
  });

  it('adds danger class when remaining is 1', () => {
    buildStub(false, { task_gen: 1 });
    createComponent('task_gen');
    const pill = fixture.nativeElement.querySelector('.usage-pill');
    expect(pill.classList).toContain('danger');
  });

  it('does NOT add danger class when remaining is 3', () => {
    buildStub(false, { task_gen: 3 });
    createComponent('task_gen');
    const pill = fixture.nativeElement.querySelector('.usage-pill');
    expect(pill.classList).not.toContain('danger');
  });
});
```

**`usage-limit.interceptor.spec.ts`**:
```typescript
import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpErrorResponse,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { usageLimitInterceptor } from './usage-limit.interceptor';

describe('usageLimitInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let router: jasmine.SpyObj<Router>;

  beforeEach(() => {
    router = jasmine.createSpyObj('Router', ['navigate']);
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([usageLimitInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('navigates to /upgrade on 429', () => {
    http.get('/api/some-endpoint').subscribe({ error: () => {} });
    const req = httpMock.expectOne('/api/some-endpoint');
    req.flush('Too Many Requests', { status: 429, statusText: 'Too Many Requests' });
    expect(router.navigate).toHaveBeenCalledWith(['/upgrade']);
  });

  it('does NOT navigate on 401', () => {
    http.get('/api/some-endpoint').subscribe({ error: () => {} });
    const req = httpMock.expectOne('/api/some-endpoint');
    req.flush('Unauthorized', { status: 401, statusText: 'Unauthorized' });
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('re-throws the error on 429 so callers can also handle it', () => {
    let caughtError: HttpErrorResponse | null = null;
    http.get('/api/some-endpoint').subscribe({ error: (e) => { caughtError = e; } });
    const req = httpMock.expectOne('/api/some-endpoint');
    req.flush('Too Many Requests', { status: 429, statusText: 'Too Many Requests' });
    expect(caughtError).not.toBeNull();
    expect(caughtError!.status).toBe(429);
  });
});
```

**`upgrade.page.spec.ts`**:
```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UpgradePage } from './upgrade.page';
import { SubscriptionService } from '../../core/services/subscription.service';
import { signal, computed } from '@angular/core';

describe('UpgradePage', () => {
  let fixture: ComponentFixture<UpgradePage>;
  let subStub: jasmine.SpyObj<SubscriptionService>;

  beforeEach(() => {
    subStub = jasmine.createSpyObj('SubscriptionService', ['startCheckout'], {
      plan: signal('free' as const).asReadonly(),
    });

    TestBed.configureTestingModule({
      imports: [UpgradePage],
      providers: [{ provide: SubscriptionService, useValue: subStub }],
    });
    fixture = TestBed.createComponent(UpgradePage);
    fixture.detectChanges();
  });

  it('renders upgrade CTA button', () => {
    const btn = fixture.nativeElement.querySelector('.cta-btn');
    expect(btn).not.toBeNull();
    expect(btn.textContent).toContain('Upgrade to Pro');
  });

  it('calls startCheckout on button click', () => {
    const btn: HTMLButtonElement = fixture.nativeElement.querySelector('.cta-btn');
    btn.click();
    expect(subStub.startCheckout).toHaveBeenCalledTimes(1);
  });
});
```

---

## 6. Commit Plan

**Executor instruction**: commit after EACH step completes — not at the end of the task. Each commit boundary below corresponds to a numbered step above.

1. `feat(billing): add SubscriptionService with signals` — after Step 2 — `web/src/app/core/services/subscription.service.ts` + `.spec.ts`: plan signal, isPro computed, refresh(), startCheckout()

2. `feat(billing): add proGuard functional CanActivateFn` — after Step 3 — `web/src/app/core/guards/pro.guard.ts` + `.spec.ts`: redirects free users to /upgrade with returnUrl

3. `feat(billing): add UsageMeterComponent pill` — after Step 4 — `web/src/app/shared/components/usage-meter/usage-meter.component.ts` + `.spec.ts`: feature input, danger class at ≤1 remaining, hidden for pro

4. `feat(billing): add usageLimitInterceptor for 429` — after Step 5 — `web/src/app/core/interceptors/usage-limit.interceptor.ts` + `.spec.ts`: catches 429, navigates to /upgrade, re-throws error

5. `feat(billing): add UpgradePage with Pro CTA` — after Step 6 — `web/src/app/pages/upgrade/upgrade.page.ts` + `.spec.ts`: pricing copy, checkout button, loading state

6. `feat(billing): wire routes, interceptor, APP_INITIALIZER, and shell` — after Step 7 — `web/src/app/app.routes.ts`, `web/src/app/app.config.ts`, shell component: /upgrade route, 429 interceptor registered, plan hydrated on init, usage meter in header

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
# Full Angular test suite
cd web && ng test --watch=false --browsers=ChromeHeadless

# TypeScript strict check across the web workspace
cd web && npx tsc --noEmit

# Build smoke test (catches missing imports, template errors)
cd web && ng build --configuration=development

# API tests must remain green (no cross-contamination)
cd api && python -m pytest --tb=short -q
```

**Expected delta**: Angular test baseline + 14 passing (5 service tests + 2 guard tests + 4 meter tests + 3 interceptor tests + 2 page tests — adjust count if executor consolidates or splits). Zero pre-existing tests broken. Python API test count remains at 624.

---

## 8. Rollback

- **Per-step rollback**: each step produces one commit. `git revert <sha>` undoes that step cleanly without affecting earlier steps.
- **Per-branch rollback**: if verification fails after Step 7, `git reset --hard <pre-task-sha>` (the SHA recorded during pre-flight `git status`). If working on a feature branch, `git checkout main && git branch -D feat/billing-angular-surface`.
- **Config revert priority**: Step 7 touches `app.config.ts` and `app.routes.ts` — these have the highest blast-radius. If the build breaks after Step 7, revert commit 6 first before debugging the earlier steps.

---

## 9. Deviations Allowed

- **`web/src/app/core/` does not exist** → the executor must create it (it's the standard Angular convention for infrastructure files; `mkdir -p` as part of the step). Note the path deviation in the commit body.
- **`web/src/app/pages/` does not exist** → same treatment; create it. If the project uses a different convention (`features/`, `views/`), use that convention and note it.
- **`HTTP_INTERCEPTORS` multi-token found instead of `withInterceptors`** → migrate `provideHttpClient(withInterceptors([...]))` as part of Step 7; this is a breaking-change [REQUIRES APPROVAL] only if the migration is expected to break existing interceptors. If no other interceptors exist, proceed silently.
- **Shell component is not `app.component.ts`** → use the path found in pre-flight step 6 grep. Any component with `<router-outlet>` in its template is the shell.
- **bubls billing surface not accessible** → implement directly from the patterns in this guide. The code blocks are complete implementations, not shape-only; no further discovery is needed.
- **Test framework is Jest** → translate `jasmine.createSpy` → `jest.fn()`, `toBeFalse()` → `toBe(false)`, `toBeTrue()` → `toBe(true)`. Note translation in commit body.
- **Step N simplification discovered** → take it; log one line in the commit body as `Deviations: simplified X`.
- **Side-effect required** (npm publish, push to remote, schema change) → STOP, mark [REQUIRES APPROVAL].

---

## 10. Out of Scope

This task delivers the minimum Angular surface: plan state, route protection, the usage pill, the 429 guard rail, and the upgrade CTA. It does not build any billing management UI — that is Stripe Customer Portal's responsibility — and it does not add per-feature remaining counts to the billing status endpoint (assumed available from Task 1). Any expansion of the Angular surface beyond these five pieces is deferred.

- **Success-page redirect after Stripe Checkout** — Stripe redirects back to a `?session_id=` URL after payment; spec-doc needs a success route that re-fetches billing status and redirects to `returnUrl`. Deferred because the `returnUrl` param is already preserved in the guard and interceptor redirect; the success handler is one `ngOnInit` call added to a future `billing-success.page.ts`.
- **Billing management link in the UI** — `manage_url` is returned by `GET /api/billing/status` but is not surfaced in any nav element here. Deferred until there is a confirmed pro subscriber; showing a blank/null link to free users creates noise.
- **`proGuard` applied to real pro-only routes** — no feature in spec-doc is gated pro-only today. The guard is wired and tested but not applied to any route. Apply it when the first pro-only feature ships.
- **Remaining count for `bootstrap` and `spec_gen` in the shell** — only `task_gen` is shown in the usage-meter pill. Contextual pills for other features (e.g., near the spec-gen button) are deferred until user testing reveals demand.
- **Annual, team, or trial plan types** — `plan` signal is typed as `'free' | 'pro'` only. Extending to additional plan tiers touches the signal type, the guard, and the upgrade page; deferred per ELA Pattern #5.
- **Token or per-minute metering UI** — daily call count is the only metering surface; per-token display is deferred per the architecture's explicit exclusion.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale for the billing/usage split and signal state choice
- [Epic](./epic.md) – Task scope; Tasks 1–3 are prerequisites
- [Timeline](./timeline.md) – Update status to `done` after verification passes