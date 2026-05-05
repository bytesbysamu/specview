# 🛠️ Task 5: Onboarding route + builder form

**Purpose**: Capture the builder profile on first run via a dedicated `/onboarding` route, with a skip escape hatch and a guard that redirects users whose `builder` is NULL and who have never skipped.

**Effort**: 1 day

**Dependencies**: Task 1 (user model: `builder` JSONB + `principles` JSONB on `superapp_users`, `server/modules/user/model.py` with `User` SQLModel, `server/openapi/user.yaml` with `BuilderProfile` schema, `superapp_users` table live in SQLite test fixture)

**Parallel With**: Task 3 (spec module + chain) and Task 4 (spec frontend). Neither touches `modules/user/` or `features/onboarding/`.

**Blocks**: Any feature that wants to read `user.builder` in its chain context (Task 3 relies on it, but defaults to empty BuilderProfile when unset, so does not hard-block).

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task wires the one-time profile capture flow that seeds `superapp_users.builder`. A user lands in the app with no builder — the `onboardingGuard` redirects them to `/onboarding`, they fill the five fields (`name`, `stack_preferences`, `style`, `goals`, `working_style`), submit, the frontend `OnboardingService` calls `PUT /api/user/builder`, the backend persists the JSONB, and the guard lets them through on subsequent nav. A "Skip for now" button instead posts `POST /api/user/onboarding/skip`, which stamps `onboarding_skipped_at = now()` — the guard honors the timestamp so the user is not nagged again this session, but the profile remains empty and settings can re-open the same route. The page is standalone, OnPush, signal-driven, and uses `data-test` selectors exclusively so the page-object tests survive a redesign.

**Trade-offs considered**:
- *Modal vs. dedicated route*: route chosen — routable, linkable from settings, not dismissable by accidental backdrop tap.
- *Reactive Forms vs. signal-backed template*: signal-backed template chosen — matches codebase's "signals per feature" rule; form has only five flat fields so FormGroup overhead is not earned.
- *One endpoint with `skip: true` vs. two endpoints*: two chosen — `PUT /builder` persists structure, `POST /onboarding/skip` stamps a timestamp; distinct verbs + distinct audit trails beat a polymorphic body.

---

## 2. Pre-flight

Run BEFORE editing any file. All commands from repo root.

