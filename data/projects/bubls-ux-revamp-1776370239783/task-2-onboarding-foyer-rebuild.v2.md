# 🛠️ Task 2: Onboarding Foyer Rebuild

**Purpose**: Replace the existing 5-field onboarding form with a three-step foyer (city → interests → email) that matches the revamp's cream-to-amber / navy-to-black radial palette and ships Cormorant-headline typography with 1200ms drift transitions.

**Effort**: 1.5 days

**Dependencies**: Task 1 (Dual-Mode Token Plumbing) — this task consumes `--page-bg`, `--accent-warm`, `--on-accent-warm`, `--text-primary`, `--hairline` and the `data-theme` attribute it installs.

**Parallel With**: Task 3 (Picks), Task 4 (Photoshoot), Task 5 (Text) — all four features are bounded contexts; no cross-feature imports.

**Blocks**: Task 6 (A11y + Screenshot QA) for the onboarding routes.

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## 1. Context

The existing onboarding collects five fields (`name`, `role`, `stack`, `style`, `goals`) in a dense form — none of which feed any downstream feature today. The revamp replaces it with three atomic questions driven by a signal-based step machine, each step mounting one `OnboardingStepComponent` with a Cormorant question, a single answer surface, and a gradient pill CTA. Drift-crossfade transitions make the foyer feel like entering a room rather than filling a form. Backend-side, the dropped fields are removed from the DTO and the underlying persistence (column drop if they're first-class columns, JSONB key removal otherwise — confirmed in pre-flight). This is a scope-narrowing task: the epic's only "kept" fields (`city`, `interests[]`, `email`) are the ones a later feature actually consumes.

**Trade-offs considered**:
- **Router-driven step navigation** (each step as its own route) — rejected because the 1200ms drift+crossfade is trivial on a single-component signal-swap and non-trivial across Ionic route transitions; the animation is the feature, not a side-effect.
- **Keep fields, hide them in an "advanced" section** — rejected because dropped fields are dead weight: the migration is cheaper than the ongoing cost of explaining why those fields exist.
- **Rebuild page + step component with signals + `data-theme`-aware SCSS** — preferred because it matches the architecture's signal/OnPush/standalone discipline and keeps all styling inside the feature's bounded context.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
# 2.1 — confirm branch state
git status
git log --oneline -5

# 2.2 — confirm Task 1 tokens landed (dependency check)
grep -n "data-theme" src/theme/tokens.scss
grep -n "\-\-accent-warm" src/theme/tokens.scss
# Expect both to return hits. If either is empty → Task 1 not merged; STOP and flag.

# 2.3 — confirm target files are clean
git diff HEAD -- src/app/features/onboarding server/modules/user

# 2.4 — locate where the dropped fields live (column vs JSONB inside `builder`/`principles`)
ls server/modules/user/
grep -rn "name\|role\|stack\|style\|goals" server/modules/user/ | grep -v test
grep -rn "'name'\|'role'\|'stack'\|'style'\|'goals'" server/modules/user/dto.py server/modules/user/service.py server/modules/user/repository.py 2>/dev/null
# Record: are these DTO-only fields? JSONB keys inside `builder`/`principles`? Separate columns?
# This determines whether Step 9 is a column-drop migration or a JSONB data migration.

# 2.5 — find existing onboarding model (may or may not exist)
ls src/app/features/onboarding/
find src/app/features/onboarding -name "*.model.ts" -o -name "*.page.*"

# 2.6 — baseline tests
npm test -- --watch=false 2>&1 | tail -20   # record FE pass count, e.g. "42 of 42"
cd server && python -m pytest 2>&1 | tail -5  # record BE pass count, e.g. "67 passed"
cd ..
```

**Baseline recorded**: FE `N_fe`/`N_fe` passing; BE `N_be` passed. (Executor writes actual numbers into the commit body of the first commit.)

**If working tree is dirty on target files**: stash or commit unrelated changes separately BEFORE starting.

**If Task 1 tokens are missing**: STOP. This task is blocked.

---

## 3. Files

### To Create (new)
- `src/app/features/onboarding/components/onboarding-step.component.ts` (new) — reusable step shell: Cormorant question, projected answer surface via `<ng-content>`, gradient pill CTA, emits `next`.
- `src/app/features/onboarding/components/onboarding-step.component.scss` (new) — step layout; consumes Task 1 tokens only.
- `src/app/features/onboarding/components/onboarding-step.component.spec.ts` (new) — Page Object + TestBed tests for the step shell.
- `server/migrations/versions/XXXX_drop_onboarding_fields.py` (new — filename from `alembic revision` output) — drops columns OR removes JSONB keys depending on pre-flight 2.4 finding.

### To Modify (cite CODEBASE CONTEXT)
- `src/app/features/onboarding/onboarding.page.ts` (`src/app/features/onboarding/` in codebase.md) — rebuilt as step machine.
- `src/app/features/onboarding/onboarding.page.html` (sibling of above) — one `<app-onboarding-step>` at a time.
- `src/app/features/onboarding/onboarding.page.scss` (sibling) — dual radial gradient, Cormorant type scale.
- `src/app/features/onboarding/onboarding.model.ts` (sibling; create if pre-flight 2.5 shows it absent) — `OnboardingAnswers = { city: string; interests: string[]; email: string }`.
- `src/app/features/onboarding/onboarding.page.spec.ts` (sibling if present; new if absent) — step-machine behavior.
- `server/modules/user/dto.py` (`server/modules/user/` in codebase.md) — remove `name`, `role`, `stack`, `style`, `goals` from the onboarding-submit DTO.
- `server/modules/user/service.py` (sibling) — stop reading/writing the dropped fields.
- `server/modules/user/repository.py` (sibling) — stop reading/writing the dropped fields.
- `server/tests/test_onboarding_routes.py` (codebase.md) — update fixtures and assertions to the new `{ city, interests, email }` payload.

### To Leave Alone
- `src/app/shared/guards/` (`onboardingGuard`) — gating logic unchanged; guard reads `/api/user/me` which still reports `onboarded` boolean.
- `src/app/services/auth-token.service.ts` — token handling unchanged.
- `src/theme/tokens.scss` — Task 1 owns it; do not edit.
- `server/modules/user/models.py` (User model lives in photoshoot module per codebase.md) — columns stay where they are; migration is the only schema touch.
- `server/modules/chain/` — AI infra; this task doesn't cross the adapter boundary.
- Any other feature under `src/app/features/` — bounded contexts; untouched.

---

## 4. Implementation Steps

### Step 1: Shrink the onboarding model

**Action**: Reduce `OnboardingAnswers` to the three kept fields. If the file doesn't exist, create it; if it does, overwrite.

**File**: `src/app/features/onboarding/onboarding.model.ts`

**Pattern**:
```typescript
export interface OnboardingAnswers {
  city: string;
  interests: string[];  // max length 3 enforced in UI
  email: string;
}

export const MAX_INTERESTS = 3;

export const INTEREST_OPTIONS: readonly string[] = [
  'Art', 'Music', 'Food', 'Theater', 'Sports', 'Tech', 'Books', 'Cinema',
];
```

**Verify**:
```bash
npx tsc --noEmit -p tsconfig.json 2>&1 | grep onboarding
# Expect: no errors mentioning onboarding.model.ts
```

### Step 2: Create the step shell component

**Action**: Build a standalone, OnPush component that renders the question header, projects the answer surface, and owns the gradient-pill CTA.

**File**: `src/app/features/onboarding/components/onboarding-step.component.ts` (new)

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-onboarding-step',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './onboarding-step.component.scss',
  template: `
    <section class="step" [class.step--visible]="true" data-test="onboarding-step">
      <h1 class="step__question" data-test="onboarding-question">{{ question }}</h1>
      <div class="step__surface">
        <ng-content></ng-content>
      </div>
      <button
        type="button"
        class="step__cta"
        data-test="onboarding-next"
        [disabled]="!canAdvance"
        (click)="next.emit()">
        {{ ctaLabel }}
      </button>
    </section>
  `,
})
export class OnboardingStepComponent {
  @Input({ required: true }) question!: string;
  @Input() ctaLabel = 'Continue';
  @Input() canAdvance = false;
  @Output() next = new EventEmitter<void>();
}
```

**Verify**:
```bash
npx tsc --noEmit -p tsconfig.json 2>&1 | grep onboarding-step
# Expect: no errors
```

### Step 3: Style the step shell

**Action**: SCSS consumes Task 1 tokens only; never hard-codes color. Gradient pill uses `--accent-warm` → mix; 1200ms upward-drift + crossfade via `@keyframes`; `@media (prefers-reduced-motion: reduce)` collapses to instant.

**File**: `src/app/features/onboarding/components/onboarding-step.component.scss` (new)

**Pattern**:
```scss
:host {
  display: contents;
}

.step {
  min-height: 100dvh;
  display: grid;
  grid-template-rows: 1fr auto 1fr auto;
  padding: 2rem 1.5rem 2.5rem;
  color: var(--text-primary);
  animation: step-enter 1200ms cubic-bezier(0.2, 0.7, 0.2, 1) both;

  &__question {
    grid-row: 2;
    align-self: end;
    font-family: var(--font-cormorant, 'Cormorant Garamond'), serif;
    font-weight: 500;
    font-size: clamp(2rem, 7vw, 3rem);
    line-height: 1.15;
    text-align: center;
    margin: 0;
  }

  &__surface {
    grid-row: 3;
    align-self: start;
    padding-top: 2rem;
    display: grid;
    place-items: center;
  }

  &__cta {
    grid-row: 4;
    justify-self: center;
    padding: 0.9rem 2.5rem;
    border: none;
    border-radius: 999px;
    font-size: 1rem;
    font-weight: 600;
    color: var(--on-accent-warm);
    background: linear-gradient(135deg, var(--accent-warm), color-mix(in oklab, var(--accent-warm) 70%, black));
    box-shadow: var(--shadow-soft);
    cursor: pointer;
    transition: opacity 200ms ease, transform 200ms ease;

    &:disabled { opacity: 0.4; cursor: not-allowed; }
    &:not(:disabled):active { transform: scale(0.97); }
  }
}

@keyframes step-enter {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .step { animation: none; }
}
```

**Verify**:
```bash
npm run build 2>&1 | grep -iE "error|onboarding-step"
# Expect: no SCSS compile errors
```

### Step 4: Rebuild the onboarding page as a step machine

**Action**: Replace the existing page component with a three-step signal machine. Interests chip list uses a system-native look (Ionic `ion-list` / `ion-item` with inset grouping — the Apple Fitness pattern) and enforces `MAX_INTERESTS`.

**File**: `src/app/features/onboarding/onboarding.page.ts`

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { IonContent, IonList, IonItem, IonLabel, IonCheckbox, IonInput } from '@ionic/angular/standalone';
import { OnboardingStepComponent } from './components/onboarding-step.component';
import { INTEREST_OPTIONS, MAX_INTERESTS, OnboardingAnswers } from './onboarding.model';

@Component({
  selector: 'app-onboarding',
  standalone: true,
  imports: [CommonModule, FormsModule, OnboardingStepComponent, IonContent, IonList, IonItem, IonLabel, IonCheckbox, IonInput],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './onboarding.page.html',
  styleUrl: './onboarding.page.scss',
})
export class OnboardingPage {
  private router = inject(Router);

  readonly currentStep = signal<0 | 1 | 2>(0);
  readonly answers = signal<OnboardingAnswers>({ city: '', interests: [], email: '' });
  readonly interestOptions = INTEREST_OPTIONS;
  readonly maxInterests = MAX_INTERESTS;

  readonly canAdvance = computed(() => {
    const a = this.answers();
    switch (this.currentStep()) {
      case 0: return a.city.trim().length > 0;
      case 1: return a.interests.length > 0 && a.interests.length <= MAX_INTERESTS;
      case 2: return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(a.email.trim());
    }
  });

  setCity(value: string): void {
    this.answers.update((a) => ({ ...a, city: value }));
  }

  toggleInterest(option: string): void {
    this.answers.update((a) => {
      const has = a.interests.includes(option);
      if (has) return { ...a, interests: a.interests.filter((i) => i !== option) };
      if (a.interests.length >= MAX_INTERESTS) return a;
      return { ...a, interests: [...a.interests, option] };
    });
  }

  setEmail(value: string): void {
    this.answers.update((a) => ({ ...a, email: value }));
  }

  advance(): void {
    if (!this.canAdvance()) return;
    const step = this.currentStep();
    if (step < 2) {
      this.currentStep.set((step + 1) as 0 | 1 | 2);
      return;
    }
    this.submit();
  }

  private async submit(): Promise<void> {
    const payload = this.answers();
    const res = await fetch('/api/user/onboarding', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`onboarding submit failed: ${res.status}`);
    await this.router.navigateByUrl('/picks');
  }
}
```

**Verify**:
```bash
npx tsc --noEmit -p tsconfig.json
# Expect: exit 0
```

### Step 5: Rewrite the template

**Action**: Render exactly one step at a time. Interests chips use `ion-list` with `lines="full"` and `ion-checkbox` for the Apple Fitness feel.

**File**: `src/app/features/onboarding/onboarding.page.html`

**Pattern**:
```html
<ion-content class="onboarding" [fullscreen]="true">
  <div class="onboarding__stage">
    @switch (currentStep()) {
      @case (0) {
        <app-onboarding-step
          question="What city are you in?"
          [canAdvance]="canAdvance()"
          ctaLabel="Next"
          (next)="advance()">
          <ion-input
            data-test="onboarding-city-input"
            class="onboarding__input"
            placeholder="e.g. Berlin"
            autocapitalize="words"
            [value]="answers().city"
            (ionInput)="setCity($any($event.target).value)">
          </ion-input>
        </app-onboarding-step>
      }

      @case (1) {
        <app-onboarding-step
          question="What pulls you out?"
          [canAdvance]="canAdvance()"
          ctaLabel="Next"
          (next)="advance()">
          <ion-list inset="true" lines="full" class="onboarding__interests" data-test="onboarding-interests">
            @for (option of interestOptions; track option) {
              <ion-item [attr.data-test]="'onboarding-interest-' + option.toLowerCase()">
                <ion-checkbox
                  slot="start"
                  [checked]="answers().interests.includes(option)"
                  [disabled]="!answers().interests.includes(option) && answers().interests.length >= maxInterests"
                  (ionChange)="toggleInterest(option)">
                </ion-checkbox>
                <ion-label>{{ option }}</ion-label>
              </ion-item>
            }
          </ion-list>
        </app-onboarding-step>
      }

      @case (2) {
        <app-onboarding-step
          question="Where should we reach you?"
          [canAdvance]="canAdvance()"
          ctaLabel="Enter"
          (next)="advance()">
          <ion-input
            data-test="onboarding-email-input"
            class="onboarding__input"
            type="email"
            inputmode="email"
            autocapitalize="off"
            placeholder="you@example.com"
            [value]="answers().email"
            (ionInput)="setEmail($any($event.target).value)">
          </ion-input>
        </app-onboarding-step>
      }
    }
  </div>
</ion-content>
```

**Verify**:
```bash
npm run build 2>&1 | grep -iE "error.*onboarding\.page\.html"
# Expect: no matches
```

### Step 6: Rebuild the page SCSS (dual radial gradient)

**Action**: Paint the foyer. Light: cream → soft amber radial. Dark: deep navy → warm-black radial. Both branch on the root `data-theme` attribute installed by Task 1's `ThemeService`.

**File**: `src/app/features/onboarding/onboarding.page.scss`

**Pattern**:
```scss
:host {
  --onboarding-bg-light: radial-gradient(ellipse at 50% 30%, #FDF8EE 0%, #F1D9A3 100%);
  --onboarding-bg-dark:  radial-gradient(ellipse at 50% 30%, #0F172A 0%, #1A0F0A 100%);
  display: block;
}

ion-content.onboarding {
  --background: var(--onboarding-bg-light);
}

:root[data-theme="dark"] ion-content.onboarding {
  --background: var(--onboarding-bg-dark);
}

.onboarding__stage {
  min-height: 100dvh;
  display: grid;
}

.onboarding__input {
  width: min(28rem, 90vw);
  --background: transparent;
  --color: var(--text-primary);
  --placeholder-color: color-mix(in oklab, var(--text-primary) 50%, transparent);
  font-family: var(--font-cormorant, 'Cormorant Garamond'), serif;
  font-size: 1.75rem;
  text-align: center;
  border-bottom: 1px solid var(--hairline);
}

.onboarding__interests {
  width: min(28rem, 90vw);
  background: transparent;
}
```

**Verify**:
```bash
npm run build 2>&1 | grep -iE "error.*onboarding\.page\.scss"
# Expect: no matches
```

### Step 7: Update the backend DTO

**Action**: Strip the five dropped fields from the onboarding submit request model. Keep the three kept fields; ensure `interests` is a `list[str]` with `max_length=3` validator.

**File**: `server/modules/user/dto.py`

**Pattern** (Pydantic v2, matching the repo's generated/hand-authored DTO style — inspect the file first; if it's generated by `datamodel-codegen`, edit the OpenAPI source at `server/openapi/user.yaml` instead and regenerate via `npm run gen:all`):
```python
class OnboardingSubmit(BaseModel):
    city: str = Field(min_length=1, max_length=80)
    interests: list[str] = Field(min_length=1, max_length=3)
    email: EmailStr
```

**Verify**:
```bash
cd server && python -c "from modules.user.dto import OnboardingSubmit; OnboardingSubmit(city='Berlin', interests=['Art'], email='a@b.co')" && cd ..
# Expect: exit 0, no output
```

### Step 8: Update service + repository to stop reading/writing dropped fields

**Action**: Remove any `name`/`role`/`stack`/`style`/`goals` references in `service.py` and `repository.py`. If a write-site built a dict like `{'name': ..., 'role': ..., ...}`, trim to `{'city', 'interests', 'email'}` — preserving the same JSONB-vs-column discipline the pre-flight 2.4 finding established.

**File**: `server/modules/user/service.py`, `server/modules/user/repository.py`

**Pattern** (illustrative — shape depends on pre-flight 2.4):
```python
# if stored as JSONB keys inside `builder` or `principles`:
profile = {
    'city': payload.city,
    'interests': payload.interests,
    'email': payload.email,
}
user.builder = profile  # or user.principles, whichever the existing code uses
```

**Verify**:
```bash
grep -rn "'name'\|'role'\|'stack'\|'style'\|'goals'" server/modules/user/ | grep -v test | grep -v __pycache__
# Expect: no matches (zero lines)
cd server && python -m pytest modules/user tests/test_user_routes.py tests/test_onboarding_routes.py -x 2>&1 | tail -10 && cd ..
# Expect: tests compile and run (they'll fail until Step 10 updates fixtures — OK to continue)
```

### Step 9: Alembic migration for the drop

**Action**: Generate a revision, then hand-author `upgrade`/`downgrade`. Shape depends on pre-flight 2.4:

- **If the fields are separate columns** on `superapp_users`: `op.drop_column('superapp_users', '<name>')` for each.
- **If the fields are JSONB keys** inside `builder` or `principles` columns: a data migration using `UPDATE superapp_users SET builder = builder - 'name' - 'role' - 'stack' - 'style' - 'goals'` (Postgres JSONB `-` operator). Downgrade is best-effort — record an empty dict if the data is lost.

**File**: `server/migrations/versions/XXXX_drop_onboarding_fields.py` (new — exact filename from `alembic revision` output)

**Pattern** (JSONB-key variant — most likely given codebase.md's "builder + principles JSONB" note):
```python
"""drop onboarding fields

Revision ID: <auto>
Revises: <prev>
Create Date: 2026-04-16
"""
from alembic import op
import sqlalchemy as sa

revision = "<auto>"
down_revision = "<prev>"
branch_labels = None
depends_on = None

DROPPED_KEYS = ("name", "role", "stack", "style", "goals")

def upgrade() -> None:
    conn = op.get_bind()
    # Postgres-only syntax; Alembic tests run on SQLite so guard the dialect.
    if conn.dialect.name == "postgresql":
        stmt = "UPDATE superapp_users SET builder = builder " + " ".join(f"- '{k}'" for k in DROPPED_KEYS)
        conn.execute(sa.text(stmt))

def downgrade() -> None:
    # Dropped keys cannot be restored; no-op.
    pass
```

**Pattern** (column-drop variant — use this if pre-flight 2.4 shows real columns):
```python
def upgrade() -> None:
    for col in ("name", "role", "stack", "style", "goals"):
        op.drop_column("superapp_users", col)

def downgrade() -> None:
    op.add_column("superapp_users", sa.Column("name", sa.String(length=120), nullable=True))
    # ... mirror for each, with original types recorded from the previous revision
```

**Verify**:
```bash
cd server && alembic upgrade head 2>&1 | tail -5 && cd ..
# Expect: "Running upgrade ... -> <new_rev>, drop onboarding fields"
cd server && alembic downgrade -1 && alembic upgrade head && cd ..
# Expect: clean round-trip
```

### Step 10: Update `test_onboarding_routes.py`

**Action**: Replace the five-field fixture payloads with the three-field shape; assert dropped keys are no longer on the user record.

**File**: `server/tests/test_onboarding_routes.py`

**Pattern**:
```python
def test_postOnboarding_newShape_persistsThreeFields(client, authed_user):
    payload = {"city": "Berlin", "interests": ["Art", "Music"], "email": "a@b.co"}
    res = client.post("/api/user/onboarding", json=payload, headers=authed_user.headers)
    assert res.status_code == 200
    me = client.get("/api/user/me", headers=authed_user.headers).get_json()
    builder = me.get("builder") or {}
    assert builder.get("city") == "Berlin"
    assert builder.get("interests") == ["Art", "Music"]
    assert builder.get("email") == "a@b.co"
    for dropped in ("name", "role", "stack", "style", "goals"):
        assert dropped not in builder, f"{dropped} should have been removed"

def test_postOnboarding_rejectsMoreThanThreeInterests(client, authed_user):
    payload = {"city": "Berlin", "interests": ["A", "B", "C", "D"], "email": "a@b.co"}
    res = client.post("/api/user/onboarding", json=payload, headers=authed_user.headers)
    assert res.status_code == 422

def test_postOnboarding_rejectsEmptyCity(client, authed_user):
    payload = {"city": "", "interests": ["Art"], "email": "a@b.co"}
    res = client.post("/api/user/onboarding", json=payload, headers=authed_user.headers)
    assert res.status_code == 422
```

**Verify**:
```bash
cd server && python -m pytest tests/test_onboarding_routes.py -v 2>&1 | tail -15 && cd ..
# Expect: 3 passed (plus any existing unrelated tests in the file)
```

---

## 5. Tests

Frontend uses Karma + Jasmine (per codebase.md). Inspect a sibling `*.spec.ts` to confirm the `TestBed.configureTestingModule` shape, then mirror it. Backend uses pytest (per codebase.md).

### 5.1 `onboarding-step.component.spec.ts` (new)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { OnboardingStepComponent } from './onboarding-step.component';

class StepPO {
  constructor(private fixture: ComponentFixture<OnboardingStepComponent>) {}
  get question() { return this.query('[data-test="onboarding-question"]')?.textContent?.trim(); }
  get cta() { return this.query<HTMLButtonElement>('[data-test="onboarding-next"]'); }
  private query<T extends HTMLElement>(sel: string): T | null {
    return this.fixture.nativeElement.querySelector(sel);
  }
}

describe('OnboardingStepComponent', () => {
  let fixture: ComponentFixture<OnboardingStepComponent>;
  let po: StepPO;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [OnboardingStepComponent] }).compileComponents();
    fixture = TestBed.createComponent(OnboardingStepComponent);
    fixture.componentInstance.question = 'What city?';
    po = new StepPO(fixture);
  });

  it('rendersQuestion_inHeading', () => {
    fixture.detectChanges();
    expect(po.question).toBe('What city?');
  });

  it('canAdvanceFalse_ctaDisabled', () => {
    fixture.componentInstance.canAdvance = false;
    fixture.detectChanges();
    expect(po.cta?.disabled).toBeTrue();
  });

  it('canAdvanceTrue_ctaEnabled', () => {
    fixture.componentInstance.canAdvance = true;
    fixture.detectChanges();
    expect(po.cta?.disabled).toBeFalse();
  });

  it('ctaClicked_emitsNext', () => {
    let emitted = 0;
    fixture.componentInstance.canAdvance = true;
    fixture.componentInstance.next.subscribe(() => emitted++);
    fixture.detectChanges();
    po.cta?.click();
    expect(emitted).toBe(1);
  });
});
```

### 5.2 `onboarding.page.spec.ts` (new or rewrite)

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { OnboardingPage } from './onboarding.page';

class OnboardingPO {
  constructor(private fixture: ComponentFixture<OnboardingPage>) {}
  get cityInput() { return this.query<HTMLInputElement>('[data-test="onboarding-city-input"]'); }
  get emailInput() { return this.query<HTMLInputElement>('[data-test="onboarding-email-input"]'); }
  get nextButton() { return this.query<HTMLButtonElement>('[data-test="onboarding-next"]'); }
  interestItem(opt: string) { return this.query(`[data-test="onboarding-interest-${opt.toLowerCase()}"]`); }
  private query<T extends HTMLElement>(sel: string): T | null {
    return this.fixture.nativeElement.querySelector(sel);
  }
}

describe('OnboardingPage', () => {
  let fixture: ComponentFixture<OnboardingPage>;
  let page: OnboardingPage;
  let po: OnboardingPO;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OnboardingPage],
      providers: [provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(OnboardingPage);
    page = fixture.componentInstance;
    po = new OnboardingPO(fixture);
    fixture.detectChanges();
  });

  it('initialState_isStepZero', () => {
    expect(page.currentStep()).toBe(0);
    expect(po.cityInput).not.toBeNull();
  });

  it('cityEmpty_cannotAdvance', () => {
    expect(page.canAdvance()).toBeFalse();
    expect(po.nextButton?.disabled).toBeTrue();
  });

  it('cityFilled_advancesToInterests', () => {
    page.setCity('Berlin');
    fixture.detectChanges();
    expect(page.canAdvance()).toBeTrue();
    page.advance();
    fixture.detectChanges();
    expect(page.currentStep()).toBe(1);
    expect(po.interestItem('Art')).not.toBeNull();
  });

  it('fourthInterest_isBlocked', () => {
    page.setCity('Berlin'); page.advance();
    page.toggleInterest('Art');
    page.toggleInterest('Music');
    page.toggleInterest('Food');
    page.toggleInterest('Theater');
    expect(page.answers().interests).toEqual(['Art', 'Music', 'Food']);
  });

  it('invalidEmail_cannotAdvance', () => {
    page.setCity('Berlin'); page.advance();
    page.toggleInterest('Art');     page.advance();
    page.setEmail('not-an-email');
    fixture.detectChanges();
    expect(page.canAdvance()).toBeFalse();
  });

  it('validEmailSubmit_callsApiAndNavigates', async () => {
    const router = TestBed.inject(Router);
    const navSpy = spyOn(router, 'navigateByUrl').and.resolveTo(true);
    const fetchSpy = spyOn(window, 'fetch').and.resolveTo(new Response(null, { status: 200 }));

    page.setCity('Berlin'); page.advance();
    page.toggleInterest('Art'); page.advance();
    page.setEmail('a@b.co');
    await page.advance();

    expect(fetchSpy).toHaveBeenCalledWith('/api/user/onboarding', jasmine.objectContaining({ method: 'POST' }));
    const body = JSON.parse((fetchSpy.calls.mostRecent().args[1] as RequestInit).body as string);
    expect(body).toEqual({ city: 'Berlin', interests: ['Art'], email: 'a@b.co' });
    expect(navSpy).toHaveBeenCalledWith('/picks');
  });

  it('toggleOff_removesInterest', () => {
    page.setCity('X'); page.advance();
    page.toggleInterest('Art');
    page.toggleInterest('Art');
    expect(page.answers().interests).toEqual([]);
  });
});
```

### 5.3 Backend tests

See Step 10. Pytest fixtures already wire a test user; reuse them.

---

## 6. Commit Plan

One commit per logical unit; deviations logged in the body.

1. `feat(onboarding): shrink OnboardingAnswers to three fields` — `src/app/features/onboarding/onboarding.model.ts`: define `{ city, interests, email }`, `MAX_INTERESTS`, `INTEREST_OPTIONS`.
2. `feat(onboarding): add step shell component` — `src/app/features/onboarding/components/onboarding-step.component.{ts,scss}` + spec: reusable step with question, surface, CTA.
3. `feat(onboarding): rebuild page as three-step signal machine` — `src/app/features/onboarding/onboarding.page.{ts,html,scss}` + spec: city → interests → email with drift animation.
4. `feat(user): strip dropped fields from onboarding DTO` — `server/modules/user/dto.py`, `service.py`, `repository.py`: remove name/role/stack/style/goals.
5. `feat(migrations): drop onboarding fields` — `server/migrations/versions/XXXX_drop_onboarding_fields.py`: JSONB-key removal (or column drop — see pre-flight 2.4).
6. `test(user): update onboarding route tests to new shape` — `server/tests/test_onboarding_routes.py`: three-field fixtures + dropped-key assertions.

**Deviation logging**: if a step deviates from this guide (e.g., the DTO turns out to be codegen'd — must edit OpenAPI instead), prefix the commit body with `Deviations:` and one line per deviation.

---

## 7. Verification

```bash
# Frontend
npm test -- --watch=false

# Backend
cd server && python -m pytest && cd ..

# TypeScript strict pass
npx tsc --noEmit -p tsconfig.json

# Migration round-trip
cd server && alembic upgrade head && alembic downgrade -1 && alembic upgrade head && cd ..

# Manual smoke (dev server)
npm run start
# Then: visit / as a fresh user → onboarding foyer renders, step 1 cream-amber radial (light) / navy-black (dark),
# submit → POST /api/user/onboarding → navigates to /picks.
```

**Expected delta**:
- Frontend: `N_fe` → `N_fe + 11` passing (7 page tests + 4 step-shell tests). Zero pre-existing tests broken.
- Backend: `N_be` → `N_be + 3` passing (new route tests) minus any pre-existing tests that asserted on dropped fields and were updated in Step 10. Net delta recorded in final commit body.

---

## 8. Rollback

- **Per-step**: each commit is independently revertible via `git revert <sha>`. Revert in reverse order (6 → 1) to keep tests passing between reverts.
- **Migration rollback**: `cd server && alembic downgrade -1` before reverting commit 5, otherwise the schema stays mutated.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (record the sha from pre-flight 2.1). Migration rollback must still be run first.

---

## 9. Deviations Allowed

- **Prescribed path doesn't exist** → check codebase.md; if still missing, flag it in the commit body (`Deviations: <path> not found; used <actual-path> per grep`). Do not invent.
- **DTO is codegen'd from OpenAPI** (Step 7) → edit `server/openapi/user.yaml`, run `npm run gen:all`, let the generator update `dto.py`. Log as deviation.
- **Dropped fields live in DB columns, not JSONB** (pre-flight 2.4) → use the column-drop migration variant in Step 9. Log which variant was chosen in the commit body.
- **Existing `onboarding.model.ts` has unrelated exports** → preserve them; only replace the `OnboardingAnswers` type.
- **Repo uses NgModules rather than standalone** → stop and flag; codebase.md asserts standalone, so this would indicate codebase drift that needs a separate decision.
- **Ionic v8 API differs from the pattern** (e.g., `ion-input` event name) → match the existing photoshoot/picks pages' Ionic usage; the shape in this guide is illustrative.
- **Step N unlocks an obvious simplification for Step N+1** → take it; log the deviation.
- **Side-effect required** (migration on prod DB, git push, publishing) → STOP. Mark [REQUIRES APPROVAL] and ask.

---

## 10. Out of Scope

This task ships the onboarding foyer only: three questions, new visuals, dropped fields removed. It does NOT touch the onboarding guard logic, the `/api/user/me` response shape beyond the dropped keys, the tab shell, or any other feature's SCSS. The foyer is a bounded rebuild — an eager executor will be tempted to "clean up adjacent things"; those are different tasks.

- **ThemeService / `data-theme` plumbing** — owned by Task 1. Assume it exists; don't edit `tokens.scss` or create a theme service here.
- **User toggle for light/dark** — deferred per architecture decision ("no user toggle; follow `prefers-color-scheme`"). Don't add a toggle even if asked.
- **Interest taxonomy curation** — the eight-option `INTEREST_OPTIONS` array in Step 1 is a placeholder seed. Refining the list belongs to a product decision, not this task.
- **Analytics events on step advance** — deferred; no Observer/analytics wiring.
- **Re-onboarding flow / edit profile** — this task only handles the first-time funnel. Editing answers later is a separate feature.
- **Cormorant font loading** — assume Task 1 installs it (font CSS custom property `--font-cormorant` is consumed). If it doesn't, flag as a deviation and fall back to `serif`; do not wire a font-loading pipeline inside onboarding.
- **Contrast audit of the new radials** — Task 6 owns it. Don't add `a11y-contrast-check.mjs` runs here.
- **Email verification / magic-link send** — unchanged. The POST just persists the email like before; the link-send side is owned by existing auth code.
- **Migrating existing production users' JSONB to strip dropped keys** — the migration in Step 9 handles it. No separate backfill script.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) — Design rationale
- [Epic](./epic.md) — Task scope
- [Timeline](./timeline.md) — Status tracking (update after done)