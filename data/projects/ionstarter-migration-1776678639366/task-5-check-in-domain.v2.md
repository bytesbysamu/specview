# Task 5: Build Check-In Domain on Ionstarter (POC)

## 1. Purpose

Build a new check-in domain (`domains/check-in/`) on the ionstarter boilerplate as a proof-of-concept validating that bubls features can be reshaped into the three-tier domain-driven architecture with TanStack Query, platform adapters, and Transloco i18n.

---

## 2. Effort / Dependencies / Parallel With / Blocks

| Field | Value |
|-------|-------|
| **Effort** | 1 day |
| **Dependencies** | Task 2 (reference migration establishes the TanStack Query pattern this domain follows) |
| **Parallel with** | Tasks 3, 4 |
| **Blocks** | Nothing (this is a POC terminal task) |

---

## 3. Context

### Why this task exists

The ionstarter migration epic needs proof that a real bubls feature can live inside the domain-driven architecture before committing to the full migration. Check-in is the right candidate: it has venue search (debounced query), a write action (mutation with cache invalidation), a history feed (paginated query), and a platform adapter requirement (geolocation). It exercises every layer of the three-tier service stack without being the most complex feature (photoshoot is harder).

### Trade-offs

- **New build, not migration**: This is NOT a port of `src/app/features/checkin/` from bubls. The bubls check-in is a relationship-rating flow backed by local SQLite. The ionstarter POC builds a *venue-based* check-in backed by a Flask API (mocked for now). The domain model, data flow, and UI are different.
- **Mock data only**: There is no Flask backend yet. All TanStack queries hit mock data behind `environment.useMocks`. The architecture is real; the data is fake.
- **No `@capacitor/geolocation` installed**: Ionstarter does not ship with Geolocation. The executor must install it or build a pure mock adapter. Since this is a POC, a mock geolocation adapter that returns a fixed Zurich coordinate is acceptable.
- **No Elf store**: Check-in has no persistent client-state requirement. TanStack Query owns all server-state, Angular signals own ephemeral UI state. An Elf store is out of scope.

---

## 4. Pre-flight

Run from the ionstarter project root (`/projects/ionstarter/`):

```bash
# 1. Verify the project builds cleanly before touching anything
cd /projects/ionstarter && npm run build

# 2. Verify tests pass
cd /projects/ionstarter && npm run test:ci

# 3. Confirm @ngneat/query is installed (TanStack wrapper)
node -e "const p = require('./package.json'); console.log('@ngneat/query:', p.dependencies['@ngneat/query'])"

# 4. Confirm @capacitor/geolocation is NOT installed (we mock it)
node -e "const p = require('./package.json'); console.log('geolocation:', p.dependencies['@capacitor/geolocation'] || 'not installed')"

# 5. Create the domain directory scaffold
mkdir -p src/app/domains/check-in/{pages/check-in,pages/check-in-history,services/check-in-page,services/check-in-history-page,services/check-in,services/check-in-backend,services/geolocation,models}
```

---

## 5. Files

### To Create (new files)

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/domains/check-in/models/check-in.model.ts` | Domain types: Venue, CheckIn, Location, CheckInHistoryItem |
| 2 | `src/app/domains/check-in/models/index.ts` | Barrel export |
| 3 | `src/app/domains/check-in/services/geolocation/geolocation.service.ts` | Platform adapter: returns Location from Capacitor or browser API |
| 4 | `src/app/domains/check-in/services/check-in-backend/check-in-backend.service.ts` | TanStack Query: injectQuery for venue search, injectMutation for check-in action, injectQuery for history |
| 5 | `src/app/domains/check-in/services/check-in/check-in.service.ts` | Domain logic: geolocation orchestration, venue ranking, distance calculation |
| 6 | `src/app/domains/check-in/services/check-in-page/check-in-page.service.ts` | Page service for venue search + check-in CTA page |
| 7 | `src/app/domains/check-in/services/check-in-history-page/check-in-history-page.service.ts` | Page service for history feed page |
| 8 | `src/app/domains/check-in/services/index.ts` | Barrel export for all services |
| 9 | `src/app/domains/check-in/pages/check-in/check-in.page.ts` | Standalone component: venue search + check-in CTA |
| 10 | `src/app/domains/check-in/pages/check-in/check-in.page.html` | Template for check-in page |
| 11 | `src/app/domains/check-in/pages/check-in/check-in.page.scss` | Styles for check-in page |
| 12 | `src/app/domains/check-in/pages/check-in-history/check-in-history.page.ts` | Standalone component: paginated history feed |
| 13 | `src/app/domains/check-in/pages/check-in-history/check-in-history.page.html` | Template for history page |
| 14 | `src/app/domains/check-in/pages/check-in-history/check-in-history.page.scss` | Styles for history page |
| 15 | `src/app/domains/check-in/pages/index.ts` | Barrel export for pages |
| 16 | `src/app/domains/check-in/routes.ts` | Lazy-loaded route definitions |
| 17 | `src/app/domains/check-in/check-in.mock.ts` | Mock venue data and mock check-in history |

### To Modify (existing files)

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/domains/tabs/routes.ts` | Add `check-in` child route |
| 2 | `src/app/domains/tabs/pages/tabs/tabs.page.ts` | Add check-in tab button + icon + navigation method |
| 3 | `src/app/domains/tabs/pages/tabs/tabs.page.html` | Add `<ion-tab-button tab="check-in">` |
| 4 | `src/app/domains/tabs/services/tabs-page/tabs-page.service.ts` | Add `navigateToCheckInPage()` |
| 5 | `src/app/core/services/router/router.service.ts` | Add `navigateToCheckInPage()` and `navigateToCheckInHistoryPage()` |
| 6 | `src/assets/i18n/en.json` | Add `domain.checkIn.*` translation keys |
| 7 | `src/assets/i18n/de.json` | Add `domain.checkIn.*` translation keys (German) |

