# Task 4: Photo Library Save (Capacitor)

**Purpose**: After a successful photoshoot generation, persist the result image to the device photo library so it survives Replicate URL expiry. Wrap the Capacitor plugin in an adapter service so page code never imports `@capacitor-community/media` directly.

**Effort**: 0.5 day

**Dependencies**: None (runs in parallel with Tasks 1-3)

**Parallel With**: Task 1 (User Migration), Task 2 (Model Migration), Task 3 (Result Migration)

**Blocks**: Task 5 (History UI needs photo-library save wired into the generate flow)

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

Replicate CDN URLs expire after a few hours. Once they do, the generated image is gone unless the user saved it. This task installs `@capacitor-community/media` and wraps it in a `PhotoLibraryService` adapter so the photoshoot page can call `saveImage(url)` without knowing the Capacitor plugin exists. On web, the call is a no-op (no photo library API). On iOS, the service requests Photos permission, downloads the image to a temp file, saves to the device library, and logs success. The photoshoot page calls this after a successful generation, right after setting the result signal.

The ACL invariant is enforced by extending the existing `scripts/architecture-acl-check.mjs` to ban `@capacitor-community/media` from page/feature code. Only `PhotoLibraryService` may import it.

**Trade-offs considered**:
- **`@capacitor/filesystem` + native Photos framework bridge** -- rejected because `@capacitor-community/media` wraps the Photos save in one call; rolling our own bridge is more code for the same result and zero additional capability
- **Save on user tap (explicit "Save to Photos" button)** -- rejected for v1 because auto-save-on-generate is the simpler UX; a manual save button can come later if users want to selectively skip saves
- **Download to app-internal filesystem instead of photo library** -- rejected because users expect generated photos to appear in their camera roll; app-internal files are not discoverable outside the app

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                       # Flag any unrelated M/?? entries
git log --oneline -10                                            # Confirm UX-revamp commits are present
ls src/app/services/                                             # Inventory existing services
ls src/app/pages/photoshoot/                                     # Confirm photoshoot page files
cat package.json | grep -E "capacitor|media"                     # Confirm @capacitor-community/media is NOT yet installed
cat scripts/architecture-acl-check.mjs                           # Read existing ACL check structure
npm test -- --watch=false --browsers=ChromeHeadless 2>&1 | tail -20   # Record baseline pass count
npm run test:acl 2>&1 | tail -10                                 # Record baseline ACL check result
```

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**If `@capacitor-community/media` is already installed**: STOP -- someone else may have started this task. Verify with the team before proceeding.

**Baseline recorded**: write the test pass count here before starting (e.g., `58/58 passing`).

---

## 3. Files

### To Create (new)
- `src/app/services/photo-library.service.ts` -- adapter wrapping `@capacitor-community/media`; exposes `saveImage(url: string): Promise<void>`; web no-op; iOS: permission request + save + console log
- `src/app/services/photo-library.service.spec.ts` -- Karma/Jasmine unit tests; mock Capacitor platform check; assert web no-op, native save call, permission denied error handling

### To Modify
- `package.json` -- add `@capacitor-community/media` to `dependencies`
- `scripts/architecture-acl-check.mjs` -- extend `BANNED` array with `@capacitor-community/media`; no changes to `KNOWN_VIOLATIONS`
- `src/app/pages/photoshoot/photoshoot.page.ts` -- inject `PhotoLibraryService`; call `saveImage(result.result_image_url)` after successful generation (fire-and-forget, no await -- save failure must not block UX)
- `src/app/pages/photoshoot/photoshoot.page.spec.ts` -- add test case: `generateSuccess_callsSaveImage` verifying the service is called with the result URL; add test case: `saveImageFailure_doesNotBlockResultView` verifying the page still transitions to result view even if save throws
- `ios/App/App/Info.plist` -- add `NSPhotoLibraryAddUsageDescription` key with value "Bubls saves your generated photos to your camera roll."
- `capacitor.config.ts` -- no changes needed (plugin auto-registers)

### To Leave Alone
- `src/app/services/photoshoot-api.service.ts` -- API surface unchanged
- `src/app/pages/photoshoot/components/` -- contact-sheet and progress-portrait untouched
- `src/app/pages/photoshoot/photoshoot.types.ts` -- no new types needed
- `server/` -- no backend changes
- `src/app/pages/home/`, `src/app/pages/text/` -- other feature folders
- `src/app/shell/` -- shell is not involved

---

## 4. Implementation Steps

### Step 1: Install `@capacitor-community/media`

**Action**: Add the Capacitor plugin as a production dependency.

**File**: `package.json`

**Pattern**:
```bash
npm install @capacitor-community/media
```

**Verify**:
```bash
grep "@capacitor-community/media" package.json
ls node_modules/@capacitor-community/media/package.json
```
Expect: dependency listed in `package.json`; package exists in `node_modules`.

### Step 2: Add `NSPhotoLibraryAddUsageDescription` to Info.plist

**Action**: Add the photo library usage description string so iOS prompts the user for permission. Use `NSPhotoLibraryAddUsageDescription` (write-only access -- we do not need read access to the photo library).

**File**: `ios/App/App/Info.plist`

**Pattern**: Add this key-value pair inside the top-level `<dict>`:
```xml
<key>NSPhotoLibraryAddUsageDescription</key>
<string>Bubls saves your generated photos to your camera roll.</string>
```

**Verify**:
```bash
grep -A1 "NSPhotoLibraryAddUsageDescription" ios/App/App/Info.plist
```
Expect: key and string value present.

### Step 3: Create `PhotoLibraryService` adapter

**Action**: Create the adapter service. It is `providedIn: 'root'` (singleton). The `saveImage` method checks `Capacitor.isNativePlatform()`. On web: return immediately (no-op). On native: use `Media.savePhoto({ path: url })` from `@capacitor-community/media`. Wrap in try/catch -- log errors to console but do not throw (caller treats save as fire-and-forget). Request permissions via `Media.getMedias()` or the plugin's built-in permission flow before saving.

**File**: `src/app/services/photo-library.service.ts` (new)

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Media } from '@capacitor-community/media';

@Injectable({ providedIn: 'root' })
export class PhotoLibraryService {
  /**
   * Save an image URL to the device photo library.
   * On web: no-op (no photo library API).
   * On native: downloads the URL and saves to the camera roll.
   * Errors are logged but never thrown -- callers treat this as fire-and-forget.
   */
  async saveImage(url: string): Promise<void> {
    if (!Capacitor.isNativePlatform()) {
      return;
    }
    try {
      await Media.savePhoto({ path: url, albumIdentifier: undefined });
      console.info('[PhotoLibrary] saved to camera roll');
    } catch (err) {
      console.error('[PhotoLibrary] save failed:', err);
    }
  }
}
```

