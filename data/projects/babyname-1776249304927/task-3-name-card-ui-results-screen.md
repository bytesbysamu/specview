Now I have all the context needed. Let me generate the implementation guide.

# Implementation: Name Card UI + Results Screen

**Purpose**: Build the results page that renders AI-generated names as scrollable cards with full metadata — name, pronunciation, origin, meaning, popularity indicator, and the personalized rationale — and provides save-to-favorites functionality on each card. The rationale prominence is what separates this product from every static name database.

**Effort**: 1 day

**Dependencies**: Task 2 (AI Name Generation Engine) — the `NameCard` interface and `GenerationResponse` shape define the data contract this task renders.

**Parallel With**: Task 4 (Favorites + Partner Sharing) — both consume the `NameCard` data structure independently. Task 4 builds the `FavoritesPage`; this task builds the save action that feeds into it.

**Blocks**: Task 5 (Paywall + Subscription) — the paywall gates access to generation, which surfaces through this results screen.

**Related**:
- [Solution Architecture](./architecture.md) — Name Card Display component design, cards-are-immutable pattern
- [Epic](./epic.md) — Task 3 definition, success criteria requiring all metadata fields visible

---

## Overview

### What's Included
- `ResultsPage` — scrollable card list consuming the generation response passed via router state
- `NameCardComponent` — standalone component rendering a single name with all metadata fields
- Popularity badge with visual differentiation (common, rising, rare)
- Save-to-favorites action per card with `FavoritesService` integration
- Loading state for the generation wait (shown when navigating from preferences)
- Empty state and error state handling
- "Generate Again" action to re-run with the same preferences
- Regeneration count indicator (`generationsRemaining`)

### What's NOT Included
- Swipe-to-dismiss or Tinder-style card interaction — scrollable list is simpler and lets parents compare cards side-by-side; swipe mechanics are a post-validation UX experiment
- Favorites page or favorites management — Task 4 builds the full `FavoritesPage`; this task only writes to the service
- Share action on individual cards — sharing operates on the full favorites list (Task 4), not individual names
- Paywall interstitial — Task 5 wires the gate based on `generationsRemaining`

---

## Prerequisites

Before starting:
- Task 2 complete — `NameCard` interface exists in `src/app/models/name-card.model.ts`, `GenerationService` exists, and the backend returns valid `GenerationResponse` JSON
- Task 1 complete — `PreferenceModel` and `PreferencePage` exist, router state carries `names`, `generationsRemaining`, and `preferences` to the results route
- Ionic 8 components available: `ion-card`, `ion-chip`, `ion-icon`, `ion-fab`, `ion-spinner`
- Capacitor Preferences plugin installed (for the `FavoritesService`)

---

## Implementation Steps

### Step 1: Create the FavoritesService

**File**: `src/app/services/favorites.service.ts`

**Purpose**: On-device persistence for saved name cards using Capacitor Preferences. This service is consumed by the results page (this task) for the save action and by the favorites page (Task 4) for the list display. Building it here keeps the save action functional immediately.

Per [Architecture](./architecture.md), favoriting copies the full card data to local storage rather than storing a reference — there's no server-side card persistence to reference against.

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { Preferences } from '@capacitor/preferences';
import { NameCard } from '../models/name-card.model';
import { BehaviorSubject } from 'rxjs';

const FAVORITES_KEY = 'favorites';

@Injectable({ providedIn: 'root' })
export class FavoritesService {

  private favoritesSubject = new BehaviorSubject<NameCard[]>([]);
  favorites$ = this.favoritesSubject.asObservable();

  async load(): Promise<void> {
    const { value } = await Preferences.get({ key: FAVORITES_KEY });
    const favorites = value ? JSON.parse(value) : [];
    this.favoritesSubject.next(favorites);
  }

  async add(card: NameCard): Promise<void> {
    const current = this.favoritesSubject.value;
    // Deduplicate by name — a parent won't favorite the same name twice
    if (current.some(f => f.name === card.name)) return;
    const updated = [...current, card];
    await this.save(updated);
  }