### To Leave Alone

- `src/app/domains/tasks/` -- Reference domain, do not modify
- `src/app/core/services/capacitor/` -- No new Capacitor service wrappers; geolocation adapter lives inside the domain
- `src/app/store/` -- No Elf store for check-in (no persistent client-state)
- `src/app/shared/` -- No changes needed for this POC
- `package.json` -- Do not install `@capacitor/geolocation`; use a mock adapter

---

## 6. Implementation Steps

### Step 1: Define domain models

**Action**: Create the type definitions for the check-in domain. These are the *domain* types, not API DTOs. The anti-corruption layer maps API responses to these shapes.

**File**: `src/app/domains/check-in/models/check-in.model.ts`

**Pattern** (mirrors `domains/tasks/interfaces/task.ts`):

```typescript
export interface Location {
  latitude: number;
  longitude: number;
}

export interface Venue {
  id: string;
  name: string;
  address: string;
  category: string;
  location: Location;
  /** Distance in meters from user's current location. Computed client-side. */
  distanceMeters: number | null;
}

export interface CheckIn {
  id: string;
  venueId: string;
  venueName: string;
  checkedInAt: string;
}

export interface CheckInHistoryItem {
  id: string;
  venueId: string;
  venueName: string;
  venueCategory: string;
  checkedInAt: string;
}
```

**File**: `src/app/domains/check-in/models/index.ts`

```typescript
export * from './check-in.model';
```

**Verify**: `npx tsc --noEmit` passes (types compile).

---

### Step 2: Create mock data

**Action**: Create mock venue data and mock check-in history. This file is the data source when `environment.useMocks` is true (or always, since there is no backend yet).

**File**: `src/app/domains/check-in/check-in.mock.ts`

**Pattern**:

```typescript
import { CheckInHistoryItem, Venue } from './models';

export const MOCK_VENUES: Venue[] = [
  {
    id: 'v1',
    name: 'Hive Zurich',
    address: 'Geroldstrasse 5, 8005 Zurich',
    category: 'Bar',
    location: { latitude: 47.3884, longitude: 8.5187 },
    distanceMeters: null,
  },
  {
    id: 'v2',
    name: 'Frau Gerolds Garten',
    address: 'Geroldstrasse 23, 8005 Zurich',
    category: 'Restaurant',
    location: { latitude: 47.3878, longitude: 8.5193 },
    distanceMeters: null,
  },
  {
    id: 'v3',
    name: 'Moods im Schiffbau',
    address: 'Schiffbaustrasse 6, 8005 Zurich',
    category: 'Music Venue',
    location: { latitude: 47.3891, longitude: 8.5165 },
    distanceMeters: null,
  },
  {
    id: 'v4',
    name: 'Volkshaus Zurich',
    address: 'Stauffacherstrasse 60, 8004 Zurich',
    category: 'Bar',
    location: { latitude: 47.3747, longitude: 8.5277 },
    distanceMeters: null,
  },
  {
    id: 'v5',
    name: 'Cafe Odeon',
    address: 'Am Bellevue, Limmatquai 2, 8001 Zurich',
    category: 'Cafe',
    location: { latitude: 47.3667, longitude: 8.5458 },
    distanceMeters: null,
  },
];

export const MOCK_CHECK_IN_HISTORY: CheckInHistoryItem[] = [
  {
    id: 'ci1',
    venueId: 'v1',
    venueName: 'Hive Zurich',
    venueCategory: 'Bar',
    checkedInAt: '2026-04-18T21:30:00.000Z',
  },
  {
    id: 'ci2',
    venueId: 'v3',
    venueName: 'Moods im Schiffbau',
    venueCategory: 'Music Venue',
    checkedInAt: '2026-04-15T19:00:00.000Z',
  },
  {
    id: 'ci3',
    venueId: 'v5',
    venueName: 'Cafe Odeon',
    venueCategory: 'Cafe',
    checkedInAt: '2026-04-12T10:00:00.000Z',
  },
];
```

**Verify**: File imports resolve -- `npx tsc --noEmit`.