**Verify**:
```bash
grep -n "Media" src/app/services/photo-library.service.ts
grep -n "@capacitor-community/media" src/app/services/photo-library.service.ts
npm run build 2>&1 | tail -5
```
Expect: `Media` imported from `@capacitor-community/media`; build passes.

### Step 4: Extend ACL check to ban `@capacitor-community/media` from pages

**Action**: Add `@capacitor-community/media` to the `BANNED` array in `scripts/architecture-acl-check.mjs`. The service file lives in `src/app/services/`, which is outside the `ROOTS` scan directories (`src/app/pages`, `src/app/features`), so it will not trigger a violation.

**File**: `scripts/architecture-acl-check.mjs`

**Pattern**: Change the `BANNED` array from:
```javascript
const BANNED = ['@capacitor/status-bar', '@capacitor/haptics'];
```
to:
```javascript
const BANNED = ['@capacitor/status-bar', '@capacitor/haptics', '@capacitor-community/media'];
```

**Verify**:
```bash
npm run test:acl 2>&1
```
Expect: PASS or SKIPPED-WITH-REASON (existing known violations only); no new failures. The service file is in `src/app/services/`, not under `src/app/pages/` or `src/app/features/`, so it is not scanned.

### Step 5: Wire `PhotoLibraryService` into photoshoot page generate flow

**Action**: Inject `PhotoLibraryService` in `PhotoshootPage`. After a successful generation (after `this.latest.set(result)` and `this.history.update(...)`), call `this.photoLibrary.saveImage(result.result_image_url)` as a fire-and-forget (no `await`). The `.catch(() => {})` is already inside the service, so the page does not need error handling.

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

**Pattern**: Add to the class:
```typescript
private readonly photoLibrary = inject(PhotoLibraryService);
```

In the `generate()` method, after the line `this.history.update((rows) => [result, ...rows]);`, add:
```typescript
this.photoLibrary.saveImage(result.result_image_url);
```