  async remove(name: string): Promise<void> {
    const updated = this.favoritesSubject.value.filter(f => f.name !== name);
    await this.save(updated);
  }

  isFavorited(name: string): boolean {
    return this.favoritesSubject.value.some(f => f.name === name);
  }

  private async save(favorites: NameCard[]): Promise<void> {
    await Preferences.set({ key: FAVORITES_KEY, value: JSON.stringify(favorites) });
    this.favoritesSubject.next(favorites);
  }
}
```

Design notes:
- `BehaviorSubject` provides reactive updates — the heart icon on each card toggles immediately when tapped.
- Deduplication by `name` string is sufficient. Two different generations could theoretically produce the same name with different rationale, but parents won't notice or care.
- `load()` is called once at app startup (or on first access). Task 4 can call it again when displaying the favorites page.
- The entire favorites list is serialized as one JSON blob. At tens of names, this is negligible storage.

### Step 2: Create the NameCard Component

**File**: `src/app/components/name-card/name-card.component.ts`

**Purpose**: Standalone, reusable component that renders a single name card with all metadata. Used by the results page (this task) and reused by the favorites page (Task 4). The rationale section gets visual prominence — it's the product differentiator.

Generate the component:
```bash
ionic generate component components/name-card
```

**Pattern**:
```typescript
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { NameCard } from '../../models/name-card.model';

@Component({
  selector: 'app-name-card',
  standalone: true,
  imports: [CommonModule, IonicModule],
  template: `
    <ion-card>
      <ion-card-header>
        <div class="card-top-row">
          <ion-card-title class="name-title">{{ card.name }}</ion-card-title>
          <ion-button fill="clear" (click)="toggleFavorite()">
            <ion-icon
              [name]="isFavorited ? 'heart' : 'heart-outline'"
              [color]="isFavorited ? 'danger' : 'medium'"
              size="large"
            ></ion-icon>
          </ion-button>
        </div>
        <ion-card-subtitle class="pronunciation">{{ card.pronunciation }}</ion-card-subtitle>
      </ion-card-header>

      <ion-card-content>
        <div class="metadata-row">
          <ion-chip [outline]="true">
            <ion-icon name="globe-outline"></ion-icon>
            <ion-label>{{ card.origin }}</ion-label>
          </ion-chip>
          <ion-chip [outline]="true" [color]="popularityColor">
            <ion-icon [name]="popularityIcon"></ion-icon>
            <ion-label>{{ card.popularity }}</ion-label>
          </ion-chip>
        </div>

        <p class="meaning">
          <strong>Meaning:</strong> {{ card.meaning }}
        </p>

        <div class="rationale">
          <p>{{ card.rationale }}</p>
        </div>
      </ion-card-content>
    </ion-card>
  `,
  styles: [`
    .card-top-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .name-title {
      font-size: 1.8rem;
      font-weight: 700;
    }
    .pronunciation {
      font-style: italic;
      color: var(--ion-color-medium);
    }
    .metadata-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }
    .meaning {
      margin-bottom: 12px;
      color: var(--ion-text-color);
    }
    .rationale {
      background: var(--ion-color-light);
      border-radius: 8px;
      padding: 12px;
      border-left: 3px solid var(--ion-color-primary);
    }
    .rationale p {
      margin: 0;
      line-height: 1.5;
      color: var(--ion-text-color);
    }
  `]
})
export class NameCardComponent {
  @Input() card!: NameCard;
  @Input() isFavorited = false;
  @Output() favorite = new EventEmitter<NameCard>();

  get popularityColor(): string {
    switch (this.card.popularity) {
      case 'common': return 'primary';
      case 'rising': return 'warning';
      case 'rare': return 'tertiary';
      default: return 'medium';
    }
  }

  get popularityIcon(): string {
    switch (this.card.popularity) {
      case 'common': return 'people-outline';
      case 'rising': return 'trending-up-outline';
      case 'rare': return 'diamond-outline';
      default: return 'help-outline';
    }
  }