---

### Step 3: Build the geolocation platform adapter

**Action**: Create an adapter service that abstracts geolocation access. Since `@capacitor/geolocation` is not installed, this POC returns a fixed Zurich coordinate. The adapter interface is ready for a real Capacitor implementation later.

**File**: `src/app/domains/check-in/services/geolocation/geolocation.service.ts`

**Pattern** (mirrors how `TasksService` delegates to platform-specific storage):

```typescript
import { Injectable } from '@angular/core';
import { Location } from '../../models';

/** Default location: Zurich Hauptbahnhof */
const ZURICH_HB: Location = {
  latitude: 47.3769,
  longitude: 8.5417,
};

@Injectable({
  providedIn: 'root',
})
export class GeolocationService {
  /**
   * Returns the user's current location.
   *
   * POC: always returns a fixed Zurich coordinate.
   * Production: use Capacitor Geolocation on native, navigator.geolocation on web.
   */
  public async getCurrentLocation(): Promise<Location> {
    // TODO: Replace with real Capacitor Geolocation / browser API
    return ZURICH_HB;
  }
}
```

**Verify**: `npx tsc --noEmit`.

---

### Step 4: Build the backend service (TanStack Query layer)

**Action**: Create the backend service that wraps all server-state operations in TanStack Query. This is the lowest tier. It uses `injectQuery` for reads and `injectMutation` for writes, exactly matching the pattern in `TaskListPageService` and `TaskUpsertPageService`.

**File**: `src/app/domains/check-in/services/check-in-backend/check-in-backend.service.ts`

**Pattern** (mirrors `task-list-page.service.ts` TanStack usage):

```typescript
import { Injectable, signal } from '@angular/core';
import {
  MutationResult,
  QueryObserverResult,
  injectMutation,
  injectQuery,
  injectQueryClient,
} from '@ngneat/query';
import { Result } from '@ngneat/query/lib/types';
import { CheckIn, CheckInHistoryItem, Venue } from '../../models';
import { MOCK_CHECK_IN_HISTORY, MOCK_VENUES } from '../../check-in.mock';

@Injectable({
  providedIn: 'root',
})
export class CheckInBackendService {
  #client = injectQueryClient();
  #mutation = injectMutation();
  #query = injectQuery();

  /**
   * Venue search query. Debounce is handled at the page-service level;
   * this layer just executes the query with the current search term.
   */
  public searchVenues(
    searchTerm: () => string,
  ): Result<QueryObserverResult<Venue[], Error>> {
    return this.#query({
      queryKey: ['venues', { search: searchTerm }],
      queryFn: () => this.mockSearchVenues(searchTerm()),
    });
  }

  /**
   * Check-in history query. Returns all past check-ins, newest first.
   */
  public getCheckInHistory(): Result<
    QueryObserverResult<CheckInHistoryItem[], Error>
  > {
    return this.#query({
      queryKey: ['check-in-history'],
      queryFn: () => this.mockGetHistory(),
    });
  }

  /**
   * Check-in mutation. On success, invalidates the history query
   * so the feed updates immediately.
   */
  public checkIn(): MutationResult<CheckIn, Error, string, unknown> {
    return this.#mutation({
      mutationFn: (venueId: string) => this.mockCheckIn(venueId),
      onSuccess: () => {
        void this.#client.invalidateQueries({
          queryKey: ['check-in-history'],
        });
      },
    });
  }

  // ── Mock implementations (replace with real HTTP when Flask lands) ──

  private async mockSearchVenues(term: string): Promise<Venue[]> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 200));
    if (!term.trim()) {
      return MOCK_VENUES;
    }
    const lower = term.toLowerCase();
    return MOCK_VENUES.filter(
      v =>
        v.name.toLowerCase().includes(lower) ||
        v.category.toLowerCase().includes(lower),
    );
  }

  private async mockGetHistory(): Promise<CheckInHistoryItem[]> {
    await new Promise(resolve => setTimeout(resolve, 150));
    return MOCK_CHECK_IN_HISTORY;
  }

  private async mockCheckIn(venueId: string): Promise<CheckIn> {
    await new Promise(resolve => setTimeout(resolve, 300));
    const venue = MOCK_VENUES.find(v => v.id === venueId);
    if (!venue) {
      throw new Error('Venue not found');
    }
    return {
      id: crypto.randomUUID(),
      venueId: venue.id,
      venueName: venue.name,
      checkedInAt: new Date().toISOString(),
    };
  }
}
```

**Verify**: `npx tsc --noEmit`. Confirm `injectQuery`, `injectMutation`, `injectQueryClient` resolve from `@ngneat/query`.

---

### Step 5: Build the domain service (business logic layer)

**Action**: Create the domain service that orchestrates geolocation and venue ranking. This is pure business logic -- no TanStack, no UI concerns.

**File**: `src/app/domains/check-in/services/check-in/check-in.service.ts`

**Pattern**:

