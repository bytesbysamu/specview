# Task 2: Session Creation + Partner Selection

## 1. Purpose

Build the entry-point page for check-ins: the user taps "New Check-In", selects Partner A or Partner B, and either resumes an existing active session or creates a new one. After selection, navigate to the rating screen. This page also handles 48-hour expiry — sessions older than 48h are marked expired before the active-session query runs.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 1 day |
| **Dependencies** | Task 1 (domain models + persistence) |
| **Parallel with** | Task 3 (rating UI) |
| **Blocks** | Task 4 (auto-save), Task 5 (submission) |

---

## 3. Context

### Why this task exists

Task 1 delivered raw persistence (CheckInService, SQLite/localStorage backends). But there is no UI to start a session. This task wires the first page into the check-in route tree: partner selection with resume-or-create logic. It follows the exact page-service pattern from the tasks domain (`TaskListPageService` + `TaskListPage`) but adapts it for TanStack Query mutations and active-session lookup.

### Trade-offs

- **Page service encapsulates all async logic**: The page component stays synchronous and declarative (signals + template bindings). All TanStack Query calls live in the page service. This matches `TaskListPageService`.
- **Expiry check runs on page init, not app init**: The architecture says "on app init", but that requires a global bootstrap hook. For now, the page service marks expired sessions before querying active ones. Task 4 may move this to an app initializer.
- **Two large buttons instead of a dropdown**: The UI spec says "two large tap targets". This is intentional for speed and clarity on mobile.
- **Constructor DI instead of `inject()`**: Mirrors the tasks domain pattern established in Task 1.

### Rejected alternatives

- **Modal for partner selection**: Adds an extra dismiss step. A dedicated page is simpler and matches the route tree.
- **Automatic partner detection**: No auth system, no way to know who is holding the phone. Explicit selection is correct.

---

## 4. Pre-flight

Run from the ionstarter project root (`/projects/ionstarter/`):

```bash
# 1. Verify the project builds cleanly
cd /projects/ionstarter && npm run build

# 2. Verify tests pass
cd /projects/ionstarter && npm run test:ci

# 3. Verify Task 1 outputs exist
ls src/app/domains/check-in/services/check-in/check-in.service.ts
ls src/app/domains/check-in/interfaces/check-in.ts
ls src/app/domains/check-in/services/index.ts

# 4. Verify TanStack Query is installed
node -e "const p = require('./package.json'); console.log('@ngneat/query:', p.dependencies['@ngneat/query'])"

# 5. Verify RouterService exists
ls src/app/core/services/router/router.service.ts

# 6. Create the directory scaffold
mkdir -p src/app/domains/check-in/pages/check-in-start
mkdir -p src/app/domains/check-in/services/check-in-start-page
```

---

## 5. Files

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/domains/check-in/pages/check-in-start/check-in-start.page.ts` | Partner selection page component |
| 2 | `src/app/domains/check-in/pages/check-in-start/check-in-start.page.html` | Template with two partner buttons |
| 3 | `src/app/domains/check-in/pages/check-in-start/check-in-start.page.scss` | Styles for partner tap targets |
| 4 | `src/app/domains/check-in/services/check-in-start-page/check-in-start-page.service.ts` | TanStack Query page service (query + mutation + navigation) |
| 5 | `src/app/domains/check-in/check-in.routes.ts` | Route definitions for the check-in domain |
| 6 | `src/app/domains/check-in/services/check-in-start-page/check-in-start-page.service.spec.ts` | Unit tests for page service |
| 7 | `src/app/domains/check-in/pages/check-in-start/check-in-start.page.spec.ts` | Unit tests for page component |

### To Modify

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/core/services/router/router.service.ts` | Add `navigateToCheckInStartPage()` and `navigateToCheckInRatingPage(sessionId)` methods |
| 2 | `src/app/domains/check-in/services/index.ts` | Add barrel export for `check-in-start-page` service |

### To Leave Alone

- `src/app/domains/check-in/services/check-in/check-in.service.ts` -- Consumed, not modified
- `src/app/domains/check-in/interfaces/` -- Read-only
- `src/app/domains/tasks/` -- Reference only
- `src/app/domains/check-in/pages/check-in-rating/` -- Task 3's concern

