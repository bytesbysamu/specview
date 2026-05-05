# Task 2: Partner Selection + Session Creation Screen

**Purpose**: Build the entry point for the Relationship Check-In feature at `/checkin`. This is the session management hub: it shows active session status or invites the user to start a new check-in, presents a Partner A / Partner B selection, creates a session via the data service from Task 1, and routes the selected partner into the rating flow (Task 3). It also displays completed session history as tappable cards.

**Effort**: 1 day

**Dependencies**: Task 1 (SQLite schema + migration + data service) -- `CheckinDataService` must exist and expose `createSession()`, `getSession()`, `bothSubmitted()`, `getScoresForSession()`.

**Parallel With**: Task 3 (Question Rating Interface) -- both depend only on Task 1. Task 2 builds the session entry point; Task 3 builds the rating flow. They share no components and connect only via router navigation.

**Blocks**: Task 4 (Submission Lock + Results) -- needs session creation (this task) and submitted responses (Task 3) to function.

**Related**:
- [Solution Architecture](./architecture.md) -- Task 2 component design, privacy model, feature guard pattern
- [Epic](./epic.md) -- Task scope, success criteria, non-goals

---

## 1. Context + Trade-offs

The check-in feature is a lazy-loaded route inside the Bubls shell. The shell at `/projects/bubls/src/app/shell/shell-layout.component.ts` renders a tab bar driven by `FEATURE_ROUTES` at `/projects/bubls/src/app/shell/feature-registry.ts`. Currently three tabs exist: Photoshoot, Picks, Text. This task adds a fourth tab for Check-in and registers the `/checkin` route with child routes for the rating and results screens that downstream tasks will build.

The data service is already shipped as `CheckinDataService` at `/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts`. It exposes `createSession()` (returns session ID string), `getSession(id)`, `submitScores()`, `bothSubmitted()`, and `getScoresForSession()`. The model at `/projects/bubls/src/app/features/checkin/checkin.model.ts` defines `Partner` (`'A' | 'B'`), `SessionStatus`, `CheckinSession`, and the ten questions with four quality mappings. The public API is re-exported from `/projects/bubls/src/app/features/checkin/index.ts`.

The app routes at `/projects/bubls/src/app/app.routes.ts` use lazy-loaded components inside a shell wrapper with `canActivate: [onboardingGuard]`. Each route loads a standalone page component. The checkin route follows this pattern but needs child routes for the multi-screen flow (home, rate, waiting, results, trends).

**Trade-offs considered**:

- **Tab bar entry vs. hidden route** -- tab bar entry wins. The architecture specifies `/checkin` as a first-class lazy route. Hiding it behind a menu would reduce discoverability for a feature designed for repeated use. A fourth tab is acceptable given the three existing tabs do not crowd the bar.
- **Ionicons icon choice** -- use `heart-outline` for the check-in tab. The feature is about relationship health. Alternatives (`chatbubbles-outline`, `pulse-outline`) are less immediately evocative. The icon must be registered in `ShellLayoutComponent` constructor via `addIcons()`.
- **Partner selection as modal vs. inline** -- inline selection wins. The architecture mentions "Modal or inline selector" but a modal adds a dismiss UX and an extra layer of state. Inline partner buttons on the main screen are one tap to start -- zero friction. The partner selection section simply hides once a session is active.
- **Partner identity persistence** -- NOT persisted across app restarts. Architecture specifies: "Selected partner stored in session signal (not persisted -- each rating flow starts with selection)." This is deliberate: it forces conscious identity selection each time, preventing Partner A from accidentally rating as Partner B.
- **Session list rendering** -- completed sessions shown as simple date-labeled cards below the active session area. Tapping a completed session navigates to results (Task 4 builds the results view; this task provides the navigation shell and placeholder route).
- **Active session detection** -- the service does not have a `getActiveSession()` method. Instead, query via `getSession()` combined with a locally stored session ID. On session creation, store the ID in a component signal. On page load, attempt to reload the last-known session ID from a lightweight persistence mechanism (Capacitor Preferences or a simple localStorage key). If the session is still `'active'`, resume the flow.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                       # Flag any unrelated M/?? entries
git diff HEAD -- src/app/shell/ src/app/app.routes.ts src/app/features/checkin/
npm test -- --watch=false --browsers=ChromeHeadless              # Baseline FE suite; record pass count
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting. The shell, routes, and checkin feature directory must be clean at HEAD.

**Baseline recorded**: write the pass count here after running (format: `N/N passing`). This is the `N` referenced in section 7.

**Verify Task 1 deliverables exist**:
```bash
ls src/app/features/checkin/checkin.model.ts        # Must exist: Partner type, CheckinSession, CHECKIN_QUESTIONS
ls src/app/features/checkin/services/checkin-data.service.ts  # Must exist: createSession(), getSession(), bothSubmitted()
ls src/app/features/checkin/index.ts                # Must exist: barrel exports
```

If any of these are missing, STOP. Task 1 is a hard dependency.

---

## 3. Files (Create / Modify / Leave Alone)

### To Create (new)

- `src/app/features/checkin/pages/checkin.page.ts` -- Entry point component at `/checkin`. Displays three states: (1) no active session with partner selection, (2) active session with partner not yet submitted (navigate to rate), (3) active session with partner already submitted (waiting state). Includes completed session history list.
- `src/app/features/checkin/pages/checkin.page.spec.ts` -- Unit tests for the page component: state transitions, session creation, partner selection, navigation, session history rendering.
- `src/app/features/checkin/components/partner-select.component.ts` -- Two large tap targets for Partner A / Partner B. Emits selected partner via output signal. Standalone, OnPush.
- `src/app/features/checkin/components/partner-select.component.spec.ts` -- Unit tests for partner selection: tap emits correct partner, visual selected state.
- `src/app/features/checkin/checkin.routes.ts` -- Child route config for the checkin feature: default path loads checkin page, `rate/:sessionId/:partner` is a placeholder route for Task 3, `results/:sessionId` is a placeholder for Task 4, `trends` is a placeholder for Task 5.