```typescript
import { Injectable } from '@angular/core';
import { Location, Venue } from '../../models';
import { GeolocationService } from '../geolocation/geolocation.service';

@Injectable({
  providedIn: 'root',
})
export class CheckInService {
  constructor(private readonly geolocationService: GeolocationService) {}

  /**
   * Get the user's current location and compute distance
   * to each venue, returning venues sorted by proximity.
   */
  public async rankVenuesByDistance(venues: Venue[]): Promise<Venue[]> {
    const location = await this.geolocationService.getCurrentLocation();
    const withDistance = venues.map(venue => ({
      ...venue,
      distanceMeters: this.haversineDistance(location, venue.location),
    }));
    return withDistance.sort(
      (a, b) => (a.distanceMeters ?? Infinity) - (b.distanceMeters ?? Infinity),
    );
  }

  /**
   * Haversine formula: returns distance in meters between two coordinates.
   */
  private haversineDistance(a: Location, b: Location): number {
    const R = 6_371_000; // Earth radius in meters
    const toRad = (deg: number): number => (deg * Math.PI) / 180;
    const dLat = toRad(b.latitude - a.latitude);
    const dLon = toRad(b.longitude - a.longitude);
    const sinLat = Math.sin(dLat / 2);
    const sinLon = Math.sin(dLon / 2);
    const h =
      sinLat * sinLat +
      Math.cos(toRad(a.latitude)) * Math.cos(toRad(b.latitude)) * sinLon * sinLon;
    return R * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
  }
}
```

**Verify**: `npx tsc --noEmit`.

---

### Step 6: Build the check-in page service (UI orchestration layer)

**Action**: Create the page service that the check-in page injects. Owns the debounced search signal and delegates to the backend and domain services.

**File**: `src/app/domains/check-in/services/check-in-page/check-in-page.service.ts`

**Pattern** (mirrors `TaskListPageService` structure with additions for debounce):

```typescript
import { Injectable, signal } from '@angular/core';
import { RouterService } from '@app/core';
import {
  MutationResult,
  QueryObserverResult,
  injectMutation,
  injectQuery,
  injectQueryClient,
} from '@ngneat/query';
import { Result } from '@ngneat/query/lib/types';
import { Venue, CheckIn } from '../../models';
import { CheckInBackendService } from '../check-in-backend/check-in-backend.service';
import { CheckInService } from '../check-in/check-in.service';

@Injectable({
  providedIn: 'root',
})
export class CheckInPageService {
  /** Debounced search term -- page sets this, backend service reads it. */
  public readonly searchTerm = signal('');

  constructor(
    private readonly routerService: RouterService,
    private readonly checkInBackendService: CheckInBackendService,
    private readonly checkInService: CheckInService,
  ) {}

  public searchVenues(): Result<QueryObserverResult<Venue[], Error>> {
    return this.checkInBackendService.searchVenues(() => this.searchTerm());
  }

  public checkIn(): MutationResult<CheckIn, Error, string, unknown> {
    return this.checkInBackendService.checkIn();
  }

  public async navigateToCheckInHistoryPage(): Promise<void> {
    await this.routerService.navigateToCheckInHistoryPage();
  }
}
```

**Verify**: `npx tsc --noEmit`.

---

### Step 7: Build the check-in history page service

**Action**: Create the page service for the history feed page.

**File**: `src/app/domains/check-in/services/check-in-history-page/check-in-history-page.service.ts`

**Pattern**:

```typescript
import { Injectable } from '@angular/core';
import { RouterService } from '@app/core';
import { QueryObserverResult, injectQuery } from '@ngneat/query';
import { Result } from '@ngneat/query/lib/types';
import { CheckInHistoryItem } from '../../models';
import { CheckInBackendService } from '../check-in-backend/check-in-backend.service';

@Injectable({
  providedIn: 'root',
})
export class CheckInHistoryPageService {
  constructor(
    private readonly routerService: RouterService,
    private readonly checkInBackendService: CheckInBackendService,
  ) {}

  public getHistory(): Result<
    QueryObserverResult<CheckInHistoryItem[], Error>
  > {
    return this.checkInBackendService.getCheckInHistory();
  }

  public async navigateToCheckInPage(): Promise<void> {
    await this.routerService.navigateToCheckInPage();
  }
}
```

**Verify**: `npx tsc --noEmit`.

---

### Step 8: Create barrel export for services

**File**: `src/app/domains/check-in/services/index.ts`

**Pattern** (mirrors `domains/tasks/services/index.ts`):

```typescript
export * from './check-in-page/check-in-page.service';
export * from './check-in-history-page/check-in-history-page.service';
export * from './check-in-backend/check-in-backend.service';
export * from './check-in/check-in.service';
export * from './geolocation/geolocation.service';
```

**Verify**: `npx tsc --noEmit`.

---

### Step 9: Build the check-in page component

**Action**: Create the venue search + check-in CTA page as a standalone component with OnPush change detection.

**File**: `src/app/domains/check-in/pages/check-in/check-in.page.ts`

