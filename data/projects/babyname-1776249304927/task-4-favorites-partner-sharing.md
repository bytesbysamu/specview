# 🛠️ Implementation: Favorites + Partner Sharing

**Purpose**: Give parents a curated shortlist they can manage on-device and share with a partner via a read-only link — no app install required. This solves the partner alignment problem from the [Analysis](./analysis.md): parents currently share names via screenshots and texts.

**Effort**: 1 day

**Dependencies**: Task 1 (Preference Input Flow) — the `NameCard` interface and `FavoritesService` established in Task 3.

**Parallel With**: Task 3 (Name Card UI + Results Screen) — both consume the `NameCard` data structure independently.

**Blocks**: —

**Related**:
- [Solution Architecture](./architecture.md) — Favorites and Sharing component design, write-once shareable links pattern
- [Epic](./epic.md) — Task 4 definition, success criteria requiring shortlist sharing

---

## Overview

### What's Included
- `FavoritesPage` — full-screen view of saved name cards with remove and reorder actions
- `ShareService` — posts the favorites list to a backend endpoint, returns a shareable URL
- Backend `/api/share` endpoint — stores the shortlist in Neon Postgres, returns a unique link
- Backend `/shared/:id` route — serves a read-only HTML page rendering the shortlist for the partner
- `shared_lists` table in Neon Postgres
- Share action wired to native share sheet via Capacitor

### What's NOT Included
- Collaborative editing or partner voting — post-PMF feature per [Architecture](./architecture.md)
- Mutable shared links — write-once by design; resharing generates a new link
- User accounts or authentication — the shared list is public by URL, no login required
- Analytics on shared link views — App Store Connect and server logs are sufficient for MVP

---

## Prerequisites

Before starting:
- `FavoritesService` exists in `src/app/services/favorites.service.ts` (built in Task 3)
- `NameCardComponent` exists in `src/app/components/name-card/` (built in Task 3)
- `NameCard` interface exists in `src/app/models/name-card.model.ts` (built in Task 2)
- Neon Postgres connection string available (shared instance, already used by other products)
- Flask backend running with `psycopg2` or `psycopg` installed
- Capacitor Share plugin: `npm install @capacitor/share`

---

## Implementation Steps

### Step 1: Create the `shared_lists` Table

**File**: `backend/schema.sql` (or run directly against Neon)

**Purpose**: Single table to store shared shortlists. Each row is a write-once snapshot of a favorites list at the moment of sharing.

**Pattern**:
```sql
CREATE TABLE IF NOT EXISTS shared_lists (
    id TEXT PRIMARY KEY,
    names JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- No indexes beyond the PK — reads are by ID only, volume is negligible at MVP scale.
```

Design notes:
- `id` is a short random string (nanoid or uuid prefix), not an auto-increment. This becomes the URL slug.
- `names` stores the full `NameCard[]` JSON array. Denormalized by design — per [Architecture](./architecture.md), there's no server-side card persistence to normalize against.
- No `updated_at` — shared lists are immutable. Resharing creates a new row.
- No foreign keys to a users table — there are no user accounts.
- No TTL or expiration for MVP. At 200-user validation scale, storage is negligible. Add cleanup post-validation if needed.

### Step 2: Add the Share Endpoint to the Backend

**File**: `backend/app.py`

**Purpose**: Two endpoints — one to create a shared list (POST), one to serve it as a read-only web page (GET). The POST endpoint stores the favorites snapshot and returns a URL. The GET endpoint renders a minimal HTML page the partner sees in their mobile browser.

**Pattern**:
```python
import json
import os
import uuid
import psycopg2
from flask import Flask, request, jsonify, render_template_string

# Database connection (add to existing setup)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL)

# --- Share endpoint ---
@app.route('/api/share', methods=['POST'])
def create_shared_list():
    data = request.get_json()
    names = data.get('names', [])

    if not names:
        return jsonify({'error': 'No names provided'}), 400

    list_id = uuid.uuid4().hex[:8]  # 8-char hex slug

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO shared_lists (id, names) VALUES (%s, %s)',
                (list_id, json.dumps(names))
            )
        conn.commit()
    finally:
        conn.close()

    base_url = os.environ.get('BASE_URL', 'https://yourdomain.com')
    share_url = f'{base_url}/shared/{list_id}'

    return jsonify({'url': share_url, 'id': list_id})

# --- Shared list viewer ---
@app.route('/shared/<list_id>')
def view_shared_list(list_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT names FROM shared_lists WHERE id = %s', (list_id,))
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return 'List not found', 404

    names = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    return render_template_string(SHARED_LIST_TEMPLATE, names=names)
```