```bash
git status                                                          # Flag any unrelated M/?? entries; stash or commit them separately
git diff HEAD -- src/app/app.routes.ts server/openapi/user.yaml     # Confirm target files are clean at HEAD
git log --oneline -5                                                # Confirm Task 1 commits are present (builder/principles migration)
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -30 # Record frontend baseline: "Executed N of N" → note N_FE
cd server && pytest -q 2>&1 | tail -10 && cd ..                     # Record backend baseline: "N passed" → note N_BE
ls server/modules/user/model.py server/openapi/user.yaml            # Confirm Task 1 artifacts exist; abort if missing
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately, BEFORE starting this task.

**Baseline recorded**: executor writes `N_FE` and `N_BE` into the commit body of the final commit.

---

## 3. Files

### To Create (new)

- `server/migrations/versions/20260416_add_onboarding_skipped_at.py` — Alembic migration adding `onboarding_skipped_at TIMESTAMP NULL` to `superapp_users`. New, sibling to existing `20260416_add_original_image_url.py`.
- `server/modules/user/routes.py` — Flask blueprint `bp` with `PUT /api/user/builder` and `POST /api/user/onboarding/skip`. New; `modules/user/` currently has only `model.py` from Task 1.
- `server/modules/user/service.py` — Thin service wrapping repo calls and JSON validation. New.
- `server/modules/user/repository.py` — SQLAlchemy writes for `builder` column and `onboarding_skipped_at`. New.
- `server/tests/test_user_routes.py` — pytest coverage for both endpoints (auth, validation, persistence, idempotency). New.
- `src/app/features/onboarding/onboarding.page.ts` — standalone Angular component, OnPush, signal-backed form fields. New.
- `src/app/features/onboarding/onboarding.page.html` — template with five `<ion-input>`/`<ion-textarea>` controls, each with `data-test`. New.
- `src/app/features/onboarding/onboarding.page.scss` — minimal layout. New.
- `src/app/features/onboarding/onboarding.page.spec.ts` — TestBed + Page Object: `validForm_submitsAndRedirects`, `skipButton_callsSkipAndRedirects`, `existingBuilder_prefillsForm`, `emptyRequired_disablesSubmit`. New.
- `src/app/features/onboarding/onboarding.service.ts` — adapter: `saveBuilder(profile)` → `PUT`, `skip()` → `POST`, returns Observables. New.
- `src/app/features/onboarding/onboarding.service.spec.ts` — HttpTestingController tests: `saveBuilder_putsToBuilderEndpoint`, `skip_postsToSkipEndpoint`, `saveBuilder_serverError_propagates`. New.
- `src/app/shared/guards/onboarding.guard.ts` — CanActivateFn; reads current user; redirects to `/onboarding` iff `builder` is null AND `onboarding_skipped_at` is null. New (`src/app/shared/guards/` is new — no guards directory yet).
- `src/app/shared/guards/onboarding.guard.spec.ts` — three cases: `nullBuilderNoSkip_redirectsToOnboarding`, `nullBuilderWithSkip_allowsNav`, `populatedBuilder_allowsNav`. New.

### To Modify (cite CODEBASE CONTEXT)

- `src/app/app.routes.ts` — currently routes shell → `home`, `photoshoot`; add `{ path: 'onboarding', loadComponent: () => import('./features/onboarding/onboarding.page').then(m => m.OnboardingPage) }` as a peer of the shell route (NOT a child — onboarding must not render inside the tab bar). Attach `onboardingGuard` to the shell route's `canActivate`.
- `server/app.py` — `ENABLED_MODULES` registry lists `photoshoot`; append `user`. `create_app()` already iterates the list.
- `server/openapi/user.yaml` — extend with `paths./api/user/builder: put` and `paths./api/user/onboarding/skip: post`; extend `User` schema with `onboarding_skipped_at: {type: string, format: date-time, nullable: true}`. Request body for `PUT /builder` is `BuilderProfile` (already defined by Task 1).
- `src/app/models/user.api.d.ts` — regenerated from updated `user.yaml`. Do not hand-edit.
- `server/modules/user/dto.py` — regenerated from updated `user.yaml`. Do not hand-edit.
- `server/modules/user/model.py` — add `onboarding_skipped_at: Optional[datetime] = None` field mapped to the new column. Do not touch `builder`/`principles` fields from Task 1.
- `package.json` — the `gen:all` script already exists per codebase context; if it targets only `photoshoot.yaml`, extend to also run `openapi-typescript server/openapi/user.yaml -o src/app/models/user.api.d.ts` and `datamodel-codegen --input server/openapi/user.yaml --output server/modules/user/dto.py --output-model-type pydantic_v2`. Inspect first — if Task 1 already extended `gen:all`, leave alone.

### To Leave Alone

- `server/modules/photoshoot/**` — unrelated feature; no shared code touched.
- `src/app/pages/**` (dashboard, pick-detail, photoshoot) — legacy `pages/` convention stays; `features/` is the new home for onboarding and forward work only. Do not migrate existing pages.
- `src/app/shell/feature-registry.ts` — onboarding is not a tab; it is a one-shot route outside the shell.
- `server/core/auth.py` — `core.auth.current_user` already exists; reuse, do not fork.
- `capacitor.config.ts` — no native behavior change.

---

## 4. Implementation Steps

### Step 1: Alembic migration for `onboarding_skipped_at`

**Action**: Add a nullable timestamp column to `superapp_users`.

**File**: `server/migrations/versions/20260416_add_onboarding_skipped_at.py` (new)

**Pattern**:
```python
"""add onboarding_skipped_at

Revision ID: 20260416_onboarding
Revises: <prev_revision_id_from_task_1>
"""
from alembic import op
import sqlalchemy as sa

revision = "20260416_onboarding"
down_revision = "<set to head at time of authoring — check with `alembic heads`>"

def upgrade() -> None:
    op.add_column("superapp_users", sa.Column("onboarding_skipped_at", sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column("superapp_users", "onboarding_skipped_at")
```

**Verify**: `cd server && alembic heads` — expect single head pointing at `20260416_onboarding`. `cd server && alembic upgrade head` on a scratch SQLite URL — expect no error.

### Step 2: Extend `User` SQLModel

**Action**: Add `onboarding_skipped_at` field to `User` mapping to the new column.

**File**: `server/modules/user/model.py` (modify — created by Task 1)

**Pattern**:
```python
from datetime import datetime
from typing import Optional
# existing imports + existing builder/principles fields untouched
onboarding_skipped_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
```

**Verify**: `cd server && python -c "from modules.user.model import User; u = User(); assert u.onboarding_skipped_at is None"` — expect no output, exit 0.

### Step 3: Update OpenAPI spec, regenerate DTOs

**Action**: Add two paths and one schema field; regenerate TS + Pydantic.

**File**: `server/openapi/user.yaml` (modify — created by Task 1)

**Pattern**:
```yaml
paths:
  /api/user/builder:
    put:
      operationId: putBuilder
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          application/json:
            schema: { $ref: '#/components/schemas/BuilderProfile' }
      responses:
        '200':
          content:
            application/json:
              schema: { $ref: '#/components/schemas/User' }
  /api/user/onboarding/skip:
    post:
      operationId: skipOnboarding
      security: [{ bearerAuth: [] }]
      responses:
        '200':
          content:
            application/json:
              schema: { $ref: '#/components/schemas/User' }
components:
  schemas:
    User:
      # existing props
      properties:
        onboarding_skipped_at:
          type: string
          format: date-time
          nullable: true
```

**Verify**: `npm run gen:all` — expect no error. `git diff src/app/models/user.api.d.ts` — expect new `putBuilder`, `skipOnboarding` operation ids and `onboarding_skipped_at` on `User`. `git diff server/modules/user/dto.py` — expect matching Pydantic classes.

### Step 4: Repository

**Action**: Two writes against `User`, each in its own function.

**File**: `server/modules/user/repository.py` (new)

**Pattern**:
```python
def set_builder(session: Session, user_id: UUID, builder: dict) -> User:
    user = session.get(User, user_id)
    user.builder = builder
    user.onboarding_skipped_at = None   # saving profile clears the skip stamp
    session.commit(); session.refresh(user)
    return user

def mark_onboarding_skipped(session: Session, user_id: UUID) -> User:
    user = session.get(User, user_id)
    user.onboarding_skipped_at = datetime.now(timezone.utc)
    session.commit(); session.refresh(user)
    return user
```

**Verify**: `cd server && pytest tests/test_user_routes.py -q` (after Step 7) — expect pass.

### Step 5: Service

**Action**: Validate payload via DTO and delegate to repo.

**File**: `server/modules/user/service.py` (new)

**Pattern**:
```python
from .dto import BuilderProfile
from . import repository

def save_builder(session, user_id, payload: dict):
    profile = BuilderProfile.model_validate(payload)   # pydantic validation
    return repository.set_builder(session, user_id, profile.model_dump())

def skip_onboarding(session, user_id):
    return repository.mark_onboarding_skipped(session, user_id)
```

**Verify**: same as Step 4.

### Step 6: Routes (Flask blueprint)

**Action**: Mirror the photoshoot routes convention — ~30 lines, auth via `core.auth.current_user`, ORM via `core.database.SessionLocal`.

**File**: `server/modules/user/routes.py` (new)

**Pattern**:
```python
from flask import Blueprint, request, jsonify
from core.auth import current_user
from core.database import SessionLocal
from . import service

bp = Blueprint("user", __name__, url_prefix="/api/user")

@bp.put("/builder")
def put_builder():
    user = current_user()
    with SessionLocal() as session:
        updated = service.save_builder(session, user.id, request.get_json() or {})
    return jsonify(_serialize(updated)), 200

@bp.post("/onboarding/skip")
def skip_onboarding():
    user = current_user()
    with SessionLocal() as session:
        updated = service.skip_onboarding(session, user.id)
    return jsonify(_serialize(updated)), 200
```

Register by appending `"user"` to `ENABLED_MODULES` in `server/app.py`.

**Verify**: `cd server && python -c "from app import create_app; app = create_app(); print([r.rule for r in app.url_map.iter_rules() if 'user' in r.rule])"` — expect `['/api/user/builder', '/api/user/onboarding/skip']`.

### Step 7: Backend tests

**Action**: Four pytest cases using the existing SQLite `conftest` fixture pattern (per `server/tests/test_routes.py`).

**File**: `server/tests/test_user_routes.py` (new)

See Section 5 for full bodies.

**Verify**: `cd server && pytest tests/test_user_routes.py -q` — expect 4 passed.

### Step 8: Frontend service

**Action**: Minimal adapter using Angular's `HttpClient` + `inject()`, typed against generated DTOs.

**File**: `src/app/features/onboarding/onboarding.service.ts` (new)

**Pattern**:
```typescript
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { components } from '../../models/user.api';
type BuilderProfile = components['schemas']['BuilderProfile'];
type User = components['schemas']['User'];

@Injectable({ providedIn: 'root' })
export class OnboardingService {
  private http = inject(HttpClient);
  saveBuilder(profile: BuilderProfile): Observable<User> {
    return this.http.put<User>('/api/user/builder', profile);
  }
  skip(): Observable<User> {
    return this.http.post<User>('/api/user/onboarding/skip', {});
  }
}
```

**Verify**: `npm test -- --watch=false --include='**/onboarding.service.spec.ts'` — expect 3 passed.

