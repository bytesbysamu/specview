# 🛠️ Task 2: Cross-Platform Client (iOS + Web) — Frontend Only, Mock Data

**Purpose**: Build the one-screen picks dashboard with mock data. No backend, no API. Style it, get it on TestFlight, then wire up Flask later.

**Effort**: 2 days

**Dependencies**: None (mock data, no backend required)

**Parallel With**: Task 1 (ingestion worker can be built simultaneously)

**Blocks**: Task 4 (push notifications), Task 5 (onboarding)

---

## Approach

Pure frontend. Hardcoded mock data for 5 Zürich events. The dashboard should look and feel complete — a user testing via TestFlight shouldn't know the data is fake. Flask backend comes later (Task 3 delivers curation, then we replace mocks with HTTP calls).

---

## Executor Container Setup

The project runs inside a Docker executor container (same pattern as trendfy). The container has Node 20, Angular CLI, Ionic CLI, and all dependencies pre-installed.

### Container Files

**`docker-compose.yml`** (project root):
```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8100:8100"   # Ionic dev server
    volumes:
      - .:/app
      - node_modules:/app/node_modules
    working_dir: /app
    command: ionic serve --host 0.0.0.0

volumes:
  node_modules:
```

**`Dockerfile`**:
```dockerfile
FROM node:20-alpine
RUN apk add --no-cache git bash curl python3 make g++
RUN npm install -g @ionic/cli @angular/cli @capacitor/cli
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 8100
CMD ["ionic", "serve", "--host", "0.0.0.0"]
```

### Local dev (no container):
```bash
npm install
ionic serve        # web at localhost:8100
# or
ng build && npx cap copy ios && npx cap open ios   # Xcode
```

---

## Step 1: Scaffold Project

**Source**: Constellation frontend boilerplate

```bash
# Start fresh
ionic start bubls blank --type=angular --capacitor
cd bubls

# Match Constellation versions
npm install @ionic/angular@8.4.3 @capacitor/core@7.0.0 @capacitor/ios@7.0.0
npm install @capacitor/push-notifications @capacitor/share @capacitor/haptics
```

**`capacitor.config.ts`**:
```typescript
import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'ch.bubls.app',
  appName: 'Bubls',
  webDir: 'www',
  server: {
    androidScheme: 'https'
  }
};

export default config;
```

**`ionic.config.json`**:
```json
{
  "name": "bubls",
  "integrations": { "capacitor": {} },
  "type": "angular"
}
```

**`angular.json`** key settings:
- `outputPath`: `www`
- `standalone`: true (no NgModules)
- `changeDetection`: OnPush

---

## Step 2: Data Model

**`src/app/models/pick.model.ts`**:
```typescript
export interface Pick {
  title: string;        // German title preserved from source
  summary: string;      // English AI summary
  datetime: string;     // ISO 8601
  venue: string;
  price: string;        // "Free" or "CHF 25"
  url: string;          // Link to original event
  source: string;       // "ticketmaster" | "guidle"
  image_url?: string;
}

export interface WeeklyPicks {
  subscriber_id: string;
  week_start: string;   // ISO date
  events: Pick[];
  created_at: string;
}

export interface Subscriber {
  email: string;
  city: string;
  interests: string[];
  token: string;
}
```

---

## Step 3: Mock Data

**`src/app/mocks/picks.mock.ts`**:
```typescript
import { Pick, WeeklyPicks } from '../models/pick.model';

export const MOCK_PICKS: Pick[] = [
  {
    title: 'Streetfood Festival am Seebecken',
    summary: '40 food trucks along the lake with live DJs from 6pm — the best outdoor eating in Zürich this summer.',
    datetime: '2026-04-18T14:00:00+02:00',
    venue: 'Bellevue, Zürich',
    price: 'Free',
    url: 'https://www.zuerich.com/en/visit/events/streetfood-festival',
    source: 'guidle'
  },
  {
    title: 'Gauthier Dance: Nijinsky',
    summary: 'Contemporary dance retelling of Nijinsky\'s descent into madness — raw, physical, sold out three times in Stuttgart.',
    datetime: '2026-04-17T19:30:00+02:00',
    venue: 'Theater Winterthur',
    price: 'CHF 35',
    url: 'https://www.ticketmaster.ch/event/gauthier-dance',
    source: 'ticketmaster'
  },
  {
    title: 'Vinyl & Wein Markt',
    summary: 'Dig through 2000+ records from Zürich collectors while drinking natural wine from Swiss producers.',
    datetime: '2026-04-19T11:00:00+02:00',
    venue: 'Im Viadukt, Zürich',
    price: 'Free',
    url: 'https://www.imviadukt.ch/events/vinyl-wein',
    source: 'guidle'
  },
  {
    title: 'Bouldering Night',
    summary: 'All-you-can-climb with DJ and bar — no experience needed, shoes included. Best way to meet people.',
    datetime: '2026-04-18T20:00:00+02:00',
    venue: 'Minimum Kletterzentrum, Zürich',
    price: 'CHF 25',
    url: 'https://www.minimum.ch/bouldering-night',
    source: 'guidle'
  },
  {
    title: 'AI Zürich Meetup #47',
    summary: 'Demo night: 3 local startups show what they built with Claude and GPT. Free pizza, good crowd.',
    datetime: '2026-04-17T18:30:00+02:00',
    venue: 'Google Europaallee, Zürich',
    price: 'Free',
    url: 'https://www.meetup.com/ai-zurich/events/47',
    source: 'ticketmaster'
  }
];

export const MOCK_WEEKLY_PICKS: WeeklyPicks = {
  subscriber_id: 'mock-user-001',
  week_start: '2026-04-14',
  events: MOCK_PICKS,
  created_at: new Date().toISOString()
};

export const MOCK_SUBSCRIBER = {
  email: 'sam@bubls.ch',
  city: 'zurich',
  interests: ['music', 'food', 'tech'],
  token: 'mock-token-abc123'
};
```