Design notes:
- `uuid.uuid4().hex[:8]` gives 4 billion possible slugs. Collision probability at MVP scale is effectively zero. No collision check needed.
- `BASE_URL` env var controls the shareable link domain. Set to the production URL when deployed.
- `get_db()` creates a new connection per request. At MVP scale (single-digit shares per day), connection pooling is unnecessary overhead. Add `psycopg2.pool` post-validation.
- The shared list viewer serves HTML directly from Flask rather than redirecting to a separate frontend. The partner doesn't have the app — they need a self-contained web page.

### Step 3: Create the Shared List HTML Template

**File**: `backend/app.py` (inline template constant)

**Purpose**: A minimal, mobile-optimized HTML page that renders the shared shortlist. The partner opens this link in their phone's browser after receiving it via text or messaging app. No CSS framework, no JavaScript — just styled HTML that loads instantly.

**Pattern**:
```python
SHARED_LIST_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Baby Name Shortlist</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f5f5;
            color: #1a1a1a;
            padding: 16px;
            max-width: 600px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            padding: 24px 0;
        }
        .header h1 { font-size: 1.5rem; font-weight: 700; }
        .header p { color: #666; margin-top: 4px; font-size: 0.9rem; }
        .card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 12px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }
        .card-name { font-size: 1.6rem; font-weight: 700; }
        .card-pronunciation {
            font-style: italic;
            color: #888;
            margin-top: 2px;
        }
        .card-meta {
            display: flex;
            gap: 8px;
            margin: 12px 0;
            flex-wrap: wrap;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 0.8rem;
            font-weight: 500;
            border: 1px solid #ddd;
            color: #555;
        }
        .card-meaning { margin-bottom: 12px; line-height: 1.5; }
        .card-meaning strong { color: #333; }
        .rationale {
            background: #f0f4ff;
            border-left: 3px solid #4a6cf7;
            border-radius: 8px;
            padding: 12px;
            line-height: 1.5;
            color: #333;
        }
        .footer {
            text-align: center;
            padding: 24px 0;
            color: #999;
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Our Baby Name Shortlist</h1>
        <p>{{ names | length }} name{{ 's' if names | length != 1 else '' }} saved</p>
    </div>

    {% for name in names %}
    <div class="card">
        <div class="card-name">{{ name.name }}</div>
        <div class="card-pronunciation">{{ name.pronunciation }}</div>
        <div class="card-meta">
            <span class="chip">{{ name.origin }}</span>
            <span class="chip">{{ name.popularity }}</span>
        </div>
        <p class="card-meaning"><strong>Meaning:</strong> {{ name.meaning }}</p>
        <div class="rationale">{{ name.rationale }}</div>
    </div>
    {% endfor %}

    <div class="footer">
        Made with ❤️ by babyname
    </div>
</body>
</html>
'''
```

Design notes:
- System font stack (`-apple-system`) for native feel on iOS and Android browsers. No web font download.
- No JavaScript. The page is a static render — there's nothing interactive for the partner to do except read.
- The rationale section mirrors the in-app card styling (blue left border, tinted background) so the experience feels consistent.
- `max-width: 600px` keeps it readable on tablets without looking stretched. On phones, full-width with 16px padding.
- Jinja2 templating via `render_template_string` — no separate template file needed for a single page.

### Step 4: Create the ShareService on the Frontend

**File**: `src/app/services/share.service.ts`

**Purpose**: Posts the current favorites list to the backend share endpoint and triggers the native share sheet with the returned URL. Wraps the Capacitor Share plugin for native integration.

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Share } from '@capacitor/share';
import { NameCard } from '../models/name-card.model';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';

interface ShareResponse {
  url: string;
  id: string;
}

@Injectable({ providedIn: 'root' })
export class ShareService {

  private apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  async shareList(names: NameCard[]): Promise<string> {
    // Post favorites to backend, get shareable URL
    const response = await firstValueFrom(
      this.http.post<ShareResponse>(`${this.apiUrl}/api/share`, { names })
    );

    // Trigger native share sheet
    await Share.share({
      title: 'Our Baby Name Shortlist',
      text: `Check out our baby name shortlist!`,
      url: response.url,
      dialogTitle: 'Share your shortlist',
    });

    return response.url;
  }
}
```

Design notes:
- `firstValueFrom` converts the Observable to a Promise for cleaner async/await flow. The share action is a one-shot operation, not a stream.
- Capacitor's `Share.share()` opens the native iOS share sheet (or Android's equivalent). The partner receives the link via iMessage, WhatsApp, or whatever the parent prefers. No in-app messaging system needed.
- The `text` field provides context when shared — messaging apps show this alongside the URL.
- Returns the URL so the calling component can display it as a fallback (e.g., if the share sheet is cancelled).

### Step 5: Create the FavoritesPage

**File**: `src/app/pages/favorites/favorites.page.ts`

**Purpose**: Dedicated screen for managing the saved name shortlist. Parents can review their selections, remove names, reorder the list, and share the entire list with a partner. This is the primary surface for the partner sharing flow.

Generate the page:
```bash
ionic generate page pages/favorites
```

**Pattern**:
```typescript
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { IonicModule, ToastController, ItemReorderEventDetail } from '@ionic/angular';
import { Router } from '@angular/router';
import { NameCard } from '../../models/name-card.model';
import { FavoritesService } from '../../services/favorites.service';
import { ShareService } from '../../services/share.service';
import { NameCardComponent } from '../../components/name-card/name-card.component';

