# Task 4: Draft Auto-Save + Session Expiry

## 1. Purpose

Wire immediate persistence on every tap circle selection so that in-progress check-ins survive app kills. On app reopen, detect active sessions: if the session is younger than 48 hours, restore the draft with previously tapped answers pre-filled; if older, mark it expired. Clean up expired sessions on app launch so they never appear in the active session list.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 0.5 day |
| **Dependencies** | Task 2 (session creation), Task 3 (rating UI + tap circles) |
| **Parallel with** | None — depends on both prior UI tasks |
| **Blocks** | Task 5 (submission flow) |

---

## 3. Context

### Why this task exists

Tasks 2 and 3 delivered session creation and the tap-circle rating page. Task 3 already calls `CheckInService.saveResponse()` on each tap, persisting responses via INSERT OR REPLACE (SQLite) or object-merge upsert (localStorage). However, there is no draft-restoration logic on page load, no session expiry enforcement, and no cleanup of stale sessions. This task closes those gaps so the check-in behaves like a resilient mobile form.

### Trade-offs

- **48-hour window is hardcoded as a constant**: Keeps it simple and testable. If the window needs to become configurable later, extract to a config service.
- **Expiry check runs synchronously at app bootstrap (APP_INITIALIZER)**: Ensures expired sessions are purged before any UI queries them. Cost is one read + possible write on cold start (< 5 ms on SQLite, negligible on localStorage).
- **Expired sessions are marked, not deleted**: Preserves data for potential analytics. Cleanup deletes them only after marking. Alternatively the executor may hard-delete; both are acceptable.
- **Rating page pre-fills from local storage on init**: Uses the existing `getResponses(sessionId)` call and maps results into the `scores` signal. No new TanStack query needed; the existing query from Task 3's page service already fetches responses.

### Rejected alternatives

- **Server-side session expiry via TTL**: No backend yet; all logic must be client-side.
- **Background timer / periodic expiry check**: Overkill for a 48h window. Checking once on app launch and once before rating page init is sufficient.
- **Soft-delete with `deletedAt` flag**: Adds schema complexity. A simple `expiredAt` timestamp field (already on the interface) is cleaner.

---

## 4. Pre-flight

Run from the ionstarter project root (`/projects/ionstarter/`):

```bash
# 1. Verify the project builds cleanly
cd /projects/ionstarter && npm run build

# 2. Verify tests pass
cd /projects/ionstarter && npm run test:ci

# 3. Verify Task 3 outputs exist (rating page + saveResponse flow)
ls src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts
ls src/app/domains/check-in/services/check-in/check-in.service.ts
ls src/app/domains/check-in/services/check-in-rating-page/check-in-rating-page.service.ts

# 4. Verify the CheckInSession interface has expiredAt field
grep "expiredAt" src/app/domains/check-in/interfaces/check-in.ts

# 5. Verify SQLite schema already has expired_at column
grep "expired_at" src/app/domains/check-in/services/check-in-sqlite/check-in-sqlite.service.ts

# 6. Verify APP_INITIALIZER or bootstrap hook mechanism exists
grep -r "APP_INITIALIZER\|provideAppInitializer" src/app/ || echo "No initializer yet — will create one"
```

---

## 5. Files

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/domains/check-in/constants/expiry.ts` | `SESSION_EXPIRY_MS` constant (48h in milliseconds) |
| 2 | `src/app/domains/check-in/services/check-in-expiry/check-in-expiry.service.ts` | Expiry logic: `expireStale()`, `isExpired()`, `getActiveDraft()` |
| 3 | `src/app/domains/check-in/services/check-in-expiry/check-in-expiry.service.spec.ts` | Unit tests for expiry service |
| 4 | `src/app/domains/check-in/providers/check-in-initializer.ts` | `provideCheckInInitializer()` — APP_INITIALIZER that calls `expireStale()` on bootstrap |

### To Modify

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts` | On init, load saved responses for the session and pre-fill the `scores` signal |
| 2 | `src/app/domains/check-in/services/check-in/check-in.service.ts` | Add `getActiveSessions()` method (unsubmitted + unexpired) |
| 3 | `src/app/domains/check-in/services/index.ts` | Add barrel export for `check-in-expiry` service |
| 4 | `src/app/domains/check-in/check-in.routes.ts` or `src/app/app.config.ts` | Register `provideCheckInInitializer()` |

