# 🛠️ Task 3: /photoshoot route + camera + inference

**Purpose**: Add native camera capture, image upload, and a before/after gallery to the existing `/photoshoot` feature so testers can generate LoRA-styled photos from their own selfies instead of prompt-only input.

**Effort**: 2 days

**Dependencies**: Task 1 (shell scaffold) — routes and tab navigation must exist. The photoshoot module skeleton (service, repository, prompt-only flow) already exists in the repo.

**Parallel With**: Task 2 (auth + user model + gating) — this task consumes the user's LoRA model ID from Neon but does not need the new auth flow; it reads from the existing `superapp_users` table via `AuthTokenService`.

**Blocks**: Task 4 (deploy web + iOS) — TestFlight submission requires the camera flow to function.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The existing photoshoot module in this repo only accepts text prompts: a user types a prompt, the trigger word activates their LoRA, and Replicate returns a generated image. The epic task is to make the feature photo-first — capture a selfie (native camera on iOS via Capacitor, file input on web), upload it, run LoRA inference against the user's pre-trained model, and render the original next to the result. The before/after view is the "magic moment" the validation phase hinges on. This task therefore extends both sides: frontend gets a `CameraService` plus a `GalleryComponent` and reworks `PhotoshootPage`; backend adds an image-upload endpoint, a mapping from uploaded image → Replicate input → persisted result, and an `original_image_url` column on `superapp_generations`. The OpenAPI contract is updated in lockstep so both sides regenerate from the same YAML.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                                      # Flag any unrelated M/?? entries
git diff HEAD -- src/app/pages/photoshoot src/app/services/photoshoot-api.service.ts server/modules/photoshoot server/openapi/photoshoot.yaml
git log -1 --format='%H %s'                                                     # Record pre-task SHA for rollback
npm test -- --watch=false --browsers=ChromeHeadless                             # Baseline frontend passing count
(cd server && pytest -q)                                                        # Baseline backend passing count
```

**If working tree is dirty on target files**: stash or commit unrelated changes on a separate branch BEFORE starting. Do not mix this task's commits with pre-existing dirty state.

**Baseline recorded**: `F` frontend specs passing, `B` backend tests passing. Substitute the numbers from the two commands above into the Verification section.

---

## 3. Files

### To Create (new)
- `src/app/services/camera.service.ts` (new) — Injectable service wrapping `@capacitor/camera` with a file-input fallback; returns a normalized `{ dataUrl: string; mimeType: string; filename: string }` regardless of platform.
- `src/app/services/camera.service.spec.ts` (new) — Jasmine spec verifying native path delegates to `Camera.getPhoto` and web path opens a hidden `<input type=file>`.
- `src/app/pages/photoshoot/components/gallery/gallery.component.ts` (new) — Standalone OnPush component rendering a list of `{ originalUrl, resultUrl, createdAt }` pairs as a before/after swipe card.
- `src/app/pages/photoshoot/components/gallery/gallery.component.spec.ts` (new) — TestBed spec with a Page Object querying `data-test='gallery-pair'` and `data-test='gallery-empty'`.
- `server/migrations/versions/20260416_add_original_image_url.py` (new) — Alembic revision adding `original_image_url VARCHAR(2048) NULL` to `superapp_generations`.
- `server/tests/test_generate_from_image.py` (new) — pytest module covering the new upload endpoint (happy path, missing file, unauthorized, no LoRA mapping).

### To Modify (cite CODEBASE CONTEXT)
- `src/app/pages/photoshoot/photoshoot.page.ts` (`src/app/pages/photoshoot/`) — current state: prompt textarea + Submit + history list → target state: three entry points (`Take Photo`, `Choose from Library`, prompt-only legacy button kept behind `data-test='photoshoot-prompt-fallback'`), upload progress, integration with `GalleryComponent`.
- `src/app/pages/photoshoot/photoshoot.page.spec.ts` (same folder) — extend existing Page Object with camera/upload assertions.
- `src/app/services/photoshoot-api.service.ts` (`src/app/services/`) — add `generateFromImage(file: File | Blob): Promise<GenerationResponse>` posting multipart to `/photoshoot/generate-from-image`; reuse `AuthTokenService` for `Authorization: Bearer`.
- `src/app/services/photoshoot-api.service.spec.ts` — add specs for the new method (happy, 401, 422).
- `server/openapi/photoshoot.yaml` (`server/openapi/`) — add `POST /photoshoot/generate-from-image` with `multipart/form-data` body (`image: binary`) and response reusing existing `GenerationResponse`.
- `src/app/models/photoshoot.api.d.ts` — regenerated from YAML; do not hand-edit.
- `server/modules/photoshoot/dto.py` — regenerated from YAML; do not hand-edit.
- `server/modules/photoshoot/routes.py` (`server/modules/photoshoot/`) — add `@bp.post("/generate-from-image")` route; thin controller, passes `request.files["image"]` to service.
- `server/modules/photoshoot/service.py` — add `generate_from_image(user, file_storage) -> Generation`; resolves LoRA via existing repository helper, calls `ReplicateService` with image input, persists `original_image_url` + `result_url`.
- `server/modules/photoshoot/repository.py` — add `insert_generation_with_original(user_id, lora_id, original_url, result_url)`; keep existing inserter untouched.
- `server/modules/photoshoot/models.py` — add `original_image_url: Mapped[Optional[str]]` column matching the Alembic revision.
- `server/tests/test_service.py` — add `generate_from_image_noLora_raises`, `generate_from_image_persistsOriginalUrl`.
- `server/tests/test_routes.py` — add 401 + 422 + happy-path cases for the new route.

### To Leave Alone
- `src/app/shell/feature-registry.ts` — the `photoshoot` tab entry already points to the right path; the shell is feature-agnostic and must not learn about camera capture.
- `src/app/app.routes.ts` — no new route; we are extending the existing lazy-loaded `photoshoot` route.
- `server/app.py` — `ENABLED_MODULES` already includes `photoshoot`; no re-registration needed.
- `server/core/auth.py` — bearer-token lookup already works; do not add upload-specific auth.
- `src/app/services/picks.service.ts` and `src/app/pages/dashboard/` — unrelated feature, no cross-feature imports.
- `server/seed.py` — seeding semantics unchanged; new column is nullable so existing seed rows still load.

---

## 4. Implementation Steps

### Step 1: Update OpenAPI contract

**Action**: Add the `POST /photoshoot/generate-from-image` operation to the YAML, then regenerate both TS types and Pydantic DTOs. The YAML is the single source of truth — neither `photoshoot.api.d.ts` nor `dto.py` is edited by hand.

**File**: `server/openapi/photoshoot.yaml`

**Pattern**:
```yaml
paths:
  /photoshoot/generate-from-image:
    post:
      operationId: generateFromImage
      security: [{ bearerAuth: [] }]
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              required: [image]
              properties:
                image: { type: string, format: binary }
      responses:
        '200': { $ref: '#/components/responses/GenerationResponse' }
        '401': { $ref: '#/components/responses/Unauthorized' }
        '422': { $ref: '#/components/responses/ValidationError' }