@Component({
  selector: 'app-favorites',
  standalone: true,
  imports: [CommonModule, IonicModule, NameCardComponent],
  template: `
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-back-button defaultHref="/results"></ion-back-button>
        </ion-buttons>
        <ion-title>Favorites</ion-title>
        <ion-buttons slot="end">
          <ion-button
            (click)="shareList()"
            [disabled]="isSharing || favorites.length === 0"
          >
            <ion-icon name="share-outline" slot="icon-only"></ion-icon>
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-content>
      <!-- Empty State -->
      <div class="empty-state" *ngIf="favorites.length === 0">
        <ion-icon name="heart-outline" size="large" color="medium"></ion-icon>
        <h2>No favorites yet</h2>
        <p>Tap the heart on any name card to save it here.</p>
        <ion-button routerLink="/preferences" fill="outline">
          Generate Names
        </ion-button>
      </div>

      <!-- Favorites List -->
      <ion-list *ngIf="favorites.length > 0" lines="none">
        <ion-reorder-group
          [disabled]="false"
          (ionItemReorder)="onReorder($event)"
        >
          <ion-item *ngFor="let card of favorites; trackBy: trackByName">
            <ion-reorder slot="start"></ion-reorder>
            <div class="favorite-card-wrapper">
              <app-name-card
                [card]="card"
                [isFavorited]="true"
                (favorite)="removeFavorite($event)"
              ></app-name-card>
            </div>
          </ion-item>
        </ion-reorder-group>
      </ion-list>

      <!-- Share Footer -->
      <div class="share-footer" *ngIf="favorites.length > 0">
        <ion-button
          expand="block"
          (click)="shareList()"
          [disabled]="isSharing"
        >
          <ion-spinner *ngIf="isSharing" name="crescent" slot="start"></ion-spinner>
          <ion-icon *ngIf="!isSharing" name="share-outline" slot="start"></ion-icon>
          {{ isSharing ? 'Creating link...' : 'Share with Partner' }}
        </ion-button>
        <ion-note class="share-note">
          Creates a read-only link anyone can view
        </ion-note>
      </div>
    </ion-content>
  `,
  styles: [`
    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 60vh;
      text-align: center;
      padding: 0 24px;
    }
    .empty-state h2 {
      margin-top: 16px;
      font-weight: 600;
    }
    .empty-state p {
      color: var(--ion-color-medium);
      margin: 8px 0 24px;
    }
    .favorite-card-wrapper {
      width: 100%;
    }
    ion-item {
      --padding-start: 0;
      --inner-padding-end: 0;
    }
    .share-footer {
      padding: 16px;
      padding-bottom: 32px;
      text-align: center;
    }
    .share-note {
      display: block;
      margin-top: 8px;
      font-size: 0.85rem;
    }
  `]
})
export class FavoritesPage implements OnInit {
  favorites: NameCard[] = [];
  isSharing = false;

  constructor(
    private favoritesService: FavoritesService,
    private shareService: ShareService,
    private toastController: ToastController,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.favoritesService.favorites$.subscribe(favs => {
      this.favorites = favs;
    });
    this.favoritesService.load();
  }

  async removeFavorite(card: NameCard): Promise<void> {
    await this.favoritesService.remove(card.name);
  }

  async onReorder(event: CustomEvent<ItemReorderEventDetail>): Promise<void> {
    // Ionic handles the DOM reorder; we persist the new order
    const reordered = [...this.favorites];
    const [moved] = reordered.splice(event.detail.from, 1);
    reordered.splice(event.detail.to, 0, moved);
    await this.favoritesService.reorder(reordered);
    event.detail.complete();
  }

  async shareList(): Promise<void> {
    if (this.favorites.length === 0) return;

    this.isSharing = true;
    try {
      await this.shareService.shareList(this.favorites);
      const toast = await this.toastController.create({
        message: 'Shortlist shared!',
        duration: 2000,
        position: 'bottom',
        color: 'success',
      });
      await toast.present();
    } catch (err) {
      const toast = await this.toastController.create({
        message: 'Could not share list. Please try again.',
        duration: 3000,
        position: 'bottom',
        color: 'danger',
      });
      await toast.present();
    } finally {
      this.isSharing = false;
    }
  }

