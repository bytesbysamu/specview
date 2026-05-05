# 🛠️ Task 2: Auth + user model + feature gating

**Purpose**: Replace three incompatible auth approaches with a single Supabase-backed auth system, define the user model with `enabled_features` JSONB, and wire route-level and API-level middleware that checks feature access before rendering or processing requests.

**Effort**: 2 days

**Dependencies**: Task 1 (Shell scaffold + navigation) — routes, layout, and feature registry must exist

**Parallel With**: Task 3 (/photoshoot route + camera + inference) — both build against the shared schema contract for `users` and `lora_models` tables

**Blocks**: Task 4 (Deploy web + iOS), Task 5 (Pre-train 15 LoRA models + invite testers)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Supabase Auth integration on the Angular client (signup, login, session persistence, token refresh)
- Signal-based `UserStore` holding auth state, user profile, and `enabled_features`
- `AuthGuard` functional guard that checks `enabled_features[featureKey]` before route activation
- Login/signup page with email + password (Supabase Auth UI or minimal custom form)
- Neon Postgres `users` table with `supabase_auth_id`, `email`, `enabled_features` JSONB, and `stripe_customer_id` placeholder
- Flask `FeatureGateMiddleware` that validates Supabase JWTs and checks feature access on API requests
- `UserRepository` in Flask for Neon Postgres user lookups
- Seed script to insert test users with `enabled_features: { "photoshoot": true }`

### What's NOT Included
- Stripe billing integration — `stripe_customer_id` column exists but is null for all Month 1 users; payments come in Month 2
- OAuth providers (Google, Apple) — email + password only for 15 testers; OAuth is a fast-follow if testers request it
- Password reset flow — Supabase provides this out of the box, but no custom UI; testers use the default Supabase email
- User profile editing — no settings page; `enabled_features` is manually set in the database during onboarding
- Self-serve signup — testers are pre-seeded; the signup flow exists but is not publicly promoted

---

## Prerequisites

Before starting:
- Task 1 complete: shell serves with tab navigation and feature registry
- Supabase project created (free tier) with Auth enabled — note the project URL and anon key
- Neon Postgres connection string available (existing shared instance)
- `@supabase/supabase-js` package available for Angular integration
- Flask backend from Task 1 running (or starting fresh — this task defines the auth middleware that Task 3's Blueprint will sit behind)

---

## Implementation Steps

### Step 1: Create the Neon Postgres schema

**File**: `backend/schema.sql`

**Purpose**: Define the `users` table that is the single source of truth for identity and feature access. The `enabled_features` JSONB column is the gating mechanism — the middleware reads it, nothing else needs to.

The Architecture specifies JSONB over a join table. For 15 users with 1–3 features, this is the right call — a single read, a single update, zero joins.

**Pattern**:
```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supabase_auth_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    enabled_features JSONB NOT NULL DEFAULT '{}',
    stripe_customer_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index on supabase_auth_id for JWT-based lookups (every API request hits this)
CREATE INDEX IF NOT EXISTS idx_users_supabase_auth_id ON users(supabase_auth_id);

-- The lora_models table (Task 3 populates this, but the FK to users is defined here)
CREATE TABLE IF NOT EXISTS lora_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    replicate_model_id TEXT NOT NULL,
    trigger_word TEXT,
    default_style_prompt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_lora_models_user_id ON lora_models(user_id);

-- Generations table (Task 3 writes to this, FK to users defined here)
CREATE TABLE IF NOT EXISTS generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    lora_model_id UUID REFERENCES lora_models(id),
    original_image_url TEXT,
    result_image_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_generations_user_id ON generations(user_id);
```

Run this against the Neon instance:

```bash
psql "$NEON_CONNECTION_STRING" -f backend/schema.sql
```

The `lora_models` and `generations` tables are included here because the foreign keys reference `users`. Task 3 will populate them, but the schema should be created atomically.

---

### Step 2: Install Supabase client on Angular

**File**: `package.json` (install), then `src/environments/environment.ts`

**Purpose**: Wire the Supabase JS client into the Angular app. The client handles signup, login, JWT issuance, session persistence (localStorage), and token refresh. Angular doesn't need `@supabase/ssr` — that's for server-rendered frameworks. The vanilla `@supabase/supabase-js` works.

```bash
npm install @supabase/supabase-js
```

**Pattern** (`src/environments/environment.ts`):
```typescript
export const environment = {
  production: false,
  supabaseUrl: 'https://YOUR_PROJECT.supabase.co',
  supabaseAnonKey: 'YOUR_ANON_KEY',
  apiUrl: 'http://localhost:5000',  // Flask API
};
```

Keep secrets out of the codebase — the anon key is public by design (Supabase row-level security protects data), but the `apiUrl` should point to the Flask backend.

---

### Step 3: Build the AuthService

**File**: `src/app/services/auth.service.ts`

**Purpose**: Thin wrapper around Supabase Auth. Handles signup, login, logout, session recovery on app startup, and exposes the current session (including JWT) for API calls. This is the `AuthService` from the Architecture.

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { createClient, SupabaseClient, Session, User } from '@supabase/supabase-js';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private supabase: SupabaseClient;

  constructor() {
    this.supabase = createClient(environment.supabaseUrl, environment.supabaseAnonKey);
  }

  async signUp(email: string, password: string) {
    return this.supabase.auth.signUp({ email, password });
  }

  async signIn(email: string, password: string) {
    return this.supabase.auth.signInWithPassword({ email, password });
  }

  async signOut() {
    return this.supabase.auth.signOut();
  }

  async getSession(): Promise<Session | null> {
    const { data } = await this.supabase.auth.getSession();
    return data.session;
  }

  async getUser(): Promise<User | null> {
    const { data } = await this.supabase.auth.getUser();
    return data.user;
  }

  onAuthStateChange(callback: (event: string, session: Session | null) => void) {
    return this.supabase.auth.onAuthStateChange(callback);
  }
}
```

The Supabase client handles JWT refresh automatically via `onAuthStateChange`. The session is persisted in localStorage — on app restart, `getSession()` recovers the existing session without re-login.

---

### Step 4: Build the UserStore

**File**: `src/app/services/user.store.ts`

**Purpose**: Signal-based reactive store that holds the current user's profile including `enabled_features`. This is the `UserStore` from the Architecture. Components and guards read signals — no manual subscription management.

The store initializes by checking for an existing Supabase session, then fetches the user profile (with `enabled_features`) from the Flask API. The profile is the Neon `users` row, not the Supabase auth metadata.

**Pattern**:
```typescript
import { Injectable, signal, computed } from '@angular/core';
import { AuthService } from './auth.service';
import { environment } from '../../environments/environment';