### Step 9: Frontend page

**Action**: Standalone component, OnPush, signals per field, `data-test` on every interactive element.

**File**: `src/app/features/onboarding/onboarding.page.ts` (new)

**Pattern**:
```typescript
@Component({
  standalone: true,
  selector: 'app-onboarding',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [/* Ionic components, FormsModule */],
  templateUrl: './onboarding.page.html',
  styleUrls: ['./onboarding.page.scss'],
})
export class OnboardingPage {
  name = signal(''); stackPreferences = signal(''); style = signal('');
  goals = signal(''); workingStyle = signal('');
  submitting = signal(false); error = signal<string | null>(null);
  isValid = computed(() => this.name().trim().length > 0 && this.goals().trim().length > 0);
  private svc = inject(OnboardingService);
  private router = inject(Router);
  // ngOnInit: if route state carries an existing builder, hydrate signals
  submit() { /* calls svc.saveBuilder, navigates to '/' on 200, sets error on failure */ }
  skip() { /* calls svc.skip, navigates to '/' on 200 */ }
}
```

Template: each input carries `data-test="onboarding-{field}"`, submit button `data-test="onboarding-submit"`, skip button `data-test="onboarding-skip"`.

**Verify**: `npm run build` — expect successful compile. Tests run in Step 11.

