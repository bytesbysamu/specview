# Implementation: Preference Input Flow

**Purpose**: Build the multi-step preference capture wizard that translates what parents care about into structured input for the AI generation engine. This is the core differentiator — no competitor captures preferences before showing results.

**Effort**: 2 days

**Dependencies**: None — this is the first task on the critical path.

**Parallel With**: —

**Blocks**: Task 2 (AI Name Generation Engine) — the generation engine consumes the `PreferenceModel` output from this flow.

**Related**:
- [Solution Architecture](./architecture.md) — Preference Capture component design, wizard pattern
- [Epic](./epic.md) — Task 1 definition, under-60-second completion target

---

## Overview

### What's Included
- `PreferenceModel` — typed interface holding all input dimensions (style, origin, meaning, gender, constraints)
- `PreferencePage` — multi-step wizard using Ionic slides, one preference dimension per step
- On-device caching of preferences via Capacitor Preferences for regeneration
- Navigation from preferences to generation (wired to emit the model, actual generation is Task 2)

### What's NOT Included
- AI generation call — that's Task 2, which consumes the model this task produces
- Results display — Task 3
- Preference learning across sessions — out of MVP scope per [Epic](./epic.md)
- Validation against a name database — Claude IS the algorithm, no static data

---

## Prerequisites

Before starting:
- Constellation boilerplate cloned and running (`ionic serve` works on `localhost:8100`)
- Angular 19 + Ionic 8 + Capacitor 7 project scaffolded from boilerplate
- Familiarity with Ionic's `ion-slides` (Swiper) component or `ion-segment` for step navigation
- Capacitor Preferences plugin installed (`@capacitor/preferences`)

---

## Implementation Steps

### Step 1: Define the PreferenceModel

**File**: `src/app/models/preference.model.ts`

**Purpose**: Create the typed data structure that every downstream component depends on — the generation engine, the API request payload, and the local cache all consume this shape.

This interface is the contract between the preference UI and the generation engine. Keep it flat and serializable — it gets JSON-stringified for both the API request and Capacitor Preferences storage.

**Pattern**:
```typescript
export interface PreferenceModel {
  gender: 'boy' | 'girl' | 'neutral';
  styles: NameStyle[];
  origins: string[];
  meaningThemes: string[];
  startingLetter: string | null;
  siblingNames: string[];
}

export type NameStyle = 'classic' | 'modern' | 'unique' | 'nature' | 'literary' | 'mythological';

export const DEFAULT_PREFERENCES: PreferenceModel = {
  gender: 'neutral',
  styles: [],
  origins: [],
  meaningThemes: [],
  startingLetter: null,
  siblingNames: [],
};
```

Design notes:
- `gender` is the only required field (per [Architecture](./architecture.md) — everything else has sensible defaults or is optional).
- `styles` is an array because parents often want a blend ("modern but not too out there" = `['modern', 'classic']`).
- `origins` is `string[]` rather than an enum to support the long tail of cultural origins without maintaining an exhaustive list. Provide a curated set of common options in the UI but allow free-text entry.
- `siblingNames` is an array of strings — Claude uses these to evaluate phonetic harmony. No validation needed; Claude handles interpretation.

### Step 2: Create the PreferencePage Component

**File**: `src/app/pages/preferences/preferences.page.ts`

**Purpose**: Scaffold the page component that hosts the multi-step wizard. This is the entry point for the entire app experience.

Generate the page using the Ionic CLI to get the module, routing, and template scaffolded:

```bash
ionic generate page pages/preferences
```

The page manages wizard state: which step is active, whether the user can proceed, and the accumulated `PreferenceModel` being built across steps.