### To Modify (cite codebase context)

- `src/app/app.routes.ts` -- Add a `checkin` child route under the shell wrapper, lazy-loading `checkin.routes.ts`. Currently has `photoshoot`, `home`, and `text` routes inside the shell `children` array at line 19. Add `checkin` as a fourth entry using `loadChildren` to point at `checkin.routes.ts`.
- `src/app/shell/feature-registry.ts` -- Add a fourth entry to `FEATURE_ROUTES` for the checkin tab. Currently has three entries: `photoshoot`, `home`, `text` (lines 9-34). Add `{ path: 'checkin', label: 'Check-in', icon: 'heart-outline', featureKey: 'checkin', loadComponent: ... }`.
- `src/app/shell/shell-layout.component.ts` -- Import `heartOutline` from `ionicons/icons` and add it to the `addIcons()` call in the constructor (line 143). Currently registers `sparklesOutline`, `newspaperOutline`, `pencilOutline`.
- `src/app/features/checkin/index.ts` -- Add barrel exports for the new page component and routes if needed by consumers outside the feature.

### To Leave Alone

- `src/app/features/checkin/checkin.model.ts` -- No changes. All types needed (`Partner`, `CheckinSession`, `SessionStatus`) already defined.
- `src/app/features/checkin/services/checkin-data.service.ts` -- No changes. Consumed as-is via `inject()`.
- `src/app/features/checkin/services/checkin-data.service.spec.ts` -- No changes. Task 1 tests.
- `src/app/shared/sqlite/` -- No changes. SQLite infrastructure consumed transitively through the data service.
- `src/app/pages/` -- Existing pages untouched. Checkin pages live under `features/checkin/pages/` to keep the bounded context self-contained.
- `src/app/services/theme.service.ts` -- No changes. Dark theme inherited via CSS custom properties.
- `src/environments/` -- No changes needed for this task. Mock mode is handled inside the data service.
- `server/` -- No backend changes. This feature is local-only.

---

## 4. Implementation Steps

### Step 1: Read existing infrastructure and confirm conventions

**Action**: Inspect the files you will modify to confirm current shape. Verify the shell tab bar, feature registry, app routes, and the checkin data service API.

**Files**:
- `/projects/bubls/src/app/shell/feature-registry.ts` -- confirm `FEATURE_ROUTES` array shape and current entries
- `/projects/bubls/src/app/shell/shell-layout.component.ts` -- confirm `addIcons()` call in constructor, confirm ionicons import pattern
- `/projects/bubls/src/app/app.routes.ts` -- confirm shell `children` array structure and lazy-loading pattern
- `/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts` -- confirm `createSession()` returns `Promise<string>`, `getSession(id)` returns `Promise<CheckinSession | null>`, `bothSubmitted(sessionId)` returns `Promise<boolean>`
- `/projects/bubls/src/app/features/checkin/checkin.model.ts` -- confirm `Partner`, `CheckinSession`, `SessionStatus` types

**Verify**: all files exist and match the shapes described. If the data service API differs from what's described here, adjust the page component calls accordingly and log as deviation.

### Step 2: Register the checkin icon in the shell

**Action**: Import `heartOutline` from `ionicons/icons` and add it to the `addIcons()` call in the `ShellLayoutComponent` constructor.

**File**: `src/app/shell/shell-layout.component.ts`

**Pattern**:
```typescript
// Line 3 — add heartOutline to the import
import { heartOutline, newspaperOutline, pencilOutline, sparklesOutline } from 'ionicons/icons';

// Line 143 — add heartOutline to addIcons
addIcons({ sparklesOutline, newspaperOutline, pencilOutline, heartOutline });
```

**Verify**: `npx tsc --noEmit` clean. No visual change yet (tab not registered).

### Step 3: Add checkin to the feature registry

**Action**: Add a fourth entry to `FEATURE_ROUTES` for the checkin tab.

**File**: `src/app/shell/feature-registry.ts`

**Pattern**:
```typescript
export const FEATURE_ROUTES: FeatureRoute[] = [
  // ... existing 3 entries ...
  {
    path: 'checkin',
    label: 'Check-in',
    icon: 'heart-outline',
    featureKey: 'checkin',
    loadComponent: () =>
      import('../features/checkin/pages/checkin.page').then((m) => m.CheckinPage),
  },
];
```

**Verify**: `npx tsc --noEmit` will fail because `CheckinPage` doesn't exist yet. This is expected -- it's resolved in Step 5.

### Step 4: Add the checkin route to app routes

**Action**: Add a `checkin` path with `loadChildren` pointing to the checkin routes file. This goes inside the shell `children` array alongside `home`, `photoshoot`, and `text`.

**File**: `src/app/app.routes.ts`

**Pattern**:
```typescript
children: [
  { path: '', redirectTo: 'photoshoot', pathMatch: 'full' },
  // ... existing routes ...
  {
    path: 'checkin',
    loadChildren: () =>
      import('./features/checkin/checkin.routes').then((m) => m.CHECKIN_ROUTES),
  },
],
```

**Verify**: `npx tsc --noEmit` will fail because the routes file doesn't exist yet. Resolved in Step 5.

### Step 5: Create the checkin routes file