```

**Verify**: `npm run gen:all` — expect zero diff noise except the intended additions in `src/app/models/photoshoot.api.d.ts` and `server/modules/photoshoot/dto.py`.

### Step 2: Alembic migration for `original_image_url`

**Action**: Generate a new revision adding the nullable column to `superapp_generations`, then update the ORM model to match. Nullable so existing rows remain valid.

**File**: `server/migrations/versions/20260416_add_original_image_url.py` (new) and `server/modules/photoshoot/models.py`

**Pattern**:
```python
# migration upgrade()
op.add_column(
    "superapp_generations",
    sa.Column("original_image_url", sa.String(2048), nullable=True),
)
# downgrade()
op.drop_column("superapp_generations", "original_image_url")
```

```python
# models.py — add beside existing fields
original_image_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
```

**Verify**: `cd server && alembic upgrade head && alembic downgrade -1 && alembic upgrade head` — expect clean up/down/up cycle with no errors.

### Step 3: Backend — repository + service + route

**Action**: Add an insertion helper that accepts the original image URL, a service method that orchestrates LoRA lookup → Replicate call → persistence, and a thin Flask route that reads `request.files["image"]`. Reuse the existing `ReplicateService` wrapper; do not inline Replicate calls in the route.

**File**: `server/modules/photoshoot/repository.py`, `service.py`, `routes.py`

**Pattern**:
```python
# repository.py
def insert_generation_with_original(
    session, *, user_id: UUID, lora_id: UUID, original_url: str, result_url: str
) -> Generation:
    gen = Generation(
        user_id=user_id, lora_model_id=lora_id,
        original_image_url=original_url, result_url=result_url,
    )
    session.add(gen); session.flush()
    return gen

