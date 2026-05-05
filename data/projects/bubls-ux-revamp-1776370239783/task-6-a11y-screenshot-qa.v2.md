# 🛠️ Task 6: A11y + Screenshot QA

**Purpose**: Prove the four-worlds revamp meets WCAG-AA contrast, respects `prefers-reduced-motion`, and produce a contact-sheet PDF as retrospective evidence.

**Effort**: 1 day

**Dependencies**: Tasks 1–5 complete (token plumbing, onboarding, picks, photoshoot, text).

**Parallel With**: —

**Blocks**: Epic close-out.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

This task adds two deterministic guardrails and one evidence artifact. The contrast script parses `src/theme/tokens.scss`, walks every documented `@contrast:` pair, and computes WCAG ratios — failures exit non-zero and block merge. The Playwright screenshot matrix captures every user-reachable route on two iPhone viewports in both color modes with motion on and off, yielding a 30-image grid. The contact-sheet generator composes that grid into a single PDF for the retrospective. None of this touches feature code; it's pure verification on top of what Tasks 1–5 already shipped. The only tokens that should change in this task are contrast fixes — and only by adjusting the hex, not by restructuring the design.

**Trade-offs considered**:
- **Axe-core + full a11y audit** — rejected because scope here is contrast + reduced-motion, not full ARIA/semantics (deferred to a later pass); axe would flag noise we can't triage in a day.
- **Percy / Chromatic for screenshot diffs** — rejected because SaaS adds external dependency and cost for a one-shot retrospective artifact; local Playwright captures suffice.
- **Enumerate pairs in the script** — rejected in favor of parsing `@contrast:` comments from `tokens.scss`; keeps the source of truth in the tokens file and fails closed when a new pair ships without a comment.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                      # flag unrelated M/?? entries
git log --oneline -6                            # confirm tasks 1-5 commits are present
npm test -- --watch=false --browsers=ChromeHeadless   # baseline FE test count
cd server && pytest -q && cd ..                 # baseline BE test count
test -f src/theme/tokens.scss || echo "MISSING tokens.scss — Task 1 not merged"
```

**If working tree is dirty on `src/theme/tokens.scss`, `scripts/`, `e2e/`, `package.json`**: stash or commit unrelated changes first.

**Baseline recorded**: write FE + BE pass counts into the Task 6 PR description.

---

## 3. Files

### To Create (new)
- `scripts/a11y-contrast-check.mjs` — Node script, zero deps; parses tokens.scss, computes WCAG ratio per `@contrast:` pair, exits 1 on failure.
- `e2e/screenshot-matrix.spec.ts` — Playwright spec: routes × modes × viewports × motion; writes PNGs to `e2e/screenshots/`.
- `e2e/contact-sheet.mjs` — Node script that emits `e2e/contact-sheet.html` (grid of all PNGs), then renders it to PDF via Playwright's `page.pdf()`.
- `playwright.config.ts` — Playwright config pinned to `http://localhost:4200` (Ionic dev server), Chromium only.
- `docs/retrospectives/2026-04-16-revamp-contact-sheet.pdf` — output of the contact-sheet script; checked in for the retro.
- `e2e/.gitignore` — ignore `screenshots/` and `contact-sheet.html`.

### To Modify (cite CODEBASE CONTEXT)
- `src/theme/tokens.scss` — add `@contrast:` comment markers next to each pair so the parser can discover them; adjust any failing hex values (amber → `#C8761A` per architecture Risks table) without restructuring.
- `package.json` — add devDeps `@playwright/test`, scripts `test:a11y`, `test:screenshots`, `test:contact-sheet`.

### To Leave Alone
- All feature page components (`src/app/features/{onboarding,picks,photoshoot,text}/`) — Tasks 2–5 already shipped; don't re-touch.
- `src/app/services/theme.service.ts`, `src/app/shell/shell-layout.component.ts` — unchanged; Task 1's surface area is already correct.
- `server/` — no backend changes in this task.