**Pattern**:
```typescript
@Component({
  selector: 'app-preferences',
  templateUrl: './preferences.page.html',
  styleUrls: ['./preferences.page.scss'],
})
export class PreferencesPage {
  currentStep = 0;
  totalSteps = 5;
  preferences: PreferenceModel = { ...DEFAULT_PREFERENCES };

  // Step labels for the progress indicator
  steps = ['Gender', 'Style', 'Origin', 'Meaning', 'Details'];

  canProceed(): boolean {
    // Only gender (step 0) is required
    if (this.currentStep === 0) {
      return this.preferences.gender !== null;
    }
    return true; // All other steps are skippable
  }

  next(): void {
    if (this.currentStep < this.totalSteps - 1) {
      this.currentStep++;
    } else {
      this.submit();
    }
  }

  back(): void {
    if (this.currentStep > 0) {
      this.currentStep--;
    }
  }

  skip(): void {
    this.next(); // Same as next — optional steps just advance
  }

  submit(): void {
    // Cache preferences on-device, then navigate to results
    this.cachePreferences();
    this.router.navigate(['/results'], {
      state: { preferences: this.preferences }
    });
  }
}
```

### Step 3: Build the Gender Step (Required)

**File**: `src/app/pages/preferences/preferences.page.html`

**Purpose**: The first and only required step. Three large, tappable options — no dropdown, no form field. This sets the conversational tone for the entire flow.

This step should feel like answering a question, not filling in a field. The visual pattern is three full-width cards or pill buttons with icons.

**Pattern**:
```html
<ion-content>
  <!-- Progress indicator -->
  <div class="progress">
    <div class="progress-bar" [style.width.%]="((currentStep + 1) / totalSteps) * 100"></div>
  </div>

  <!-- Step 0: Gender -->
  <div class="step" *ngIf="currentStep === 0">
    <h1>Who is this name for?</h1>
    <p class="subtitle">This helps us tailor our suggestions</p>

    <div class="option-group">
      <button class="option-card"
              [class.selected]="preferences.gender === 'boy'"
              (click)="preferences.gender = 'boy'">
        <ion-icon name="male-outline"></ion-icon>
        <span>Boy</span>
      </button>
      <button class="option-card"
              [class.selected]="preferences.gender === 'girl'"
              (click)="preferences.gender = 'girl'">
        <ion-icon name="female-outline"></ion-icon>
        <span>Girl</span>
      </button>
      <button class="option-card"
              [class.selected]="preferences.gender === 'neutral'"
              (click)="preferences.gender = 'neutral'">
        <ion-icon name="infinite-outline"></ion-icon>
        <span>Gender-neutral</span>
      </button>
    </div>
  </div>

  <!-- Navigation -->
  <div class="nav-bar">
    <ion-button fill="clear" (click)="back()" *ngIf="currentStep > 0">Back</ion-button>
    <ion-button (click)="next()" [disabled]="!canProceed()">
      {{ currentStep === totalSteps - 1 ? 'Find Names' : 'Next' }}
    </ion-button>
  </div>
</ion-content>
```

Design notes:
- Question-as-heading pattern ("Who is this name for?" not "Select Gender") maintains the conversational feel called out in the [Epic](./epic.md).
- `gender-neutral` is a first-class option, not an afterthought. This matters for both inclusivity and Claude's generation quality — neutral names are a distinct category, not a union of boy and girl names.

### Step 4: Build the Style Step (Optional, Multi-Select)

**File**: `src/app/pages/preferences/preferences.page.html` (continued)

**Purpose**: Capture name style preferences. This is the highest-signal optional input — style preferences directly shape the generation prompt and produce the most noticeable differentiation in results.

Parents can select multiple styles. The UI uses a chip/pill grid — tappable, toggleable, visually lightweight.

**Pattern**:
```html
<!-- Step 1: Style -->
<div class="step" *ngIf="currentStep === 1">
  <h1>What vibe are you going for?</h1>
  <p class="subtitle">Pick as many as you like, or skip</p>

  <div class="chip-grid">
    <ion-chip *ngFor="let style of availableStyles"
              [color]="isStyleSelected(style.value) ? 'primary' : 'medium'"
              (click)="toggleStyle(style.value)">
      <ion-label>{{ style.label }}</ion-label>
    </ion-chip>
  </div>
</div>
```