  trackByName(_index: number, card: NameCard): string {
    return card.name;
  }
}
```

Design notes:
- `ion-reorder-group` gives drag-to-reorder for free. Parents naturally want to rank their favorites — first position signals "top choice."
- Tapping the heart on a favorited card calls `removeFavorite()`, not `toggleFavorite()`. On the favorites page, the only heart action is removal. The interaction is unambiguous: "unfavorite this name."
- The share button appears in both the toolbar (quick access) and as a prominent footer button (discoverable). Two entry points because sharing is the page's primary action.
- "Creates a read-only link anyone can view" sets expectations — no login, no app install for the partner.
- `isSharing` disables the button and shows a spinner during the API call. The share sheet appears after the link is created, not before.

### Step 6: Add `reorder()` to FavoritesService

**File**: `src/app/services/favorites.service.ts`

**Purpose**: Extend the service built in Task 3 with a `reorder()` method that accepts the new array order and persists it.

**Pattern**:
```typescript
// Add to FavoritesService class (alongside existing add/remove methods)

async reorder(reordered: NameCard[]): Promise<void> {
  await this.save(reordered);
}
```

This is a one-liner because `save()` already handles persistence and subject emission. The `reorder()` method exists for semantic clarity — calling `save()` directly from the component would obscure intent.

### Step 7: Add the Favorites Route

**File**: `src/app/app-routing.module.ts` (or `app.routes.ts`)

**Purpose**: Register the `/favorites` route. The results page header badge links here, and the share flow lives on this page.

**Pattern**:
```typescript
{
  path: 'favorites',
  loadComponent: () =>
    import('./pages/favorites/favorites.page').then(m => m.FavoritesPage),
},
```

### Step 8: Add CORS for the Shared List Route

**File**: `backend/app.py`

**Purpose**: The `/shared/:id` route serves HTML to browsers outside the app. Ensure CORS headers allow the page to load from any origin (it's a public, read-only page).

**Pattern**:
```python
# If using flask-cors, the existing CORS config likely covers this.
# Verify the /shared/ route is not restricted to the app's origin.

# If CORS is origin-restricted:
from flask_cors import CORS

CORS(app, resources={
    r'/api/*': {'origins': ['capacitor://localhost', 'http://localhost']},
    r'/shared/*': {'origins': '*'},
})
```

Design notes:
- The `/api/*` routes remain restricted to the app origin. Only `/shared/*` is public.
- In practice, the shared page is server-rendered HTML, not a CORS-dependent API call. But if the partner's browser makes any preflight requests (unlikely for a simple GET), this ensures it works.

---

## Verification

### Favorites management:

```bash
# Terminal 1: Backend
cd backend && python app.py

# Terminal 2: Frontend
ionic serve
```

1. Generate names from preferences page
2. Tap hearts on 3-4 name cards to favorite them
3. Tap the heart badge in the results header to navigate to `/favorites`
4. Verify all favorited names appear with filled hearts
5. Drag a card to reorder — verify the new order persists after navigating away and back
6. Tap the heart on a card — verify it's removed from the list

**Expected Result**: Favorites persist across navigation. Reorder sticks. Removal is instant.

### Partner sharing:

1. With 2+ favorites saved, tap "Share with Partner"
2. Spinner appears on the button ("Creating link...")
3. Native share sheet opens with a URL
4. Copy the URL and open it in a browser

**Expected Result**: The browser shows a clean, mobile-optimized page titled "Our Baby Name Shortlist" with all favorited name cards rendered — name, pronunciation, origin, popularity, meaning, and rationale. No login prompt, no app install prompt.

### Shared list edge cases:

1. Share, then add a new favorite and share again — verify a new URL is generated (different slug)
2. Open an old shared link — verify it still shows the snapshot from when it was created (not the updated list)
3. Open a non-existent shared link (`/shared/doesnotexist`) — verify a 404 response

**Expected Result**: Each share creates an independent snapshot. Old links remain valid. Invalid links return 404.

### Empty state:

1. Remove all favorites
2. Navigate to `/favorites`
3. Verify the empty state shows with a prompt to generate names
4. Verify the share button is disabled when the list is empty

**Expected Result**: Empty state is helpful, not broken. Share is ungated when names exist.

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 4 as done
2. Task 3 and Task 5 are independent — proceed with whichever is next on the critical path
3. Set the `BASE_URL` environment variable in production to the real domain before deploying

---

## Related Documents

- [Solution Architecture](./architecture.md) — Favorites and Sharing component design, write-once shareable links pattern, local-first data strategy
- [Epic](./epic.md) — Task 4 scope, partner alignment problem context
- [Analysis](./analysis.md) — Partner decision-making friction that sharing addresses
- [Task 3: Name Card UI + Results Screen](./task-3-name-card-ui-results-screen.md) — FavoritesService and NameCardComponent built there, reused here
- [Timeline](./timeline.md) — Status tracking