**Pattern** (mirrors `task-list.page.ts`):

```typescript
import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SharedModule } from '@app/shared';
import {
  IonButton,
  IonContent,
  IonHeader,
  IonIcon,
  IonInput,
  IonItem,
  IonLabel,
  IonList,
  IonSearchbar,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import { TranslocoPipe } from '@jsverse/transloco';
import { addIcons } from 'ionicons';
import { checkmarkCircle, location, time } from 'ionicons/icons';
import { Venue } from '../../models';
import { CheckInPageService } from '../../services';

@Component({
  selector: 'app-check-in',
  templateUrl: './check-in.page.html',
  styleUrls: ['./check-in.page.scss'],
  imports: [
    SharedModule,
    TranslocoPipe,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonSearchbar,
    IonList,
    IonItem,
    IonLabel,
    IonIcon,
    IonButton,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInPage {
  public readonly venues = this.checkInPageService.searchVenues().result;

  private readonly checkIn = this.checkInPageService.checkIn();
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(private readonly checkInPageService: CheckInPageService) {
    addIcons({ location, checkmarkCircle, time });
  }

  public onSearchInput(event: CustomEvent): void {
    const value = (event.detail.value as string) ?? '';
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.debounceTimer = setTimeout(() => {
      this.checkInPageService.searchTerm.set(value);
    }, 300);
  }

  public onCheckIn(venue: Venue): void {
    this.checkIn.mutate(venue.id);
  }

  public async onNavigateToHistory(): Promise<void> {
    await this.checkInPageService.navigateToCheckInHistoryPage();
  }
}
```

**File**: `src/app/domains/check-in/pages/check-in/check-in.page.html`

```html
<ion-header [translucent]="true">
  <ion-toolbar>
    <ion-title>{{ "domain.checkIn.page.checkIn.title" | transloco }}</ion-title>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true">
  <ion-header collapse="condense">
    <ion-toolbar>
      <ion-title size="large">{{
        "domain.checkIn.page.checkIn.title" | transloco
      }}</ion-title>
    </ion-toolbar>
  </ion-header>

  <ion-searchbar
    [placeholder]="'domain.checkIn.page.checkIn.searchPlaceholder' | transloco"
    (ionInput)="onSearchInput($event)"
    [debounce]="0"
  ></ion-searchbar>

  <ion-list>
    @for (venue of venues().data; track venue.id; let last = $last) {
      <ion-item [lines]="last ? 'none' : 'inset'">
        <ion-icon name="location" slot="start"></ion-icon>
        <ion-label>
          <h2>{{ venue.name }}</h2>
          <p>{{ venue.address }}</p>
        </ion-label>
        <ion-button
          slot="end"
          fill="clear"
          (click)="onCheckIn(venue)"
        >
          <ion-icon name="checkmark-circle" slot="icon-only"></ion-icon>
        </ion-button>
      </ion-item>
    }
  </ion-list>
</ion-content>
```

**File**: `src/app/domains/check-in/pages/check-in/check-in.page.scss`

```scss
:host-context(body:not(.ion-palette-dark)) {
  ion-content {
    --background: var(--ion-color-light);
  }
}

ion-searchbar {
  padding: 8px 16px;
}
```

**Verify**: `npx tsc --noEmit` -- component compiles.

---

### Step 10: Build the check-in history page component

**File**: `src/app/domains/check-in/pages/check-in-history/check-in-history.page.ts`

**Pattern**:

```typescript
import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SharedModule } from '@app/shared';
import {
  IonBackButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonIcon,
  IonItem,
  IonLabel,
  IonList,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import { TranslocoPipe } from '@jsverse/transloco';
import { addIcons } from 'ionicons';
import { time } from 'ionicons/icons';
import { CheckInHistoryPageService } from '../../services';

@Component({
  selector: 'app-check-in-history',
  templateUrl: './check-in-history.page.html',
  styleUrls: ['./check-in-history.page.scss'],
  imports: [
    SharedModule,
    DatePipe,
    TranslocoPipe,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonBackButton,
    IonContent,
    IonList,
    IonItem,
    IonLabel,
    IonIcon,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInHistoryPage {
  public readonly history =
    this.checkInHistoryPageService.getHistory().result;

  constructor(
    private readonly checkInHistoryPageService: CheckInHistoryPageService,
  ) {
    addIcons({ time });
  }
}
```

**File**: `src/app/domains/check-in/pages/check-in-history/check-in-history.page.html`

```html
<ion-header>
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-back-button
        defaultHref="/check-in"
        [text]="'core.button.back' | transloco"
      ></ion-back-button>
    </ion-buttons>
    <ion-title>{{
      "domain.checkIn.page.checkInHistory.title" | transloco
    }}</ion-title>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true">
  <ion-list>
    @for (item of history().data; track item.id; let last = $last) {
      <ion-item [lines]="last ? 'none' : 'inset'">
        <ion-icon name="time" slot="start"></ion-icon>
        <ion-label>
          <h2>{{ item.venueName }}</h2>
          <p>{{ item.venueCategory }} &middot; {{ item.checkedInAt | date: "short" }}</p>
        </ion-label>
      </ion-item>
    }
  </ion-list>
</ion-content>
```