**Action**: Define the child route configuration for the checkin feature. The default path loads the checkin page. Child paths for `rate`, `results`, and `trends` are defined as placeholder routes that downstream tasks will wire up.

**File**: `src/app/features/checkin/checkin.routes.ts` (new)

**Pattern**:
```typescript
import { Routes } from '@angular/router';

export const CHECKIN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/checkin.page').then((m) => m.CheckinPage),
  },
  {
    path: 'rate/:sessionId/:partner',
    loadComponent: () =>
      import('./pages/checkin.page').then((m) => m.CheckinPage),
    // TODO Task 3: replace with CheckinRateComponent
  },
  {
    path: 'results/:sessionId',
    loadComponent: () =>
      import('./pages/checkin.page').then((m) => m.CheckinPage),
    // TODO Task 4: replace with CheckinResultsComponent
  },
  {
    path: 'trends',
    loadComponent: () =>
      import('./pages/checkin.page').then((m) => m.CheckinPage),
    // TODO Task 5: replace with CheckinTrendsComponent
  },
];
```

**Verify**: routes compile once the page component exists (next step).

### Step 6: Create the partner-select component

**Action**: Build a standalone, OnPush component that renders two large tap targets for Partner A and Partner B. On tap, emits the selected partner via an output signal. Visual design follows the dark-theme Bubls aesthetic: large circular or rounded-rect buttons with distinct labels, accent-colored active state.

**File**: `src/app/features/checkin/components/partner-select.component.ts` (new)

**Pattern**:
```typescript
import {
  ChangeDetectionStrategy,
  Component,
  output,
} from '@angular/core';
import type { Partner } from '../checkin.model';

@Component({
  selector: 'app-partner-select',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="partner-select" data-test="partner-select">
      <h2 class="prompt">Who's rating?</h2>
      <div class="buttons">
        <button
          class="partner-btn"
          data-test="partner-btn-A"
          (click)="partnerSelected.emit('A')"
        >
          <span class="partner-label">Partner A</span>
        </button>
        <button
          class="partner-btn"
          data-test="partner-btn-B"
          (click)="partnerSelected.emit('B')"
        >
          <span class="partner-label">Partner B</span>
        </button>
      </div>
    </div>
  `,
  styles: `
    :host { display: block; }

    .partner-select {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--sp-6, 24px);
      padding: var(--sp-8, 32px) var(--sp-4, 16px);
    }

    .prompt {
      font-family: var(--font-display);
      font-size: 24px;
      font-weight: 500;
      letter-spacing: -0.015em;
      color: var(--text-primary);
      margin: 0;
    }

    .buttons {
      display: flex;
      gap: var(--sp-4, 16px);
      width: 100%;
      max-width: 320px;
    }

    .partner-btn {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: var(--sp-6, 24px) var(--sp-4, 16px);
      border-radius: var(--r-lg, 16px);
      border: 2px solid var(--hairline);
      background: var(--surface);
      cursor: pointer;
      transition:
        background-color 0.15s ease,
        border-color 0.15s ease,
        transform 0.1s ease;
      -webkit-tap-highlight-color: transparent;
    }

    .partner-btn:active {
      transform: scale(0.96);
      background: var(--accent-warm-tint);
      border-color: var(--accent-warm);
    }

    .partner-label {
      font-family: var(--font-body);
      font-size: 18px;
      font-weight: 600;
      color: var(--text-primary);
    }
  `,
})
export class PartnerSelectComponent {
  readonly partnerSelected = output<Partner>();
}
```

**Key details**:
- `data-test="partner-btn-A"` and `data-test="partner-btn-B"` for test targeting.
- No internal state -- the parent handles what happens after selection.
- CSS uses the existing Bubls design token custom properties (`--surface`, `--hairline`, `--accent-warm`, `--font-display`, etc.) from `src/app/styles/tokens.scss`.

**Verify**: `npx tsc --noEmit` clean. Component has zero imports from services or shared modules.

### Step 7: Create the checkin page component

**Action**: Build the main check-in page. This is the hub that displays three states: (1) empty/no session -- show partner selection, (2) active session, current partner not submitted -- navigate to rating, (3) active session, current partner submitted -- show waiting state. Below the active area, show a list of completed sessions.

**File**: `src/app/features/checkin/pages/checkin.page.ts` (new)

**Pattern**:
```typescript
import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  inject,
  signal,
  computed,
} from '@angular/core';
import { Router } from '@angular/router';
import { IonContent } from '@ionic/angular/standalone';
import { DatePipe } from '@angular/common';

import { CheckinDataService } from '../services/checkin-data.service';
import { PartnerSelectComponent } from '../components/partner-select.component';
import type { Partner, CheckinSession } from '../checkin.model';

type PageState = 'loading' | 'no-session' | 'awaiting-partner' | 'ready-to-rate';

