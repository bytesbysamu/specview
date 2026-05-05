Now I have everything I need. Let me generate the implementation guide.

# 🛠️ Task 1: Shell scaffold + navigation

**Purpose**: Evolve the existing Bubls codebase into a multi-route super app shell with tab navigation, dark theme, and a feature-as-route registry — the structural foundation that Tasks 2–5 all build against.

**Effort**: 1 day

**Dependencies**: None

**Parallel With**: —

**Blocks**: Task 2 (Auth + user model), Task 3 (/photoshoot route), Task 4 (Deploy), Task 5 (LoRA models)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Tab-based navigation shell with dynamic route registration
- Dark theme global styles
- Shared layout component (header + content area + tab bar)
- Feature route registry pattern (array-driven, shell never imports feature code)
- Placeholder home route and placeholder photoshoot route (empty pages, wired to tabs)
- Capacitor config updated for super app identity

### What's NOT Included
- Auth or user model — Task 2 adds `AuthGuard` and `UserStore` into the shell
- Actual /photoshoot implementation — Task 3 builds the camera/inference page
- Feature gating logic — The `AuthGuard` that reads `enabled_features` comes with Task 2; the shell only provides the registration hook
- iOS build/deploy — Task 4 handles TestFlight submission

---

## Prerequisites

Before starting:
- Existing Bubls codebase cloned locally (Angular 19 + Ionic 8 + Capacitor 8)
- Node 20+, `@ionic/cli`, `@angular/cli`, `@capacitor/cli` installed
- The codebase builds and serves (`ionic serve` or `ng serve`)

---

## Implementation Steps

### Step 1: Update Capacitor identity

**File**: `capacitor.config.ts`