### Step 10: Route guard + route registration

**Action**: `CanActivateFn` redirecting NULL-builder, un-skipped users; wire to the shell's `canActivate` plus register `/onboarding` as a peer route.

**File**: `src/app/shared/guards/onboarding.guard.ts` (new) and `src/app/app.routes.ts` (modify)

**Pattern (guard)**:
```typescript
export const onboardingGuard: CanActivateFn = (route, state) => {
  const user = inject(CurrentUserService).user();           // signal reads current user
  const router = inject(Router);
  if (state.url.startsWith('/onboarding')) return true;
  if (!user) return true;                                   // unauth flows handled elsewhere
  if (user.builder == null && user.onboarding_skipped_at == null) {
    return router.createUrlTree(['/onboarding']);
  }
  return true;
};
```

**Pattern (routes)**:
```typescript
export const routes: Routes = [
  { path: 'onboarding', loadComponent: () => import('./features/onboarding/onboarding.page').then(m => m.OnboardingPage) },
  { path: '', canActivate: [onboardingGuard], loadComponent: () => import('./shell/shell-layout.component')...  // existing shell },
];
```

If `CurrentUserService` does not yet exist in the codebase, inspect `src/app/services/` for the existing user-state holder (likely introduced by Task 1). If absent, stop and flag — do not invent a new auth store inside this task.

**Verify**: `npm test -- --watch=false --include='**/onboarding.guard.spec.ts'` — expect 3 passed.

### Step 11: Frontend component tests

**Action**: Four TestBed cases via a Page Object (see Section 5).

**File**: `src/app/features/onboarding/onboarding.page.spec.ts` (new)

**Verify**: `npm test -- --watch=false --include='**/onboarding.page.spec.ts'` — expect 4 passed.

---

## 5. Tests

### Backend: `server/tests/test_user_routes.py`