### To Leave Alone

- `src/app/domains/check-in/services/check-in-sqlite/check-in-sqlite.service.ts` — Already has `INSERT OR REPLACE` + `expired_at` column
- `src/app/domains/check-in/services/check-in-local-storage/check-in-local-storage.service.ts` — Already has upsert logic
- `src/app/domains/check-in/interfaces/check-in.ts` — `expiredAt?: string` already present
- `src/app/domains/check-in/services/check-in-rating-page/check-in-rating-page.service.ts` — Already has `saveResponse` mutation + `getResponses` query

---

## 6. Implementation Steps

### Step 1: Create the expiry constant

**Action**: Define the 48-hour expiry window as a typed constant.

**File**: `src/app/domains/check-in/constants/expiry.ts`

```typescript
/** Sessions older than this are considered expired (48 hours). */
export const SESSION_EXPIRY_MS = 48 * 60 * 60 * 1000; // 172_800_000
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 2: Create the check-in-expiry service

**Action**: Build a service that encapsulates all expiry logic. It reads all sessions, checks timestamps, and marks expired ones.

**File**: `src/app/domains/check-in/services/check-in-expiry/check-in-expiry.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { SESSION_EXPIRY_MS } from '../../constants/expiry';
import { CheckInSession } from '../../interfaces';
import { CheckInService } from '../check-in/check-in.service';

@Injectable({
  providedIn: 'root',
})
export class CheckInExpiryService {
  constructor(private readonly checkInService: CheckInService) {}

  /**
   * Check if a session has expired (created more than 48h ago and not submitted).
   */
  public isExpired(session: CheckInSession, now: Date = new Date()): boolean {
    if (session.submitted) {
      return false;
    }
    if (session.expiredAt) {
      return true;
    }
    const createdAt = new Date(session.createdAt).getTime();
    return now.getTime() - createdAt > SESSION_EXPIRY_MS;
  }

  /**
   * Scan all sessions. Mark any unsubmitted session older than 48h as expired.
   * Returns the number of sessions that were expired.
   */
  public async expireStale(): Promise<number> {
    const sessions = await this.checkInService.getSessions();
    const now = new Date();
    let expiredCount = 0;

    for (const session of sessions) {
      if (!session.submitted && !session.expiredAt && this.isExpired(session, now)) {
        await this.checkInService.markExpired(session.id);
        expiredCount++;
      }
    }

    return expiredCount;
  }

  /**
   * Get the most recent active (non-submitted, non-expired) session, if any.
   * Returns null if no active draft exists.
   */
  public async getActiveDraft(): Promise<CheckInSession | null> {
    const sessions = await this.checkInService.getSessions();
    const now = new Date();

    const activeDrafts = sessions
      .filter(s => !s.submitted && !s.expiredAt && !this.isExpired(s, now))
      .sort(
        (a, b) =>
          new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
      );

    return activeDrafts[0] ?? null;
  }