@Component({
  selector: 'app-checkin',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IonContent, PartnerSelectComponent, DatePipe],
  template: `
    <ion-content [fullscreen]="true" class="checkin-content">
      <div class="page-wrapper" data-test="checkin-page">

        <header class="page-header">
          <h1 class="page-title">Check-in</h1>
        </header>

        @if (pageState() === 'loading') {
          <div class="state-card" data-test="checkin-loading" aria-busy="true">
            <p class="state-text">Loading...</p>
          </div>
        }

        @if (pageState() === 'no-session') {
          <div class="start-section" data-test="checkin-start">
            @if (completedSessions().length === 0) {
              <div class="empty-card" data-test="empty-state-cta">
                <p class="empty-headline">Start your first check-in</p>
                <p class="empty-sub">Rate 10 questions independently, then compare.</p>
              </div>
            }
            <app-partner-select (partnerSelected)="onPartnerSelected($event)" />
          </div>
        }

        @if (pageState() === 'awaiting-partner') {
          <div class="state-card waiting-card" data-test="checkin-waiting">
            <div class="lock-icon" aria-hidden="true">&#x1F512;</div>
            <p class="state-headline">Waiting for partner</p>
            <p class="state-text">
              Hand the device to your partner so they can rate independently.
            </p>
            <button
              class="rate-btn"
              data-test="rate-as-other-btn"
              (click)="onRateAsOtherPartner()"
            >
              Rate as {{ otherPartner() }}
            </button>
          </div>
        }

        @if (pageState() === 'ready-to-rate') {
          <div class="state-card" data-test="checkin-resume">
            <p class="state-headline">Session in progress</p>
            <p class="state-text">Pick your name to continue rating.</p>
            <app-partner-select (partnerSelected)="onPartnerSelected($event)" />
          </div>
        }

        @if (completedSessions().length > 0) {
          <section class="history" data-test="session-history">
            <h2 class="section-title">Past Check-ins</h2>
            <div class="session-list">
              @for (session of completedSessions(); track session.id) {
                <button
                  class="session-card"
                  [attr.data-test]="'session-card-' + session.id"
                  (click)="onViewResults(session.id)"
                >
                  <span class="session-date">
                    {{ session.created_at | date:'mediumDate' }}
                  </span>
                  <span class="session-badge complete">Complete</span>
                </button>
              }
            </div>
          </section>
        }

      </div>
    </ion-content>
  `,
  styles: `
    :host {
      display: block;
      min-height: 100%;
      background: var(--page-bg);
      color: var(--text-primary);
    }

    :host ::ng-deep ion-content.checkin-content {
      --background: var(--page-bg);
    }

    .page-wrapper {
      padding: var(--sp-4, 16px) var(--page-pad, 16px)
               calc(var(--sp-8, 32px) + env(safe-area-inset-bottom));
    }

    .page-header {
      padding: var(--sp-6, 24px) 0 var(--sp-4, 16px);
    }

    .page-title {
      font-family: var(--font-display);
      font-size: 32px;
      font-weight: 500;
      letter-spacing: -0.02em;
      margin: 0;
    }

    /* ── State cards ── */
    .state-card {
      background: var(--surface);
      border-radius: var(--r-lg, 16px);
      padding: var(--sp-6, 24px);
      text-align: center;
      margin-bottom: var(--sp-4, 16px);
    }

    .state-headline {
      font-family: var(--font-display);
      font-size: 20px;
      font-weight: 500;
      margin: 0 0 var(--sp-2, 8px);
    }

    .state-text {
      color: var(--text-secondary);
      font-size: 14px;
      margin: 0;
    }

    /* ── Empty state ── */
    .empty-card {
      text-align: center;
      padding: var(--sp-4, 16px) 0;
    }

    .empty-headline {
      font-family: var(--font-display);
      font-size: 22px;
      font-weight: 500;
      margin: 0 0 var(--sp-2, 8px);
    }

    .empty-sub {
      color: var(--text-secondary);
      font-size: 14px;
      margin: 0;
    }

    /* ── Waiting card ── */
    .lock-icon {
      font-size: 36px;
      margin-bottom: var(--sp-3, 12px);
    }

    .waiting-card .rate-btn {
      margin-top: var(--sp-4, 16px);
      padding: var(--sp-3, 12px) var(--sp-6, 24px);
      border-radius: var(--r-pill, 999px);
      border: 2px solid var(--accent-warm);
      background: transparent;
      color: var(--accent-warm);
      font-family: var(--font-body);
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      transition: background-color 0.15s ease;
      -webkit-tap-highlight-color: transparent;
    }

    .waiting-card .rate-btn:active {
      background: var(--accent-warm-tint);
    }

    /* ── History ── */
    .history {
      margin-top: var(--sp-6, 24px);
      border-top: 1px solid var(--hairline);
      padding-top: var(--sp-4, 16px);
    }

    .section-title {
      font-family: var(--font-display);
      font-size: 18px;
      font-weight: 500;
      margin: 0 0 var(--sp-3, 12px);
    }

    .session-list {
      display: flex;
      flex-direction: column;
      gap: var(--sp-2, 8px);
    }

    .session-card {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--sp-3, 12px) var(--sp-4, 16px);
      background: var(--surface);
      border-radius: var(--r-md, 12px);
      border: 1px solid var(--hairline);
      cursor: pointer;
      transition: background-color 0.15s ease;
      -webkit-tap-highlight-color: transparent;
    }

    .session-card:active {
      background: var(--accent-warm-tint);
    }

    .session-date {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary);
    }

    .session-badge {
      font-size: 11px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: var(--r-pill, 999px);
    }

    .session-badge.complete {
      background: color-mix(in srgb, var(--success) 15%, transparent);
      color: var(--success);
    }
  `,
})
export class CheckinPage implements OnInit {
  private readonly router = inject(Router);
  private readonly checkinData = inject(CheckinDataService);

  // ── State ──────────────────────────────────────────────────────────
  readonly pageState = signal<PageState>('loading');
  readonly activeSession = signal<CheckinSession | null>(null);
  readonly completedSessions = signal<CheckinSession[]>([]);
  readonly lastSelectedPartner = signal<Partner | null>(null);

  readonly otherPartner = computed<string>(() => {
    const session = this.activeSession();
    if (!session) return 'Partner';
    // If A submitted, the other is B, and vice versa
    if (session.partner_a_submitted && !session.partner_b_submitted) return 'Partner B';
    if (session.partner_b_submitted && !session.partner_a_submitted) return 'Partner A';
    return 'Partner';
  });