---

## 6. Implementation Steps

### Step 1: Add navigation methods to RouterService

**Action**: Add two navigation methods to the existing `RouterService` for check-in routes.

**File**: `src/app/core/services/router/router.service.ts`

**Add after `navigateToSettingsPage`**:

```typescript
public navigateToCheckInStartPage(options?: NavigationOptions): Promise<boolean> {
  return this.navigateForward(['/check-in'], options);
}

public navigateToCheckInRatingPage(
  sessionId: string,
  options?: NavigationOptions,
): Promise<boolean> {
  return this.navigateForward(['/check-in', 'rating', sessionId], options);
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 2: Create the check-in-start-page service

**Action**: Create the TanStack Query page service. It provides: (1) a query that fetches all sessions, (2) a mutation that creates a new session, (3) an `onSelectPartner` method that handles the resume-or-create logic with expiry check.

**File**: `src/app/domains/check-in/services/check-in-start-page/check-in-start-page.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { RouterService } from '@app/core';
import {
  MutationResult,
  QueryObserverResult,
  injectMutation,
  injectQuery,
  injectQueryClient,
} from '@ngneat/query';
import { Result } from '@ngneat/query/lib/types';
import { CheckInSession } from '../../interfaces';
import { CheckInService } from '../check-in/check-in.service';

const EXPIRY_MS = 48 * 60 * 60 * 1000; // 48 hours

@Injectable({
  providedIn: 'root',
})
export class CheckInStartPageService {
  #client = injectQueryClient();
  #mutation = injectMutation();
  #query = injectQuery();

  constructor(
    private readonly routerService: RouterService,
    private readonly checkInService: CheckInService,
  ) {}

  public getSessions(): Result<QueryObserverResult<CheckInSession[], Error>> {
    return this.#query({
      queryKey: ['check-in-sessions'],
      queryFn: () => this.checkInService.getSessions(),
    });
  }

  public createSession(): MutationResult<
    CheckInSession,
    Error,
    CheckInSession['partner'],
    unknown
  > {
    return this.#mutation({
      mutationFn: (partner: CheckInSession['partner']) =>
        this.checkInService.createSession(partner),
      onSuccess: () => {
        void this.#client.invalidateQueries({
          queryKey: ['check-in-sessions'],
        });
      },
    });
  }

  public async onSelectPartner(
    partner: CheckInSession['partner'],
  ): Promise<void> {
    // 1. Fetch current sessions
    const sessions = await this.checkInService.getSessions();

    // 2. Expire stale sessions (createdAt + 48h < now)
    const now = Date.now();
    for (const session of sessions) {
      const createdAtMs = new Date(session.createdAt).getTime();
      if (
        !session.submitted &&
        !session.expiredAt &&
        createdAtMs + EXPIRY_MS < now
      ) {
        await this.checkInService.markComplete(session.id);
      }
    }

    // 3. Find active session for this partner (non-submitted, non-expired)
    const refreshedSessions = await this.checkInService.getSessions();
    const activeSession = refreshedSessions.find(
      s => s.partner === partner && !s.submitted && !s.expiredAt,
    );

    if (activeSession) {
      // 4a. Resume existing session
      await this.routerService.navigateToCheckInRatingPage(activeSession.id);
    } else {
      // 4b. Create new session and navigate
      const newSession = await this.checkInService.createSession(partner);
      void this.#client.invalidateQueries({
        queryKey: ['check-in-sessions'],
      });
      await this.routerService.navigateToCheckInRatingPage(newSession.id);
    }
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 3: Create the check-in-start page component

**Action**: Create the standalone page component with two partner selection buttons.

**File**: `src/app/domains/check-in/pages/check-in-start/check-in-start.page.ts`