**Purpose**: The app identity stays on `ch.bubls.app` (per Architecture — repurpose, don't register new) but the display name changes to reflect the super app. This preserves the existing TestFlight group and provisioning profile.

**Pattern**:
```typescript
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ch.bubls.app',
  appName: 'Bubls',        // Keep for now — App Store metadata update is Task 4
  webDir: 'www',
  server: {
    androidScheme: 'https'
  }
};

export default config;
```

No change to `appId` — existing TestFlight testers get the update automatically. The `appName` can be updated later when the branding is finalized.

---

### Step 2: Define the feature route registry

**File**: `src/app/shell/feature-registry.ts`

**Purpose**: The central contract that decouples the shell from feature knowledge. Every feature is an entry in this array — the shell reads it to build tabs and routes. Adding a new feature means adding one entry here and one lazy-loaded page component. The shell never imports feature-specific code.

**Pattern**:
```typescript
export interface FeatureRoute {
  path: string;          // URL segment: 'photoshoot'
  label: string;         // Tab label: 'Photoshoot'
  icon: string;          // Ionic icon name: 'camera-outline'
  featureKey: string;    // Maps to enabled_features['photoshoot'] — used by AuthGuard in Task 2
  loadComponent: () => Promise<any>;  // Lazy import
}

export const FEATURE_ROUTES: FeatureRoute[] = [
  {
    path: 'home',
    label: 'Home',
    icon: 'home-outline',
    featureKey: 'home',    // Always enabled — not gated
    loadComponent: () => import('../pages/home/home.page').then(m => m.HomePage),
  },
  {
    path: 'photoshoot',
    label: 'Photoshoot',
    icon: 'camera-outline',
    featureKey: 'photoshoot',
    loadComponent: () => import('../pages/photoshoot/photoshoot.page').then(m => m.PhotoshootPage),
  },
];
```

Month 2 adds entries for `/humanize` and `/headshot` — no shell code changes.

---

### Step 3: Build the app routes from the registry

**File**: `src/app/app.routes.ts`

**Purpose**: Translate the feature registry into Angular routes. Each feature is lazy-loaded. The tab layout wraps all feature routes. A wildcard redirect catches unknown paths.

**Pattern**:
```typescript
import { Routes } from '@angular/router';
import { FEATURE_ROUTES } from './shell/feature-registry';

const featureChildren: Routes = FEATURE_ROUTES.map(feature => ({
  path: feature.path,
  loadComponent: feature.loadComponent,
  // Task 2 adds: canActivate: [authGuard(feature.featureKey)]
}));

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./shell/shell-layout.component').then(m => m.ShellLayoutComponent),
    children: [
      { path: '', redirectTo: 'home', pathMatch: 'full' },
      ...featureChildren,
    ],
  },
  { path: '**', redirectTo: '' },
];
```

The `canActivate` guard is a placeholder comment — Task 2 wires in the `AuthGuard` that checks `enabled_features[featureKey]`.

---

### Step 4: Create the shell layout component

**File**: `src/app/shell/shell-layout.component.ts`

**Purpose**: The shared chrome that all feature routes render inside — header and tab bar. This is the `ShellLayoutComponent` from the Architecture. It reads the feature registry to build tabs dynamically, so new features appear in the tab bar automatically.

**Pattern**:
```typescript
import { Component } from '@angular/core';
import { IonTabs, IonTabBar, IonTabButton, IonIcon, IonLabel,
         IonHeader, IonToolbar, IonTitle, IonRouterOutlet } from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { homeOutline, cameraOutline } from 'ionicons/icons';
import { FEATURE_ROUTES } from './feature-registry';

@Component({
  selector: 'app-shell-layout',
  standalone: true,
  imports: [IonTabs, IonTabBar, IonTabButton, IonIcon, IonLabel,
            IonHeader, IonToolbar, IonTitle, IonRouterOutlet],
  template: `
    <ion-header>
      <ion-toolbar>
        <ion-title>bubls</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-tabs>
      <ion-tab-bar slot="bottom">
        @for (feature of features; track feature.path) {
          <ion-tab-button [tab]="feature.path">
            <ion-icon [name]="feature.icon"></ion-icon>
            <ion-label>{{ feature.label }}</ion-label>
          </ion-tab-button>
        }
      </ion-tab-bar>
    </ion-tabs>
  `,
})
export class ShellLayoutComponent {
  features = FEATURE_ROUTES;

  constructor() {
    addIcons({ homeOutline, cameraOutline });
  }
}
```

As new features register in `FEATURE_ROUTES`, their icons need to be added to `addIcons()`. This is the one manual step per feature — Ionicons requires explicit registration for tree-shaking.

---

### Step 5: Create placeholder page components

**File**: `src/app/pages/home/home.page.ts`

**Purpose**: Minimal home route so the shell has something to render. Task 2 and beyond will flesh this out with user info and feature cards.

**Pattern**:
```typescript
import { Component } from '@angular/core';
import { IonContent, IonText } from '@ionic/angular/standalone';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [IonContent, IonText],
  template: `
    <ion-content class="ion-padding">
      <ion-text>
        <h2>Welcome to Bubls</h2>
        <p>Your AI features, one app.</p>
      </ion-text>
    </ion-content>
  `,
})
export class HomePage {}
```

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

**Purpose**: Placeholder for the /photoshoot route. Task 3 replaces this with the camera capture + inference + gallery implementation.

**Pattern**:
```typescript
import { Component } from '@angular/core';
import { IonContent, IonText } from '@ionic/angular/standalone';

@Component({
  selector: 'app-photoshoot',
  standalone: true,
  imports: [IonContent, IonText],
  template: `
    <ion-content class="ion-padding">
      <ion-text>
        <h2>Photoshoot</h2>
        <p>Camera + LoRA inference coming in Task 3.</p>
      </ion-text>
    </ion-content>
  `,
})
export class PhotoshootPage {}
```

Both pages are standalone components with zero dependencies — they lazy-load independently and don't import anything from the shell or each other.

---

### Step 6: Update AppComponent to minimal root

**File**: `src/app/app.component.ts`

**Purpose**: Strip the existing Bubls `AppComponent` down to a bare root. The shell layout lives in `ShellLayoutComponent` (loaded via routing), so the root component is just the Ionic app wrapper with a router outlet. Remove any Bubls-specific content (event cards, signal subscriptions, etc.).

**Pattern**:
```typescript
import { Component } from '@angular/core';
import { IonApp, IonRouterOutlet } from '@ionic/angular/standalone';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [IonApp, IonRouterOutlet],
  template: `<ion-app><ion-router-outlet /></ion-app>`,
})
export class AppComponent {}
```

This is the thinnest possible root — all layout and navigation are handled by the `ShellLayoutComponent` loaded by the router.

---

### Step 7: Apply dark theme globals

**File**: `src/global.scss` (or `src/theme/variables.scss`)

**Purpose**: Set the dark theme as the default. The Architecture specifies dark theme globals — Ionic supports this via CSS custom properties on the `:root` and `body.dark` selectors.

**Pattern**:
```scss
// Force dark mode regardless of system preference
:root {
  --ion-background-color: #1a1a1a;
  --ion-background-color-rgb: 26, 26, 26;
  --ion-text-color: #f4f4f4;
  --ion-text-color-rgb: 244, 244, 244;

  --ion-toolbar-background: #1a1a1a;
  --ion-toolbar-color: #f4f4f4;
  --ion-tab-bar-background: #1a1a1a;
  --ion-tab-bar-color: #8c8c8c;
  --ion-tab-bar-color-selected: #ffffff;

  --ion-card-background: #2a2a2a;
  --ion-item-background: #2a2a2a;
}

body {
  background-color: var(--ion-background-color);
  color: var(--ion-text-color);
}

ion-content {
  --background: var(--ion-background-color);
}
```

Ionic's color system is entirely CSS-variable-driven, so this propagates to all Ionic components without touching individual templates.

---

### Step 8: Clean up Bubls-specific code

**Purpose**: Remove Bubls event curation artifacts that don't belong in the super app shell. The goal is a clean shell with no feature-specific code in the root — only the registry-driven infrastructure.

**What to remove**:
- Any `PicksService`, `EventCardComponent`, `DashboardPage` from the Bubls event curation app
- Mock data files (`picks.mock.ts`, etc.)
- Bubls-specific models (`pick.model.ts`, `subscriber.model.ts`)
- References to Bubls-specific routes in `app.routes.ts` (now replaced by registry-driven routes)

**What to keep**:
- The Angular/Ionic/Capacitor scaffold (package.json, angular.json, capacitor.config.ts, tsconfig, etc.)
- The `ios/` directory and Xcode project structure
- Any CI/CD workflow files
- The Capacitor plugin installations (`@capacitor/camera`, `@capacitor/push-notifications`, etc.) — Task 3 needs these

**Rule**: If a file is specific to event curation, remove it. If it's platform infrastructure, keep it.

---

## Verification

How to verify this implementation works:

```bash
# Start the dev server
ionic serve
# or
ng serve
```

**Expected Result**:
1. App loads at `localhost:8100` (or configured port) with a dark background
2. Header shows "bubls" title
3. Bottom tab bar shows two tabs: "Home" (home icon) and "Photoshoot" (camera icon)
4. Tapping "Home" shows the welcome placeholder
5. Tapping "Photoshoot" shows the photoshoot placeholder
6. URL changes to `/home` and `/photoshoot` respectively
7. Direct navigation to `/photoshoot` works (lazy loading)
8. Unknown routes (e.g., `/foo`) redirect to `/home`

**Registry test** — Confirm the pattern works by temporarily adding a third entry to `FEATURE_ROUTES`:
```typescript
{
  path: 'test',
  label: 'Test',
  icon: 'flask-outline',
  featureKey: 'test',
  loadComponent: () => import('../pages/home/home.page').then(m => m.HomePage), // reuse placeholder
}
```
A third tab should appear automatically with no other changes. Remove after confirming.

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 done
2. Tasks 2 and 3 can begin in parallel:
   - **Task 2** adds `AuthGuard`, `UserStore`, and `AuthService` into the shell — wires `canActivate` guards onto the routes
   - **Task 3** replaces the `PhotoshootPage` placeholder with camera capture, upload, Replicate inference, and gallery

---

## Related Documents

- [Solution Architecture](./architecture.md) – Shell Framework component design, Feature-as-Route pattern, design decisions
- [Epic](./epic.md) – Task 1 scope, dependencies, success criteria
- [Timeline](./timeline.md) – Status tracking
- [Analysis](./analysis.md) – Codebase fragmentation problem this task solves