  /**
   * Delete all expired sessions and their responses.
   * Call after expireStale() to reclaim storage.
   */
  public async cleanupExpired(): Promise<number> {
    const sessions = await this.checkInService.getSessions();
    let deletedCount = 0;

    for (const session of sessions) {
      if (session.expiredAt) {
        await this.checkInService.deleteSession(session.id);
        deletedCount++;
      }
    }

    return deletedCount;
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 3: Add `markExpired` method to CheckInService

**Action**: Add a `markExpired` method that sets the `expiredAt` timestamp on a session.

**File**: `src/app/domains/check-in/services/check-in/check-in.service.ts`

Add after the existing `markComplete` method:

```typescript
  public async markExpired(id: CheckInSession['id']): Promise<void> {
    const isWeb = Capacitor.getPlatform() === 'web';
    const expiredAt = new Date().toISOString();
    if (isWeb) {
      await this.checkInLocalStorageService.updateSession(id, { expiredAt });
    } else {
      await this.checkInSqliteService.updateSession(id, { expiredAt });
    }
  }

  public async getActiveSessions(): Promise<CheckInSession[]> {
    const sessions = await this.getSessions();
    return sessions.filter(s => !s.submitted && !s.expiredAt);
  }
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 4: Create the APP_INITIALIZER provider

**Action**: Create a provider function that runs `expireStale()` + `cleanupExpired()` during app bootstrap.

**File**: `src/app/domains/check-in/providers/check-in-initializer.ts`

```typescript
import { APP_INITIALIZER, Provider } from '@angular/core';
import { CheckInExpiryService } from '../services/check-in-expiry/check-in-expiry.service';

function checkInInitializerFactory(
  expiryService: CheckInExpiryService,
): () => Promise<void> {
  return async () => {
    await expiryService.expireStale();
    await expiryService.cleanupExpired();
  };
}

export function provideCheckInInitializer(): Provider {
  return {
    provide: APP_INITIALIZER,
    useFactory: checkInInitializerFactory,
    deps: [CheckInExpiryService],
    multi: true,
  };
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 5: Register the initializer in app config

**Action**: Import and register `provideCheckInInitializer()` in the app's provider array.

**File**: `src/app/app.config.ts` (or wherever `provideZoneChangeDetection`, `provideRouter`, etc. are configured)

Add to the `providers` array:

```typescript
import { provideCheckInInitializer } from './domains/check-in/providers/check-in-initializer';

// Inside the providers array:
provideCheckInInitializer(),
```

**Verify**:

```bash
cd /projects/ionstarter && npm run build
```

---

### Step 6: Update the rating page to pre-fill saved responses on init

**Action**: Modify the `CheckInRatingPage` constructor (or use `ngOnInit`) to load existing responses for the session and populate the `scores` signal. Task 3's implementation already has a `loadExistingResponses()` method — ensure it works correctly by calling `checkInService.getResponses(sessionId)` and mapping results into the signal.

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts`

Replace or enhance the existing `loadExistingResponses` method:

```typescript
  private async loadExistingResponses(): Promise<void> {
    try {
      const responses = await this.checkInService.getResponses(this.sessionId);
      if (responses.length > 0) {
        const map = new Map<number, number>();
        for (const r of responses) {
          map.set(r.questionIndex, r.score);
        }
        this.scores.set(map);
      }
    } catch {
      // Silently fail — user will just see empty circles
    }
  }
```

Ensure the component injects `CheckInService` directly (or accesses it through the page service) and calls `loadExistingResponses()` during construction or `ngOnInit`:

```typescript
import { CheckInService } from '../../services/check-in/check-in.service';
import { CheckInExpiryService } from '../../services/check-in-expiry/check-in-expiry.service';

// In the constructor:
constructor(
  private readonly activatedRoute: ActivatedRoute,
  private readonly checkInRatingPageService: CheckInRatingPageService,
  private readonly checkInService: CheckInService,
  private readonly checkInExpiryService: CheckInExpiryService,
) {
  this.sessionId = this.activatedRoute.snapshot.params['sessionId'];
  this.responsesResult = this.checkInRatingPageService.getResponses(this.sessionId).result;
  this.saveResponseMutation = this.checkInRatingPageService.saveResponse();

  this.initializeSession();
}

private async initializeSession(): Promise<void> {
  // Check if session is expired before loading
  const session = await this.checkInService.getSession(this.sessionId);
  if (session && this.checkInExpiryService.isExpired(session)) {
    // Navigate away — session is stale
    await this.checkInRatingPageService.navigateBack();
    return;
  }

  await this.loadExistingResponses();
}
```

**Key behavior**: On each tap circle selection, `onScoreChange` already calls `saveResponseMutation.mutate(...)` which persists immediately. This is the auto-save — no additional logic needed for the save path.

**Verify**:

```bash
cd /projects/ionstarter && npm run build
```

---

### Step 7: Update the services barrel export

**Action**: Add the expiry service to the barrel.

**File**: `src/app/domains/check-in/services/index.ts`

Append:

```typescript
export * from './check-in-expiry/check-in-expiry.service';
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

## 7. Tests

### Test 1: `check-in-expiry.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in-expiry/check-in-expiry.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { CheckInExpiryService } from './check-in-expiry.service';
import { CheckInService } from '../check-in/check-in.service';
import { CheckInSession } from '../../interfaces';
import { SESSION_EXPIRY_MS } from '../../constants/expiry';

describe('CheckInExpiryService', () => {
  let service: CheckInExpiryService;
  let checkInSpy: jasmine.SpyObj<CheckInService>;

  function makeSession(overrides: Partial<CheckInSession> = {}): CheckInSession {
    return {
      id: 'sess-1',
      createdAt: new Date().toISOString(),
      partner: 'A',
      submitted: false,
      ...overrides,
    };
  }

  beforeEach(() => {
    checkInSpy = jasmine.createSpyObj('CheckInService', [
      'getSessions',
      'getSession',
      'getResponses',
      'markExpired',
      'deleteSession',
    ]);
    checkInSpy.getSessions.and.resolveTo([]);
    checkInSpy.markExpired.and.resolveTo();
    checkInSpy.deleteSession.and.resolveTo();

    TestBed.configureTestingModule({
      providers: [
        CheckInExpiryService,
        { provide: CheckInService, useValue: checkInSpy },
      ],
    });
    service = TestBed.inject(CheckInExpiryService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('isExpired', () => {
    it('should return false for a session created less than 48h ago', () => {
      const session = makeSession({
        createdAt: new Date(Date.now() - 1000 * 60 * 60).toISOString(), // 1 hour ago
      });
      expect(service.isExpired(session)).toBe(false);
    });

    it('should return true for a session created more than 48h ago', () => {
      const session = makeSession({
        createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 1000).toISOString(),
      });
      expect(service.isExpired(session)).toBe(true);
    });

    it('should return false for a submitted session regardless of age', () => {
      const session = makeSession({
        createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 1000).toISOString(),
        submitted: true,
      });
      expect(service.isExpired(session)).toBe(false);
    });

    it('should return true for a session already marked with expiredAt', () => {
      const session = makeSession({
        expiredAt: new Date().toISOString(),
      });
      expect(service.isExpired(session)).toBe(true);
    });

    it('should return false for a session created exactly at the boundary', () => {
      const session = makeSession({
        createdAt: new Date(Date.now() - SESSION_EXPIRY_MS).toISOString(),
      });
      // Exactly at boundary — not expired (need to exceed, not equal)
      expect(service.isExpired(session)).toBe(false);
    });

    it('should accept a custom now parameter for testing', () => {
      const created = new Date('2024-01-01T00:00:00Z');
      const session = makeSession({ createdAt: created.toISOString() });
      const within48h = new Date('2024-01-02T00:00:00Z');
      const after48h = new Date('2024-01-03T01:00:00Z');

      expect(service.isExpired(session, within48h)).toBe(false);
      expect(service.isExpired(session, after48h)).toBe(true);
    });
  });

  describe('expireStale', () => {
    it('should mark stale sessions as expired', async () => {
      const staleSession = makeSession({
        id: 'stale-1',
        createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 60_000).toISOString(),
      });
      checkInSpy.getSessions.and.resolveTo([staleSession]);

      const count = await service.expireStale();

      expect(count).toBe(1);
      expect(checkInSpy.markExpired).toHaveBeenCalledWith('stale-1');
    });

    it('should not mark fresh sessions', async () => {
      const freshSession = makeSession({
        id: 'fresh-1',
        createdAt: new Date().toISOString(),
      });
      checkInSpy.getSessions.and.resolveTo([freshSession]);

      const count = await service.expireStale();

      expect(count).toBe(0);
      expect(checkInSpy.markExpired).not.toHaveBeenCalled();
    });

    it('should not mark already-expired sessions again', async () => {
      const alreadyExpired = makeSession({
        id: 'expired-1',
        createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 60_000).toISOString(),
        expiredAt: new Date().toISOString(),
      });
      checkInSpy.getSessions.and.resolveTo([alreadyExpired]);

      const count = await service.expireStale();

      expect(count).toBe(0);
      expect(checkInSpy.markExpired).not.toHaveBeenCalled();
    });

    it('should not mark submitted sessions', async () => {
      const submittedSession = makeSession({
        id: 'submitted-1',
        createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 60_000).toISOString(),
        submitted: true,
      });
      checkInSpy.getSessions.and.resolveTo([submittedSession]);

      const count = await service.expireStale();

      expect(count).toBe(0);
      expect(checkInSpy.markExpired).not.toHaveBeenCalled();
    });

    it('should handle multiple sessions correctly', async () => {
      const sessions = [
        makeSession({ id: 'stale-1', createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 60_000).toISOString() }),
        makeSession({ id: 'fresh-1', createdAt: new Date().toISOString() }),
        makeSession({ id: 'stale-2', createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 120_000).toISOString() }),
      ];
      checkInSpy.getSessions.and.resolveTo(sessions);

      const count = await service.expireStale();

      expect(count).toBe(2);
      expect(checkInSpy.markExpired).toHaveBeenCalledWith('stale-1');
      expect(checkInSpy.markExpired).toHaveBeenCalledWith('stale-2');
    });
  });