---

## 4. Implementation Steps

### Step 1: Annotate tokens.scss with `@contrast:` markers

**Action**: Walk `tokens.scss` and add a comment above each defined text/bg pair in both `:root` and `:root[data-theme="dark"]`. Comment format is the parser's contract.

**File**: `src/theme/tokens.scss` (per CODEBASE CONTEXT §Task 1)

**Pattern**:
```scss
:root {
  /* @contrast: --text-primary on --page-bg ratio>=4.5 */
  --text-primary: #1a1a1a;
  --page-bg: #FAFAF5;

  /* @contrast: --on-accent-warm on --accent-warm ratio>=4.5 */
  --accent-warm: #C8761A;      /* deepened from amber; see architecture Risks */
  --on-accent-warm: #ffffff;

  /* @contrast: --text-primary on --surface ratio>=4.5 */
  --surface: #ffffff;

  /* @contrast: --hairline on --page-bg ratio>=3.0 large */
  --hairline: #8a8a85;
}

:root[data-theme="dark"] {
  /* @contrast: --text-primary on --page-bg ratio>=4.5 */
  --text-primary: #f2f2f0;
  --page-bg: #0c0c0c;
  /* … repeat for every pair present in light block … */
}
```

Enumeration rule: **every foreground custom property must have at least one `@contrast:` line naming the bg it pairs with, in both modes**. If a token is foreground-only (e.g., `--shadow-soft`), mark it `/* @contrast: skip */`.

**Verify**: `grep -cE '@contrast:' src/theme/tokens.scss` — expect ≥ (count of foreground tokens × 2).

### Step 2: Add the contrast check script

**Action**: Create `scripts/a11y-contrast-check.mjs`. Parse tokens, evaluate every `@contrast:` line, print a table, exit 1 on failure.

**File**: `scripts/a11y-contrast-check.mjs` (new)

**Pattern**:
```javascript
#!/usr/bin/env node
import { readFileSync } from 'node:fs';

const src = readFileSync('src/theme/tokens.scss', 'utf8');

// Split into mode blocks. Light = :root { ... }, Dark = :root[data-theme="dark"] { ... }
function blockFor(header) {
  const i = src.indexOf(header);
  if (i < 0) throw new Error(`missing block: ${header}`);
  const open = src.indexOf('{', i);
  let depth = 0, j = open;
  for (; j < src.length; j++) {
    if (src[j] === '{') depth++;
    else if (src[j] === '}' && --depth === 0) break;
  }
  return src.slice(open + 1, j);
}

const blocks = { light: blockFor(':root {'), dark: blockFor(':root[data-theme="dark"]') };

function parseTokens(block) {
  const map = {};
  for (const [, name, value] of block.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    map[name.trim()] = value.trim();
  }
  return map;
}

function parseContrastLines(block) {
  // @contrast: --fg on --bg ratio>=4.5  OR  ratio>=3.0 large  OR  skip
  const out = [];
  for (const [, body] of block.matchAll(/@contrast:\s*([^*]+?)\*\//g)) {
    const b = body.trim();
    if (b === 'skip') continue;
    const m = b.match(/^(--[\w-]+)\s+on\s+(--[\w-]+)\s+ratio>=([\d.]+)(\s+large)?/);
    if (!m) throw new Error(`malformed @contrast: ${b}`);
    out.push({ fg: m[1], bg: m[2], min: parseFloat(m[3]), large: !!m[4] });
  }
  return out;
}

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  const n = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
  return [0, 2, 4].map(i => parseInt(n.slice(i, i + 2), 16));
}
function luminance([r, g, b]) {
  const ch = [r, g, b].map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2];
}
function ratio(a, b) {
  const [L1, L2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (L1 + 0.05) / (L2 + 0.05);
}

let failed = 0;
for (const mode of ['light', 'dark']) {
  const tokens = parseTokens(blocks[mode]);
  const pairs = parseContrastLines(blocks[mode]);
  for (const { fg, bg, min, large } of pairs) {
    const fgHex = tokens[fg], bgHex = tokens[bg];
    if (!fgHex || !bgHex) { console.error(`[${mode}] MISSING token ${fg} or ${bg}`); failed++; continue; }
    const r = ratio(hexToRgb(fgHex), hexToRgb(bgHex));
    const ok = r >= min;
    const tag = large ? 'large' : 'body';
    const line = `[${mode}] ${fg} on ${bg} (${tag}) = ${r.toFixed(2)} (min ${min})`;
    if (ok) console.log('PASS', line);
    else { console.error('FAIL', line); failed++; }
  }
}
if (failed) { console.error(`\n${failed} contrast failure(s)`); process.exit(1); }
console.log('\nAll contrast pairs pass WCAG-AA.');
```