# service.py
def generate_from_image(user: User, file_storage) -> Generation:
    lora = repository.get_lora_for_user(session, user.id)
    if lora is None:
        raise NoLoraModelError(user.id)
    original_url = replicate_service.upload_input_image(file_storage)
    result_url = replicate_service.run_lora_image_to_image(
        model_id=lora.replicate_model_id, input_image_url=original_url,
    )
    return repository.insert_generation_with_original(
        session, user_id=user.id, lora_id=lora.id,
        original_url=original_url, result_url=result_url,
    )

# routes.py
@bp.post("/generate-from-image")
@require_bearer_token
def generate_from_image_route():
    if "image" not in request.files:
        return {"error": "image field required"}, 422
    gen = service.generate_from_image(g.current_user, request.files["image"])
    return GenerationResponse.model_validate(gen).model_dump(), 200
```

**Verify**: `cd server && pytest server/tests/test_routes.py server/tests/test_service.py server/tests/test_repository.py -q` — expect all existing tests still pass; the new tests come in Step 7.

### Step 4: Frontend — CameraService

**Action**: Create a standalone injectable service that checks `Capacitor.isNativePlatform()` and calls `Camera.getPhoto({ resultType: CameraResultType.DataUrl, source: CameraSource.Camera })` on native, or opens a hidden file input on web. Normalize to `{ dataUrl, mimeType, filename }`.

**File**: `src/app/services/camera.service.ts` (new)

**Pattern**:
```typescript
@Injectable({ providedIn: 'root' })
export class CameraService {
  async capture(): Promise<CapturedPhoto> {
    if (Capacitor.isNativePlatform()) {
      const photo = await Camera.getPhoto({
        resultType: CameraResultType.DataUrl,
        source: CameraSource.Camera,
        quality: 85,
      });
      return { dataUrl: photo.dataUrl!, mimeType: `image/${photo.format}`, filename: `capture.${photo.format}` };
    }
    return this.pickFromWebInput();
  }
  async pickFromLibrary(): Promise<CapturedPhoto> { /* source: CameraSource.Photos */ }
  private pickFromWebInput(): Promise<CapturedPhoto> { /* hidden <input type=file accept=image/*> */ }
}
```

**Verify**: `npx tsc --noEmit` (or rely on `npm test` compilation) — expect no type errors.

### Step 5: Frontend — extend PhotoshootApiService

**Action**: Add `generateFromImage(file: Blob, filename: string): Promise<GenerationResponse>` that builds a `FormData`, sets `Authorization: Bearer` from `AuthTokenService`, and posts to `/photoshoot/generate-from-image`. Reuse the base URL already defined in the service.

**File**: `src/app/services/photoshoot-api.service.ts`

**Pattern**:
```typescript
async generateFromImage(file: Blob, filename: string): Promise<GenerationResponse> {
  const form = new FormData();
  form.append('image', file, filename);
  const res = await fetch(`${this.baseUrl}/photoshoot/generate-from-image`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${this.authToken.get()}` },
    body: form,
  });
  if (res.status === 401) throw new UnauthorizedError();
  if (!res.ok) throw new PhotoshootApiError(await res.text());
  return (await res.json()) as GenerationResponse;
}
```

**Verify**: `npm test -- --watch=false --include='**/photoshoot-api.service.spec.ts'` — expect previously-passing specs still pass; new specs added in Step 7.

### Step 6: Frontend — GalleryComponent + PhotoshootPage wiring

**Action**: Build a standalone `GalleryComponent` that takes a `generations` input signal and renders before/after pairs. Modify `PhotoshootPage` to inject `CameraService`, wire the two buttons (`data-test='photoshoot-capture'`, `data-test='photoshoot-library'`), call `generateFromImage`, push results onto the existing history signal, and render `<app-gallery [generations]="history()">`.

**File**: `src/app/pages/photoshoot/components/gallery/gallery.component.ts` (new) and `src/app/pages/photoshoot/photoshoot.page.ts`

**Pattern**:
```typescript
// gallery.component.ts
@Component({
  selector: 'app-gallery', standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (generations().length === 0) {
      <div data-test="gallery-empty">No photos yet</div>
    } @else {
      @for (g of generations(); track g.id) {
        <article data-test="gallery-pair">
          <img [src]="g.originalImageUrl" data-test="gallery-before" />
          <img [src]="g.resultUrl" data-test="gallery-after" />
        </article>
      }
    }`,
})
export class GalleryComponent {
  generations = input.required<GenerationResponse[]>();
}