  describe('getActiveDraft', () => {
    it('should return null when no sessions exist', async () => {
      checkInSpy.getSessions.and.resolveTo([]);

      const result = await service.getActiveDraft();

      expect(result).toBeNull();
    });

    it('should return null when all sessions are submitted', async () => {
      checkInSpy.getSessions.and.resolveTo([
        makeSession({ submitted: true }),
      ]);

      const result = await service.getActiveDraft();

      expect(result).toBeNull();
    });

    it('should return null when all sessions are expired', async () => {
      checkInSpy.getSessions.and.resolveTo([
        makeSession({
          createdAt: new Date(Date.now() - SESSION_EXPIRY_MS - 60_000).toISOString(),
        }),
      ]);

      const result = await service.getActiveDraft();

      expect(result).toBeNull();
    });

    it('should return the most recent active draft', async () => {
      const older = makeSession({
        id: 'older',
        createdAt: new Date(Date.now() - 60_000).toISOString(),
      });
      const newer = makeSession({
        id: 'newer',
        createdAt: new Date().toISOString(),
      });
      checkInSpy.getSessions.and.resolveTo([older, newer]);

      const result = await service.getActiveDraft();

      expect(result?.id).toBe('newer');
    });

    it('should exclude sessions with expiredAt set', async () => {
      const expired = makeSession({
        id: 'expired',
        createdAt: new Date().toISOString(),
        expiredAt: new Date().toISOString(),
      });
      const active = makeSession({
        id: 'active',
        createdAt: new Date().toISOString(),
      });
      checkInSpy.getSessions.and.resolveTo([expired, active]);

      const result = await service.getActiveDraft();

      expect(result?.id).toBe('active');
    });
  });