```typescript
availableStyles = [
  { value: 'classic', label: 'Classic & Timeless' },
  { value: 'modern', label: 'Modern & Fresh' },
  { value: 'unique', label: 'Unique & Uncommon' },
  { value: 'nature', label: 'Nature-Inspired' },
  { value: 'literary', label: 'Literary & Artistic' },
  { value: 'mythological', label: 'Mythological & Heroic' },
];

toggleStyle(style: NameStyle): void {
  const idx = this.preferences.styles.indexOf(style);
  if (idx > -1) {
    this.preferences.styles.splice(idx, 1);
  } else {
    this.preferences.styles.push(style);
  }
}

isStyleSelected(style: NameStyle): boolean {
  return this.preferences.styles.includes(style);
}
```

### Step 5: Build the Origin Step (Optional, Multi-Select with Search)

**File**: `src/app/pages/preferences/preferences.page.html` (continued)

**Purpose**: Capture cultural origin preferences. This is sensitive territory — the UI should present origins respectfully and allow parents to express cultural blending (e.g., "Japanese and Irish heritage").

Use a curated list of common origins as chips, plus a searchable input for the long tail. Multi-select because multicultural families are common.

**Pattern**:
```html
<!-- Step 2: Origin -->
<div class="step" *ngIf="currentStep === 2">
  <h1>Any cultural roots to draw from?</h1>
  <p class="subtitle">Select origins that matter to your family</p>

  <ion-searchbar placeholder="Search origins..."
                 (ionInput)="filterOrigins($event)">
  </ion-searchbar>

  <div class="chip-grid">
    <ion-chip *ngFor="let origin of filteredOrigins"
              [color]="isOriginSelected(origin) ? 'primary' : 'medium'"
              (click)="toggleOrigin(origin)">
      <ion-label>{{ origin }}</ion-label>
    </ion-chip>
  </div>
</div>
```

```typescript
allOrigins = [
  'English', 'Irish', 'Scottish', 'French', 'German', 'Italian', 'Spanish',
  'Portuguese', 'Greek', 'Latin', 'Norse', 'Scandinavian', 'Dutch',
  'Hebrew', 'Arabic', 'Persian', 'Turkish',
  'Hindi', 'Sanskrit', 'Bengali', 'Tamil', 'Urdu',
  'Chinese', 'Japanese', 'Korean', 'Vietnamese', 'Thai',
  'Swahili', 'Yoruba', 'Igbo', 'Amharic', 'Zulu',
  'Hawaiian', 'Maori', 'Native American',
  'Russian', 'Polish', 'Czech', 'Hungarian', 'Romanian',
];

filteredOrigins = [...this.allOrigins];

filterOrigins(event: any): void {
  const query = event.detail.value?.toLowerCase() || '';
  this.filteredOrigins = this.allOrigins.filter(o =>
    o.toLowerCase().includes(query)
  );
}

toggleOrigin(origin: string): void {
  const idx = this.preferences.origins.indexOf(origin);
  if (idx > -1) {
    this.preferences.origins.splice(idx, 1);
  } else {
    this.preferences.origins.push(origin);
  }
}
```

Design notes:
- Origins are strings, not enums, to keep the model flexible. Claude handles any cultural context — the list is for UI convenience, not a constraint.
- The searchbar surfaces less common origins without cluttering the default view.

### Step 6: Build the Meaning Step (Optional, Multi-Select)

**File**: `src/app/pages/preferences/preferences.page.html` (continued)

**Purpose**: Capture what themes or qualities parents want the name to evoke. This is the most "conversational" step — it's asking "what do you want this name to *feel* like?"

**Pattern**:
```html
<!-- Step 3: Meaning -->
<div class="step" *ngIf="currentStep === 3">
  <h1>What should the name evoke?</h1>
  <p class="subtitle">Themes and qualities that resonate with you</p>

  <div class="chip-grid">
    <ion-chip *ngFor="let theme of availableThemes"
              [color]="isThemeSelected(theme) ? 'primary' : 'medium'"
              (click)="toggleTheme(theme)">
      <ion-label>{{ theme }}</ion-label>
    </ion-chip>
  </div>
</div>
```