// photoshoot.page.ts — add (existing template fragments retained)
async onCapture() {
  const photo = await this.camera.capture();
  const blob = await (await fetch(photo.dataUrl)).blob();
  const gen = await this.api.generateFromImage(blob, photo.filename);
  this.history.update(list => [gen, ...list]);
}
```

**Verify**: `npm start` (manual), navigate to `/photoshoot`, click `Take Photo` in Chrome — expect web file input fallback, upload completes, new pair appears in gallery. Also `npm test -- --watch=false --include='**/photoshoot*'`.

### Step 7: Tests

**Action**: Write the specs described in the Tests section below. Match the existing repo convention: Jasmine + TestBed for Angular, pytest with the existing fixtures (`client`, `db_session`, `seeded_user`) for Flask.

**File**: as listed in §3 To Create and the `-spec.ts` / `test_*.py` siblings in §3 To Modify.

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless` and `cd server && pytest -q` — both green.

### Step 8: Final integration pass

**Action**: Run `npm run gen:all`, full frontend suite, full backend suite, and `npm run build` once to catch AOT errors that karma/jest miss.

**Verify**:
```bash
npm run gen:all
npm test -- --watch=false --browsers=ChromeHeadless
(cd server && pytest -q)
npm run build
```

Expect clean exit from all four.

---

## 5. Tests

Frontend — Karma + Jasmine, TestBed with Page Objects querying `data-test` only.

```typescript
// src/app/services/camera.service.spec.ts
describe('CameraService', () => {
  let service: CameraService;
  beforeEach(() => { TestBed.configureTestingModule({}); service = TestBed.inject(CameraService); });

  it('nativePlatform_delegatesToCapacitorCamera', async () => {
    spyOnProperty(Capacitor, 'isNativePlatform').and.returnValue(() => true);
    const getPhoto = spyOn(Camera, 'getPhoto').and.resolveTo({ dataUrl: 'data:image/jpeg;base64,AAA', format: 'jpeg' } as any);
    const result = await service.capture();
    expect(getPhoto).toHaveBeenCalledTimes(1);
    expect(result.dataUrl).toBe('data:image/jpeg;base64,AAA');
    expect(result.mimeType).toBe('image/jpeg');
  });

  it('webPlatform_opensFileInput', async () => {
    spyOnProperty(Capacitor, 'isNativePlatform').and.returnValue(() => false);
    const clickSpy = spyOn(HTMLInputElement.prototype, 'click');
    const promise = service.capture();
    const input = document.querySelector('input[type=file]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(clickSpy).toHaveBeenCalled();
    const file = new File(['x'], 'pic.png', { type: 'image/png' });
    Object.defineProperty(input, 'files', { value: [file] });
    input.dispatchEvent(new Event('change'));
    const result = await promise;
    expect(result.filename).toBe('pic.png');
    expect(result.mimeType).toBe('image/png');
  });
});
```

```typescript
// src/app/services/photoshoot-api.service.spec.ts — added specs
it('generateFromImage_postsMultipartWithBearer', async () => {
  authToken.get.and.returnValue('tok-123');
  const fetchSpy = spyOn(window, 'fetch').and.resolveTo(new Response(JSON.stringify(fakeGen), { status: 200 }));
  const blob = new Blob(['x'], { type: 'image/png' });
  const result = await service.generateFromImage(blob, 'pic.png');
  const [, init] = fetchSpy.calls.mostRecent().args as [string, RequestInit];
  expect((init.headers as any).Authorization).toBe('Bearer tok-123');
  expect(init.body).toBeInstanceOf(FormData);
  expect(result.id).toBe(fakeGen.id);
});

it('generateFromImage_on401_throwsUnauthorized', async () => {
  spyOn(window, 'fetch').and.resolveTo(new Response('', { status: 401 }));
  await expectAsync(service.generateFromImage(new Blob(), 'p.png')).toBeRejectedWithError(UnauthorizedError);
});

it('generateFromImage_on422_throwsApiError', async () => {
  spyOn(window, 'fetch').and.resolveTo(new Response('missing image', { status: 422 }));
  await expectAsync(service.generateFromImage(new Blob(), 'p.png')).toBeRejectedWithError(PhotoshootApiError);
});
```

