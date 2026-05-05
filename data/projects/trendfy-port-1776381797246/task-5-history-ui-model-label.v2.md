# Task 5: History UI -- Migrated Results + Model Label

**Purpose**: Extend the photoshoot contact-sheet component to render unified history (Trendfy migrations + Bubls generations), show a placeholder for expired-URL results, and display the active model label in the photoshoot page header.

**Effort**: 0.5 day

**Dependencies**: Task 3 (Result Migration -- `superapp_generations` rows with `expired` column and `feature = 'photoshoot'` must exist), Task 4 (Photo Library Save -- `PhotoLibraryService` wired into generate flow)

**Parallel With**: None (depends on both Task 3 and Task 4)

**Blocks**: Task 6 (Integration Test + TestFlight QA -- needs history rendering and model label to verify)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

After Tasks 1-3, Trendfy's 76 historical results exist as `superapp_generations` rows with `feature = 'photoshoot'`. Some have `expired = true` because their Replicate CDN URLs were dead at migration time. The existing contact-sheet component (from UX-revamp Task 4) only renders in-session generations from a signal -- it has no concept of persistent history, expiry, or model labels.

This task makes three changes: (1) the photoshoot history API response now includes an `expired` field, and the contact-sheet renders expired results with a placeholder overlay instead of a broken `<img>`; (2) the `GET /api/photoshoot/history` endpoint already returns all `superapp_generations` for the user -- the frontend maps them into `GenerationTile[]` and feeds them to the contact sheet; (3) the photoshoot page header gains a model label ("Model: Sam v3a") read from a new `GET /api/photoshoot/active-model` endpoint (or inline from the existing generate response -- see deviations).