**File**: `src/app/domains/check-in/pages/check-in-history/check-in-history.page.scss`

```scss
:host-context(body:not(.ion-palette-dark)) {
  ion-content {
    --background: var(--ion-color-light);
  }
}
```

**Verify**: `npx tsc --noEmit`.

---

### Step 11: Create barrel export for pages

**File**: `src/app/domains/check-in/pages/index.ts`

```typescript
export * from './check-in/check-in.page';
export * from './check-in-history/check-in-history.page';
```

---

### Step 12: Define routes

**Action**: Create the lazy-loaded route definitions for the check-in domain.

**File**: `src/app/domains/check-in/routes.ts`

**Pattern** (mirrors `domains/tasks/routes.ts`):

```typescript
import { Routes } from '@angular/router';
import { leavePageGuard } from '@app/core';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/check-in/check-in.page').then(m => m.CheckInPage),
    canDeactivate: [leavePageGuard],
  },
  {
    path: 'history',
    loadComponent: () =>
      import('./pages/check-in-history/check-in-history.page').then(
        m => m.CheckInHistoryPage,
      ),
    canDeactivate: [leavePageGuard],
  },
];
```

**Verify**: `npx tsc --noEmit`.

---

### Step 13: Wire into the tabs router

**Action**: Add `check-in` as a child route in the tabs domain.

**File**: `src/app/domains/tabs/routes.ts`

**Change**: Add a new child route for check-in between `tasks` and `settings`:

```typescript
// Add this child to the TabsPage children array:
{
  path: 'check-in',
  loadChildren: () => import('../check-in/routes').then(m => m.routes),
},
```

The full children array should be: `home`, `tasks`, `check-in`, `settings`.

**Verify**: `npx tsc --noEmit`.

---

### Step 14: Add router navigation methods

**Action**: Add check-in navigation methods to the `RouterService`.

**File**: `src/app/core/services/router/router.service.ts`

**Change**: Add two methods after `navigateToTaskUpsertPage`:

```typescript
public navigateToCheckInPage(options?: NavigationOptions): Promise<boolean> {
  return this.navigateForward(['/check-in'], options);
}

public navigateToCheckInHistoryPage(options?: NavigationOptions): Promise<boolean> {
  return this.navigateForward(['/check-in/history'], options);
}
```

**Verify**: `npx tsc --noEmit`.

---

### Step 15: Wire the tab bar

**Action**: Add the check-in tab button to the tabs page.

**File**: `src/app/domains/tabs/services/tabs-page/tabs-page.service.ts`

**Change**: Add navigation method:

```typescript
public async navigateToCheckInPage(): Promise<void> {
  await this.routerService.navigateToCheckInPage();
}
```

**File**: `src/app/domains/tabs/pages/tabs/tabs.page.ts`

**Change**: Import `locationOutline` (or `location`) icon and add navigation method:

```typescript
// In constructor addIcons call, add:
import { cog, fileTrayFull, home, location } from 'ionicons/icons';
// ...
addIcons({ home, fileTrayFull, location, cog });

// Add method:
public async onNavigateToCheckInPage(): Promise<void> {
  await this.tabsPageService.navigateToCheckInPage();
}
```

**File**: `src/app/domains/tabs/pages/tabs/tabs.page.html`

**Change**: Add tab button before the settings tab:

```html
<ion-tab-button tab="check-in" (click)="onNavigateToCheckInPage()">
  <ion-icon name="location"></ion-icon>
  <ion-label>{{
    "domain.tabs.page.tabs.button.checkIn" | transloco
  }}</ion-label>
</ion-tab-button>
```

**Verify**: `npx tsc --noEmit`.

---

### Step 16: Add i18n translation keys

**Action**: Add Transloco keys for the check-in domain.

**File**: `src/assets/i18n/en.json`

**Change**: Add the following block inside `"domain"`:

```json
"checkIn": {
  "page": {
    "checkIn": {
      "title": "Check In",
      "searchPlaceholder": "Search venues..."
    },
    "checkInHistory": {
      "title": "History"
    }
  }
}
```

And add to `"domain.tabs.page.tabs.button"`:

```json
"checkIn": "Check In"
```

**File**: `src/assets/i18n/de.json`

**Change**: Add the same structure with German translations:

```json
"checkIn": {
  "page": {
    "checkIn": {
      "title": "Einchecken",
      "searchPlaceholder": "Locations suchen..."
    },
    "checkInHistory": {
      "title": "Verlauf"
    }
  }
}
```

And add to `"domain.tabs.page.tabs.button"`:

```json
"checkIn": "Einchecken"
```

**Verify**: `ionic serve` -- navigate to the Check In tab, confirm labels render.

---