  toggleFavorite(): void {
    this.favorite.emit(this.card);
  }
}
```

Design notes:
- The rationale section uses a left-border accent and tinted background to draw the eye. This is the "why it fits" content that no competitor offers — it needs to be the most visually prominent metadata after the name itself.
- Popularity chips use color + icon coding: `common` (blue, people), `rising` (amber, trending-up), `rare` (purple, diamond). These map to emotional associations — parents looking for unique names gravitate toward the purple "rare" badge.
- The favorite button is inside the card header, not in a swipe action or separate row. One-tap save, no gestures to discover.
- Standalone component with inline template. The card is simple enough that a separate HTML file adds indirection without value.

### Step 3: Create the Results Page

**File**: `src/app/pages/results/results.page.ts`

**Purpose**: The main results screen that receives generation output via router state and renders a scrollable list of `NameCardComponent` instances. Handles three states: loading (if generation is in progress), results (cards rendered), and error (generation failed).

Generate the page:
```bash
ionic generate page pages/results
```

**Pattern**:
```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule } from '@ionic/angular';
import { Router } from '@angular/router';
import { NameCard } from '../../models/name-card.model';
import { PreferenceModel } from '../../models/preference.model';
import { FavoritesService } from '../../services/favorites.service';
import { GenerationService } from '../../services/generation.service';
import { DeviceService } from '../../services/device.service';
import { NameCardComponent } from '../../components/name-card/name-card.component';

@Component({
  selector: 'app-results',
  standalone: true,
  imports: [CommonModule, IonicModule, NameCardComponent],
  template: `
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-back-button defaultHref="/preferences"></ion-back-button>
        </ion-buttons>
        <ion-title>Your Names</ion-title>
        <ion-buttons slot="end">
          <ion-button (click)="navigateToFavorites()" *ngIf="getFavoriteCount() > 0">
            <ion-icon name="heart" color="danger"></ion-icon>
            <ion-badge color="danger">{{ getFavoriteCount() }}</ion-badge>
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <!-- Loading State -->
      <div class="state-container" *ngIf="isLoading">
        <ion-spinner name="crescent" color="primary"></ion-spinner>
        <p>Finding perfect names...</p>
      </div>

      <!-- Error State -->
      <div class="state-container" *ngIf="error">
        <ion-icon name="cloud-offline-outline" size="large" color="medium"></ion-icon>
        <p>{{ error }}</p>
        <ion-button (click)="regenerate()" fill="outline">Try Again</ion-button>
      </div>

      <!-- Results -->
      <div *ngIf="!isLoading && !error && names.length > 0">
        <div class="results-header" *ngIf="generationsRemaining !== null">
          <ion-note>
            {{ generationsRemaining }} free generation{{ generationsRemaining !== 1 ? 's' : '' }} remaining
          </ion-note>
        </div>

        <app-name-card
          *ngFor="let card of names; trackBy: trackByName"
          [card]="card"
          [isFavorited]="favoritesService.isFavorited(card.name)"
          (favorite)="onFavorite($event)"
        ></app-name-card>

        <div class="actions-footer">
          <ion-button
            expand="block"
            (click)="regenerate()"
            [disabled]="isLoading"
          >
            <ion-icon name="refresh-outline" slot="start"></ion-icon>
            Generate More Names
          </ion-button>
        </div>
      </div>

      <!-- Empty State (shouldn't happen, but defensive) -->
      <div class="state-container" *ngIf="!isLoading && !error && names.length === 0">
        <ion-icon name="search-outline" size="large" color="medium"></ion-icon>
        <p>No names generated. Try adjusting your preferences.</p>
        <ion-button routerLink="/preferences" fill="outline">Edit Preferences</ion-button>
      </div>
    </ion-content>
  `,
  styles: [`
    .state-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 60vh;
      text-align: center;
      padding: 0 24px;
    }
    .state-container p {
      margin-top: 16px;
      color: var(--ion-color-medium);
      font-size: 1.1rem;
    }
    .results-header {
      text-align: center;
      padding: 12px 16px 4px;
    }
    .actions-footer {
      padding: 16px;
      padding-bottom: 32px;
    }
  `]
})
export class ResultsPage implements OnInit {
  names: NameCard[] = [];
  preferences: PreferenceModel | null = null;
  generationsRemaining: number | null = null;
  isLoading = false;
  error: string | null = null;