```typescript
// src/app/pages/photoshoot/components/gallery/gallery.component.spec.ts
class GalleryPO {
  constructor(private f: ComponentFixture<GalleryComponent>) {}
  pairs() { return this.f.nativeElement.querySelectorAll("[data-test='gallery-pair']"); }
  empty() { return this.f.nativeElement.querySelector("[data-test='gallery-empty']"); }
}

describe('GalleryComponent', () => {
  it('emptyList_rendersEmptyState', () => {
    const f = TestBed.createComponent(GalleryComponent);
    f.componentRef.setInput('generations', []);
    f.detectChanges();
    const po = new GalleryPO(f);
    expect(po.empty()).not.toBeNull();
    expect(po.pairs().length).toBe(0);
  });

  it('twoGenerations_rendersTwoBeforeAfterPairs', () => {
    const f = TestBed.createComponent(GalleryComponent);
    f.componentRef.setInput('generations', [
      { id: '1', originalImageUrl: 'o1', resultUrl: 'r1', createdAt: '2026-04-16' },
      { id: '2', originalImageUrl: 'o2', resultUrl: 'r2', createdAt: '2026-04-16' },
    ]);
    f.detectChanges();
    const po = new GalleryPO(f);
    expect(po.pairs().length).toBe(2);
    expect(po.empty()).toBeNull();
  });
});
```

```typescript
// src/app/pages/photoshoot/photoshoot.page.spec.ts — added specs
it('captureButton_clicked_invokesCameraAndApi', async () => {
  camera.capture.and.resolveTo({ dataUrl: 'data:image/png;base64,AAA', mimeType: 'image/png', filename: 'p.png' });
  api.generateFromImage.and.resolveTo({ id: 'g1', originalImageUrl: 'o', resultUrl: 'r', createdAt: '2026-04-16' });
  po.captureButton.click();
  await fixture.whenStable();
  expect(camera.capture).toHaveBeenCalledTimes(1);
  expect(api.generateFromImage).toHaveBeenCalledTimes(1);
  expect(po.galleryPairs().length).toBe(1);
});

it('cameraRejects_showsErrorToast', async () => {
  camera.capture.and.rejectWith(new Error('denied'));
  po.captureButton.click();
  await fixture.whenStable();
  expect(po.errorToast.textContent).toContain('denied');
});
```

Backend — pytest with the existing fixtures.

```python
# server/tests/test_generate_from_image.py
def noBearer_returns401(client):
    resp = client.post("/photoshoot/generate-from-image", data={"image": (io.BytesIO(b"x"), "p.png")})
    assert resp.status_code == 401

def missingImageField_returns422(client, seeded_user_token):
    resp = client.post(
        "/photoshoot/generate-from-image",
        headers={"Authorization": f"Bearer {seeded_user_token}"},
        data={},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 422
    assert b"image field required" in resp.data

def validUpload_returns200AndPersistsOriginalUrl(client, db_session, seeded_user_token, seeded_lora, mock_replicate):
    mock_replicate.upload_input_image.return_value = "https://r.delivery/in.png"
    mock_replicate.run_lora_image_to_image.return_value = "https://r.delivery/out.png"
    resp = client.post(
        "/photoshoot/generate-from-image",
        headers={"Authorization": f"Bearer {seeded_user_token}"},
        data={"image": (io.BytesIO(b"fakeimg"), "selfie.png")},
        content_type="multipart/form-data",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["originalImageUrl"] == "https://r.delivery/in.png"
    assert body["resultUrl"] == "https://r.delivery/out.png"
    row = db_session.execute(select(Generation).where(Generation.id == body["id"])).scalar_one()
    assert row.original_image_url == "https://r.delivery/in.png"
```