export interface UserProfile {
  id: string;
  email: string;
  enabled_features: Record<string, boolean>;
}

@Injectable({ providedIn: 'root' })
export class UserStore {
  private _user = signal<UserProfile | null>(null);
  private _loading = signal(true);

  user = this._user.asReadonly();
  loading = this._loading.asReadonly();
  isAuthenticated = computed(() => this._user() !== null);

  constructor(private auth: AuthService) {
    this.init();
  }

  private async init() {
    const session = await this.auth.getSession();
    if (session) {
      await this.fetchProfile(session.access_token);
    }
    this._loading.set(false);

    this.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        await this.fetchProfile(session.access_token);
      } else if (event === 'SIGNED_OUT') {
        this._user.set(null);
      }
    });
  }

  private async fetchProfile(accessToken: string) {
    const res = await fetch(`${environment.apiUrl}/api/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (res.ok) {
      this._user.set(await res.json());
    }
  }

  hasFeature(featureKey: string): boolean {
    const user = this._user();
    if (!user) return false;
    if (featureKey === 'home') return true;  // Home is never gated
    return user.enabled_features[featureKey] === true;
  }
}
```

The `hasFeature` method is the central gating check. The `AuthGuard` (next step) delegates to it. The `/api/auth/me` endpoint (Step 7) returns the Neon user profile including `enabled_features`.

---

### Step 5: Build the AuthGuard

**File**: `src/app/guards/auth.guard.ts`

**Purpose**: Route-level functional guard that checks two things: (1) the user is authenticated, (2) the user has the feature enabled. This is the `AuthGuard` from the Architecture. It uses the feature key from the route registry to look up access.

**Pattern**:
```typescript
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { UserStore } from '../services/user.store';

export function authGuard(featureKey: string): CanActivateFn {
  return () => {
    const userStore = inject(UserStore);
    const router = inject(Router);

    if (!userStore.isAuthenticated()) {
      return router.createUrlTree(['/login']);
    }

    if (!userStore.hasFeature(featureKey)) {
      // User is authenticated but doesn't have this feature enabled
      return router.createUrlTree(['/home']);
    }

    return true;
  };
}
```

This is a factory function — `authGuard('photoshoot')` returns a guard that checks for the `photoshoot` feature key. The guard redirects unauthenticated users to `/login` and unauthorized users to `/home`.

---

### Step 6: Wire guards into routes

**File**: `src/app/app.routes.ts`

**Purpose**: Connect the `AuthGuard` to every feature route using the feature key from the registry. Also add the login route (unauthenticated).

**Pattern**:
```typescript
import { Routes } from '@angular/router';
import { FEATURE_ROUTES } from './shell/feature-registry';
import { authGuard } from './guards/auth.guard';

const featureChildren: Routes = FEATURE_ROUTES.map(feature => ({
  path: feature.path,
  loadComponent: feature.loadComponent,
  canActivate: [authGuard(feature.featureKey)],
}));

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login.page').then(m => m.LoginPage),
  },
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

The login route sits outside the shell layout — no tab bar on the login screen. Every feature route now has a guard.

---

### Step 7: Create the login page

**File**: `src/app/pages/login/login.page.ts`

**Purpose**: Minimal email + password form for tester onboarding. No frills — the 15 testers get a direct invite, not a marketing landing page.

**Pattern**:
```typescript
import { Component, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { IonContent, IonInput, IonButton, IonText, IonCard,
         IonCardContent, IonCardHeader, IonCardTitle } from '@ionic/angular/standalone';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, IonContent, IonInput, IonButton, IonText,
            IonCard, IonCardContent, IonCardHeader, IonCardTitle],
  template: `
    <ion-content class="ion-padding">
      <ion-card>
        <ion-card-header>
          <ion-card-title>{{ isSignUp() ? 'Create Account' : 'Sign In' }}</ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <ion-input
            type="email"
            label="Email"
            labelPlacement="floating"
            [(ngModel)]="email"
          />
          <ion-input
            type="password"
            label="Password"
            labelPlacement="floating"
            [(ngModel)]="password"
          />
          @if (error()) {
            <ion-text color="danger"><p>{{ error() }}</p></ion-text>
          }
          <ion-button expand="block" (click)="submit()">
            {{ isSignUp() ? 'Sign Up' : 'Sign In' }}
          </ion-button>
          <ion-button expand="block" fill="clear" (click)="toggleMode()">
            {{ isSignUp() ? 'Already have an account? Sign In' : 'Need an account? Sign Up' }}
          </ion-button>
        </ion-card-content>
      </ion-card>
    </ion-content>
  `,
})
export class LoginPage {
  email = '';
  password = '';
  isSignUp = signal(false);
  error = signal('');