  constructor(
    private router: Router,
    public favoritesService: FavoritesService,
    private generationService: GenerationService,
    private deviceService: DeviceService,
  ) {}

  ngOnInit(): void {
    this.favoritesService.load();

    const nav = this.router.getCurrentNavigation();
    const state = nav?.extras?.state;

    if (state && state['names']) {
      this.names = state['names'];
      this.generationsRemaining = state['generationsRemaining'] ?? null;
      this.preferences = state['preferences'] ?? null;
    } else {
      // Direct navigation without state — redirect to preferences
      this.router.navigate(['/preferences']);
    }
  }

  async regenerate(): Promise<void> {
    if (!this.preferences) {
      this.router.navigate(['/preferences']);
      return;
    }

    this.isLoading = true;
    this.error = null;

    const deviceId = await this.deviceService.getDeviceId();

    this.generationService.generate(this.preferences, deviceId).subscribe({
      next: (response) => {
        this.names = response.names;
        this.generationsRemaining = response.generationsRemaining;
        this.isLoading = false;
      },
      error: () => {
        this.error = 'Something went wrong generating names. Please try again.';
        this.isLoading = false;
      }
    });
  }

  async onFavorite(card: NameCard): Promise<void> {
    if (this.favoritesService.isFavorited(card.name)) {
      await this.favoritesService.remove(card.name);
    } else {
      await this.favoritesService.add(card);
    }
  }

  getFavoriteCount(): number {
    return this.favoritesService['favoritesSubject'].value.length;
  }

  navigateToFavorites(): void {
    this.router.navigate(['/favorites']);
  }

  trackByName(_index: number, card: NameCard): string {
    return card.name;
  }
}
```

Design notes:
- Router state is the data transport — no service intermediary or state store. The preferences page passes `names`, `generationsRemaining`, and `preferences` via `router.navigate state`. This is deliberate simplicity: there's no reason to persist results in a service when they're ephemeral per generation.
- If someone deep-links to `/results` without state, the guard redirects to `/preferences`. No error page needed.
- The "Generate More Names" button calls `regenerate()` which re-posts the same preferences. Each tap produces a different set of names from Claude — no deduplication against previous results. Parents expect fresh suggestions on each tap.
- `generationsRemaining` is displayed as a gentle note, not a blocker. Task 5 adds the hard paywall gate.
- `trackByName` optimizes the `*ngFor` — when regenerating, Angular can diff by name string rather than re-rendering all cards.
- `getFavoriteCount()` directly reads from the BehaviorSubject. For the favorites badge in the header, this is adequate. A cleaner approach would use an `async` pipe, but the count is simple enough to read synchronously.

### Step 4: Add the Results Route

**File**: `src/app/app-routing.module.ts` (or `app.routes.ts` if using standalone routing)

**Purpose**: Register the `/results` route so navigation from preferences works.

**Pattern**:
```typescript
{
  path: 'results',
  loadComponent: () =>
    import('./pages/results/results.page').then(m => m.ResultsPage),
},
```

Place this alongside the existing `preferences` route. The results page uses `defaultHref="/preferences"` for the back button, so no additional guard configuration is needed.

### Step 5: Add a Loading Transition

**File**: `src/app/pages/preferences/preferences.page.ts` (extend — already modified in Task 2)

**Purpose**: Enhance the loading experience during the 3-8 second Claude API call. The spinner from Task 2 is functional but minimal. Replace it with a full-screen overlay that sets expectations.

**Pattern**:
```html
<!-- Add to preferences.page.html or inline template -->
<div class="generating-overlay" *ngIf="isGenerating">
  <div class="generating-content">
    <ion-spinner name="crescent" color="primary"></ion-spinner>
    <h2>Finding names for you...</h2>
    <p>This takes a few seconds</p>
  </div>