---

## Step 4: PicksService (mock mode)

**`src/app/services/picks.service.ts`**:
```typescript
import { Injectable, signal } from '@angular/core';
import { Pick, WeeklyPicks } from '../models/pick.model';
import { MOCK_WEEKLY_PICKS, MOCK_SUBSCRIBER } from '../mocks/picks.mock';

@Injectable({ providedIn: 'root' })
export class PicksService {
  readonly picks = signal<Pick[]>([]);
  readonly loading = signal(false);
  readonly subscriber = signal(MOCK_SUBSCRIBER);

  async loadPicks(): Promise<void> {
    this.loading.set(true);
    // TODO: Replace with HTTP call to Flask backend
    // const res = await fetch(`/api/picks/${token}`);
    await new Promise(r => setTimeout(r, 300)); // simulate network
    this.picks.set(MOCK_WEEKLY_PICKS.events);
    this.loading.set(false);
  }

  getNextThursday(): Date {
    const now = new Date();
    const thursday = new Date(now);
    thursday.setDate(now.getDate() + ((4 - now.getDay() + 7) % 7 || 7));
    thursday.setHours(18, 0, 0, 0);
    if (thursday <= now) thursday.setDate(thursday.getDate() + 7);
    return thursday;
  }
}
```

---

## Step 5: EventCardComponent

**`src/app/components/event-card/event-card.component.ts`**:
```typescript
import { Component, input } from '@angular/core';
import { IonCard, IonCardHeader, IonCardTitle, IonCardSubtitle,
         IonCardContent, IonChip, IonLabel, IonButton, IonIcon } from '@ionic/angular/standalone';
import { Pick } from '../../models/pick.model';

@Component({
  selector: 'app-event-card',
  standalone: true,
  imports: [IonCard, IonCardHeader, IonCardTitle, IonCardSubtitle,
            IonCardContent, IonChip, IonLabel, IonButton, IonIcon],
  template: `
    <ion-card>
      <ion-card-header>
        <ion-card-title>{{ pick().title }}</ion-card-title>
        <ion-card-subtitle>{{ pick().summary }}</ion-card-subtitle>
      </ion-card-header>
      <ion-card-content>
        <div class="event-meta">
          <ion-chip>
            <ion-label>{{ formatDate(pick().datetime) }}</ion-label>
          </ion-chip>
          <ion-chip>
            <ion-label>{{ pick().venue }}</ion-label>
          </ion-chip>
          <ion-chip [color]="pick().price === 'Free' ? 'success' : 'medium'">
            <ion-label>{{ pick().price }}</ion-label>
          </ion-chip>
        </div>
        <ion-button expand="block" fill="outline" (click)="openEvent()">
          View Event →
        </ion-button>
      </ion-card-content>
    </ion-card>
  `
})
export class EventCardComponent {
  pick = input.required<Pick>();

  formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })
      + ' · ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
  }

  openEvent(): void {
    window.open(this.pick().url, '_blank');
  }
}
```

---

## Step 6: PicksDashboardPage (the one screen)