**Trade-offs considered**:
- **Client-side URL HEAD-check for expiry** -- rejected because migration already flags expired rows at write time; re-checking on every render wastes bandwidth and adds latency for a known-stale URL
- **Hide expired results entirely** -- rejected because losing history signal is worse than a placeholder; users should see that 76 results existed even if URLs are dead
- **Fetch model name from a separate user-profile endpoint** -- rejected because the model label is photoshoot-specific; adding a thin `/api/photoshoot/active-model` endpoint (or extending `/history` response) keeps the feature self-contained

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                       # Flag any unrelated M/?? entries
git log --oneline -10                                            # Confirm Task 3 + Task 4 commits are present
ls src/app/pages/photoshoot/components/                          # Confirm contact-sheet.component.ts exists
grep -n "expired" server/modules/photoshoot/models.py            # Confirm Task 3 added the expired column
grep -n "GenerationTile" src/app/pages/photoshoot/photoshoot.types.ts  # Confirm existing type
grep -n "getHistory" src/app/services/photoshoot-api.service.ts  # Confirm history endpoint call
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -20   # Record baseline pass count
cd server && python -m pytest --tb=short 2>&1 | tail -20 && cd ..     # Record backend baseline
```

**If `expired` column is missing from models.py**: STOP -- Task 3 is not done. Do not add the column as part of this task.

**If contact-sheet component does not exist**: STOP -- UX-revamp Task 4 is not done. The component must already be in-tree.

**Baseline recorded**: write the test pass count here before starting (e.g., FE: `63/63`, BE: `18/18`).

---

## 3. Files

### To Create (new)
- `server/modules/photoshoot/lora_routes.py` -- single-endpoint Blueprint: `GET /api/photoshoot/active-model` returning `{ model_name: string | null }`. Reads from `superapp_lora_models` where `user_id = current AND is_active = true` (or most-recent fallback per existing `find_active_lora_for_user`).
- `server/tests/test_active_model_route.py` -- pytest tests for the new endpoint: model exists, no model, unauthorized.

### To Modify
- `server/modules/photoshoot/models.py` -- add `expired: Mapped[bool | None]` column to `Generation` class (nullable boolean, default `None` for backward compat with pre-migration rows); add `model_name: Mapped[str | None]` column to `LoraModel` class (nullable string -- Task 2 migration copies `model_name` from Trendfy; existing rows get `None`); add `is_active: Mapped[bool]` column to `LoraModel` class (default `False` -- Task 2 migration sets `True` on the most recent per user)
- `server/modules/photoshoot/repository.py` -- update `find_active_lora_for_user` to prefer `is_active = True` if column exists, fallback to most-recent by `created_at`
- `server/modules/photoshoot/routes.py` -- update `_serialize_generation` to include `expired` field in the response DTO
- `server/openapi/photoshoot.yaml` -- add `expired` (boolean, nullable) to `GenerationResponse` schema; add `ActiveModelResponse` schema and `/api/photoshoot/active-model` path
- `server/app.py` -- register the new `lora_routes.bp` Blueprint
- `src/app/models/photoshoot.api.d.ts` -- regenerate via `npm run gen:ts:photoshoot` after YAML change (auto-generated, do not hand-edit)
- `src/app/pages/photoshoot/photoshoot.types.ts` -- add `expired?: boolean` field to `GenerationTile`
- `src/app/pages/photoshoot/components/contact-sheet.component.ts` -- render expired tiles with a placeholder overlay: if `g.expired`, replace `<img>` with a `<div class="expired-placeholder">` containing "Image expired" text; add `data-test="tile-expired"` on the overlay
- `src/app/pages/photoshoot/components/contact-sheet.component.spec.ts` -- add tests for expired tile rendering
- `src/app/pages/photoshoot/photoshoot.page.ts` -- add model label signal; fetch from `/api/photoshoot/active-model` on init; display in header bar; map history response `expired` field into `GenerationTile`
- `src/app/pages/photoshoot/photoshoot.page.spec.ts` -- add tests for model label display and expired tile mapping
- `src/app/services/photoshoot-api.service.ts` -- add `getActiveModel(token: string): Promise<{ model_name: string | null }>` method; add mock branch

### To Leave Alone
- `src/app/services/photo-library.service.ts` -- Task 4's work, untouched here
- `src/app/pages/home/`, `src/app/pages/text/` -- other feature folders
- `src/app/shell/` -- no shell changes
- `server/migrations/` -- schema changes are migration-ready but the Alembic migration file is NOT created in this task; Task 3's migration adds the `expired` column, and Tasks 1-2 add `is_active` + `model_name`. If those migrations have not landed, STOP and flag
- `scripts/architecture-acl-check.mjs` -- no new ACL concerns in this task

---

## 4. Implementation Steps

### Step 1: Add `expired`, `is_active`, and `model_name` columns to models

**Action**: Add three columns to the SQLAlchemy models. The `expired` column on `Generation`, and `is_active` + `model_name` on `LoraModel`. All nullable for backward compat. If Task 2/3 migrations have already added these columns, skip this step and note in the commit body.

**File**: `server/modules/photoshoot/models.py`

**Pattern** -- add to `Generation` class:
```python
expired: Mapped[bool | None] = mapped_column(nullable=True, default=None)
```

Add to `LoraModel` class:
```python
model_name: Mapped[str | None] = mapped_column(String, nullable=True)
is_active: Mapped[bool] = mapped_column(nullable=False, default=False)
```

**Verify**:
```bash
grep -n "expired" server/modules/photoshoot/models.py
grep -n "is_active\|model_name" server/modules/photoshoot/models.py
cd server && python -m pytest --tb=short 2>&1 | tail -10
```
Expect: columns defined; existing backend tests still pass (SQLite auto-migrates via `create_all`).

### Step 2: Update repository to prefer `is_active` for model lookup

**Action**: Modify `find_active_lora_for_user` to first query where `is_active = True`. If no row found, fall back to the existing most-recent-by-created_at query. This preserves backward compat for users who have no `is_active = True` row yet.

**File**: `server/modules/photoshoot/repository.py`

**Pattern**:
```python
def find_active_lora_for_user(db: Session, user_id: uuid.UUID) -> LoraModel | None:
    """Return the user's active LoRA model, or most recent as fallback."""
    active = (
        db.query(LoraModel)
        .filter(LoraModel.user_id == user_id, LoraModel.is_active == True)
        .first()
    )
    if active is not None:
        return active
    return (
        db.query(LoraModel)
        .filter(LoraModel.user_id == user_id)
        .order_by(LoraModel.created_at.desc())
        .first()
    )