Import at top of file:
```typescript
import { PhotoLibraryService } from '../../services/photo-library.service';
```

**Verify**:
```bash
grep -n "PhotoLibraryService\|photoLibrary\|saveImage" src/app/pages/photoshoot/photoshoot.page.ts
grep -n "@capacitor-community/media" src/app/pages/photoshoot/photoshoot.page.ts
npm run build 2>&1 | tail -5
```
Expect: `PhotoLibraryService` injected and `saveImage` called; NO direct import of `@capacitor-community/media` in the page file; build passes.

### Step 6: Verify ACL check still passes after page modification

**Action**: Run the ACL check to confirm the photoshoot page does not import the banned plugin directly.

**File**: N/A

**Pattern**:
```bash
npm run test:acl 2>&1
```

**Verify**: Expect same result as Step 4 -- no new violations. If the page accidentally imports `@capacitor-community/media`, the check will FAIL and print the violating file.

---

## 5. Tests

Karma + Jasmine. TestBed with real or mocked dependencies. Page Object with `data-test` selectors. Test naming: `condition_expectedOutcome`.

### `src/app/services/photo-library.service.spec.ts` (new)

```typescript
import { TestBed } from '@angular/core/testing';
import { Capacitor } from '@capacitor/core';
import { Media } from '@capacitor-community/media';
import { PhotoLibraryService } from './photo-library.service';

describe('PhotoLibraryService', () => {
  let service: PhotoLibraryService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PhotoLibraryService);
  });

  it('webPlatform_saveImage_returnsWithoutCallingMedia', async () => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(false);
    const saveSpy = spyOn(Media, 'savePhoto');
    await service.saveImage('https://cdn.example.com/photo.png');
    expect(saveSpy).not.toHaveBeenCalled();
  });

  it('nativePlatform_saveImage_callsMediaSavePhoto', async () => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
    const saveSpy = spyOn(Media, 'savePhoto').and.resolveTo({} as any);
    await service.saveImage('https://cdn.example.com/photo.png');
    expect(saveSpy).toHaveBeenCalledOnceWith({
      path: 'https://cdn.example.com/photo.png',
      albumIdentifier: undefined,
    });
  });

  it('nativePlatform_savePhotoThrows_doesNotRethrow', async () => {
    spyOn(Capacitor, 'isNativePlatform').and.returnValue(true);
    spyOn(Media, 'savePhoto').and.rejectWith(new Error('Permission denied'));
    const errorSpy = spyOn(console, 'error');
    await expectAsync(
      service.saveImage('https://cdn.example.com/photo.png'),
    ).toBeResolved();
    expect(errorSpy).toHaveBeenCalledWith(
      '[PhotoLibrary] save failed:',
      jasmine.any(Error),
    );
  });
});
```

### `src/app/pages/photoshoot/photoshoot.page.spec.ts` (modify -- add cases)

Add to the existing `describe('generate happy path', ...)` block:

```typescript
it('generateSuccess_callsSaveImage', async () => {
  await setup();
  const photoLib = TestBed.inject(PhotoLibraryService);
  const saveSpy = spyOn(photoLib, 'saveImage').and.resolveTo();
  apiSpy.generate.and.resolveTo(makeResult('saved-1'));

  page.tapGenerate();
  await flush();
  await new Promise((r) => setTimeout(r, 250));
  await flush();

  expect(saveSpy).toHaveBeenCalledOnceWith('https://cdn/saved-1.png');
});

it('saveImageFailure_doesNotBlockResultView', async () => {
  await setup();
  const photoLib = TestBed.inject(PhotoLibraryService);
  spyOn(photoLib, 'saveImage').and.rejectWith(new Error('save failed'));
  apiSpy.generate.and.resolveTo(makeResult('still-shows'));

  page.tapGenerate();
  await flush();
  await new Promise((r) => setTimeout(r, 250));
  await flush();

  expect(page.result).toBeTruthy();
  expect(page.resultImg?.getAttribute('src')).toBe('https://cdn/still-shows.png');
});
```

Note: The `setup()` function in the existing spec must add `PhotoLibraryService` to TestBed providers if it is not auto-provided. Since it is `providedIn: 'root'`, TestBed picks it up automatically; the spy overrides the real method.

---

## 6. Commit Plan

One commit per logical unit. Deviations logged in the commit body with `Deviations:` prefix.