**Verify**: `node scripts/a11y-contrast-check.mjs` — prints PASS lines for every pair, exits 0. If any fail, adjust the hex in `tokens.scss` (amber → `#C8761A`; deepen dark `--hairline` if needed) and rerun — **do not lower the threshold**.

### Step 3: Install Playwright + add config

**Action**: Add `@playwright/test` as a devDep, install Chromium binary, write `playwright.config.ts`.

**File**: `package.json` (cite CODEBASE CONTEXT §Dependencies) + `playwright.config.ts` (new)

**Pattern**:
```bash
npm install --save-dev @playwright/test
npx playwright install --with-deps chromium
```

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,   // deterministic order for contact sheet
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'off',
  },
  webServer: {
    command: 'npm start',
    url: 'http://localhost:4200',
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
```

Add `package.json` scripts:
```json
"scripts": {
  "test:a11y": "node scripts/a11y-contrast-check.mjs",
  "test:screenshots": "playwright test e2e/screenshot-matrix.spec.ts",
  "test:contact-sheet": "node e2e/contact-sheet.mjs"
}
```

**Verify**: `npx playwright --version` prints a version; `ls node_modules/@playwright/test` exists.

### Step 4: Write the screenshot matrix spec

**Action**: One Playwright spec parametrized across 6 routes × 2 modes × 2 viewports × 2 motion settings, plus behavioral assertions for reduced-motion.

**File**: `e2e/screenshot-matrix.spec.ts` (new)

**Pattern**:
```typescript
import { test, expect, devices } from '@playwright/test';
import { mkdirSync } from 'node:fs';

const ROUTES = [
  { path: '/onboarding', name: 'onboarding' },
  { path: '/home',       name: 'picks-feed' },
  { path: '/pick-detail/mock-1', name: 'pick-detail' },
  { path: '/photoshoot', name: 'photoshoot' },
  { path: '/text',       name: 'text' },
  { path: '/dashboard',  name: 'dashboard' },
];
const VIEWPORTS = [
  { name: 'mini',   device: devices['iPhone 13 Mini'] },
  { name: 'promax', device: devices['iPhone 14 Pro Max'] },
];
const MODES = ['light', 'dark'] as const;
const MOTION = ['full', 'reduce'] as const;

mkdirSync('e2e/screenshots', { recursive: true });

for (const vp of VIEWPORTS) {
  for (const mode of MODES) {
    for (const motion of MOTION) {
      test.describe(`${vp.name}-${mode}-${motion}`, () => {
        test.use({ ...vp.device, colorScheme: mode, reducedMotion: motion });

        for (const route of ROUTES) {
          test(`${route.name}`, async ({ page }) => {
            // Dev-token bypass so the onboarding guard doesn't redirect routes under the shell.
            // bubls.devToken is read by AuthTokenService (per CODEBASE CONTEXT).
            await page.addInitScript(() => localStorage.setItem('bubls.devToken', 'e2e-dev-token'));
            await page.goto(route.path, { waitUntil: 'networkidle' });
            await page.waitForTimeout(250);  // settle
            await page.screenshot({
              path: `e2e/screenshots/${route.name}__${vp.name}__${mode}__${motion}.png`,
              fullPage: false,
            });
          });
        }
      });
    }
  }
}

// Reduced-motion behavioral guards (per epic: onboarding drift, photoshoot scanline, text char-stream)
test.describe('reduced-motion behavioral', () => {
  test.use({ ...devices['iPhone 13 Mini'], reducedMotion: 'reduce', colorScheme: 'light' });

  test('onboarding step entry has no transform drift under reduced-motion', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('bubls.devToken', 'e2e-dev-token'));
    await page.goto('/onboarding');
    const step = page.locator('[data-test="onboarding-step"]').first();
    await expect(step).toBeVisible();
    // Step should be settled at translate(0) immediately — no drift animation.
    const transform = await step.evaluate((el) => getComputedStyle(el).transform);
    expect(['none', 'matrix(1, 0, 0, 1, 0, 0)']).toContain(transform);
  });

  test('text page renders full output immediately under reduced-motion', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('bubls.devToken', 'e2e-dev-token'));
    await page.goto('/text');
    // Trigger a generation via the mock provider (env.useMocks.text).
    await page.locator('[data-test="text-generate"]').click();
    const output = page.locator('[data-test="text-output"]');
    await expect(output).toContainText(/.{50,}/, { timeout: 2000 });
    // Under full-motion this text would appear char-by-char at 18ms/char and fail the 2s deadline.
  });

  test('photoshoot scanline has no running animation under reduced-motion', async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('bubls.devToken', 'e2e-dev-token'));
    await page.goto('/photoshoot');
    const scanline = page.locator('[data-test="scanline-overlay"]');
    if (await scanline.count() === 0) test.skip(true, 'scanline only visible during generation');
    const animationName = await scanline.evaluate((el) => getComputedStyle(el).animationName);
    expect(animationName === 'none' || animationName === '').toBeTruthy();
  });
});
```

**Verify**: `npm start` in another terminal, then `npm run test:screenshots`. Expect 96 PNGs (24 matrix × 4 motion-combos? No — 6 × 2 × 2 × 2 = 48) in `e2e/screenshots/`. Behavioral assertions green.

Enumeration rule for `data-test` requirements above: Tasks 2, 4, 5 must expose `onboarding-step`, `scanline-overlay`, `text-generate`, `text-output`. If any is missing, STOP and flag — don't invent selectors (see §9).

### Step 5: Contact-sheet generator

**Action**: Walk `e2e/screenshots/`, render an HTML grid grouped by viewport/mode, use Playwright to print the grid to PDF.

**File**: `e2e/contact-sheet.mjs` (new)

**Pattern**:
```javascript
#!/usr/bin/env node
import { readdirSync, writeFileSync } from 'node:fs';
import { chromium } from '@playwright/test';
import path from 'node:path';