  private static readonly SESSION_KEY = 'bubls.checkin.activeSessionId';

  // ── Lifecycle ──────────────────────────────────────────────────────

  async ngOnInit(): Promise<void> {
    await this.checkinData.init();
    await this.loadState();
  }

  // ── Actions ────────────────────────────────────────────────────────

  async onPartnerSelected(partner: Partner): Promise<void> {
    this.lastSelectedPartner.set(partner);

    let session = this.activeSession();

    if (!session) {
      // Create a new session
      const sessionId = await this.checkinData.createSession();
      session = await this.checkinData.getSession(sessionId);
      if (!session) return; // Safety: should not happen

      this.activeSession.set(session);
      this.persistSessionId(session.id);
    }

    // Check if this partner already submitted
    const submitted = partner === 'A'
      ? session.partner_a_submitted
      : session.partner_b_submitted;

    if (submitted) {
      // This partner already submitted -- show waiting state
      this.pageState.set('awaiting-partner');
      return;
    }

    // Navigate to rating flow
    await this.router.navigate(['/checkin', 'rate', session.id, partner]);
  }

  async onRateAsOtherPartner(): Promise<void> {
    const session = this.activeSession();
    if (!session) return;

    const partner: Partner =
      session.partner_a_submitted ? 'B' : 'A';
    await this.router.navigate(['/checkin', 'rate', session.id, partner]);
  }

  async onViewResults(sessionId: string): Promise<void> {
    await this.router.navigate(['/checkin', 'results', sessionId]);
  }

  // ── Private ────────────────────────────────────────────────────────

  private async loadState(): Promise<void> {
    // Load completed sessions for history list
    // Query all sessions and filter by status
    const storedId = this.getStoredSessionId();

    if (storedId) {
      const session = await this.checkinData.getSession(storedId);
      if (session && session.status === 'active') {
        this.activeSession.set(session);

        // Determine page state based on submission flags
        if (!session.partner_a_submitted && !session.partner_b_submitted) {
          // Neither submitted yet -- show partner selection
          this.pageState.set('ready-to-rate');
        } else if (session.partner_a_submitted && session.partner_b_submitted) {
          // Both submitted -- session should be complete, clear active
          this.activeSession.set(null);
          this.clearStoredSessionId();
          this.pageState.set('no-session');
        } else {
          // One partner submitted -- waiting for other
          this.pageState.set('awaiting-partner');
        }
      } else {
        // Session not found or not active -- clear stored ID
        this.clearStoredSessionId();
        this.pageState.set('no-session');
      }
    } else {
      this.pageState.set('no-session');
    }

    // Load completed sessions -- use getScoresForSession to check
    // which sessions are complete by querying all sessions
    // For now, this requires a method to list sessions.
    // The data service doesn't have a listAll method, so we track
    // completed session IDs locally or add the method in this task.
    // Decision: add getCompletedSessions() to the page logic via
    // a direct SQLite query through the data service.
    // Since the data service does not expose this, we will call
    // getScoresForSession() for known session IDs -- but we don't
    // know them without a list query.
    //
    // Practical approach: store completed session IDs in localStorage
    // as a JSON array. When a session completes (detected on page load
    // or after navigation back from results), add its ID to the list.
    this.completedSessions.set(this.getStoredCompletedSessions());
  }

  // ── Session ID persistence (lightweight, not SQLite) ───────────────

  private persistSessionId(id: string): void {
    try {
      localStorage.setItem(CheckinPage.SESSION_KEY, id);
    } catch { /* best-effort */ }
  }

  private getStoredSessionId(): string | null {
    try {
      return localStorage.getItem(CheckinPage.SESSION_KEY);
    } catch {
      return null;
    }
  }

  private clearStoredSessionId(): void {
    try {
      localStorage.removeItem(CheckinPage.SESSION_KEY);
    } catch { /* best-effort */ }
  }

  private static readonly COMPLETED_KEY = 'bubls.checkin.completedSessionIds';

  /** Retrieve completed session objects from the data service. */
  private getStoredCompletedSessions(): CheckinSession[] {
    // Completed sessions are loaded asynchronously in loadState.
    // This synchronous call returns an empty array; the async
    // loadCompletedSessions() below populates the signal.
    void this.loadCompletedSessions();
    return [];
  }

  private async loadCompletedSessions(): Promise<void> {
    try {
      const idsJson = localStorage.getItem(CheckinPage.COMPLETED_KEY);
      if (!idsJson) return;
      const ids: string[] = JSON.parse(idsJson);
      const sessions: CheckinSession[] = [];
      for (const id of ids) {
        const session = await this.checkinData.getSession(id);
        if (session && session.status === 'complete') {
          sessions.push(session);
        }
      }
      // Sort newest first
      sessions.sort((a, b) => b.created_at.localeCompare(a.created_at));
      this.completedSessions.set(sessions);
    } catch { /* best-effort */ }
  }