```typescript
availableThemes = [
  'Strength', 'Wisdom', 'Grace', 'Joy', 'Peace', 'Courage',
  'Nature', 'Light', 'Love', 'Hope', 'Freedom', 'Beauty',
  'Adventure', 'Faith', 'Honor', 'Creativity', 'Resilience',
];

toggleTheme(theme: string): void {
  const idx = this.preferences.meaningThemes.indexOf(theme);
  if (idx > -1) {
    this.preferences.meaningThemes.splice(idx, 1);
  } else {
    this.preferences.meaningThemes.push(theme);
  }
}
```

### Step 7: Build the Details Step (Optional Constraints)

**File**: `src/app/pages/preferences/preferences.page.html` (continued)

**Purpose**: Capture specific constraints — starting letter and sibling names. These are the "power user" inputs that most parents skip but some care deeply about. Grouped on a single step to keep the wizard short.

**Pattern**:
```html
<!-- Step 4: Details -->
<div class="step" *ngIf="currentStep === 4">
  <h1>Any specifics?</h1>
  <p class="subtitle">Totally optional — skip if you're open to anything</p>

  <ion-list lines="none">
    <ion-item>
      <ion-label position="stacked">Starting letter</ion-label>
      <ion-input placeholder="e.g. A, M, S..."
                 maxlength="1"
                 [value]="preferences.startingLetter"
                 (ionInput)="setStartingLetter($event)">
      </ion-input>
    </ion-item>

    <ion-item>
      <ion-label position="stacked">Sibling names to harmonize with</ion-label>
      <ion-input placeholder="e.g. Oliver, Luna"
                 (ionInput)="setSiblingInput($event)"
                 (keyup.enter)="addSibling()">
      </ion-input>
    </ion-item>

    <div class="sibling-chips" *ngIf="preferences.siblingNames.length > 0">
      <ion-chip *ngFor="let name of preferences.siblingNames"
                (click)="removeSibling(name)">
        <ion-label>{{ name }}</ion-label>
        <ion-icon name="close-circle"></ion-icon>
      </ion-chip>
    </div>
  </ion-list>
</div>
```

```typescript
siblingInput = '';

setStartingLetter(event: any): void {
  const val = event.detail.value?.toUpperCase() || null;
  this.preferences.startingLetter = val && val.length > 0 ? val[0] : null;
}

setSiblingInput(event: any): void {
  this.siblingInput = event.detail.value || '';
}

addSibling(): void {
  const name = this.siblingInput.trim();
  if (name && !this.preferences.siblingNames.includes(name)) {
    this.preferences.siblingNames.push(name);
  }
  this.siblingInput = '';
}

removeSibling(name: string): void {
  this.preferences.siblingNames = this.preferences.siblingNames.filter(n => n !== name);
}
```

### Step 8: Cache Preferences On-Device

**File**: `src/app/services/preference-cache.service.ts`

**Purpose**: Persist preferences to Capacitor Preferences so parents don't re-enter them when regenerating or returning to the app. This is the local-first pattern from the [Architecture](./architecture.md).

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { Preferences } from '@capacitor/preferences';
import { PreferenceModel, DEFAULT_PREFERENCES } from '../models/preference.model';

const STORAGE_KEY = 'user_preferences';

@Injectable({ providedIn: 'root' })
export class PreferenceCacheService {

  async save(prefs: PreferenceModel): Promise<void> {
    await Preferences.set({
      key: STORAGE_KEY,
      value: JSON.stringify(prefs),
    });
  }

  async load(): Promise<PreferenceModel> {
    const { value } = await Preferences.get({ key: STORAGE_KEY });
    if (value) {
      return JSON.parse(value) as PreferenceModel;
    }
    return { ...DEFAULT_PREFERENCES };
  }

  async clear(): Promise<void> {
    await Preferences.remove({ key: STORAGE_KEY });
  }
}
```

Wire into `PreferencesPage`:

```typescript
constructor(
  private router: Router,
  private prefCache: PreferenceCacheService,
) {}

async ngOnInit(): Promise<void> {
  // Restore cached preferences if returning user
  this.preferences = await this.prefCache.load();
}