const files = readdirSync('e2e/screenshots').filter(f => f.endsWith('.png')).sort();

const sections = {};
for (const f of files) {
  const [route, vp, mode, motion] = f.replace('.png', '').split('__');
  const key = `${vp} · ${mode} · ${motion}`;
  (sections[key] ??= []).push({ route, file: f });
}

const html = `<!doctype html><meta charset="utf-8"><title>Revamp contact sheet</title>
<style>
  body { font: 12px/1.4 -apple-system, sans-serif; margin: 24px; color: #111; }
  h1 { font-size: 16px; margin: 0 0 12px; }
  h2 { font-size: 13px; margin: 24px 0 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }
  .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
  figure { margin: 0; }
  img { width: 100%; border: 1px solid #eee; }
  figcaption { margin-top: 4px; color: #555; }
</style>
<h1>Bubls four-worlds revamp — contact sheet (${new Date().toISOString().slice(0,10)})</h1>
${Object.entries(sections).map(([title, items]) => `
  <h2>${title}</h2>
  <div class="grid">
    ${items.map(i => `<figure><img src="screenshots/${i.file}"><figcaption>${i.route}</figcaption></figure>`).join('')}
  </div>`).join('')}
`;

writeFileSync('e2e/contact-sheet.html', html);

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file://' + path.resolve('e2e/contact-sheet.html'));
await page.pdf({
  path: 'docs/retrospectives/2026-04-16-revamp-contact-sheet.pdf',
  format: 'A3',
  printBackground: true,
  margin: { top: '12mm', bottom: '12mm', left: '12mm', right: '12mm' },
});
await browser.close();
console.log('wrote docs/retrospectives/2026-04-16-revamp-contact-sheet.pdf');
```

**Verify**: `mkdir -p docs/retrospectives && npm run test:contact-sheet` — prints success; `ls -lh docs/retrospectives/2026-04-16-revamp-contact-sheet.pdf` shows a non-empty file.

### Step 6: Add `.gitignore` and documentation tie-in

**Action**: Exclude screenshot PNGs and the intermediate HTML from the repo (keep only the PDF). Add a one-line pointer in Timeline marking Task 6 done.

**File**: `e2e/.gitignore` (new), `projects/iteration-0006/timeline.md` (if exists per CODEBASE) — status only.

**Pattern**:
```gitignore
screenshots/
contact-sheet.html
```

**Verify**: `git status -- e2e/screenshots/ | grep -c .` → 0.

---

## 5. Tests

The contrast script and Playwright spec are themselves the tests; they replace unit tests for this task. No Karma/pytest additions.

Self-check the contrast script logic with a scratch assertion (remove after verifying once):

```javascript
// scripts/a11y-contrast-check.mjs — scratch self-check (do NOT commit)
import assert from 'node:assert/strict';
// black on white must be 21:1
assert.equal(ratio(hexToRgb('#000000'), hexToRgb('#ffffff')).toFixed(2), '21.00',
  'contrast math wrong: black/white must be 21:1');
