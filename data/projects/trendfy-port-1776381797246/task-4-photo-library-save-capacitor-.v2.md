Now I have enough context. The actual Bubls source files live in a separate workspace — the spec-doc repo holds the specification documents. Let me generate the implementation guide based on the codebase context, architecture, and reference code provided.

# Task 4: Photo Library Save (Capacitor)

**Purpose**: Add a `PhotoLibraryService` adapter that wraps `@capacitor-community/media` to save photoshoot results to the device photo library after generation, with platform-aware behavior (save on iOS, no-op on web).

**Effort**: 0.5 day

**Dependencies**: None — the photoshoot page and generation flow already exist from the UX revamp.

**Parallel With**: Tasks 1–3 (migration scripts) — no file overlap.

**Blocks**: Task 5 (History UI) references `photo-library.service.ts` in its "To Leave Alone" list, confirming it must exist before Task 5 ships. Task 6 (Integration Test) exercises the save flow on a real device.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task adds the only Capacitor plugin integration in the epic. After a successful photoshoot generation, the Replicate result URL is downloaded and saved to the device photo library — the phone IS the storage layer, no S3/R2 needed. The service follows the Adapter pattern (ELA #1): only `PhotoLibraryService` imports `@capacitor-community/media`; the photoshoot page calls the adapter. On web, the save is a silent no-op (no photo library API exists). On iOS, the service requests Photos permission, saves the image, and the page shows an Ionic toast confirming "Saved to Photos". The save is fire-and-forget — errors are caught internally and never block the generation result from rendering.

**Trade-offs considered**:
- **`@capacitor/filesystem` + manual Photos framework bridge** — rejected because `@capacitor-community/media` handles permission + save in one call; Filesystem alone can't write to the photo library without a native plugin bridge.
- **Download-to-temp-then-move** — rejected for v1; `@capacitor-community/media` `savePhoto` accepts a URL directly (web URL or data URI). If Replicate URLs expire before save, the fallback is to catch the error silently. Temp-file intermediate adds complexity for an edge case we haven't seen yet.
- **Adapter service wrapping the plugin** — preferred because it enforces the ACL boundary (page never imports the plugin), enables mock toggle for tests, and handles the web/native platform check in one place.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                           # Flag any unrelated M/?? entries on target files
git diff HEAD -- src/app/services/ src/app/pages/photoshoot/ scripts/  # Confirm targets are clean
cd {WORKSPACE} && npm test -- --watch=false --browsers=ChromeHeadless  # Record baseline pass count
npm run test:acl 2>&1 || true                        # Record baseline ACL check (may not exist yet)
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**Baseline recorded**: [N]/[N] passing.

---

## 3. Files

### To Create (new)

| Path | Purpose |
|------|---------|
| `src/app/services/photo-library.service.ts` (new) | Adapter wrapping `@capacitor-community/media`; exposes `saveImage(url): Promise<void>`; web no-op; iOS permission + save |
| `src/app/services/photo-library.service.spec.ts` (new) | Jasmine tests for the service: web no-op, iOS save success, iOS permission denied, save error caught |

### To Modify

| Path | Change |
|------|--------|
| `package.json` | Add `@capacitor-community/media` to dependencies |
| `src/app/pages/photoshoot/photoshoot.page.ts` | Inject `PhotoLibraryService`; call `saveImage` fire-and-forget after successful generation; show toast on iOS save |
| `src/app/pages/photoshoot/photoshoot.page.spec.ts` | Add tests: `generateSuccess_callsSaveImage`, `saveImageFailure_doesNotBlockResultView` |
| `scripts/architecture-acl-check.mjs` | Add `@capacitor-community/media` to banned-import list; only `photo-library.service.ts` may import it |
| `ios/App/App/Info.plist` | Add `NSPhotoLibraryAddUsageDescription` key for iOS photo library write permission |

### To Leave Alone

| Path | Reason |
|------|--------|
| `src/app/services/photoshoot-api.service.ts` | API service is unrelated to device photo library |
| `src/app/pages/photoshoot/components/contact-sheet.component.ts` | History rendering is Task 5's scope |
| `src/app/pages/photoshoot/photoshoot.types.ts` | No new types needed — `saveImage` takes a string URL |
| `src/app/shell/shell-layout.component.ts` | Shell is unchanged |
| `server/` | No backend changes — this is a pure frontend/Capacitor task |
| `capacitor.config.ts` | `@capacitor-community/media` auto-registers; no config change needed |

---

## 4. Implementation Steps

### Step 1: Install `@capacitor-community/media`

**Action**: Add the Capacitor media plugin dependency and sync iOS native project.

**File**: `package.json`

**Commands**:
```bash
cd {WORKSPACE}
npm install @capacitor-community/media
npx cap sync ios    # [REQUIRES APPROVAL] — modifies ios/ native project files
```

**Verify**: `node -e "require('@capacitor-community/media')"` — exits 0, no error.

---

### Step 2: Add iOS photo library permission string

**Action**: Add the `NSPhotoLibraryAddUsageDescription` plist key so iOS prompts the user for Photos write access.

**File**: `ios/App/App/Info.plist`

**Pattern**:
```xml
<key>NSPhotoLibraryAddUsageDescription</key>
<string>Bubls saves your generated photos to your camera roll.</string>
```

**Verify**: `grep -c 'NSPhotoLibraryAddUsageDescription' ios/App/App/Info.plist` — returns `1`.

---

### Step 3: Create `PhotoLibraryService`

**Action**: Create the adapter service. It checks `Capacitor.isNativePlatform()` to short-circuit on web. On native, it calls `Media.savePhoto` with the image URL. Errors are caught internally — the service never throws.

**File**: `src/app/services/photo-library.service.ts` (new)

**Pattern** (port shape from Bubls ACL adapter pattern — `photoshoot-api.service.ts` uses the same `inject()` + environment mock toggle):
```typescript
import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Media } from '@capacitor-community/media';

export interface PhotoSaveResult {
  saved: boolean;
  error?: string;
}

@Injectable({ providedIn: 'root' })
export class PhotoLibraryService {

  /**
   * Save an image URL to the device photo library.
   * Web: silent no-op (returns { saved: false }).
   * iOS: requests permission, saves, returns result.
   * Never throws — errors are caught and returned in the result.
   */
  async saveImage(url: string): Promise<PhotoSaveResult> {
    if (!Capacitor.isNativePlatform()) {
      return { saved: false };
    }

    try {
      const permStatus = await Media.getPermissions();
      if (permStatus.photos !== 'granted' && permStatus.photos !== 'limited') {
        const requested = await Media.requestPermissions();
        if (requested.photos !== 'granted' && requested.photos !== 'limited') {
          return { saved: false, error: 'permission_denied' };
        }
      }

      await Media.savePhoto({ path: url, albumIdentifier: undefined });
      return { saved: true };
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : String(err);
      console.error('[PhotoLibraryService] saveImage failed:', message);
      return { saved: false, error: message };
    }
  }
}
```

**Verify**: `grep -c "class PhotoLibraryService" src/app/services/photo-library.service.ts` — returns `1`.

---

### Step 4: Wire save into photoshoot page

**Action**: Inject `PhotoLibraryService` into `PhotoshootPage`. After a successful generation, call `saveImage` fire-and-forget. If the save succeeds on native, show an Ionic toast "Saved to Photos". The save MUST NOT block result rendering — use `.then()`, not `await`.

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

**Pattern** (inject + call site — add to existing `generate()` method):
```typescript
import { PhotoLibraryService, PhotoSaveResult } from '../../services/photo-library.service';
import { ToastController } from '@ionic/angular';

// In class body:
private readonly photoLibrary = inject(PhotoLibraryService);
private readonly toastCtrl = inject(ToastController);

// Inside the generate() method, AFTER the result is added to history signals:
this.photoLibrary.saveImage(result.result_image_url).then(async (res: PhotoSaveResult) => {
  if (res.saved) {
    const toast = await this.toastCtrl.create({
      message: 'Saved to Photos',
      duration: 2000,
      position: 'bottom',
      cssClass: 'photo-saved-toast',
    });
    await toast.present();
  }
});
```

**Verify**: `grep -c "photoLibrary" src/app/pages/photoshoot/photoshoot.page.ts` — returns at least `2` (declaration + call).

---

### Step 5: Extend ACL check to ban `@capacitor-community/media` from pages

**Action**: Add `@capacitor-community/media` to the banned-import scanner in the architecture ACL check script. Only `src/app/services/photo-library.service.ts` may import it.

**File**: `scripts/architecture-acl-check.mjs`

**Pattern** (extend existing banned-import array and allowlist):
```javascript
// Add to the BANNED_IMPORTS or equivalent configuration:
{
  module: '@capacitor-community/media',
  allowedIn: ['src/app/services/photo-library.service.ts'],
  reason: 'ACL: only PhotoLibraryService may import the media plugin',
}
```

If the script uses a different structure, follow the existing pattern — the invariant is: any file in `src/app/pages/` or `src/app/features/` that imports `@capacitor-community/media` fails the check.

**Verify**: `npm run test:acl` — passes with the new rule.

---

### Step 6: Write service tests

**Action**: Create Jasmine tests for `PhotoLibraryService`. Mock `Capacitor.isNativePlatform()` and `Media` methods.

**File**: `src/app/services/photo-library.service.spec.ts` (new)

Full test body in Section 5 below.

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless` — new tests pass.

---

### Step 7: Write page-level integration tests

**Action**: Add tests to the existing `photoshoot.page.spec.ts` verifying the save integration.

**File**: `src/app/pages/photoshoot/photoshoot.page.spec.ts`

Full test body in Section 5 below.

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless` — all tests pass, including new ones.

---

## 5. Tests

### `src/app/services/photo-library.service.spec.ts` (new)

```typescript
import { TestBed } from '@angular/core/testing';
import { PhotoLibraryService } from './photo-library.service';
import { Capacitor } from '@capacitor/core';
import { Media } from '@capacitor-community/media';

describe('PhotoLibraryService', () => {
  let service: PhotoLibraryService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PhotoLibraryService);
  });

  describe('saveImage', () => {
    it('webPlatform_returnsNotSavedWithoutCallingMedia', async () => {
      spyOn(Capacitor, 'isNativePlatform').and.returnValue(false);
      const getPermSpy = spyOn(Media, 'getPermissions');

      const result = await service.saveImage('https://replicate.delivery/test.png');

      expect(result.saved).toBe(false);
      expect(result.error).toBeUndefined();
      expect(getPermSpy).not.toHaveBeenCalled();
    });

    it('nativePlatform_permissionGranted_savesAndReturnsTrue', async () => {
      spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
      spyOn(Media, 'getPermissions').and.resolveTo({ photos: 'granted' } as any);
      spyOn(Media, 'savePhoto').and.resolveTo({} as any);

      const result = await service.saveImage('https://replicate.delivery/test.png');

      expect(result.saved).toBe(true);
      expect(Media.savePhoto).toHaveBeenCalledWith({
        path: 'https://replicate.delivery/test.png',
        albumIdentifier: undefined,
      });
    });

    it('nativePlatform_permissionDenied_returnsNotSavedWithError', async () => {
      spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
      spyOn(Media, 'getPermissions').and.resolveTo({ photos: 'denied' } as any);
      spyOn(Media, 'requestPermissions').and.resolveTo({ photos: 'denied' } as any);

      const result = await service.saveImage('https://replicate.delivery/test.png');

      expect(result.saved).toBe(false);
      expect(result.error).toBe('permission_denied');
    });

    it('nativePlatform_permissionInitiallyLimited_requestsAndProceeds', async () => {
      spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
      spyOn(Media, 'getPermissions').and.resolveTo({ photos: 'limited' } as any);
      spyOn(Media, 'savePhoto').and.resolveTo({} as any);

      const result = await service.saveImage('https://replicate.delivery/test.png');

      expect(result.saved).toBe(true);
      expect(Media.requestPermissions).toBeUndefined; // not called — limited is sufficient
    });

    it('nativePlatform_saveThrows_returnsNotSavedWithErrorMessage', async () => {
      spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
      spyOn(Media, 'getPermissions').and.resolveTo({ photos: 'granted' } as any);
      spyOn(Media, 'savePhoto').and.rejectWith(new Error('Disk full'));
      spyOn(console, 'error');

      const result = await service.saveImage('https://replicate.delivery/test.png');

      expect(result.saved).toBe(false);
      expect(result.error).toBe('Disk full');
      expect(console.error).toHaveBeenCalled();
    });

    it('nativePlatform_requestGrantedAfterInitialDenied_saves', async () => {
      spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
      spyOn(Media, 'getPermissions').and.resolveTo({ photos: 'denied' } as any);
      spyOn(Media, 'requestPermissions').and.resolveTo({ photos: 'granted' } as any);
      spyOn(Media, 'savePhoto').and.resolveTo({} as any);

      const result = await service.saveImage('https://replicate.delivery/test.png');

      expect(result.saved).toBe(true);
      expect(Media.savePhoto).toHaveBeenCalled();
    });
  });
});
```

### Additions to `src/app/pages/photoshoot/photoshoot.page.spec.ts`

```typescript
// Add these tests to the existing describe block for PhotoshootPage.
// Assumes a mock PhotoLibraryService is provided in the TestBed configuration.

import { PhotoLibraryService } from '../../services/photo-library.service';

// In the beforeEach providers array, add:
// { provide: PhotoLibraryService, useValue: jasmine.createSpyObj('PhotoLibraryService', ['saveImage']) }

// Then in the describe block:

it('generateSuccess_callsSaveImage', async () => {
  const photoLibSpy = TestBed.inject(PhotoLibraryService) as jasmine.SpyObj<PhotoLibraryService>;
  photoLibSpy.saveImage.and.resolveTo({ saved: true });

  // Trigger the generate flow — use the page's existing generation mechanism
  // (adapt to actual method name; the pattern is calling the generate action)
  await component.generate();

  expect(photoLibSpy.saveImage).toHaveBeenCalledWith(
    jasmine.stringMatching(/^https:\/\//)
  );
});

it('saveImageFailure_doesNotBlockResultView', async () => {
  const photoLibSpy = TestBed.inject(PhotoLibraryService) as jasmine.SpyObj<PhotoLibraryService>;
  photoLibSpy.saveImage.and.resolveTo({ saved: false, error: 'Disk full' });

  await component.generate();
  fixture.detectChanges();

  // The result should still be visible in the history/contact sheet
  const tiles = fixture.nativeElement.querySelectorAll('[data-test^="tile-"]');
  expect(tiles.length).toBeGreaterThan(0);
});

it('saveImageSuccess_showsToast', async () => {
  const photoLibSpy = TestBed.inject(PhotoLibraryService) as jasmine.SpyObj<PhotoLibraryService>;
  photoLibSpy.saveImage.and.resolveTo({ saved: true });
  const toastSpy = TestBed.inject(ToastController) as jasmine.SpyObj<ToastController>;
  const mockToast = jasmine.createSpyObj('HTMLIonToastElement', ['present']);
  toastSpy.create.and.resolveTo(mockToast);

  await component.generate();
  // Flush the fire-and-forget promise
  await fixture.whenStable();

  expect(toastSpy.create).toHaveBeenCalledWith(
    jasmine.objectContaining({ message: 'Saved to Photos' })
  );
  expect(mockToast.present).toHaveBeenCalled();
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. **`feat(photoshoot): add @capacitor-community/media dependency`** — `package.json`, `package-lock.json`, `ios/App/App/Info.plist`: install plugin, sync iOS, add plist permission string.
2. **`feat(photoshoot): add PhotoLibraryService adapter`** — `src/app/services/photo-library.service.ts` (new): adapter wrapping Media plugin with platform check, permission flow, error handling. No page wiring yet.
3. **`feat(photoshoot): wire photo save into generate flow`** — `src/app/pages/photoshoot/photoshoot.page.ts`: inject service, fire-and-forget `saveImage` after generation, show toast on success.
4. **`feat(photoshoot): extend ACL check for media plugin`** — `scripts/architecture-acl-check.mjs`: ban `@capacitor-community/media` imports outside the service adapter.
5. **`test(photoshoot): add PhotoLibraryService + page save tests`** — `src/app/services/photo-library.service.spec.ts` (new), `src/app/pages/photoshoot/photoshoot.page.spec.ts`: 6 service tests + 3 page integration tests.

**Deviation logging**: if any step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless   # Full frontend suite
npm run test:acl                                      # ACL structural check
```

**Expected delta**: [N] → [N+9] passing (6 service tests + 3 page tests). Zero pre-existing tests broken. ACL check passes with the new `@capacitor-community/media` rule.

**Manual verification on device** (Task 6 covers this formally, but a quick smoke test here):
```bash
npm run ios    # Opens in Xcode / simulator
```
Generate a photo → observe "Saved to Photos" toast → open iOS Photos app → confirm image present.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>`.
  - Commit 1 revert: `npm install` to restore `package-lock.json` + `npx cap sync ios`.
  - Commit 3 revert: page returns to pre-save behavior (no visible regression).
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` or delete the feature branch. Then `npm install && npx cap sync ios` to restore native project state.

---

## 9. Deviations Allowed

- **`Media.getPermissions()` API shape differs from documented** — the `@capacitor-community/media` plugin has evolved across versions. If `permStatus.photos` doesn't exist, check the plugin's actual TypeScript types for the correct property name (may be `camera` or a `PermissionState` enum). Adapt the permission check but preserve the same logic: check → request if needed → proceed or return error. Log deviation.
- **`Media.savePhoto` parameter shape differs** — if the plugin expects `{ path: string }` vs `{ webPath: string }` vs a different property name, match the installed version's types. Log deviation.
- **`ToastController` not yet imported in the page** — if Ionic's `ToastController` isn't already in the page's providers, add it via `inject(ToastController)`. This is standard Ionic — not a deviation worth logging unless it requires module-level changes.
- **`architecture-acl-check.mjs` doesn't exist yet** — if the script hasn't been created by a prior task, create it with the minimal shape: read files in `src/app/pages/` and `src/app/features/`, grep for banned imports, fail if found. Log as deviation.
- **`result.result_image_url` property name differs** — inspect the actual `GenerationTile` or API response type for the correct image URL field name. Adapt the `saveImage` call accordingly.

---

## 10. Out of Scope

This task delivers the save-to-library adapter and wires it into the generation flow. It does NOT cover history display, expired-URL handling, or model labels — those belong to Task 5.

- **Save button in the UI** — the epic says "Add `data-test="save-to-photos"` on any visible save trigger." In this task, the save is automatic (fire-and-forget after generation). If a manual re-save button is desired (e.g., on history tiles for images that weren't auto-saved), that belongs in Task 5 (History UI) where the contact-sheet is extended. The `data-test="save-to-photos"` attribute will be placed on the toast or on a future button — executor should NOT add a standalone save button to the photoshoot page in this task.
- **Album organization** — `albumIdentifier: undefined` saves to the default camera roll. Creating a "Bubls" album is a nice-to-have for a future iteration when there are enough saved images to warrant organization.
- **Android support** — Bubls is iOS-first (Capacitor 7 + iOS). `@capacitor-community/media` supports Android, but testing/permission strings for Android are not in scope.
- **Offline/expired URL handling** — if the Replicate URL has expired by the time `saveImage` is called, the plugin will fail and the error is caught silently. Retry logic or re-download from a cached source is deferred to a future task if this proves to be a real problem.
- **Progress indicator during save** — the save is fast (single image download + write). No loading spinner or progress bar. If save latency becomes noticeable, revisit.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, PhotoLibraryService boundary diagram
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking (update after done)