### Step 17: Full build verification

```bash
cd /projects/ionstarter && npm run build
cd /projects/ionstarter && npm run lint
```

**Expected**: Zero errors, zero warnings. The check-in domain is lazy-loaded, so the main bundle size should not increase materially.

---

## 7. Tests

Ionstarter uses **Jasmine + Karma** (see `karma.conf.js`). The existing test at `app.component.spec.ts` uses `jasmine.createSpyObj` for mocking.

### Test 1: `check-in.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in/check-in.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { CheckInService } from './check-in.service';
import { GeolocationService } from '../geolocation/geolocation.service';
import { Venue } from '../../models';

describe('CheckInService', () => {
  let service: CheckInService;
  let geolocationSpy: jasmine.SpyObj<GeolocationService>;

  const mockVenues: Venue[] = [
    {
      id: 'v1',
      name: 'Far Venue',
      address: 'Far away',
      category: 'Bar',
      location: { latitude: 48.0, longitude: 9.0 },
      distanceMeters: null,
    },
    {
      id: 'v2',
      name: 'Near Venue',
      address: 'Nearby',
      category: 'Cafe',
      location: { latitude: 47.377, longitude: 8.542 },
      distanceMeters: null,
    },
  ];

  beforeEach(() => {
    geolocationSpy = jasmine.createSpyObj('GeolocationService', [
      'getCurrentLocation',
    ]);
    geolocationSpy.getCurrentLocation.and.resolveTo({
      latitude: 47.3769,
      longitude: 8.5417,
    });

    TestBed.configureTestingModule({
      providers: [
        CheckInService,
        { provide: GeolocationService, useValue: geolocationSpy },
      ],
    });
    service = TestBed.inject(CheckInService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should rank venues by distance (nearest first)', async () => {
    const ranked = await service.rankVenuesByDistance(mockVenues);
    expect(ranked[0].id).toBe('v2');
    expect(ranked[1].id).toBe('v1');
  });

  it('should compute non-null distanceMeters for each venue', async () => {
    const ranked = await service.rankVenuesByDistance(mockVenues);
    for (const venue of ranked) {
      expect(venue.distanceMeters).not.toBeNull();
      expect(venue.distanceMeters).toBeGreaterThan(0);
    }
  });

  it('should call geolocation service', async () => {
    await service.rankVenuesByDistance(mockVenues);
    expect(geolocationSpy.getCurrentLocation).toHaveBeenCalledTimes(1);
  });

  it('should handle empty venue list', async () => {
    const ranked = await service.rankVenuesByDistance([]);
    expect(ranked.length).toBe(0);
  });
});
```

### Test 2: `geolocation.service.spec.ts`

**File**: `src/app/domains/check-in/services/geolocation/geolocation.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { GeolocationService } from './geolocation.service';

describe('GeolocationService', () => {
  let service: GeolocationService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [GeolocationService],
    });
    service = TestBed.inject(GeolocationService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return a location with latitude and longitude', async () => {
    const location = await service.getCurrentLocation();
    expect(location.latitude).toBeDefined();
    expect(location.longitude).toBeDefined();
  });

  it('should return Zurich coordinates (POC mock)', async () => {
    const location = await service.getCurrentLocation();
    expect(location.latitude).toBeCloseTo(47.3769, 2);
    expect(location.longitude).toBeCloseTo(8.5417, 2);
  });
});
```

### Test 3: `check-in.page.spec.ts`

**File**: `src/app/domains/check-in/pages/check-in/check-in.page.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CheckInPage } from './check-in.page';
import { CheckInPageService } from '../../services';
import { provideQueryClientOptions } from '@ngneat/query';
import { getTranslocoModule } from '../../../../widgets/transloco/transloco-testing.module';