async submit(): Promise<void> {
  await this.prefCache.save(this.preferences);
  this.router.navigate(['/results'], {
    state: { preferences: this.preferences }
  });
}
```

### Step 9: Add Styling

**File**: `src/app/pages/preferences/preferences.page.scss`

**Purpose**: Make the wizard feel conversational and mobile-native. The key visual principles: large tap targets, breathing room between elements, and clear progress.

**Pattern**:
```scss
:host {
  --step-padding: 24px;
}

.progress {
  height: 4px;
  background: var(--ion-color-light);
  margin: 0;

  .progress-bar {
    height: 100%;
    background: var(--ion-color-primary);
    transition: width 0.3s ease;
  }
}

.step {
  padding: var(--step-padding);
  padding-top: 48px;

  h1 {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 8px;
    line-height: 1.2;
  }

  .subtitle {
    font-size: 16px;
    color: var(--ion-color-medium);
    margin-bottom: 32px;
  }
}

.option-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.option-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 16px;
  border: 2px solid var(--ion-color-light);
  background: var(--ion-background-color);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s;

  &.selected {
    border-color: var(--ion-color-primary);
    background: var(--ion-color-primary-tint);
  }

  ion-icon {
    font-size: 24px;
  }
}

.chip-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.nav-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  padding: 16px var(--step-padding);
  padding-bottom: calc(16px + var(--ion-safe-area-bottom));
  background: var(--ion-background-color);
  border-top: 1px solid var(--ion-color-light);
}

.sibling-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
```

### Step 10: Configure Routing

**File**: `src/app/app-routing.module.ts`

**Purpose**: Set the preferences page as the default landing route. New users start here; returning users with cached preferences can be redirected past it (future optimization, not MVP).

**Pattern**:
```typescript
const routes: Routes = [
  {
    path: '',
    redirectTo: 'preferences',
    pathMatch: 'full',
  },
  {
    path: 'preferences',
    loadChildren: () =>
      import('./pages/preferences/preferences.module')
        .then(m => m.PreferencesPageModule),
  },
  {
    path: 'results',
    loadChildren: () =>
      import('./pages/results/results.module')
        .then(m => m.ResultsPageModule),  // Task 3 creates this
  },
];
```

---

## Verification

How to verify this implementation works:

```bash
# Start the dev server
ionic serve
```

**Manual walkthrough** (target: under 60 seconds end-to-end):

1. App loads on the Gender step. Tap "Girl" — the card highlights, Next button enables.
2. Tap Next. Style step appears. Select "Modern & Fresh" and "Nature-Inspired". Tap Next.
3. Origin step appears. Type "Jap" in search — "Japanese" filters to top. Tap it. Tap Next.
4. Meaning step appears. Select "Grace" and "Strength". Tap Next.
5. Details step appears. Type "E" for starting letter. Type "Oliver" + Enter for sibling. Chip appears. Tap "Find Names".
6. App navigates to `/results` with the full `PreferenceModel` in router state.

**Verify caching**:

7. Kill and restart the app. Navigate to `/preferences` — the previously entered values should be pre-filled from Capacitor Preferences.

**Verify skip behavior**:

8. Start fresh (clear storage). Select gender, then tap Skip through all remaining steps. The model should submit with only `gender` set and all other fields at defaults.

**Expected console output on submit** (add a `console.log` during development):
```json
{
  "gender": "girl",
  "styles": ["modern", "nature"],
  "origins": ["Japanese"],
  "meaningThemes": ["Grace", "Strength"],
  "startingLetter": "E",
  "siblingNames": ["Oliver"]
}
```

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 as done
2. Proceed to **Task 2: AI Name Generation Engine** — it consumes the `PreferenceModel` this task produces, constructing the Claude prompt from the structured preferences

---

## Related Documents

- [Solution Architecture](./architecture.md) — Preference Capture component design, wizard pattern, PreferenceModel definition
- [Epic](./epic.md) — Task 1 scope, under-60-second target, skip-friendly requirement
- [Analysis](./analysis.md) — Problems driving this feature: preference capture is nonexistent in the category
- [Timeline](./timeline.md) — Status tracking