  /**
   * Call after a session completes to add it to the completed list.
   * Public so downstream navigation (back from results) can trigger it.
   */
  addCompletedSession(sessionId: string): void {
    try {
      const idsJson = localStorage.getItem(CheckinPage.COMPLETED_KEY) ?? '[]';
      const ids: string[] = JSON.parse(idsJson);
      if (!ids.includes(sessionId)) {
        ids.unshift(sessionId);
        localStorage.setItem(CheckinPage.COMPLETED_KEY, JSON.stringify(ids));
      }
    } catch { /* best-effort */ }
  }
}
```

**Key decisions embedded in the code**:
- `pageState` signal drives all template branching. Four states: `loading`, `no-session`, `awaiting-partner`, `ready-to-rate`.
- Active session ID persisted to `localStorage` under `bubls.checkin.activeSessionId`. This survives page reload without adding a SQLite dependency for ephemeral state.
- Completed session IDs tracked in `localStorage` as a JSON array. Each ID is resolved against the data service on page load. This avoids adding a `listAllSessions()` method to the data service (which would require a new SQL query and expand Task 1's surface).
- Navigation uses relative paths within the checkin route: `/checkin/rate/:sessionId/:partner` and `/checkin/results/:sessionId`.
- The `submitted` check uses integer comparison (`partner_a_submitted` is `0 | 1` per the `CheckinSession` interface from the actual data service, not boolean as the task-1 plan suggested).
- The "Rate as other partner" button appears in the waiting state. This is the mechanism for handing the device to the second partner.

**Verify**: `npx tsc --noEmit` clean. All imports resolve.

### Step 8: Update the barrel export

**Action**: Add exports for the new page and component to the checkin feature barrel.

**File**: `src/app/features/checkin/index.ts`

**Pattern**:
```typescript
export { CheckinDataService } from './services/checkin-data.service';
export { CheckinPage } from './pages/checkin.page';
export { PartnerSelectComponent } from './components/partner-select.component';
export { CHECKIN_ROUTES } from './checkin.routes';
// ... existing type exports ...
```

**Verify**: `npx tsc --noEmit` clean.

---

## 5. Tests

Framework: Jasmine + Karma (repo convention). Mock pattern: `jasmine.createSpyObj<CheckinDataService>` with controlled return values, matching the `checkin-data.service.spec.ts` pattern from Task 1.

### `src/app/features/checkin/components/partner-select.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PartnerSelectComponent } from './partner-select.component';
import type { Partner } from '../checkin.model';

describe('PartnerSelectComponent', () => {
  let component: PartnerSelectComponent;
  let fixture: ComponentFixture<PartnerSelectComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PartnerSelectComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(PartnerSelectComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders two partner buttons', () => {
    const buttons = fixture.nativeElement.querySelectorAll('[data-test^="partner-btn-"]');
    expect(buttons.length).toBe(2);
  });

  it('tapPartnerA_emitsPartnerA', () => {
    let emitted: Partner | undefined;
    component.partnerSelected.subscribe((p: Partner) => (emitted = p));

    const btnA = fixture.nativeElement.querySelector('[data-test="partner-btn-A"]');
    btnA.click();

    expect(emitted).toBe('A');
  });

  it('tapPartnerB_emitsPartnerB', () => {
    let emitted: Partner | undefined;
    component.partnerSelected.subscribe((p: Partner) => (emitted = p));

    const btnB = fixture.nativeElement.querySelector('[data-test="partner-btn-B"]');
    btnB.click();

    expect(emitted).toBe('B');
  });

  it('renders prompt text', () => {
    const prompt = fixture.nativeElement.querySelector('.prompt');
    expect(prompt.textContent).toContain("Who's rating?");
  });
});
```

### `src/app/features/checkin/pages/checkin.page.spec.ts`

```typescript
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { Router } from '@angular/router';
import { provideRouter } from '@angular/router';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';

import { CheckinPage } from './checkin.page';
import { CheckinDataService } from '../services/checkin-data.service';
import type { CheckinSession } from '../checkin.model';