describe('CheckInPage', () => {
  let component: CheckInPage;
  let fixture: ComponentFixture<CheckInPage>;
  let checkInPageServiceSpy: jasmine.SpyObj<CheckInPageService>;

  beforeEach(async () => {
    checkInPageServiceSpy = jasmine.createSpyObj('CheckInPageService', [
      'searchVenues',
      'checkIn',
      'navigateToCheckInHistoryPage',
    ]);
    // Provide a minimal result shape for searchVenues
    checkInPageServiceSpy.searchVenues.and.returnValue({
      result: jasmine.createSpy().and.returnValue({ data: [] }),
    } as any);
    checkInPageServiceSpy.checkIn.and.returnValue({
      mutate: jasmine.createSpy(),
    } as any);

    await TestBed.configureTestingModule({
      imports: [CheckInPage],
      providers: [
        { provide: CheckInPageService, useValue: checkInPageServiceSpy },
        provideQueryClientOptions({
          defaultOptions: {
            queries: { retry: false },
          },
        }),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CheckInPage);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
```

> **Note to executor**: The Transloco testing module import path may need adjustment. If ionstarter does not have a `transloco-testing.module.ts`, create one or use `TranslocoTestingModule` from `@jsverse/transloco`. Check if `src/app/widgets/transloco/` exports a testing helper.

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(check-in): add domain models and mock data` | `models/check-in.model.ts`, `models/index.ts`, `check-in.mock.ts` |
| 2 | `feat(check-in): add geolocation adapter service` | `services/geolocation/geolocation.service.ts`, `services/geolocation/geolocation.service.spec.ts` |
| 3 | `feat(check-in): add backend service with TanStack Query` | `services/check-in-backend/check-in-backend.service.ts` |
| 4 | `feat(check-in): add domain service with venue ranking` | `services/check-in/check-in.service.ts`, `services/check-in/check-in.service.spec.ts` |
| 5 | `feat(check-in): add page services for check-in and history` | `services/check-in-page/check-in-page.service.ts`, `services/check-in-history-page/check-in-history-page.service.ts`, `services/index.ts` |
| 6 | `feat(check-in): add check-in and history page components` | `pages/check-in/*`, `pages/check-in-history/*`, `pages/index.ts`, `routes.ts` |
| 7 | `feat(check-in): wire into tabs routing and i18n` | `tabs/routes.ts`, `tabs/pages/*`, `tabs/services/*`, `router.service.ts`, `en.json`, `de.json` |

---

## 9. Verification

After all steps are complete, run these commands from `/projects/ionstarter/`:

```bash
# 1. TypeScript compilation
npx tsc --noEmit
# Expected: 0 errors

# 2. Full build
npm run build
# Expected: Build succeeds, check-in domain is lazily bundled

# 3. Lint
npm run lint
# Expected: 0 errors, 0 warnings

# 4. Unit tests
npm run test:ci
# Expected: All tests pass, including new check-in specs

# 5. Serve and manual verification
ionic serve
# Expected:
#   - Tab bar shows 4 tabs: Home, Tasks, Check In, Settings
#   - Check In tab loads the venue search page
#   - Typing in the searchbar filters venues after 300ms debounce
#   - Tapping the check-in icon on a venue triggers the mutation
#   - Navigate to /check-in/history shows the mock history list
```

---

## 10. Rollback

All changes are within the new `src/app/domains/check-in/` directory plus small modifications to 7 existing files. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -7   # find the 7 commit SHAs
git revert <sha7> <sha6> <sha5> <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~7

# Option 3: Surgical removal
rm -rf src/app/domains/check-in/
git checkout HEAD -- \
  src/app/domains/tabs/routes.ts \
  src/app/domains/tabs/pages/tabs/tabs.page.ts \
  src/app/domains/tabs/pages/tabs/tabs.page.html \
  src/app/domains/tabs/services/tabs-page/tabs-page.service.ts \
  src/app/core/services/router/router.service.ts \
  src/assets/i18n/en.json \
  src/assets/i18n/de.json
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Mock data** | Executor may add/remove mock venues or history items. The structure must match the model types. |
| **Debounce implementation** | Executor may use `rxjs debounceTime` via `Subject` instead of `setTimeout`. Either approach is valid. |
| **Geolocation adapter** | Executor may install `@capacitor/geolocation` and wire a real implementation if desired. The guide prescribes a mock for speed. |
| **Icon choice** | Executor may choose different Ionicons for the tab bar or list items. `location`, `pin`, `navigate` are all acceptable. |
| **Page service vs direct injection** | If the executor prefers the backend service to be injected directly into the page (2-tier instead of 3-tier) to reduce boilerplate for a POC, that is acceptable. The architecture doc prescribes 3-tier but acknowledges this is a proof-of-concept. |
| **Test depth** | Executor may add more tests (encouraged) or simplify the page spec if the Transloco testing setup is complex. Service specs must remain. |
| **SCSS** | Executor may expand or simplify the page styles. The only requirement is `OnPush` and Ionic component usage. |
| **Infinite scroll** | The architecture mentions paginated infinite query for history. For the POC, a simple list is acceptable. Infinite scroll can be a follow-up. |

---

## 12. Out of Scope

- **Real Flask API integration** -- All data is mocked. No HTTP calls to a real backend.
- **SQLite persistence** -- The bubls check-in uses SQLite for local session storage. The ionstarter POC uses TanStack Query (which caches in memory). No SQLite tables.
- **Elf store** -- Check-in has no persistent client-state. If the executor feels it is needed later (e.g., for remembering last-searched venue), it can be added as a follow-up.
- **Relationship check-in logic** -- The bubls check-in is a partner-rating flow. This POC is a venue-based check-in. The domain model is intentionally different.
- **Offline support** -- No service worker, no offline cache, no queue-and-sync.
- **`@capacitor/geolocation` installation** -- The guide uses a mock. Real geolocation is a Task 1 concern (shared platform adapter).
- **RevenueCat / paywall gating** -- No purchase checks before check-in.
- **Analytics / tracking** -- No check-in event tracking.
- **E2E tests** -- Only unit/spec tests are in scope.
- **Other domains** -- Do not modify tasks, home, or settings domains.