```

**Verify**:
```bash
cd server && python -m pytest tests/test_repository.py --tb=short 2>&1 | tail -10
```
Expect: existing repo tests pass; no regression on the generate flow.

### Step 3: Update `_serialize_generation` to include `expired` field

**Action**: Extend the generation serializer to include the `expired` flag.

**File**: `server/modules/photoshoot/routes.py`

**Pattern**: In `_serialize_generation`, add `expired` to the DTO construction. Since the `GenerationResponse` Pydantic model is auto-generated from OpenAPI, first update the YAML (Step 4), then regenerate. For now, manually add the field to the response dict:

```python
def _serialize_generation(gen: Generation) -> dict:
    dto = GenerationResponse(
        id=gen.id,
        result_image_url=gen.result_image_url or '',
        created_at=_ensure_utc(gen.created_at),
    )
    result = dto.model_dump(mode="json")
    result['expired'] = gen.expired or False
    return result
```

**Verify**:
```bash
cd server && python -m pytest tests/test_routes.py --tb=short 2>&1 | tail -10
```
Expect: existing route tests pass.

### Step 4: Update OpenAPI spec and regenerate TypeScript types

**Action**: Add `expired` to `GenerationResponse` schema and add the `ActiveModelResponse` schema + `/api/photoshoot/active-model` path.

**File**: `server/openapi/photoshoot.yaml`

**Pattern** -- add to `GenerationResponse` properties:
```yaml
expired:
  type: boolean
  nullable: true
  description: True if the Replicate CDN URL has expired. Frontend renders a placeholder.
```

Add new schema:
```yaml
ActiveModelResponse:
  type: object
  required:
    - model_name
  properties:
    model_name:
      type: string
      nullable: true
      description: Display name of the user's active LoRA model, or null if none
```

Add new path:
```yaml
/api/photoshoot/active-model:
  get:
    summary: Get the caller's active LoRA model name
    operationId: getActiveModel
    responses:
      '200':
        description: Active model info
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ActiveModelResponse'
      '401':
        description: Unauthorized
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ErrorResponse'
```

Then regenerate:
```bash
npm run gen:ts:photoshoot
npm run gen:py:photoshoot
```

**Verify**:
```bash
grep "expired" src/app/models/photoshoot.api.d.ts
grep "ActiveModelResponse\|active.model\|getActiveModel" src/app/models/photoshoot.api.d.ts
```
Expect: `expired` present in `GenerationResponse`; `ActiveModelResponse` type generated.

### Step 5: Create `GET /api/photoshoot/active-model` route

**Action**: Create a new Blueprint with a single endpoint that returns the active model name.

**File**: `server/modules/photoshoot/lora_routes.py` (new)

**Pattern**:
```python
from __future__ import annotations

from flask import Blueprint, g, jsonify

from core.auth import require_auth
from . import repository

bp = Blueprint("photoshoot_lora", __name__, url_prefix="/api/photoshoot")


@bp.get("/active-model")
@require_auth
def active_model():
    lora = repository.find_active_lora_for_user(g.db, g.user.id)
    model_name = lora.model_name if lora else None
    return jsonify({"model_name": model_name}), 200