  constructor(private auth: AuthService, private router: Router) {}

  toggleMode() {
    this.isSignUp.update(v => !v);
    this.error.set('');
  }

  async submit() {
    this.error.set('');
    const { error } = this.isSignUp()
      ? await this.auth.signUp(this.email, this.password)
      : await this.auth.signIn(this.email, this.password);

    if (error) {
      this.error.set(error.message);
    } else {
      this.router.navigate(['/home']);
    }
  }
}
```

After successful auth, Supabase fires `onAuthStateChange` → `UserStore` fetches the profile → guards unlock routes based on `enabled_features`.

---

### Step 8: Build the Flask auth middleware

**File**: `backend/middleware/auth.py`

**Purpose**: The `FeatureGateMiddleware` from the Architecture. Validates the Supabase JWT on every API request, resolves the Neon user record, checks `enabled_features`, and attaches the user to the request context. Feature Blueprints (like `/photoshoot` in Task 3) can assume an authenticated, authorized user.

**Pattern**:
```python
import os
import functools
from flask import request, jsonify, g
import jwt
import psycopg2
from psycopg2.extras import RealDictCursor

SUPABASE_JWT_SECRET = os.environ['SUPABASE_JWT_SECRET']
NEON_CONNECTION_STRING = os.environ['NEON_CONNECTION_STRING']