```python
import uuid
from datetime import datetime, timezone

def _auth_headers(user_id):
    return {"Authorization": f"Bearer {user_id}"}

def test_putBuilder_authedUser_persistsAndClearsSkip(client, db_session, seed_user):
    seed_user.onboarding_skipped_at = datetime.now(timezone.utc)
    db_session.commit()
    payload = {"name": "Sam", "stack_preferences": ["angular", "flask"],
               "style": "minimal", "goals": "ship fast", "working_style": "async"}
    resp = client.put("/api/user/builder", json=payload, headers=_auth_headers(seed_user.id))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["builder"]["name"] == "Sam"
    assert body["onboarding_skipped_at"] is None

def test_putBuilder_unauthed_returns401(client):
    resp = client.put("/api/user/builder", json={"name": "x"})
    assert resp.status_code == 401

def test_putBuilder_invalidPayload_returns400(client, seed_user):
    resp = client.put("/api/user/builder", json={"name": 123}, headers=_auth_headers(seed_user.id))
    assert resp.status_code == 400

def test_skipOnboarding_authedUser_stampsTimestamp(client, db_session, seed_user):
    assert seed_user.onboarding_skipped_at is None
    resp = client.post("/api/user/onboarding/skip", headers=_auth_headers(seed_user.id))
    assert resp.status_code == 200
    db_session.refresh(seed_user)
    assert seed_user.onboarding_skipped_at is not None
    assert seed_user.builder is None
```

If `seed_user` fixture does not exist, inspect `server/tests/conftest.py` for the established user-seeding helper (photoshoot tests have one); reuse its name. If none exists, add one inline in this test file — do not modify `conftest.py` under this task.

### Frontend service: `src/app/features/onboarding/onboarding.service.spec.ts`

```typescript
describe('OnboardingService', () => {
  let service: OnboardingService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(OnboardingService);
    httpMock = TestBed.inject(HttpTestingController);
  });
  afterEach(() => httpMock.verify());

  it('saveBuilder_putsToBuilderEndpoint', () => {
    const profile = { name: 'Sam', stack_preferences: ['angular'], style: 'minimal', goals: 'g', working_style: 'w' };
    service.saveBuilder(profile as any).subscribe(u => {
      expect(u.builder?.name).toBe('Sam');
    });
    const req = httpMock.expectOne('/api/user/builder');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual(profile);
    req.flush({ id: 'u1', builder: profile, onboarding_skipped_at: null });
  });

  it('skip_postsToSkipEndpoint', () => {
    service.skip().subscribe(u => {
      expect(u.onboarding_skipped_at).toBeTruthy();
    });
    const req = httpMock.expectOne('/api/user/onboarding/skip');
    expect(req.request.method).toBe('POST');
    req.flush({ id: 'u1', builder: null, onboarding_skipped_at: '2026-04-16T12:00:00Z' });
  });

  it('saveBuilder_serverError_propagates', () => {
    let errored = false;
    service.saveBuilder({} as any).subscribe({ error: e => { errored = true; expect(e.status).toBe(400); } });
    httpMock.expectOne('/api/user/builder').flush({ detail: 'bad' }, { status: 400, statusText: 'Bad Request' });
    expect(errored).toBeTrue();
  });
});
```

### Frontend page: `src/app/features/onboarding/onboarding.page.spec.ts`