```python
# server/tests/test_service.py — added cases
def generate_from_image_noLora_raisesNoLoraModelError(db_session, user_without_lora, mock_replicate):
    with pytest.raises(NoLoraModelError):
        service.generate_from_image(user_without_lora, _fake_file())
    mock_replicate.run_lora_image_to_image.assert_not_called()

def generate_from_image_persistsOriginalAndResultUrls(db_session, seeded_user_with_lora, mock_replicate):
    mock_replicate.upload_input_image.return_value = "https://r/in.png"
    mock_replicate.run_lora_image_to_image.return_value = "https://r/out.png"
    gen = service.generate_from_image(seeded_user_with_lora, _fake_file())
    assert gen.original_image_url == "https://r/in.png"
    assert gen.result_url == "https://r/out.png"
    assert gen.lora_model_id == seeded_user_with_lora.lora.id
```

---

## 6. Commit Plan

One commit per logical unit. Each is independently revertible.

1. `feat(photoshoot): add generate-from-image to OpenAPI + regen DTOs` — `server/openapi/photoshoot.yaml`, `server/modules/photoshoot/dto.py` (regen), `src/app/models/photoshoot.api.d.ts` (regen).
2. `feat(photoshoot/db): add original_image_url to generations` — Alembic revision + `server/modules/photoshoot/models.py`.
3. `feat(photoshoot/api): generate-from-image endpoint + service` — `routes.py`, `service.py`, `repository.py`.
4. `test(photoshoot/api): cover new endpoint + service paths` — `test_generate_from_image.py`, additions to `test_service.py`, `test_routes.py`.
5. `feat(photoshoot/ui): CameraService with native + web paths` — `camera.service.ts` + spec.
6. `feat(photoshoot/ui): GalleryComponent before/after` — gallery component + spec.
7. `feat(photoshoot/ui): wire capture + upload into PhotoshootPage` — `photoshoot.page.ts`, `photoshoot-api.service.ts`, their specs.
8. `chore(gen): refresh generated contracts` — only if `npm run gen:all` produces delta after step 7.

**Deviation logging**: if any step deviates from this guide (e.g., moving a file, splitting a commit, picking a different library), prefix the commit body with `Deviations:` followed by one line per deviation.

---

## 7. Verification

```bash
npm run gen:all
npm test -- --watch=false --browsers=ChromeHeadless
(cd server && pytest -q)
npm run build
```

**Expected delta**:
- Frontend: `F` → `F + 9` passing (2 camera + 3 api-service + 2 gallery + 2 page). Zero pre-existing specs broken.
- Backend: `B` → `B + 5` passing (3 route + 2 service). Zero pre-existing tests broken.
- `npm run build` exits 0.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` in reverse order of commits 1–8. Migration rollback: `cd server && alembic downgrade -1` before reverting commit 2.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (recorded in Pre-flight). If on a feature branch: `git switch master && git branch -D <feature-branch>` (local only; never force-push).
- **Never** re-run `alembic downgrade` against a deployed environment without [REQUIRES APPROVAL].

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → verify in CODEBASE CONTEXT; if still missing, flag it in the commit body and do not invent. The photoshoot module skeleton is presumed present per codebase scan of 2026-04-16.
- **Test framework mismatch** (e.g., repo moved to Vitest since scan) → match the repo's current convention; translate assertions silently but note the translation in the commit body.
- **Side-effect required** — deploy (`git push`, Coolify webhook), TestFlight upload, production DB migration, drop/truncate — STOP, mark `[REQUIRES APPROVAL]`, and ask before running.
- **Capacitor Camera plugin not installed** → if `@capacitor/camera` is missing despite codebase.md listing it, run `npm i @capacitor/camera@^8 && npx cap sync ios` and log it as a Deviation in commit 5.
- **Step N unlocks an obvious simplification for Step N+1** (e.g., the existing `insert_generation` already covers the new column once the model is updated) → take it, and log the deviation in the commit body rather than creating a redundant helper.
- **Replicate image-to-image endpoint unavailable for a given LoRA** → keep the upload + persistence path, stub `run_lora_image_to_image` to return a placeholder URL, and flag in the commit body so the integration test lands in a follow-up.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, camera risk mitigation
- [Epic](./epic.md) – Task scope and dependencies
- [Timeline](./timeline.md) – Status tracking (update after done)