1. `chore(deps): install @capacitor-community/media` -- `package.json`, `package-lock.json`: Step 1
2. `feat(photoshoot): PhotoLibraryService adapter for camera-roll save` -- `src/app/services/photo-library.service.ts`, `src/app/services/photo-library.service.spec.ts`: Steps 2 + 3
3. `feat(acl): ban @capacitor-community/media from page code` -- `scripts/architecture-acl-check.mjs`: Step 4
4. `feat(photoshoot): auto-save generated photo to device library` -- `src/app/pages/photoshoot/photoshoot.page.ts`, `src/app/pages/photoshoot/photoshoot.page.spec.ts`, `ios/App/App/Info.plist`: Steps 5 + 6

---

## 7. Verification

```bash
npm run build                                                           # Production build, must succeed
npm test -- --watch=false --browsers=ChromeHeadless                     # Full FE suite
npm run test:acl                                                        # ACL structural test
```

**Expected delta**: baseline `N` passing to `N + 5` (3 PhotoLibraryService tests + 2 photoshoot page tests). Zero pre-existing tests broken. ACL check: PASS or SKIPPED-WITH-REASON (existing known violations only, no new).

Native verification (actual photo-library save on iOS) is **deferred to Task 6** -- flagging is intentional, not a gap.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible. `git revert <sha>` for any one of the 4 commits.
- **Dependency rollback**: if `@capacitor-community/media` causes build issues, `npm uninstall @capacitor-community/media` and revert commit 1.
- **Per-file emergency**: if Step 5 breaks the photoshoot page, `git checkout HEAD~1 -- src/app/pages/photoshoot/photoshoot.page.ts` to restore prior version while keeping the service and ACL commits.
- **Per-branch**: if the full task verification fails catastrophically, `git reset --hard <pre-task-sha>` (capture this sha in pre-flight as `git rev-parse HEAD`) or delete the feature branch.

---

## 9. Deviations Allowed

- **`@capacitor-community/media` API shape differs from documented `Media.savePhoto({ path })`** -- match the actual installed API. The invariant is: one method, takes a URL, returns a promise. Log the actual method name in the commit body.
- **Plugin requires `Media.getPermissions()` or `Media.requestPermissions()` before save** -- add the permission call inside `saveImage()` before the save call. Same fire-and-forget error handling. Log as deviation.
- **`Media` export name differs (e.g., `MediaPlugin`)** -- import whatever the package exports. The ACL check tests for the package path (`@capacitor-community/media`), not the export name.
- **Existing `photoshoot.page.spec.ts` `setup()` function does not resolve `PhotoLibraryService` from TestBed** -- because the service is `providedIn: 'root'`, it should auto-resolve. If TestBed configuration prevents this, add it to the `providers` array in `setup()`. Log as deviation.
- **`ios/App/App/Info.plist` is XML and the exact insertion point varies** -- add the key inside the existing top-level `<dict>`. If the plist uses a different structure, place it alongside other usage description keys.
- **Side-effect commands required** (push, publish, `npx cap sync`) -- STOP, mark `[REQUIRES APPROVAL]` and ask. `npx cap sync ios` is needed before TestFlight but belongs to Task 6.

---

## 10. Out of Scope

This task adds the Capacitor plugin, wraps it in an adapter, and wires it into the generate flow. It does NOT touch history, migration, model labels, or backend code.

- **Explicit "Save to Photos" button in the UI** -- auto-save-on-generate is the v1 behavior; a manual save button is a separate task if users want selective saving
- **Toast notification "Saved to Photos"** -- deferred; the v1 implementation logs to console; a user-facing toast can come after Task 6 verifies the flow works on device
- **Album creation** (e.g., "Bubls" album in Photos) -- `albumIdentifier: undefined` saves to the default camera roll; a named album is a polish item, not v1
- **Cloud storage (S3/R2) as a fallback for expired URLs** -- explicitly out of epic scope per architecture decision table
- **Read access to photo library** (browsing saved photos) -- we use `NSPhotoLibraryAddUsageDescription` (write-only); read access is not needed
- **Photo-library save for text generations** -- text feature has no image output; if it gains one, the adapter is ready
- **`npx cap sync ios` or Xcode build** -- Task 6 handles the native build and TestFlight QA

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Architecture](./architecture.md) -- design rationale, decision table
- [Epic](./epic.md) -- scope and business context
- [Timeline](./timeline.md) -- status tracking (update Task 4 to done after verification passes)