  describe('cleanupExpired', () => {
    it('should delete sessions that have expiredAt set', async () => {
      const expired = makeSession({
        id: 'expired-1',
        expiredAt: new Date().toISOString(),
      });
      checkInSpy.getSessions.and.resolveTo([expired]);

      const count = await service.cleanupExpired();

      expect(count).toBe(1);
      expect(checkInSpy.deleteSession).toHaveBeenCalledWith('expired-1');
    });

    it('should not delete active or submitted sessions', async () => {
      const active = makeSession({ id: 'active-1' });
      const submitted = makeSession({ id: 'submitted-1', submitted: true });
      checkInSpy.getSessions.and.resolveTo([active, submitted]);

      const count = await service.cleanupExpired();

      expect(count).toBe(0);
      expect(checkInSpy.deleteSession).not.toHaveBeenCalled();
    });

    it('should return the count of deleted sessions', async () => {
      const sessions = [
        makeSession({ id: 'exp-1', expiredAt: '2024-01-01T00:00:00Z' }),
        makeSession({ id: 'exp-2', expiredAt: '2024-01-02T00:00:00Z' }),
        makeSession({ id: 'active-1' }),
      ];
      checkInSpy.getSessions.and.resolveTo(sessions);

      const count = await service.cleanupExpired();

      expect(count).toBe(2);
    });
  });
});
```

### Test 2: `check-in.service.spec.ts` additions

Add tests for the new `markExpired` and `getActiveSessions` methods to the existing service spec (or create if not present):

**File**: `src/app/domains/check-in/services/check-in/check-in.service.spec.ts`

```typescript
// Add these tests to the existing describe block:

describe('markExpired', () => {
  it('should call updateSession with expiredAt timestamp', async () => {
    // Spy on the localStorage/sqlite service updateSession
    await service.markExpired('session-123');

    // Verify the storage layer received the call
    expect(storageSpy.updateSession).toHaveBeenCalledWith(
      'session-123',
      jasmine.objectContaining({ expiredAt: jasmine.any(String) }),
    );
  });
});

describe('getActiveSessions', () => {
  it('should filter out submitted and expired sessions', async () => {
    storageSpy.selectSessions.and.resolveTo([
      { id: '1', createdAt: new Date().toISOString(), partner: 'A', submitted: false },
      { id: '2', createdAt: new Date().toISOString(), partner: 'B', submitted: true },
      { id: '3', createdAt: new Date().toISOString(), partner: 'A', submitted: false, expiredAt: new Date().toISOString() },
    ]);

    const active = await service.getActiveSessions();

    expect(active.length).toBe(1);
    expect(active[0].id).toBe('1');
  });
});
```

### Test 3: `check-in-rating.page.spec.ts` additions

Add tests verifying the pre-fill behavior:

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.spec.ts`

```typescript
// Add to existing describe block:

it('should pre-fill scores from persisted responses on init', async () => {
  // Setup: mock getResponses to return saved data
  checkInSpy.getResponses.and.resolveTo([
    { id: 'r1', sessionId: 'test-session-1', questionIndex: 0, score: 7, answeredAt: new Date().toISOString() },
    { id: 'r2', sessionId: 'test-session-1', questionIndex: 3, score: 4, answeredAt: new Date().toISOString() },
  ]);

  // Trigger init
  await component['loadExistingResponses']();

  expect(component.getScore(0)).toBe(7);
  expect(component.getScore(3)).toBe(4);
  expect(component.ratedCount()).toBe(2);
});

it('should show empty circles when no persisted responses exist', async () => {
  checkInSpy.getResponses.and.resolveTo([]);

  await component['loadExistingResponses']();

  expect(component.ratedCount()).toBe(0);
});

it('should navigate back if session is expired', async () => {
  checkInSpy.getSession.and.resolveTo({
    id: 'test-session-1',
    createdAt: new Date(Date.now() - 49 * 60 * 60 * 1000).toISOString(),
    partner: 'A',
    submitted: false,
  });

  await component['initializeSession']();

  expect(pageServiceSpy.navigateBack).toHaveBeenCalled();
});
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(check-in): add session expiry constant (48h)` | `constants/expiry.ts` |
| 2 | `feat(check-in): add markExpired + getActiveSessions to check-in service` | `services/check-in/check-in.service.ts` |
| 3 | `feat(check-in): add check-in-expiry service with stale detection + cleanup` | `services/check-in-expiry/check-in-expiry.service.ts`, `.spec.ts`, `services/index.ts` |
| 4 | `feat(check-in): add APP_INITIALIZER for session expiry on bootstrap` | `providers/check-in-initializer.ts`, `app.config.ts` |
| 5 | `feat(check-in): pre-fill rating page from persisted responses + expiry guard` | `pages/check-in-rating/check-in-rating.page.ts`, `.spec.ts` |

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
#   - CheckInExpiryService: 14 specs
#   - CheckInService (markExpired + getActiveSessions): 2+ specs
#   - CheckInRatingPage (pre-fill + expiry guard): 3+ specs