</div>
```

```css
.generating-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--ion-background-color);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
  text-align: center;
}
.generating-content h2 {
  margin-top: 24px;
  font-weight: 600;
}
.generating-content p {
  color: var(--ion-color-medium);
}
```

Design notes:
- A full-screen overlay rather than just a button spinner. The 3-8 second wait is long enough that parents need reassurance the app is working, not frozen.
- "This takes a few seconds" sets expectations. Don't use a progress bar — there's no real progress to track with a single API call.
- The overlay uses the app background color, not a semi-transparent modal. This feels like a screen transition rather than a dialog.

### Step 6: Handle Error in Generation Navigation

**File**: `src/app/pages/preferences/preferences.page.ts` (extend the error handler from Task 2)

**Purpose**: Surface generation failures to the user with a toast rather than a console.error. The preferences page stays visible so the parent can retry.

**Pattern**:
```typescript
import { ToastController } from '@ionic/angular';

// In constructor:
constructor(
  // ...existing deps
  private toastController: ToastController,
) {}

// Replace the error handler in submit():
error: async (err) => {
  this.isGenerating = false;
  const toast = await this.toastController.create({
    message: 'Could not generate names. Please try again.',
    duration: 3000,
    position: 'bottom',
    color: 'danger',
  });
  await toast.present();
}
```

Design notes:
- A toast is non-blocking — it doesn't require dismissal, and the parent can immediately retry. A modal or alert would feel heavy for a transient network error.
- 3 seconds is enough to read the message. The parent's natural next action is tapping "Find Names" again.

---

## Verification

How to verify this implementation works:

### Component rendering:

```bash
# Terminal 1: Backend
cd backend && python app.py

# Terminal 2: Frontend
ionic serve
```

1. Navigate to `/preferences`, fill out preferences (at minimum, select a gender)
2. Tap "Find Names"
3. Verify the full-screen loading overlay appears with spinner and text
4. After 3-8 seconds, the results page renders with name cards

**Expected Result**:
- Each card shows: name (large), pronunciation (italic), origin chip, popularity chip with color, meaning, and rationale in an accented box
- Rationale text references the preferences you entered (e.g., mentions "modern" if you selected that style)
- Popularity chips are color-coded: blue for common, amber for rising, purple for rare
- The "generations remaining" note appears below the header

### Favorites interaction:

1. Tap the heart icon on a name card
2. Heart fills red, indicating saved
3. Tap again — heart returns to outline, indicating removed
4. The favorites badge in the header shows the count of saved names
5. Navigate away and back — favorites persist (Capacitor Preferences)

**Expected Result**: Heart toggles instantly. Badge count updates. Favorites survive page navigation.

### Regeneration:

1. From the results page, tap "Generate More Names"
2. Loading state appears (spinner replaces card list)
3. New set of names renders — different from the first set
4. `generationsRemaining` decrements by 1

**Expected Result**: Each regeneration produces different names. The counter decreases.

### Error handling:

1. Stop the backend (`ctrl+c`)
2. From preferences, tap "Find Names"
3. A danger toast appears: "Could not generate names. Please try again."
4. Restart the backend, tap again — generation succeeds

**Expected Result**: The app doesn't crash or freeze. The toast disappears after 3 seconds.

### Edge cases:

1. Navigate directly to `/results` (type the URL) — should redirect to `/preferences`
2. Generate with minimal preferences (gender only) — should produce valid name cards
3. Save all 8 names as favorites, then regenerate — previous favorites remain, new cards show unfilled hearts

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 as done
2. Proceed to **Task 5: Paywall + Subscription** (next on critical path) — it gates the "Generate More Names" action based on `generationsRemaining`
3. **Task 4: Favorites + Partner Sharing** can proceed in parallel — it builds the `FavoritesPage` that the header badge links to, and the share action that posts favorites to the backend

---

## Related Documents

- [Solution Architecture](./architecture.md) — Name Card Display component design, cards-are-immutable pattern, local-first favorites
- [Epic](./epic.md) — Task 3 scope, success criteria requiring all metadata fields visible
- [Task 2: AI Name Generation Engine](./task-2-ai-name-generation-engine.md) — Produces the `NameCard[]` and `GenerationResponse` this task renders
- [Timeline](./timeline.md) — Status tracking