```typescript
import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SharedModule } from '@app/shared';
import {
  IonButton,
  IonContent,
  IonHeader,
  IonIcon,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import { TranslocoPipe } from '@jsverse/transloco';
import { addIcons } from 'ionicons';
import { people } from 'ionicons/icons';
import { CheckInStartPageService } from '../../services/check-in-start-page/check-in-start-page.service';

@Component({
  selector: 'app-check-in-start',
  templateUrl: './check-in-start.page.html',
  styleUrls: ['./check-in-start.page.scss'],
  imports: [
    SharedModule,
    TranslocoPipe,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButton,
    IonIcon,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInStartPage {
  public readonly sessions = this.checkInStartPageService.getSessions().result;

  constructor(
    private readonly checkInStartPageService: CheckInStartPageService,
  ) {
    addIcons({ people });
  }

  public async onSelectPartner(partner: 'A' | 'B'): Promise<void> {
    await this.checkInStartPageService.onSelectPartner(partner);
  }
}
```

---

### Step 4: Create the page template

**Action**: Create the HTML template with two large tap targets for partner selection.

**File**: `src/app/domains/check-in/pages/check-in-start/check-in-start.page.html`

```html
<ion-header [translucent]="true">
  <ion-toolbar>
    <ion-title>{{ "domain.checkIn.page.start.title" | transloco }}</ion-title>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true" class="ion-padding">
  <ion-header collapse="condense">
    <ion-toolbar>
      <ion-title size="large">{{
        "domain.checkIn.page.start.title" | transloco
      }}</ion-title>
    </ion-toolbar>
  </ion-header>

  <div class="partner-selection">
    <p class="partner-selection__subtitle">
      {{ "domain.checkIn.page.start.subtitle" | transloco }}
    </p>

    <button
      class="partner-card partner-card--a"
      data-test="partner-a-button"
      (click)="onSelectPartner('A')"
    >
      <ion-icon name="people"></ion-icon>
      <span class="partner-card__label">{{
        "domain.checkIn.page.start.partnerA" | transloco
      }}</span>
    </button>

    <button
      class="partner-card partner-card--b"
      data-test="partner-b-button"
      (click)="onSelectPartner('B')"
    >
      <ion-icon name="people"></ion-icon>
      <span class="partner-card__label">{{
        "domain.checkIn.page.start.partnerB" | transloco
      }}</span>
    </button>
  </div>
</ion-content>
```

---

### Step 5: Create the page styles

**Action**: Create the SCSS file with styles for the partner selection cards.

**File**: `src/app/domains/check-in/pages/check-in-start/check-in-start.page.scss`

```scss
:host {
  --background: var(--ion-background-color, #121212);
}

.partner-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 24px;
  min-height: 60vh;
  padding: 16px;

  &__subtitle {
    font-size: 16px;
    color: var(--ion-color-medium);
    text-align: center;
    margin-bottom: 16px;
  }
}

.partner-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  width: 100%;
  max-width: 280px;
  padding: 32px 24px;
  border-radius: 16px;
  border: 2px solid var(--ion-color-primary);
  background: transparent;
  color: var(--ion-color-primary);
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s, transform 0.1s;

  &:active {
    transform: scale(0.97);
    background: rgba(var(--ion-color-primary-rgb), 0.1);
  }

  ion-icon {
    font-size: 48px;
  }

  &__label {
    font-size: 18px;
  }

  &--a {
    border-color: var(--ion-color-primary);
    color: var(--ion-color-primary);
  }

  &--b {
    border-color: var(--ion-color-secondary);
    color: var(--ion-color-secondary);
  }
}
```

---

### Step 6: Create the route definitions

**Action**: Create the route file for the check-in domain. Include the start page as the default route and a placeholder path for the rating page (Task 3 will implement it).

**File**: `src/app/domains/check-in/check-in.routes.ts`

```typescript
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/check-in-start/check-in-start.page').then(
        m => m.CheckInStartPage,
      ),
  },
  {
    path: 'rating/:sessionId',
    loadComponent: () =>
      import('./pages/check-in-rating/check-in-rating.page').then(
        m => m.CheckInRatingPage,
      ),
  },
];
```

**Note**: The rating page does not exist yet (Task 3). Create a minimal placeholder so the route compiles:

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts` (placeholder)

```typescript
import { ChangeDetectionStrategy, Component } from '@angular/core';
import { IonContent, IonHeader, IonTitle, IonToolbar } from '@ionic/angular/standalone';