describe('CheckinPage', () => {
  let component: CheckinPage;
  let fixture: ComponentFixture<CheckinPage>;
  let dataServiceSpy: jasmine.SpyObj<CheckinDataService>;
  let routerSpy: jasmine.SpyObj<Router>;

  function fakeSession(overrides: Partial<CheckinSession> = {}): CheckinSession {
    return {
      id: 'sess-1',
      created_at: '2026-04-17T10:00:00.000Z',
      status: 'active',
      partner_a_submitted: 0,
      partner_b_submitted: 0,
      ...overrides,
    };
  }

  beforeEach(async () => {
    dataServiceSpy = jasmine.createSpyObj('CheckinDataService', [
      'init',
      'createSession',
      'getSession',
      'bothSubmitted',
      'getScoresForSession',
    ]);
    dataServiceSpy.init.and.resolveTo();
    dataServiceSpy.createSession.and.resolveTo('new-session-id');
    dataServiceSpy.getSession.and.resolveTo(null);
    dataServiceSpy.bothSubmitted.and.resolveTo(false);
    dataServiceSpy.getScoresForSession.and.resolveTo([]);

    routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    routerSpy.navigate.and.resolveTo(true);

    // Clear localStorage before each test
    localStorage.removeItem('bubls.checkin.activeSessionId');
    localStorage.removeItem('bubls.checkin.completedSessionIds');

    await TestBed.configureTestingModule({
      imports: [CheckinPage],
      providers: [
        { provide: CheckinDataService, useValue: dataServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
      schemas: [CUSTOM_ELEMENTS_SCHEMA],
    }).compileComponents();

    fixture = TestBed.createComponent(CheckinPage);
    component = fixture.componentInstance;
  });

  // ── Initial state ─────────────────────────────────────────────────

  it('ngOnInit_noStoredSession_showsNoSessionState', fakeAsync(() => {
    fixture.detectChanges();
    tick();

    expect(component.pageState()).toBe('no-session');
    expect(dataServiceSpy.init).toHaveBeenCalled();
  }));

  it('ngOnInit_noSessions_showsEmptyStateCta', fakeAsync(() => {
    fixture.detectChanges();
    tick();
    fixture.detectChanges();

    const emptyCta = fixture.nativeElement.querySelector('[data-test="empty-state-cta"]');
    expect(emptyCta).toBeTruthy();
  }));

  // ── Partner selection → session creation ───────────────────────────

  it('onPartnerSelected_noActiveSession_createsSessionAndNavigates', fakeAsync(() => {
    dataServiceSpy.createSession.and.resolveTo('new-id');
    dataServiceSpy.getSession.and.resolveTo(fakeSession({ id: 'new-id' }));

    fixture.detectChanges();
    tick();

    component.onPartnerSelected('A');
    tick();

    expect(dataServiceSpy.createSession).toHaveBeenCalled();
    expect(routerSpy.navigate).toHaveBeenCalledWith(
      ['/checkin', 'rate', 'new-id', 'A'],
    );
  }));

  it('onPartnerSelected_activeSession_partnerNotSubmitted_navigatesToRate', fakeAsync(() => {
    const session = fakeSession();
    localStorage.setItem('bubls.checkin.activeSessionId', session.id);
    dataServiceSpy.getSession.and.resolveTo(session);

    fixture.detectChanges();
    tick();

    component.onPartnerSelected('B');
    tick();

    expect(dataServiceSpy.createSession).not.toHaveBeenCalled();
    expect(routerSpy.navigate).toHaveBeenCalledWith(
      ['/checkin', 'rate', session.id, 'B'],
    );
  }));

  it('onPartnerSelected_activeSession_partnerAlreadySubmitted_showsWaiting', fakeAsync(() => {
    const session = fakeSession({ partner_a_submitted: 1 });
    localStorage.setItem('bubls.checkin.activeSessionId', session.id);
    dataServiceSpy.getSession.and.resolveTo(session);

    fixture.detectChanges();
    tick();

    component.onPartnerSelected('A');
    tick();

    expect(component.pageState()).toBe('awaiting-partner');
    expect(routerSpy.navigate).not.toHaveBeenCalled();
  }));

  // ── Waiting state ─────────────────────────────────────────────────

  it('storedSession_onePartnerSubmitted_showsAwaitingPartner', fakeAsync(() => {
    const session = fakeSession({ partner_a_submitted: 1 });
    localStorage.setItem('bubls.checkin.activeSessionId', session.id);
    dataServiceSpy.getSession.and.resolveTo(session);

    fixture.detectChanges();
    tick();

    expect(component.pageState()).toBe('awaiting-partner');
  }));

  it('otherPartner_partnerASubmitted_returnsPartnerB', fakeAsync(() => {
    component.activeSession.set(fakeSession({ partner_a_submitted: 1 }));
    expect(component.otherPartner()).toBe('Partner B');
  }));

  it('otherPartner_partnerBSubmitted_returnsPartnerA', fakeAsync(() => {
    component.activeSession.set(fakeSession({ partner_b_submitted: 1 }));
    expect(component.otherPartner()).toBe('Partner A');
  }));

  // ── Results navigation ────────────────────────────────────────────

  it('onViewResults_navigatesToResultsRoute', fakeAsync(() => {
    component.onViewResults('sess-1');
    tick();

    expect(routerSpy.navigate).toHaveBeenCalledWith(
      ['/checkin', 'results', 'sess-1'],
    );
  }));

  // ── Rate as other partner ─────────────────────────────────────────

  it('onRateAsOtherPartner_partnerASubmitted_navigatesAsB', fakeAsync(() => {
    component.activeSession.set(fakeSession({
      id: 'sess-1',
      partner_a_submitted: 1,
    }));

    component.onRateAsOtherPartner();
    tick();

    expect(routerSpy.navigate).toHaveBeenCalledWith(
      ['/checkin', 'rate', 'sess-1', 'B'],
    );
  }));

  // ── Session history ───────────────────────────────────────────────

  it('completedSessions_storedIds_loadsFromService', fakeAsync(() => {
    const completed = fakeSession({ id: 'done-1', status: 'complete' });
    localStorage.setItem(
      'bubls.checkin.completedSessionIds',
      JSON.stringify(['done-1']),
    );
    dataServiceSpy.getSession.and.callFake(async (id: string) => {
      if (id === 'done-1') return completed;
      return null;
    });

    fixture.detectChanges();
    tick();

    expect(component.completedSessions().length).toBe(1);
    expect(component.completedSessions()[0].id).toBe('done-1');
  }));

  // ── addCompletedSession ───────────────────────────────────────────

  it('addCompletedSession_persistsToLocalStorage', () => {
    component.addCompletedSession('sess-99');

    const stored = JSON.parse(
      localStorage.getItem('bubls.checkin.completedSessionIds') ?? '[]',
    );
    expect(stored).toContain('sess-99');
  });

  it('addCompletedSession_noDuplicates', () => {
    component.addCompletedSession('sess-99');
    component.addCompletedSession('sess-99');

    const stored = JSON.parse(
      localStorage.getItem('bubls.checkin.completedSessionIds') ?? '[]',
    );
    expect(stored.filter((id: string) => id === 'sess-99').length).toBe(1);
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(checkin): register heart-outline icon in shell layout` -- `src/app/shell/shell-layout.component.ts`: import and register `heartOutline` in `addIcons()`.
2. `feat(checkin): add checkin tab to feature registry and app routes` -- `src/app/shell/feature-registry.ts`: add fourth tab entry. `src/app/app.routes.ts`: add `checkin` child route with `loadChildren`. `src/app/features/checkin/checkin.routes.ts`: new child routes config with placeholder routes for rate/results/trends.
3. `feat(checkin): partner selection component` -- `src/app/features/checkin/components/partner-select.component.ts`: standalone OnPush component with two tap targets, output signal. `src/app/features/checkin/components/partner-select.component.spec.ts`: unit tests.
4. `feat(checkin): partner selection + session creation page` -- `src/app/features/checkin/pages/checkin.page.ts`: entry page with state machine (no-session, awaiting-partner, ready-to-rate), session creation, partner selection, history list, localStorage session tracking. `src/app/features/checkin/pages/checkin.page.spec.ts`: unit tests.
5. `feat(checkin): update barrel exports for checkin feature` -- `src/app/features/checkin/index.ts`: export page, component, routes.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation. Keep the total to 3 or fewer per commit.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless
npm run build
```

**Expected delta**: `N` (baseline from section 2) to `N + 14` passing (4 PartnerSelectComponent specs + 10 CheckinPage specs). Zero pre-existing tests broken. `npm run build` clean with no new warnings.

**Manual check**:
1. Run `ionic serve` (or `npm start`).
2. Confirm a fourth tab labeled "Check-in" with a heart icon appears in the tab bar.
3. Tap the Check-in tab. Confirm the empty state message "Start your first check-in" renders.
4. Tap "Partner A". Confirm navigation to `/checkin/rate/<uuid>/A` (the route exists but loads the checkin page as a placeholder until Task 3 builds the rating component).
5. Navigate back to `/checkin`. Confirm the active session is detected and the page shows the "Session in progress" state with partner selection.

**Type check**: `npx tsc --noEmit` must pass with zero errors.

---

## 8. Rollback

- **Per-step**: each of the 5 commits is independently revertible. Commits 1 and 2 (shell + routes) are the most sensitive because they modify shared infrastructure. Reverting them removes the tab and route cleanly.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (record the SHA during section 2 Pre-flight) or delete the feature branch.
- **Shell regression safety**: if adding the fourth tab breaks existing tab layout (spacing, overflow), the quickest fix is to remove the checkin entry from `FEATURE_ROUTES` and add a manual navigation button inside the checkin page itself (accessible via direct URL `/checkin`). Log as deviation.
- **Route conflict**: if another feature has already claimed the `checkin` path, rename to `relationship-checkin` in both `app.routes.ts` and `feature-registry.ts`. Log as deviation.

---

## 9. Deviations Allowed

- **Data service API differs from plan** -- the actual `CheckinDataService` at `/projects/bubls/src/app/features/checkin/services/checkin-data.service.ts` returns `Promise<string>` from `createSession()` (session ID, not a full session object). The page calls `getSession(id)` afterward to get the full object. If the API has changed further since Task 1 shipped, adjust the page calls to match. Log the difference.
- **`partner_a_submitted` is `number` not `boolean`** -- the actual model uses `number` (0 | 1) for SQLite INTEGER compatibility. The page template comparisons use truthiness checks (`session.partner_a_submitted` is truthy when 1). If the model has been updated to use booleans, adjust comparisons. Log as deviation.
- **Feature directory is `features/checkin/` not `pages/checkin/`** -- Task 1 plan said `pages/checkin/` but actual execution placed files in `features/checkin/`. This task follows the actual codebase location. All new files go under `src/app/features/checkin/`.
- **No `getActiveSession()` method** -- the data service does not expose a "get active session" query. The page stores the active session ID in localStorage and uses `getSession(id)` to reload it. If a `getActiveSession()` method has been added, use it instead and remove the localStorage tracking. Log as deviation.
- **No `getCompletedSessions()` or `listSessions()` method** -- the data service does not list all sessions. The page tracks completed session IDs in localStorage. If a list method has been added, use it and remove the localStorage list. Log as deviation.
- **Icon not available** -- if `heartOutline` is not available in the installed ionicons version, use `chatbubblesOutline` as fallback. Log as deviation.
- **Four tabs cause layout overflow on small screens** -- if the tab bar wraps or truncates on 320px-wide screens, shorten the label from "Check-in" to "Check" or use icon-only mode. Log as deviation.
- **Test framework mismatch** -- if existing specs use Jest/Vitest instead of Jasmine, translate assertions to match the actual framework. Log as deviation.
- **Side-effect required** (push, publish, schema change on real device) -- STOP, mark `[REQUIRES APPROVAL]`, ask.

---

## 10. Out of Scope

This task creates the session management screen and partner selection -- nothing more. It does NOT build the rating interface, results view, trends, or expiry logic.

- **Rating interface** (`checkin-rate.component.ts`, `score-selector.component.ts`, `question-card.component.ts`) -- Task 3. This task creates the placeholder route only.
- **Results view** (`checkin-results.component.ts`) -- Task 4. This task creates the placeholder route and navigation method only.
- **Waiting polling** (periodic check if other partner submitted) -- Task 4. The waiting state in this task is static; it does not poll.
- **Trend lines** (`checkin-trends.component.ts`, `sparkline.component.ts`) -- Task 5. Placeholder route only.
- **Session expiry** (48h auto-expire on app open) -- Task 6. The `expireStale()` method exists in the data service but is not wired into any lifecycle hook by this task.
- **Draft persistence** (`checkin_draft` table for crash recovery mid-rating) -- Task 6.
- **Data service changes** -- no modifications to `checkin-data.service.ts`. If a new query method is needed, document it as a gap and work around it with localStorage (as designed in this plan).
- **Theming or token changes** -- no modifications to `src/app/styles/tokens.scss`. The checkin page uses existing CSS custom properties.
- **Backend / server changes** -- this feature is local-only, no server code.
- **Push notifications or reminders** -- explicitly out of scope per epic non-goals.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) -- Component design for Task 2, privacy model, feature guard pattern
- [Epic](./epic.md) -- Task scope, dependencies, success criteria
- [Analysis](./analysis.md) -- Problem statement and open questions
- [Timeline](./timeline.md) -- Status tracking (update after done)