# 5. Manual smoke test
ionic serve &
# Test 1: Start a check-in, tap 3 circles, kill the browser tab
# Reopen → navigate to check-in → verify the 3 circles are pre-filled
#
# Test 2: Manually set a session createdAt to >48h ago in devtools:
#   localStorage → check-in-sessions → edit createdAt
# Reload app → verify the session is no longer in active list
#
# Test 3: Start fresh check-in → rate all 10 → verify all persist across reload

# 6. Verify file structure
ls src/app/domains/check-in/constants/expiry.ts
ls src/app/domains/check-in/services/check-in-expiry/
ls src/app/domains/check-in/providers/check-in-initializer.ts
```

---

## 10. Rollback

Changes touch one new service, one new constant, one new provider, and modifications to two existing files. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -5  # find the 5 commit SHAs
git revert <sha5> <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~5

# Option 3: Manual cleanup
rm -f src/app/domains/check-in/constants/expiry.ts
rm -rf src/app/domains/check-in/services/check-in-expiry/
rm -f src/app/domains/check-in/providers/check-in-initializer.ts
# Revert modifications:
git checkout -- src/app/domains/check-in/services/check-in/check-in.service.ts
git checkout -- src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts
git checkout -- src/app/domains/check-in/services/index.ts
git checkout -- src/app/app.config.ts
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Expiry window** | Executor may use a different constant name or place it inline. The 48h value must stay at 48h. |
| **APP_INITIALIZER vs inject in root component** | Executor may call `expireStale()` from `AppComponent.ngOnInit` or an `APP_INITIALIZER`. Both achieve bootstrap-time expiry. |
| **Cleanup strategy** | Executor may hard-delete expired sessions immediately in `expireStale()` instead of a two-step mark-then-delete. Both are valid. |
| **Signal-based or effect-based restore** | Executor may use `effect()` watching TanStack query state to pre-fill scores instead of an imperative `loadExistingResponses()` call. |
| **Expiry guard in rating page** | Executor may use a route guard (`canActivate`) that checks session validity before entering the rating page instead of checking inside the component. |
| **Service location** | Executor may put expiry logic directly in `CheckInService` instead of a separate `CheckInExpiryService`. Separation is preferred but not mandatory. |
| **provideCheckInInitializer pattern** | Executor may use `provideAppInitializer(() => inject(CheckInExpiryService).expireStale())` (Angular 19+ functional initializer) instead of the class-based factory. |
| **Test count** | Executor may write fewer tests if coverage of key paths (isExpired boundary, expireStale marks correct sessions, pre-fill works) is adequate. |

---

## 12. Out of Scope

- **Session creation / partner selection** -- Task 2 (already done)
- **Rating UI / tap circles** -- Task 3 (already done)
- **Submit button / submission flow** -- Task 5
- **Quality score computation** -- Task 6
- **Push notification for expiring sessions** -- Not in spec
- **Server-side session management** -- No backend yet
- **Offline queue / retry for failed saves** -- Future concern
- **Migration of existing sessions that predate the expiredAt field** -- Not needed; field is optional and defaults to undefined (not expired)
- **User-facing "session expired" toast or modal** -- Nice-to-have but not required; silent expiry + redirect is sufficient
- **Multi-device session sync** -- No backend, no sync