// #777 on #fff must be ~4.48 (known WCAG-AA edge)
const edge = ratio(hexToRgb('#777777'), hexToRgb('#ffffff'));
assert.ok(edge > 4.4 && edge < 4.6, `edge-case ratio drifted: got ${edge}`);
```

Run once with `node -e "..."` or inline, confirm, then delete. The production script has no self-tests; correctness is proved by `test:a11y` returning 0 against real tokens.

Playwright behavioral assertions (already in Step 4):
- `onboarding-step` transform is identity under reduced-motion → drift disabled.
- `text-output` renders ≥50 chars within 2s under reduced-motion → char-stream disabled.
- `scanline-overlay` `animation-name` is `none` under reduced-motion → scanline disabled.

---

## 6. Commit Plan

One commit per logical unit:

1. `chore(a11y): annotate tokens.scss with @contrast markers` — `src/theme/tokens.scss`: add `@contrast:` comments for every fg/bg pair in both modes; deepen `--accent-warm` to `#C8761A`.
2. `feat(a11y): WCAG-AA contrast check script` — `scripts/a11y-contrast-check.mjs`, `package.json` (script + no deps).
3. `chore(e2e): add Playwright + config` — `package.json` (devDep), `playwright.config.ts`, `e2e/.gitignore`.
4. `test(e2e): screenshot matrix + reduced-motion guards` — `e2e/screenshot-matrix.spec.ts`.
5. `chore(e2e): contact-sheet PDF generator` — `e2e/contact-sheet.mjs`, `package.json` script.
6. `docs(retro): add revamp contact-sheet PDF` — `docs/retrospectives/2026-04-16-revamp-contact-sheet.pdf`.