**`src/app/pages/dashboard/dashboard.page.ts`**:
```typescript
import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonContent, IonHeader, IonToolbar, IonTitle, IonSpinner,
         IonChip, IonLabel, IonText } from '@ionic/angular/standalone';
import { EventCardComponent } from '../../components/event-card/event-card.component';
import { PicksService } from '../../services/picks.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, IonContent, IonHeader, IonToolbar, IonTitle,
            IonSpinner, IonChip, IonLabel, IonText, EventCardComponent],
  template: `
    <ion-header>
      <ion-toolbar>
        <ion-title>bubls.</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content class="ion-padding">
      @if (picksService.loading()) {
        <div class="loading">
          <ion-spinner></ion-spinner>
        </div>
      } @else if (picksService.picks().length > 0) {
        <div class="week-header">
          <h2>Your Weekend</h2>
          <p class="subtitle">{{ picksService.subscriber().city | titlecase }} · {{ weekLabel() }}</p>
        </div>

        @for (pick of picksService.picks(); track pick.title) {
          <app-event-card [pick]="pick" />
        }

        <div class="footer">
          <div class="interests">
            @for (interest of picksService.subscriber().interests; track interest) {
              <ion-chip>
                <ion-label>{{ interest }}</ion-label>
              </ion-chip>
            }
          </div>
          <ion-text color="medium">
            <p class="refresh-note">Next refresh: Thursday 6pm</p>
          </ion-text>
        </div>
      } @else {
        <div class="empty-state">
          <h2>Your picks are coming!</h2>
          <p>First delivery: {{ countdown() }}</p>
        </div>
      }
    </ion-content>
  `
})
export class DashboardPage implements OnInit {
  countdown = signal('');
  weekLabel = computed(() => {
    const now = new Date();
    const start = new Date(now);
    start.setDate(now.getDate() - now.getDay() + 5); // Friday
    const end = new Date(start);
    end.setDate(start.getDate() + 2); // Sunday
    return `${start.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })} – ${end.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}`;
  });

  constructor(public picksService: PicksService) {}

  ngOnInit(): void {
    this.picksService.loadPicks();
    this.updateCountdown();
    setInterval(() => this.updateCountdown(), 60000);
  }

  private updateCountdown(): void {
    const next = this.picksService.getNextThursday();
    const diff = next.getTime() - Date.now();
    const days = Math.floor(diff / 86400000);
    const hours = Math.floor((diff % 86400000) / 3600000);
    this.countdown.set(days > 0 ? `${days}d ${hours}h` : `${hours}h`);
  }
}
```

---

## Step 7: App Bootstrap

**`src/app/app.routes.ts`**:
```typescript
import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', loadComponent: () => import('./pages/dashboard/dashboard.page').then(m => m.DashboardPage) },
  { path: '**', redirectTo: '' }
];
```

**`src/app/app.component.ts`**:
```typescript
import { Component } from '@angular/core';
import { IonApp, IonRouterOutlet } from '@ionic/angular/standalone';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [IonApp, IonRouterOutlet],
  template: `<ion-app><ion-router-outlet /></ion-app>`
})
export class AppComponent {}
```

---

## Step 8: iOS Build Pipeline

```bash
# 1. Build Angular
ng build --configuration=production

# 2. Copy to native project
npx cap copy ios
npx cap sync ios

# 3. Open in Xcode
npx cap open ios

# 4. In Xcode:
#    - Select team (Apple Developer account)
#    - Set bundle ID: ch.bubls.app
#    - Product → Archive → Distribute → TestFlight
```

---

## Step 9: PWA Manifest

**`src/manifest.webmanifest`**:
```json
{
  "name": "Bubls",
  "short_name": "Bubls",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1e1e1e",
  "theme_color": "#6eb4ff",
  "icons": [
    { "src": "assets/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "assets/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

---

## Verification Checklist

### Web
- [ ] `ionic serve` → dashboard loads at localhost:8100
- [ ] 5 event cards render with title, summary, date, venue, price
- [ ] "View Event →" opens external link
- [ ] Interests shown at bottom
- [ ] "Next refresh: Thursday 6pm" countdown visible

### iOS
- [ ] `ng build && npx cap copy ios && npx cap open ios`
- [ ] App runs in iOS Simulator
- [ ] Same 5 cards as web
- [ ] TestFlight archive builds successfully

### Cross-platform parity
- [ ] Same content on web and iOS
- [ ] Event card layout matches on both
- [ ] External links work on both

---

## What This Does NOT Include

- ❌ Backend API calls (mocked — Task 3 delivers real curation)
- ❌ Onboarding flow (Task 5)
- ❌ Push notifications (Task 4)
- ❌ Styling/theming beyond Ionic defaults (polish pass later)
- ❌ Error handling for network failures (no network calls yet)

---

## Resources from Existing Projects

| Resource | Source | What to reuse |
|----------|--------|---------------|
| Capacitor config pattern | `constellation/frontend/capacitor.config.ts` | appId structure, webDir setting |
| iOS directory structure | `constellation/frontend/ios/` | Xcode project scaffold |
| Angular standalone pattern | `constellation/frontend/src/app/app.component.ts` | IonApp + IonRouterOutlet |
| CI/CD for iOS | `constellation/frontend/.github/workflows/release.yml` | TestFlight upload workflow |
| Docker executor pattern | `spec-doc/docker/Dockerfile.executor` | Node 20 Alpine + CLI tools |
| Ionic config | `constellation/frontend/ionic.config.json` | Type: angular, Capacitor integration |