@Component({
  selector: 'app-check-in-rating',
  template: `
    <ion-header><ion-toolbar><ion-title>Rating</ion-title></ion-toolbar></ion-header>
    <ion-content><p>Rating page placeholder — Task 3</p></ion-content>
  `,
  imports: [IonHeader, IonToolbar, IonTitle, IonContent],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInRatingPage {}
```

---

### Step 7: Update services barrel export

**Action**: Add the new page service to the services barrel.

**File**: `src/app/domains/check-in/services/index.ts`

**Append**:

```typescript
export * from './check-in-start-page/check-in-start-page.service';
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 8: Register the check-in route in the app routing

**Action**: Add the check-in lazy-loaded route to the app's main route configuration. Find the app routes file and add:

```typescript
{
  path: 'check-in',
  loadChildren: () =>
    import('./domains/check-in/check-in.routes').then(m => m.routes),
},
```

**Verify**:

```bash
cd /projects/ionstarter && npm run build
```

---

## 7. Tests

### Test 1: `check-in-start-page.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in-start-page/check-in-start-page.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { RouterService } from '@app/core';
import { CheckInStartPageService } from './check-in-start-page.service';
import { CheckInService } from '../check-in/check-in.service';
import { CheckInSession } from '../../interfaces';

describe('CheckInStartPageService', () => {
  let service: CheckInStartPageService;
  let checkInSpy: jasmine.SpyObj<CheckInService>;
  let routerSpy: jasmine.SpyObj<RouterService>;

  function fakeSession(overrides: Partial<CheckInSession> = {}): CheckInSession {
    return {
      id: 'sess-1',
      createdAt: new Date().toISOString(),
      partner: 'A',
      submitted: false,
      expiredAt: undefined,
      ...overrides,
    };
  }

  function expiredSession(partner: 'A' | 'B'): CheckInSession {
    const oldDate = new Date(Date.now() - 49 * 60 * 60 * 1000).toISOString();
    return fakeSession({
      id: `expired-${partner}`,
      createdAt: oldDate,
      partner,
      submitted: false,
    });
  }

  beforeEach(() => {
    checkInSpy = jasmine.createSpyObj('CheckInService', [
      'getSessions',
      'createSession',
      'markComplete',
    ]);
    checkInSpy.getSessions.and.resolveTo([]);
    checkInSpy.createSession.and.callFake((partner: 'A' | 'B') =>
      Promise.resolve(fakeSession({ id: 'new-sess', partner })),
    );
    checkInSpy.markComplete.and.resolveTo();

    routerSpy = jasmine.createSpyObj('RouterService', [
      'navigateToCheckInRatingPage',
    ]);
    routerSpy.navigateToCheckInRatingPage.and.resolveTo(true);

    TestBed.configureTestingModule({
      providers: [
        CheckInStartPageService,
        { provide: CheckInService, useValue: checkInSpy },
        { provide: RouterService, useValue: routerSpy },
      ],
    });
    service = TestBed.inject(CheckInStartPageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('onSelectPartner', () => {
    it('should create a new session when no active session exists', async () => {
      checkInSpy.getSessions.and.resolveTo([]);

      await service.onSelectPartner('A');

      expect(checkInSpy.createSession).toHaveBeenCalledWith('A');
      expect(routerSpy.navigateToCheckInRatingPage).toHaveBeenCalledWith(
        'new-sess',
      );
    });

    it('should resume existing active session for selected partner', async () => {
      const activeSession = fakeSession({
        id: 'active-a',
        partner: 'A',
        submitted: false,
      });
      checkInSpy.getSessions.and.resolveTo([activeSession]);

      await service.onSelectPartner('A');

      expect(checkInSpy.createSession).not.toHaveBeenCalled();
      expect(routerSpy.navigateToCheckInRatingPage).toHaveBeenCalledWith(
        'active-a',
      );
    });

    it('should not resume a session for the other partner', async () => {
      const sessionB = fakeSession({
        id: 'active-b',
        partner: 'B',
        submitted: false,
      });
      checkInSpy.getSessions.and.resolveTo([sessionB]);

      await service.onSelectPartner('A');

      expect(checkInSpy.createSession).toHaveBeenCalledWith('A');
    });

    it('should not resume a submitted session', async () => {
      const submitted = fakeSession({
        id: 'submitted-a',
        partner: 'A',
        submitted: true,
      });
      checkInSpy.getSessions.and.resolveTo([submitted]);

      await service.onSelectPartner('A');

      expect(checkInSpy.createSession).toHaveBeenCalledWith('A');
    });

    it('should not resume an expired session', async () => {
      const expired = fakeSession({
        id: 'expired-a',
        partner: 'A',
        submitted: false,
        expiredAt: '2026-04-18T10:00:00.000Z',
      });
      checkInSpy.getSessions.and.resolveTo([expired]);

      await service.onSelectPartner('A');

      expect(checkInSpy.createSession).toHaveBeenCalledWith('A');
    });

    it('should expire stale sessions before checking for active ones', async () => {
      const stale = expiredSession('A');
      // First call returns stale session, second call (after expiry) returns empty
      checkInSpy.getSessions.and.returnValues(
        Promise.resolve([stale]),
        Promise.resolve([]),
      );

      await service.onSelectPartner('A');

      expect(checkInSpy.markComplete).toHaveBeenCalledWith(stale.id);
      expect(checkInSpy.createSession).toHaveBeenCalledWith('A');
    });

    it('should not expire sessions that are less than 48h old', async () => {
      const fresh = fakeSession({
        id: 'fresh-a',
        partner: 'A',
        createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      });
      checkInSpy.getSessions.and.resolveTo([fresh]);

      await service.onSelectPartner('A');

      expect(checkInSpy.markComplete).not.toHaveBeenCalled();
      expect(routerSpy.navigateToCheckInRatingPage).toHaveBeenCalledWith(
        'fresh-a',
      );
    });

    it('should navigate to rating page with new session ID on create', async () => {
      checkInSpy.getSessions.and.resolveTo([]);
      checkInSpy.createSession.and.resolveTo(
        fakeSession({ id: 'brand-new', partner: 'B' }),
      );

      await service.onSelectPartner('B');

      expect(routerSpy.navigateToCheckInRatingPage).toHaveBeenCalledWith(
        'brand-new',
      );
    });
  });
});
```

### Test 2: `check-in-start.page.spec.ts`

**File**: `src/app/domains/check-in/pages/check-in-start/check-in-start.page.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { getTranslocoModule } from '@app/core/i18n/transloco-testing.module';
import { CheckInStartPage } from './check-in-start.page';
import { CheckInStartPageService } from '../../services/check-in-start-page/check-in-start-page.service';

describe('CheckInStartPage', () => {
  let component: CheckInStartPage;
  let fixture: ComponentFixture<CheckInStartPage>;
  let pageServiceSpy: jasmine.SpyObj<CheckInStartPageService>;

  beforeEach(async () => {
    pageServiceSpy = jasmine.createSpyObj('CheckInStartPageService', [
      'getSessions',
      'onSelectPartner',
    ]);
    pageServiceSpy.getSessions.and.returnValue({
      result: jasmine.createSpy().and.returnValue({ data: [], isLoading: false }),
    } as any);
    pageServiceSpy.onSelectPartner.and.resolveTo();

    await TestBed.configureTestingModule({
      imports: [CheckInStartPage, getTranslocoModule()],
      providers: [
        { provide: CheckInStartPageService, useValue: pageServiceSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CheckInStartPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should call onSelectPartner with A when partner A button clicked', async () => {
    await component.onSelectPartner('A');

    expect(pageServiceSpy.onSelectPartner).toHaveBeenCalledWith('A');
  });

  it('should call onSelectPartner with B when partner B button clicked', async () => {
    await component.onSelectPartner('B');

    expect(pageServiceSpy.onSelectPartner).toHaveBeenCalledWith('B');
  });

  it('should render two partner buttons', () => {
    const el = fixture.nativeElement as HTMLElement;
    const btnA = el.querySelector('[data-test="partner-a-button"]');
    const btnB = el.querySelector('[data-test="partner-b-button"]');

    expect(btnA).toBeTruthy();
    expect(btnB).toBeTruthy();
  });
});
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(check-in): add navigation methods for check-in routes` | `src/app/core/services/router/router.service.ts` |
| 2 | `feat(check-in): add session start page service with resume-or-create logic` | `services/check-in-start-page/check-in-start-page.service.ts`, `services/check-in-start-page/check-in-start-page.service.spec.ts`, `services/index.ts` |
| 3 | `feat(check-in): add partner selection page and check-in routes` | `pages/check-in-start/check-in-start.page.ts`, `.html`, `.scss`, `.spec.ts`, `check-in.routes.ts`, `pages/check-in-rating/check-in-rating.page.ts` |
| 4 | `feat(check-in): register check-in routes in app routing` | App routes file |

---

## 9. Verification

After all steps are complete, run from `/projects/ionstarter/`:

```bash
# 1. TypeScript compilation
npx tsc --noEmit
# Expected: 0 errors

# 2. Full build
npm run build
# Expected: Build succeeds

# 3. Lint
npm run lint
# Expected: 0 errors, 0 warnings

# 4. Unit tests
npm run test:ci
# Expected: All tests pass, including:
#   - CheckInStartPageService: 8 specs
#   - CheckInStartPage: 4 specs

# 5. Verify file structure
ls -la src/app/domains/check-in/pages/check-in-start/
# Expected: check-in-start.page.ts, .html, .scss, .spec.ts

ls -la src/app/domains/check-in/services/check-in-start-page/
# Expected: check-in-start-page.service.ts, .spec.ts

ls src/app/domains/check-in/check-in.routes.ts
# Expected: file exists

# 6. Serve and verify route loads
ionic serve &
# Navigate to http://localhost:8100/check-in
# Expected: Partner selection page renders with two buttons
```

---

## 10. Rollback

Changes are isolated to new files plus one modification to `RouterService`. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -4  # find the 4 commit SHAs
git revert <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~4

# Option 3: Manual cleanup
rm -rf src/app/domains/check-in/pages/check-in-start/
rm -rf src/app/domains/check-in/pages/check-in-rating/
rm -rf src/app/domains/check-in/services/check-in-start-page/
rm src/app/domains/check-in/check-in.routes.ts
# Then revert the two additions to router.service.ts and services/index.ts
git checkout -- src/app/core/services/router/router.service.ts
git checkout -- src/app/domains/check-in/services/index.ts
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Expiry mechanism** | Executor may use `updateSession` with `expiredAt` set to current timestamp instead of `markComplete`. The architecture is ambiguous on whether expired sessions are "submitted" or "expired". Either field works — the key is that the session no longer appears as "active". |
| **Query vs imperative fetch** | The guide uses imperative `getSessions()` in `onSelectPartner`. Executor may instead read from the TanStack query cache via `queryClient.getQueryData(['check-in-sessions'])` for a sync read. Either approach is valid. |
| **Placeholder rating page** | Executor may omit the placeholder rating page if Task 3 is being developed in parallel and the route can reference a real component. If omitted, the routes file can use a redirect or leave the path commented out. |
| **Button implementation** | Executor may use `<ion-button>` instead of native `<button>` with custom styles. The guide uses native buttons for full style control, but Ionic buttons are acceptable. |
| **i18n keys** | Executor may inline English text instead of using transloco keys if i18n setup is not yet configured. Add transloco keys in a follow-up. |
| **Additional loading/error states** | Executor may add `@if (sessions().isLoading)` or error display in the template. The guide keeps it minimal but UI polish is welcome. |
| **`expiredAt` type** | Executor may use `undefined` instead of checking for null/falsy. Both are acceptable per Task 1's deviation allowance. |

---

## 12. Out of Scope

- **Rating UI (tap circles, questions)** -- Task 3
- **Draft auto-save logic** -- Task 4
- **Session expiry on app init** -- Task 4 (this task handles expiry only at page-service level)
- **Submission flow** -- Task 5
- **Quality computation** -- Task 6
- **Trend tracking** -- Task 7
- **Tab bar integration** -- Separate task; this task only registers the route
- **i18n JSON translation files** -- Create when i18n is fully configured
- **Haptic feedback on tap** -- Nice-to-have, not required for this task
- **Tests for the placeholder rating page** -- Task 3 owns the rating page
- **Animating route transitions** -- Ionic default transitions are sufficient