def get_db():
    """Get a database connection, reusing within request context."""
    if 'db' not in g:
        g.db = psycopg2.connect(NEON_CONNECTION_STRING)
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def require_auth(f):
    """Decorator: validates JWT and attaches user to g.user."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing authorization'}), 401

        token = auth_header.split(' ', 1)[1]
        try:
            payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=['HS256'],
                                 audience='authenticated')
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        supabase_user_id = payload.get('sub')
        conn = get_db()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                'SELECT id, email, enabled_features FROM users WHERE supabase_auth_id = %s',
                (supabase_user_id,)
            )
            user = cur.fetchone()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        g.user = user
        return f(*args, **kwargs)
    return wrapper

def require_feature(feature_key):
    """Decorator: checks that g.user has the specified feature enabled."""
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(g, 'user', None)
            if not user:
                return jsonify({'error': 'Not authenticated'}), 401
            features = user.get('enabled_features', {})
            if not features.get(feature_key):
                return jsonify({'error': f'Feature {feature_key} not enabled'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

Two decorators, composable. A Task 3 endpoint uses them like:

```python
@photoshoot_bp.route('/generate', methods=['POST'])
@require_auth
@require_feature('photoshoot')
def generate():
    user = g.user  # guaranteed to exist and have photoshoot access
    ...
```

The `SUPABASE_JWT_SECRET` is found in the Supabase dashboard under Project Settings → API → JWT Secret. This is the HMAC secret used to sign JWTs — it validates tokens without calling Supabase on every request.

---

### Step 9: Build the /api/auth/me endpoint

**File**: `backend/app.py` (or `backend/routes/auth.py` as a Blueprint)

**Purpose**: The endpoint that `UserStore.fetchProfile()` calls after login. Returns the user's Neon profile including `enabled_features`. This is the bridge between Supabase auth (who you are) and Neon data (what you can do).

**Pattern**:
```python
from flask import Flask, jsonify, g
from middleware.auth import require_auth, get_db, close_db

app = Flask(__name__)
app.teardown_appcontext(close_db)

@app.route('/api/auth/me')
@require_auth
def get_me():
    user = g.user
    return jsonify({
        'id': str(user['id']),
        'email': user['email'],
        'enabled_features': user['enabled_features'],
    })
```

This endpoint also handles the user-creation-on-first-login pattern. When a tester signs up via Supabase and hits `/api/auth/me` for the first time, the user might not exist in Neon yet. Two approaches:

**Option A (recommended for 15 users)**: Pre-seed users in Neon before inviting testers. The `require_auth` middleware returns 404 if the user isn't pre-seeded. Simple, manual, matches "deliberately unscalable."

**Option B (auto-create)**: If the Supabase user isn't in Neon, create a row with default `enabled_features: {}`. Then manually enable features via SQL. Slightly more flexible but adds a code path.

For Month 1, go with Option A. Pre-seed users (Step 11) before sending invites.

---

### Step 10: Add CORS and env config to Flask

**File**: `backend/app.py`

**Purpose**: Enable CORS for the Angular dev server and configure env vars for Supabase and Neon.

**Pattern**:
```python
import os
from flask import Flask
from flask_cors import CORS
from middleware.auth import close_db

app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:8100',   # Ionic dev server
    'http://localhost:4200',   # Angular dev server
    'https://your-coolify-domain.com',  # Production web
])
app.teardown_appcontext(close_db)

# Routes registered here (auth blueprint, photoshoot blueprint in Task 3)
```

Required environment variables:
```bash
export SUPABASE_JWT_SECRET="your-jwt-secret-from-supabase-dashboard"
export NEON_CONNECTION_STRING="postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/dbname?sslmode=require"
```

Install Flask dependencies:
```bash
pip install flask flask-cors psycopg2-binary pyjwt
```

---

### Step 11: Seed test users

**File**: `backend/seed.sql`

**Purpose**: Pre-create the 15 tester accounts in Neon. Each row maps a Supabase auth ID to the user's email and enabled features. The `supabase_auth_id` is populated after the tester signs up in Supabase — initially it can be set to a placeholder, then updated.

**Pattern**:
```sql
-- Seed after testers sign up in Supabase (grab their auth IDs from Supabase dashboard)
-- For now, seed with emails and placeholder auth IDs — update after signup

INSERT INTO users (supabase_auth_id, email, enabled_features)
VALUES
  ('supabase-auth-id-1', 'tester1@example.com', '{"photoshoot": true, "home": true}'),
  ('supabase-auth-id-2', 'tester2@example.com', '{"photoshoot": true, "home": true}')
  -- ... repeat for all 15 testers
ON CONFLICT (email) DO UPDATE SET
  enabled_features = EXCLUDED.enabled_features,
  updated_at = now();
```

**Workflow for onboarding a tester**:
1. Tester signs up via the login page → Supabase creates their auth record
2. Find their `supabase_auth_id` in the Supabase dashboard (Authentication → Users)
3. Run the seed SQL with their real auth ID and email
4. Tester refreshes the app → `UserStore` fetches profile → features unlocked

For a smoother flow, consider Option B from Step 9 (auto-create on first login), then just run a SQL update to enable features:

```sql
UPDATE users SET enabled_features = '{"photoshoot": true, "home": true}'
WHERE email = 'tester@example.com';
```

---

### Step 12: Update ShellLayoutComponent to show/hide tabs based on features

**File**: `src/app/shell/shell-layout.component.ts`

**Purpose**: Only show tabs in the tab bar for features the user has access to. Without this, users see tabs they can't use — clicking them redirects to `/home`, which is confusing.

**Pattern**:
```typescript
import { Component, computed } from '@angular/core';
import { IonTabs, IonTabBar, IonTabButton, IonIcon, IonLabel,
         IonHeader, IonToolbar, IonTitle, IonRouterOutlet } from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { homeOutline, cameraOutline } from 'ionicons/icons';
import { FEATURE_ROUTES } from './feature-registry';
import { UserStore } from '../services/user.store';

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
        @for (feature of visibleFeatures(); track feature.path) {
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
  visibleFeatures = computed(() =>
    FEATURE_ROUTES.filter(f => this.userStore.hasFeature(f.featureKey))
  );

  constructor(private userStore: UserStore) {
    addIcons({ homeOutline, cameraOutline });
  }
}
```

The `visibleFeatures` computed signal re-evaluates whenever `UserStore._user` changes. Tabs appear/disappear reactively as features are enabled.

---

### Step 13: Add logout to the shell

**File**: `src/app/shell/shell-layout.component.ts`

**Purpose**: Give testers a way to sign out. A simple button in the header toolbar.

**Pattern** — add to the template toolbar:
```html
<ion-header>
  <ion-toolbar>
    <ion-title>bubls</ion-title>
    <ion-buttons slot="end">
      <ion-button (click)="logout()">
        <ion-icon name="log-out-outline" slot="icon-only"></ion-icon>
      </ion-button>
    </ion-buttons>
  </ion-toolbar>
</ion-header>
```

Add to the component class:
```typescript
async logout() {
  await this.auth.signOut();
  this.router.navigate(['/login']);
}
```

Import `AuthService`, `Router`, `IonButtons`, and add `logOutOutline` to `addIcons`.

---

## Verification

### Frontend auth flow:

```bash
# Start Flask backend
cd backend && flask run --port 5000

# Start Angular frontend
cd .. && ionic serve
```

**Test sequence**:
1. Navigate to `http://localhost:8100` → should redirect to `/login` (no session)
2. Sign up with an email → Supabase creates auth record
3. Sign-up succeeds but `/api/auth/me` returns 404 (user not seeded in Neon)
4. Run seed SQL with the Supabase auth ID from the dashboard
5. Refresh the app → `UserStore` fetches profile → tabs appear based on `enabled_features`
6. Navigate to `/photoshoot` → guard allows access (feature enabled)
7. Remove `photoshoot` from `enabled_features` via SQL → refresh → `/photoshoot` tab disappears, direct navigation redirects to `/home`
8. Click logout → redirected to `/login`, session cleared

### Flask middleware:

```bash
# Get a JWT from Supabase (sign in via the app, grab the token from browser devtools)
TOKEN="eyJ..."

# Test /api/auth/me
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/auth/me

# Expected: {"id": "...", "email": "...", "enabled_features": {"photoshoot": true}}

# Test with invalid token
curl -H "Authorization: Bearer invalid" http://localhost:5000/api/auth/me

# Expected: {"error": "Invalid token"} with 401 status
```

### Feature gating:

```bash
# Test a feature-gated endpoint (Task 3 will create /api/photoshoot/generate)
# For now, create a test endpoint:
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/test/gated

# Expected: 200 if feature enabled, 403 if not
```

**Expected Result**: An authenticated user sees only tabs for their enabled features. Unauthenticated users are redirected to login. API requests without a valid JWT are rejected with 401. API requests for disabled features are rejected with 403.

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 done
2. Integration with Task 3: the `/photoshoot` Blueprint uses `@require_auth` and `@require_feature('photoshoot')` decorators, and accesses `g.user['id']` to resolve the LoRA model from `lora_models`
3. Task 4 (Deploy) needs the Flask env vars (`SUPABASE_JWT_SECRET`, `NEON_CONNECTION_STRING`) added to the Docker Compose / Coolify config
4. Task 5 (Pre-train LoRA models) needs the seed SQL workflow to map trained models to user rows

---

## Related Documents

- [Solution Architecture](./architecture.md) – Auth + User Model component design, Supabase vs Magic Links decision, JSONB rationale
- [Epic](./epic.md) – Task 2 scope, success criteria ("a user can sign up once and access all enabled features without separate credentials")
- [Timeline](./timeline.md) – Status tracking
- [Task 1: Shell scaffold](./task-1-shell-scaffold-navigation.md) – Foundation this task builds on