```

Register in `server/app.py`:
```python
from modules.photoshoot.lora_routes import bp as lora_bp
app.register_blueprint(lora_bp)
```

**Verify**:
```bash
cd server && python -m pytest --tb=short 2>&1 | tail -10
```
Expect: all existing tests pass; new route is registered.

### Step 6: Add backend tests for active-model endpoint

**Action**: Create pytest test file for the new endpoint.

**File**: `server/tests/test_active_model_route.py` (new)

**Pattern**:
```python
import uuid
import pytest
from modules.photoshoot.models import LoraModel, User


def test_activeModel_withModel_returnsModelName(client, db_session):
    user = User(email="test@bubls.ch", token=uuid.uuid4())
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    lora = LoraModel(
        user_id=user.id,
        replicate_model_id="owner/model:v1",
        model_name="Sam v3a",
        is_active=True,
    )
    db_session.add(lora)
    db_session.commit()

    resp = client.get(
        "/api/photoshoot/active-model",
        headers={"Authorization": f"Bearer {user.token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["model_name"] == "Sam v3a"


def test_activeModel_noModel_returnsNull(client, db_session):
    user = User(email="nomodel@bubls.ch", token=uuid.uuid4())
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    resp = client.get(
        "/api/photoshoot/active-model",
        headers={"Authorization": f"Bearer {user.token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["model_name"] is None


def test_activeModel_unauthorized_returns401(client):
    resp = client.get("/api/photoshoot/active-model")
    assert resp.status_code == 401
```

**Verify**:
```bash
cd server && python -m pytest tests/test_active_model_route.py --tb=short -v 2>&1
```
Expect: 3 tests pass.

### Step 7: Add `getActiveModel` to frontend API service

**Action**: Extend `PhotoshootApiService` with a method to fetch the active model name.

**File**: `src/app/services/photoshoot-api.service.ts`

**Pattern**: Add method:
```typescript
async getActiveModel(token: string): Promise<{ model_name: string | null }> {
  if (environment.useMocks.photoshoot) {
    await delay(100);
    return { model_name: 'Sam v3a' };
  }

  const res = await fetch(`${this.baseUrl}/active-model`, {
    headers: buildHeaders({}, token),
  });

  if (!res.ok) throw await toError(res);
  return (await res.json()) as { model_name: string | null };
}
```

**Verify**:
```bash
grep -n "getActiveModel\|active-model" src/app/services/photoshoot-api.service.ts
npm run build 2>&1 | tail -5
```
Expect: method present; build passes.

### Step 8: Add `expired` field to `GenerationTile` and map it from API response

**Action**: Extend the `GenerationTile` type to include an optional `expired` field. Update the `recentGenerations` computed signal in `photoshoot.page.ts` to map the `expired` field from the API response.

**File**: `src/app/pages/photoshoot/photoshoot.types.ts`

**Pattern**:
```typescript
export interface GenerationTile {
  id: string;
  index: number;
  thumbUrl: string;
  createdAt: string;
  expired?: boolean;
}
```

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

Update the `recentGenerations` computed to include `expired`:
```typescript
protected readonly recentGenerations = computed<GenerationTile[]>(() =>
  this.history().map((r, i) => ({
    id: r.id,
    index: i,
    thumbUrl: r.result_image_url,
    createdAt: r.created_at,
    expired: (r as any).expired ?? false,
  })),
);
```

Note: The `GenerationResponse` type from OpenAPI will include `expired` after Step 4's regeneration. If the type has not been regenerated yet, use `(r as any).expired` as a temporary cast and note in the commit body.

**Verify**:
```bash
grep -n "expired" src/app/pages/photoshoot/photoshoot.types.ts
grep -n "expired" src/app/pages/photoshoot/photoshoot.page.ts
npm run build 2>&1 | tail -5
```
Expect: field present in type and mapped in computed; build passes.

### Step 9: Extend contact-sheet component for expired placeholder

**Action**: In the contact-sheet template, check `g.expired`. If true, render a placeholder `<div>` with "Image expired" text and `data-test="tile-expired"` instead of the `<img>`. Add placeholder styling.

**File**: `src/app/pages/photoshoot/components/contact-sheet.component.ts`

**Pattern** -- update the template `<li>` content:
```html
<li
  *ngFor="let g of generations(); let i = index"
  class="tile"
  [class.expired]="g.expired"
  [attr.data-test]="'tile-' + i"
>
  <span class="num">{{ i + 1 | number: '2.0-0' }}</span>
  @if (g.expired) {
    <div class="expired-placeholder" data-test="tile-expired">
      <span class="expired-label">Image expired</span>
    </div>
  } @else {
    <img [src]="g.thumbUrl" [alt]="'Generation ' + (i + 1)" loading="lazy" />
  }
</li>
```

Add styles:
```css
.tile.expired {
  filter: grayscale(100%) opacity(0.5);
}

.expired-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface, #1a1a1a);
}

.expired-label {
  font-family: var(--font-body);
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  text-align: center;
  padding: 4px;
}
```

**Verify**:
```bash
grep -n "tile-expired\|expired-placeholder\|expired-label" src/app/pages/photoshoot/components/contact-sheet.component.ts
npm run build 2>&1 | tail -5
```
Expect: expired placeholder markup and styles present; build passes.

### Step 10: Add model label to photoshoot page header

**Action**: Add a signal for the model name, fetch it on init, and display it in the header bar next to the "Photoshoot" eyebrow.

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

**Pattern** -- add signal:
```typescript
protected readonly modelName = signal<string | null>(null);
```

Add to `ngOnInit`:
```typescript
this.loadActiveModel();
```

Add method:
```typescript
private async loadActiveModel(): Promise<void> {
  try {
    const resp = await this.api.getActiveModel(this.authToken.get());
    this.modelName.set(resp.model_name);
  } catch {
    /* non-fatal — model label is cosmetic */
  }
}
```

Update the header template:
```html
<header class="bar" data-test="photoshoot-header">
  <span class="eyebrow">Photoshoot</span>
  @if (modelName(); as name) {
    <span class="model-label" data-test="model-label">Model: {{ name }}</span>
  } @else {
    <span class="model-label no-model" data-test="model-label-empty">No model</span>
  }
</header>
```

Add styles:
```css
.model-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.4px;
  color: var(--text-secondary);
}

.model-label.no-model {
  color: var(--text-muted);
}
```

**Verify**:
```bash
grep -n "model-label\|modelName\|loadActiveModel" src/app/pages/photoshoot/photoshoot.page.ts
npm run build 2>&1 | tail -5
```
Expect: signal, fetch, and template binding all present; build passes.

---

## 5. Tests

### `src/app/pages/photoshoot/components/contact-sheet.component.spec.ts` (modify -- add expired cases)

```typescript
it('expiredTile_rendersPlaceholderNotImage', () => {
  const expiredTile: GenerationTile = {
    id: 'exp-1', index: 0, thumbUrl: 'https://expired.test/gone.png',
    createdAt: '2026-04-10T00:00:00Z', expired: true,
  };
  fixture.componentRef.setInput('generations', [expiredTile]);
  fixture.detectChanges();

  const placeholder = po.tile(0)!.querySelector("[data-test='tile-expired']");
  const img = po.tile(0)!.querySelector('img');
  expect(placeholder).withContext('expired placeholder should render').not.toBeNull();
  expect(placeholder!.textContent).toContain('Image expired');
  expect(img).withContext('img should not render for expired tile').toBeNull();
});

it('mixedTiles_rendersImagesAndPlaceholders', () => {
  const tiles: GenerationTile[] = [
    { id: 'ok-1', index: 0, thumbUrl: 'https://cdn.test/1.png', createdAt: '2026-04-15T00:00:00Z' },
    { id: 'exp-2', index: 1, thumbUrl: 'https://expired.test/2.png', createdAt: '2026-04-10T00:00:00Z', expired: true },
    { id: 'ok-3', index: 2, thumbUrl: 'https://cdn.test/3.png', createdAt: '2026-04-09T00:00:00Z' },
  ];
  fixture.componentRef.setInput('generations', tiles);
  fixture.detectChanges();

  expect(po.tile(0)!.querySelector('img')).not.toBeNull();
  expect(po.tile(1)!.querySelector("[data-test='tile-expired']")).not.toBeNull();
  expect(po.tile(2)!.querySelector('img')).not.toBeNull();
});
```

### `src/app/pages/photoshoot/photoshoot.page.spec.ts` (modify -- add model label + expired mapping)

Add to the existing `setup()` function's spy configuration:
```typescript
apiSpy = jasmine.createSpyObj<PhotoshootApiService>('PhotoshootApiService', [
  'generate',
  'getHistory',
  'getActiveModel',
]);
apiSpy.getActiveModel.and.resolveTo({ model_name: null });
```

Add new test cases:

```typescript
describe('model label', () => {
  it('modelExists_displaysModelName', async () => {
    apiSpy.getActiveModel.and.resolveTo({ model_name: 'Sam v3a' });
    await setup();
    await flush();

    const label = fixture.nativeElement.querySelector("[data-test='model-label']");
    expect(label).not.toBeNull();
    expect(label!.textContent).toContain('Model: Sam v3a');
  });

  it('noModel_displaysNoModelLabel', async () => {
    apiSpy.getActiveModel.and.resolveTo({ model_name: null });
    await setup();
    await flush();

    const label = fixture.nativeElement.querySelector("[data-test='model-label-empty']");
    expect(label).not.toBeNull();
    expect(label!.textContent).toContain('No model');
  });

  it('activeModelFetchFails_noLabelCrash', async () => {
    apiSpy.getActiveModel.and.rejectWith(new Error('network'));
    await setup();
    await flush();

    const label = fixture.nativeElement.querySelector("[data-test='model-label-empty']");
    expect(label).not.toBeNull();
  });
});

describe('expired tile mapping', () => {
  it('historyWithExpiredResult_mapsExpiredFlag', async () => {
    const expiredResult = {
      ...makeResult('exp-1'),
      expired: true,
    };
    apiSpy.getHistory.and.resolveTo([expiredResult as any]);
    await setup();
    await flush();

    const tiles = fixture.nativeElement.querySelectorAll("[data-test='tile-expired']");
    expect(tiles.length).toBe(1);
  });
});
```

### `server/tests/test_active_model_route.py` (new -- full content in Step 6)

See Step 6 for the complete test file.

---

## 6. Commit Plan

One commit per logical unit. Deviations logged in the commit body with `Deviations:` prefix.

1. `feat(photoshoot): add expired/is_active/model_name columns to ORM models` -- `server/modules/photoshoot/models.py`: Step 1
2. `feat(photoshoot): prefer is_active for model lookup with created_at fallback` -- `server/modules/photoshoot/repository.py`: Step 2
3. `feat(photoshoot): include expired field in generation response` -- `server/modules/photoshoot/routes.py`, `server/openapi/photoshoot.yaml`, regenerated types: Steps 3 + 4
4. `feat(photoshoot): GET /api/photoshoot/active-model endpoint` -- `server/modules/photoshoot/lora_routes.py`, `server/app.py`, `server/tests/test_active_model_route.py`: Steps 5 + 6
5. `feat(photoshoot): getActiveModel in frontend API service` -- `src/app/services/photoshoot-api.service.ts`: Step 7
6. `feat(photoshoot): expired placeholder in contact-sheet + model label in header` -- `src/app/pages/photoshoot/photoshoot.types.ts`, `src/app/pages/photoshoot/components/contact-sheet.component.ts`, `src/app/pages/photoshoot/photoshoot.page.ts`, all spec files: Steps 8 + 9 + 10

---

## 7. Verification

```bash
# Backend
cd server && python -m pytest --tb=short -v

# Frontend
npm run build
npm test -- --watch=false --browsers=ChromeHeadless

# ACL
npm run test:acl
```

**Expected delta**:
- Backend: baseline `N` to `N + 3` (3 active-model route tests). Zero regressions.
- Frontend: baseline `M` to `M + 7` (2 contact-sheet expired tests + 3 model label tests + 1 expired mapping test + 1 getActiveModel spy addition may require adjusting existing test count). Zero regressions.
- ACL: unchanged (no new Capacitor imports in page code).

Manual visual check (web, mock mode):
```bash
npm start
# Open http://localhost:8100/photoshoot
# Confirm: header shows "Model: Sam v3a" (mock) or "No model"
# Generate a photo; confirm it appears in contact sheet
# If mock data includes expired flag, confirm placeholder renders
```

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any one of the 6 commits.
- **Backend-only rollback**: if the new endpoint breaks existing routes, revert commits 1-4 (backend changes). Frontend code degrades gracefully -- `getActiveModel` fails silently, model label shows "No model".
- **Per-file emergency**: if the contact-sheet changes break rendering, `git checkout HEAD~1 -- src/app/pages/photoshoot/components/contact-sheet.component.ts` to restore prior version.
- **Per-branch**: `git reset --hard <pre-task-sha>` or delete the feature branch.

---

## 9. Deviations Allowed

- **Task 3 already added `expired` column to `Generation`** -- skip the model.py change for that column. Note in commit 1 body.
- **Task 2 already added `is_active` and `model_name` to `LoraModel`** -- skip those column additions. Note in commit 1 body.
- **`GenerationResponse` Pydantic DTO is auto-generated and read-only** -- the `expired` field must be added via OpenAPI YAML + regen. If the executor cannot regenerate DTOs (missing tooling), add `expired` as a manual dict field in `_serialize_generation` and note the deviation.
- **`getActiveModel` returns more fields than `model_name`** -- only consume `model_name` on the frontend; ignore extra fields.
- **Existing `PhotoshootApiService` mock in `setup()` does not include `getActiveModel`** -- add it to the `createSpyObj` call's method list. If the spy setup differs from the pattern shown, match the existing pattern.
- **`@if` control-flow syntax unavailable** -- if the project's Angular version uses `*ngIf` instead of `@if`, translate the template syntax accordingly. Log as deviation.
- **History endpoint already includes `expired` field** -- skip the routes.py serializer change. Note in commit body.
- **Side-effect commands required** (Alembic migration, push) -- STOP, mark `[REQUIRES APPROVAL]` and ask.

---

## 10. Out of Scope

This task adds the expired placeholder, model label, and unified history rendering. It does NOT create Alembic migration files, does NOT implement self-serve model training, and does NOT add click-to-restore on contact-sheet tiles.

- **Alembic migration file for new columns** -- Tasks 1-3 own the migration scripts; this task adds columns to the ORM model for code-level compatibility. If Tasks 1-3 have not run, the columns exist in Python but not in the live DB -- that is expected and resolved when the migration scripts execute.
- **Model picker (multi-model selection dropdown)** -- explicitly deferred in the epic; only the most-recent active model is shown
- **"No model" CTA (link to training)** -- deferred; the label just says "No model" with no action for v1
- **Click-to-restore on contact-sheet tiles** -- tiles are non-interactive; restoring a generation from history is a separate epic
- **Pagination/virtualization of history** -- the contact-sheet renders all rows; at 76 migrated + new generations, virtualization is not needed. Add when history exceeds 200 rows.
- **Re-downloading expired URLs to S3/R2** -- explicitly out of epic scope per architecture decision table
- **Backend Alembic migration for `expired`, `is_active`, `model_name`** -- belongs to Tasks 1-3
- **Toast notification for model label state changes** -- cosmetic label only, no transitions

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) -- design rationale, decision table
- [Epic](./epic.md) -- scope and business context
- [Timeline](./timeline.md) -- status tracking (update Task 5 to done after verification passes)