```typescript
class OnboardingPageObject {
  constructor(private fixture: ComponentFixture<OnboardingPage>) {}
  private q<T extends HTMLElement>(sel: string): T | null {
    return this.fixture.nativeElement.querySelector(sel);
  }
  setField(name: string, value: string) {
    const el = this.q<HTMLInputElement>(`[data-test="onboarding-${name}"]`)!;
    el.value = value;
    el.dispatchEvent(new Event('input'));
    this.fixture.detectChanges();
  }
  get submitButton() { return this.q<HTMLButtonElement>('[data-test="onboarding-submit"]')!; }
  get skipButton() { return this.q<HTMLButtonElement>('[data-test="onboarding-skip"]')!; }
}

describe('OnboardingPage', () => {
  let fixture: ComponentFixture<OnboardingPage>;
  let page: OnboardingPageObject;
  let svc: jasmine.SpyObj<OnboardingService>;
  let router: jasmine.SpyObj<Router>;

  beforeEach(async () => {
    svc = jasmine.createSpyObj('OnboardingService', ['saveBuilder', 'skip']);
    router = jasmine.createSpyObj('Router', ['navigateByUrl']);
    await TestBed.configureTestingModule({
      imports: [OnboardingPage],
      providers: [
        { provide: OnboardingService, useValue: svc },
        { provide: Router, useValue: router },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(OnboardingPage);
    page = new OnboardingPageObject(fixture);
    fixture.detectChanges();
  });

  it('validForm_submitsAndRedirects', () => {
    svc.saveBuilder.and.returnValue(of({ id: 'u1', builder: { name: 'Sam' }, onboarding_skipped_at: null } as any));
    page.setField('name', 'Sam');
    page.setField('stack', 'angular,flask');
    page.setField('style', 'minimal');
    page.setField('goals', 'ship fast');
    page.setField('working-style', 'async');
    page.submitButton.click();
    expect(svc.saveBuilder).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/');
  });

  it('skipButton_callsSkipAndRedirects', () => {
    svc.skip.and.returnValue(of({ id: 'u1', builder: null, onboarding_skipped_at: '2026-04-16T12:00:00Z' } as any));
    page.skipButton.click();
    expect(svc.skip).toHaveBeenCalled();
    expect(router.navigateByUrl).toHaveBeenCalledWith('/');
  });

  it('existingBuilder_prefillsForm', () => {
    const pref = { name: 'Prior', stack_preferences: ['go'], style: 's', goals: 'g', working_style: 'w' };
    fixture.componentInstance.hydrate(pref);
    fixture.detectChanges();
    const nameEl = fixture.nativeElement.querySelector('[data-test="onboarding-name"]') as HTMLInputElement;
    expect(nameEl.value).toBe('Prior');
  });

  it('emptyRequired_disablesSubmit', () => {
    expect(page.submitButton.disabled).toBeTrue();
    page.setField('name', 'Sam');
    page.setField('goals', 'g');
    expect(page.submitButton.disabled).toBeFalse();
  });
});
```

### Frontend guard: `src/app/shared/guards/onboarding.guard.spec.ts`

```typescript
describe('onboardingGuard', () => {
  let router: jasmine.SpyObj<Router>;
  let userSvc: { user: WritableSignal<any> };

  function run(url: string) {
    return TestBed.runInInjectionContext(() =>
      onboardingGuard({} as any, { url } as any));
  }

  beforeEach(() => {
    router = jasmine.createSpyObj('Router', ['createUrlTree']);
    router.createUrlTree.and.callFake((cmds: any[]) => ({ toString: () => cmds.join('/') } as any));
    userSvc = { user: signal(null) };
    TestBed.configureTestingModule({
      providers: [
        { provide: Router, useValue: router },
        { provide: CurrentUserService, useValue: userSvc },
      ],
    });
  });

  it('nullBuilderNoSkip_redirectsToOnboarding', () => {
    userSvc.user.set({ id: 'u1', builder: null, onboarding_skipped_at: null });
    const result = run('/home');
    expect(router.createUrlTree).toHaveBeenCalledWith(['/onboarding']);
    expect(result).not.toBe(true);
  });

  it('nullBuilderWithSkip_allowsNav', () => {
    userSvc.user.set({ id: 'u1', builder: null, onboarding_skipped_at: '2026-04-16T12:00:00Z' });
    expect(run('/home')).toBe(true);
    expect(router.createUrlTree).not.toHaveBeenCalled();
  });

  it('populatedBuilder_allowsNav', () => {
    userSvc.user.set({ id: 'u1', builder: { name: 'Sam' }, onboarding_skipped_at: null });
    expect(run('/home')).toBe(true);
  });
});
```

---

## 6. Commit Plan

One commit per logical unit. Suggested messages:

1. `feat(user): onboarding_skipped_at column + migration` — `server/migrations/versions/20260416_add_onboarding_skipped_at.py`, `server/modules/user/model.py`. Schema change isolated from routes.
2. `feat(user): openapi for PUT /builder + POST /onboarding/skip` — `server/openapi/user.yaml`, regenerated `src/app/models/user.api.d.ts`, regenerated `server/modules/user/dto.py`. Contract before code.
3. `feat(user): backend routes for builder + skip` — `server/modules/user/{routes,service,repository}.py`, `server/app.py` (ENABLED_MODULES), `server/tests/test_user_routes.py`. Backend self-contained and tested.
4. `feat(onboarding): service + page + guard` — `src/app/features/onboarding/**`, `src/app/shared/guards/onboarding.guard.ts`, `src/app/app.routes.ts`. Frontend self-contained.
5. `test(onboarding): component, service, guard specs` — `*.spec.ts` trio. Tests added last so intermediate commits compile but the scope is obvious.