**Deviation logging**: if any step deviates (e.g., a `data-test` selector is missing and must be added in a feature file), prefix the commit body with `Deviations:` and one line per deviation naming the file and the reason.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless    # FE unchanged
cd server && pytest -q && cd ..                         # BE unchanged
npm run test:a11y                                       # exit 0, every pair PASS
npm start &                                             # serve 4200
npm run test:screenshots                                # 48 PNGs + 3 behavioral tests green
npm run test:contact-sheet                             # PDF written
ls -lh docs/retrospectives/2026-04-16-revamp-contact-sheet.pdf
```

**Expected delta**: FE/BE test counts unchanged. New verifications: `test:a11y` → 0, `test:screenshots` → 48 snapshots + 3 assertions passing, `test:contact-sheet` → one PDF on disk. Zero pre-existing tests broken.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible — `git revert <sha>`. Reverting commit 1 (token annotations) without reverting commit 2 will cause `test:a11y` to parse zero pairs and pass vacuously; avoid partial revert of 1+2.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` on the task branch, or `git branch -D <task-6-branch>` after checking out master. Delete `e2e/`, `scripts/a11y-contrast-check.mjs`, `playwright.config.ts`, and `docs/retrospectives/2026-04-16-revamp-contact-sheet.pdf`; remove Playwright from `package.json` devDeps and run `npm install`.

---

## 9. Deviations Allowed

- **A `data-test` selector referenced in Step 4 doesn't exist in the feature code** → STOP. Add the selector to the owning feature (Task 2/4/5) in a separate commit prefixed `fix({feature}): add data-test for e2e matrix`, then proceed. Do NOT query by class/id — that violates the "data-test only" rule in principles.
- **Contrast check fails on a token after Task 1 adjustments** → fix the hex value in `tokens.scss` to meet the threshold. If the design owner has a specific brand color that cannot meet AA, STOP and flag [REQUIRES APPROVAL] rather than lowering the ratio floor.
- **Playwright can't reach `/home` or other shell routes because the onboarding guard redirects** → the `bubls.devToken` localStorage injection in Step 4 is the documented bypass (per `AuthTokenService` in CODEBASE CONTEXT). If the guard now requires a server-side check against `/api/user/me`, intercept that route with `page.route()` and return a fixture — log as deviation.
- **`iPhone 13 Mini` or `iPhone 14 Pro Max` not present in Playwright's devices registry** → pin explicit viewport `{ width: 375, height: 812 }` and `{ width: 430, height: 932 }` with `deviceScaleFactor: 3, isMobile: true, hasTouch: true`; log deviation.
- **Step N unlocks an obvious simplification for N+1** → take it, log in the commit body.

---

## 10. Out of Scope

This task verifies contrast, reduced-motion, and captures visual evidence. It does NOT introduce full accessibility coverage, CI automation for these checks, pixel-diff baselines, or cross-browser matrix. Those are deliberate deferrals; an eager executor should resist bundling them.

- **ARIA / semantic / axe-core audit** — deferred; contrast is the floor this epic signed up for. Revisit when a user or app-store review flags a specific a11y defect.
- **GitHub Actions integration (`test:a11y` + `test:screenshots` in CI)** — deferred to a separate infrastructure task; wiring touches `.github/workflows/` and path-filter config.
- **Pixel-diff regression (baselines committed, `toMatchSnapshot`)** — deferred; Task 6 produces a retrospective artifact, not a diff gate. Revisit if visual regressions start slipping in.
- **Android / Safari / Firefox coverage** — deferred; the app ships iOS first and Chromium approximates WebKit well enough for contrast/layout. Add when the first non-iOS user reports a discrepancy.
- **Animated-GIF or video captures of the reveal/scanline** — deferred; static screenshots plus behavioral assertions cover the retrospective need.
- **`data-test` gap fixes in feature code** — allowed under §9 as a scoped deviation commit, but broader `data-test` audits of Task 2/3/4/5 components are out of scope.

**Rule for the executor**: if any of the above feels tempting mid-task, STOP and flag as a deviation rather than absorbing it. The task ships when the three commands in §7 are green and the PDF is on disk.

---

## Related Documents

- [Solution Architecture](./architecture.md) — design rationale
- [Epic](./epic.md) — task scope
- [Timeline](./timeline.md) — status tracking (update after done)