**Deviation logging**: if a step deviates from this guide (e.g., a sibling helper already exists, or a DTO field differs from Task 1's naming), prefix the commit body with `Deviations:` followed by one line per deviation. Also write `Baseline: FE N_FE, BE N_BE` on the final commit.

---

## 7. Verification

```bash
npm run gen:all                                                     # codegen is clean
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -5  # frontend full suite
cd server && pytest -q 2>&1 | tail -5 && cd ..                      # backend full suite
npm run build                                                        # production build compiles
```

**Expected delta**:
- Frontend: `N_FE` → `N_FE + 11` passing (3 service + 4 page + 3 guard + 1 existing onboarding.service `inject` sanity if emitted by TestBed boilerplate; count whichever tests are actually reported).
- Backend: `N_BE` → `N_BE + 4` passing.
- Zero pre-existing tests broken. Zero `npm run build` warnings beyond those already present on HEAD.

---

## 8. Rollback

- **Per-step**: every commit in the plan is independently revertible in reverse order. `git revert <sha>` on commits 5 → 4 → 3 → 2 → 1.
- **Migration rollback**: `cd server && alembic downgrade -1` removes `onboarding_skipped_at`. Safe because no production data in SQLite test fixture; Neon rollback requires coordination before any prod run.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (recorded by the pre-flight `git log --oneline -5`) on the feature branch, or delete the feature branch.

---

## 9. Deviations Allowed

- **`gen:all` script already emits user.yaml artifacts** (Task 1 may have wired it) → skip the `package.json` edit; verify the generated files match.
- **`CurrentUserService` is named differently in the codebase** (e.g., `UserStateService`, `AuthUserStore`) → inspect `src/app/services/` and use the established name. Do not introduce a parallel store.
- **`seed_user` conftest fixture missing** → define minimal inline fixture within `test_user_routes.py`; do not mutate `server/tests/conftest.py` from this task.
- **`core.auth.current_user()` returns a different shape** (e.g., dict vs. SQLModel) → adapt route handler accordingly; do not refactor auth.
- **Ionic form component events differ from plain `input`** (`ionInput` vs. `input`) → use the Ionic convention in templates and match in the page object's `setField`. Adjust both sides consistently.
- **Prescribed file path doesn't exist** → verify against CODEBASE CONTEXT; if still missing, STOP and flag rather than inventing.
- **Step N unlocks an obvious simplification for Step N+1** (e.g., service can re-use a repo helper from photoshoot) → skip only if the helper is genuinely shared; cross-feature imports are prohibited by architecture principles. If in doubt, duplicate and log the deviation.
- **Side-effect required** (push, deploy, `alembic upgrade head` against Neon) → STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

The executor must NOT absorb the following into this task. If work reveals these are needed, STOP and flag:

- **Settings page with "Edit builder" link back to `/onboarding`** — separate task. This guide only ensures the route is re-visitable; no settings UI.
- **Renaming the existing `src/app/pages/` tree to `features/`** — migration of legacy pages is not this task. New code uses `features/`; existing code stays.
- **Principles editor UI** — the `principles` JSONB column is written by other features, not here. No form field for principles.
- **Analytics / funnel tracking on onboarding completion** — no event bus wiring.
- **Re-prompting logic** based on `onboarding_skipped_at` age (e.g., "nag again after 7 days") — the column is set; consumers may read it, but no timed re-prompt in this task.
- **Authenticated session bootstrap** (login, magic link issuance, token storage) — handled by the existing `AuthTokenService` and backend `core.auth`; this task assumes a bearer token is already present.
- **i18n / translations** — English copy only.
- **Mock-mode toggle for onboarding** — the form is thin; mock mode is not earned until signals say otherwise.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale
- [Epic](./epic.md) – Task scope
- [Timeline](./timeline.md) – Status tracking (update after done)