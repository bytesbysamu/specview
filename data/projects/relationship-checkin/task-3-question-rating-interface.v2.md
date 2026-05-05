# Task 3: Question Rating Interface

**Purpose**: Build the core interaction for Relationship Check-In -- a full-screen swipeable card flow where one partner rates ten questions on a 1-10 scale, reviews a summary, and submits all responses to SQLite via the data service. This is the screen where the measurement happens. Every other screen exists to get the user here or show them what came out of here.

**Effort**: 1.5 days

**Dependencies**: Task 1 (SQLite schema + data service) -- `CheckinDataService` at `src/app/features/checkin/services/checkin-data.service.ts` and the model at `src/app/features/checkin/checkin.model.ts` must be complete.

**Parallel With**: Task 2 (Partner Selection + Session Screen) -- both depend only on Task 1. The rating interface receives `sessionId` and `partner` as route params; it does not import or depend on any Task 2 component.

**Blocks**: Task 4 (Submission Lock + Results) -- requires submitted responses to exist in SQLite. Task 5 (Trends) -- requires historical quality scores. Task 6 (Draft Persistence) -- adds crash-recovery to the rating flow built here.

**Related**:
- [Solution Architecture -- Task 3 Component Design](./architecture.md)
- [Epic -- Task 3 Details](./epic.md)

---

## 1. Context + Trade-offs

The rating interface is three components: a page-level orchestrator (`checkin-rate.component.ts`), a reusable score picker (`score-selector.component.ts`), and a question display card (`question-card.component.ts`). The orchestrator manages a local signal array of ten scores, navigates forward/backward through questions, renders a summary on the final screen, and calls `CheckinDataService.submitScores()` on confirmation.

The architecture specifies this as a full-screen flow -- no tab bar, no shell chrome. It receives `sessionId` and `partner` as route params (set by Task 2's partner selection). It writes to the same three SQLite tables defined in Task 1 (`checkin_session`, `checkin_response`, `checkin_quality_score`) via the existing `CheckinDataService`.

The Bubls codebase uses Angular 19 standalone components with OnPush change detection and signals throughout. Ionic components (`IonContent`, `IonIcon`, etc.) are imported individually from `@ionic/angular/standalone`. The design token system at `src/app/styles/tokens.scss` provides all colors via CSS custom properties (`--text-primary`, `--accent-warm`, `--page-bg`, etc.). The app supports both light and dark modes via `data-theme="dark"` on the root element. No hardcoded colors allowed.

**Trade-offs considered**:

- **Swipe gestures via Hammer.js vs. tap-only navigation** -- rejected swipe. The architecture mentions "swipeable cards" but the Bubls codebase has no Hammer.js dependency and no gesture infrastructure. Adding a gesture library for ten taps is disproportionate. Use tap-based forward/back with CSS transitions between cards. The visual effect is identical; the interaction model is simpler and more accessible. Log as deviation if architecture review flags it.
- **Angular Reactive Forms vs. raw signal bindings** -- rejected forms. Architecture explicitly states "No form module -- raw signal bindings." A `WritableSignal<number[]>` holding ten scores is simpler than wiring FormArray for ten discrete inputs. The score selector emits via output; the orchestrator updates the signal.
- **Inline template vs. separate `.html` file** -- use inline template for `score-selector` and `question-card` (small components, <30 lines of template). Use inline template for `checkin-rate` as well since the Bubls convention is inline templates for page components (see `photoshoot.page.ts`, `shell-layout.component.ts`). If the template exceeds 80 lines, extract to a `.html` file. Log as deviation.
- **Animation library vs. CSS keyframes** -- use CSS `@keyframes` for slide transitions between question cards. Bubls already uses CSS-only animation (`--t-reveal: 400ms`, `--ease-out` easing). No Angular animations module, no external library.
- **Score display: slider vs. discrete tap targets** -- use discrete tap targets (ten circles in a row). Architecture specifies "1-10 slider or tap-to-select row." Discrete targets are more precise on mobile (no thumb-dragging on a narrow slider), more accessible (each target gets `data-test` and `aria-label`), and easier to implement without a range input style override.
- **Haptic feedback on score tap** -- yes. The Bubls shell already uses `Haptics.impact({ style: ImpactStyle.Light })` for tab taps (see `shell-layout.component.ts`). Add the same call to score selection. Guarded by `Capacitor.isNativePlatform()`.

---

## 2. Pre-flight

Run BEFORE editing any file:

```bash
git status                                                       # Flag any unrelated M/?? entries
git diff HEAD -- src/app/features/checkin/
npm test -- --watch=false --browsers=ChromeHeadless              # Baseline FE suite; record pass count
```

**If working tree is dirty on checkin files**: stash or commit unrelated changes BEFORE starting. The `src/app/features/checkin/` directory must be at its Task 1 state.

**Baseline recorded**: write the pass count here after running (format: `N/N passing`). This is the `N` referenced in section 7.

**Verify Task 1 artifacts exist**:
- `src/app/features/checkin/checkin.model.ts` -- exports `CHECKIN_QUESTIONS`, `QUESTION_COUNT`, `QUALITY_DEFINITIONS`, `Partner`, `THRESHOLD_HEALTHY`, `THRESHOLD_CONCERNING`.
- `src/app/features/checkin/services/checkin-data.service.ts` -- exports `CheckinDataService` with `submitScores(sessionId, partner, scores[])`.
- `src/app/features/checkin/index.ts` -- barrel exports for all model types and service.

```bash
grep -n "submitScores\|CHECKIN_QUESTIONS\|QUESTION_COUNT" src/app/features/checkin/services/checkin-data.service.ts src/app/features/checkin/checkin.model.ts
```

---

## 3. Files (Create / Modify / Leave Alone)

### To Create (new)

- `src/app/features/checkin/components/score-selector.component.ts` -- Reusable 1-10 horizontal picker. Ten circular tap targets. Selected value highlighted with `--accent-warm`. Emits `scoreChange` output. `data-test="score-{n}"` on each target. Standalone, OnPush, signals.
- `src/app/features/checkin/components/score-selector.component.scss` -- Styles for the ten-circle row. Uses design tokens only. Responsive via flexbox.
- `src/app/features/checkin/components/score-selector.component.spec.ts` -- Unit tests: renders 10 targets, emits on tap, highlights selected value, data-test attributes present.
- `src/app/features/checkin/components/question-card.component.ts` -- Displays question text with index label ("3 of 10"). Inline template and styles. Standalone, OnPush. `data-test="question-card"`.
- `src/app/features/checkin/components/question-card.component.spec.ts` -- Unit tests: renders question text, renders progress label, data-test attribute.
- `src/app/features/checkin/pages/checkin-rate.component.ts` -- Full-screen rating orchestrator. Manages local `scores` signal array. Navigates questions forward/back. Renders summary on final screen. Calls `CheckinDataService.submitScores()` on submit. Standalone, OnPush.
- `src/app/features/checkin/pages/checkin-rate.component.scss` -- Full-screen layout, slide transitions, summary card styles. Design tokens only.
- `src/app/features/checkin/pages/checkin-rate.component.spec.ts` -- Unit tests: navigation, score persistence across back/forward, submit calls service, summary screen renders all 10 answers.

### To Modify (cite codebase context)

- `src/app/features/checkin/index.ts` -- Add barrel exports for the three new components so downstream tasks (Task 4) can import them if needed. Currently exports `CheckinDataService` and all model types.

### To Leave Alone

- `src/app/features/checkin/checkin.model.ts` -- No changes. Consumed as-is. `CHECKIN_QUESTIONS`, `QUESTION_COUNT`, `Partner` type are sufficient.
- `src/app/features/checkin/services/checkin-data.service.ts` -- No changes. `submitScores()` is the only write method needed.
- `src/app/features/checkin/services/checkin-data.service.spec.ts` -- No changes. Task 1 tests remain untouched.
- `src/app/app.routes.ts` -- Route registration for `/checkin/rate/:sessionId/:partner` belongs to Task 2 (which owns the `/checkin` route tree). If Task 2 is not yet complete, add a temporary route in this task's test harness only, not in the production route config. Log as deviation.
- `src/app/shell/` -- No shell changes. Rating is a full-screen flow within the checkin feature boundary.
- `src/app/shared/sqlite/` -- No changes. Consumed via `CheckinDataService`.

---

## 4. Implementation Steps

### Step 1: Create `score-selector.component.ts` -- the 1-10 picker

**Action**: Build a standalone component that renders ten circular tap targets in a horizontal row. Each circle contains its number (1-10). The currently selected value is highlighted with `--accent-warm` background and `--on-accent-warm` text. Unselected circles use `--surface-elevated` background and `--text-secondary` text. On tap, emit the selected value via an output signal. Add haptic feedback on native platform.

**File**: `src/app/features/checkin/components/score-selector.component.ts` (new)

**Pattern**:
```typescript
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { Capacitor } from '@capacitor/core';
import { Haptics, ImpactStyle } from '@capacitor/haptics';

@Component({
  selector: 'app-score-selector',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styleUrl: './score-selector.component.scss',
  template: `
    <div class="score-row" data-test="score-selector" role="radiogroup" aria-label="Score from 1 to 10">
      @for (n of scores; track n) {
        <button
          type="button"
          class="score-circle"
          [class.selected]="n === value"
          [attr.data-test]="'score-' + n"
          [attr.aria-checked]="n === value"
          [attr.aria-label]="'Score ' + n + ' out of 10'"
          role="radio"
          (click)="select(n)"
        >
          {{ n }}
        </button>
      }
    </div>
  `,
})
export class ScoreSelectorComponent {
  @Input() value: number | null = null;
  @Output() scoreChange = new EventEmitter<number>();

  readonly scores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  async select(n: number): Promise<void> {
    this.scoreChange.emit(n);
    if (Capacitor.isNativePlatform()) {
      try {
        await Haptics.impact({ style: ImpactStyle.Light });
      } catch { /* haptics best-effort */ }
    }
  }
}
```

**SCSS** (`score-selector.component.scss`):
```scss
.score-row {
  display: flex;
  justify-content: center;
  gap: var(--sp-2);
  padding: var(--sp-4) 0;
}

.score-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--hairline);
  background: var(--surface-elevated);
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color var(--t-in) var(--ease-out),
    color var(--t-in) var(--ease-out),
    transform var(--t-press) var(--ease-out);
  -webkit-tap-highlight-color: transparent;

  &:active {
    transform: scale(0.90);
  }

  &.selected {
    background: var(--accent-warm);
    color: var(--on-accent-warm);
    border-color: var(--accent-warm);
  }
}
```

**Verify**: `npx tsc --noEmit` clean. Component renders 10 buttons. No Angular module imports -- standalone only.

### Step 2: Create `question-card.component.ts` -- the question display

**Action**: Build a simple presentation component that displays the question text and a progress label ("3 of 10"). Inline template. No logic beyond rendering inputs.

**File**: `src/app/features/checkin/components/question-card.component.ts` (new)

**Pattern**:
```typescript
import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

@Component({
  selector: 'app-question-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="question-card" data-test="question-card">
      <span class="question-card__progress" data-test="question-progress">
        {{ currentIndex + 1 }} of {{ totalCount }}
      </span>
      <p class="question-card__text" data-test="question-text">
        {{ questionText }}
      </p>
    </div>
  `,
  styles: `
    .question-card {
      text-align: center;
      padding: var(--sp-8) var(--sp-4);
    }

    .question-card__progress {
      display: block;
      font-family: var(--font-body);
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      letter-spacing: 0.5px;
      text-transform: uppercase;
      margin-bottom: var(--sp-6);
    }

    .question-card__text {
      font-family: var(--font-display);
      font-size: 24px;
      line-height: 1.35;
      color: var(--text-primary);
      margin: 0;
    }
  `,
})
export class QuestionCardComponent {
  @Input({ required: true }) questionText!: string;
  @Input({ required: true }) currentIndex!: number;
  @Input({ required: true }) totalCount!: number;
}
```

**Verify**: `npx tsc --noEmit` clean. Zero dependencies beyond Angular core.

### Step 3: Create `checkin-rate.component.ts` -- the rating orchestrator

**Action**: Build the full-screen page component that wires together `QuestionCardComponent` and `ScoreSelectorComponent`. Manages the rating state machine: question navigation, score collection, summary display, and submission.

**File**: `src/app/features/checkin/pages/checkin-rate.component.ts` (new)

**State model**:
```
currentIndex signal (0-9)  ──→  renders CHECKIN_QUESTIONS[currentIndex]
scores signal (number[])   ──→  scores[currentIndex] = selected value
viewMode signal            ──→  'rating' | 'summary'
submitting signal          ──→  disables submit button during write
```

**Pattern**:
```typescript
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { IonContent } from '@ionic/angular/standalone';
import { Capacitor } from '@capacitor/core';
import { Haptics, NotificationType } from '@capacitor/haptics';

import { CheckinDataService } from '../services/checkin-data.service';
import {
  CHECKIN_QUESTIONS,
  QUESTION_COUNT,
  Partner,
} from '../checkin.model';
import { ScoreSelectorComponent } from '../components/score-selector.component';
import { QuestionCardComponent } from '../components/question-card.component';

type ViewMode = 'rating' | 'summary';

@Component({
  selector: 'app-checkin-rate',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IonContent, ScoreSelectorComponent, QuestionCardComponent],
  styleUrl: './checkin-rate.component.scss',
  template: `
    <ion-content [fullscreen]="true" class="rate-content" data-test="checkin-rate">

      @if (viewMode() === 'rating') {
        <!-- Navigation header -->
        <header class="rate-header">
          <button
            type="button"
            class="rate-header__back"
            data-test="rate-back"
            [disabled]="currentIndex() === 0"
            (click)="prev()"
          >
            &#8592;
          </button>
          <div class="rate-header__dots" data-test="rate-dots">
            @for (q of questions; track q.index) {
              <span
                class="dot"
                [class.dot--filled]="scores()[q.index] !== 0"
                [class.dot--active]="q.index === currentIndex()"
              ></span>
            }
          </div>
          <span class="rate-header__spacer"></span>
        </header>

        <!-- Question + score selector -->
        <div class="rate-body" [class.slide-left]="slideDir() === 'left'" [class.slide-right]="slideDir() === 'right'">
          <app-question-card
            [questionText]="currentQuestion().text"
            [currentIndex]="currentIndex()"
            [totalCount]="questionCount"
            data-test="current-question"
          />

          <app-score-selector
            [value]="currentScore()"
            (scoreChange)="onScore($event)"
            data-test="current-score-selector"
          />
        </div>

        <!-- Next / Review button -->
        <footer class="rate-footer">
          <button
            type="button"
            class="rate-footer__cta"
            data-test="rate-next"
            [disabled]="currentScore() === 0"
            (click)="next()"
          >
            {{ isLastQuestion() ? 'Review Answers' : 'Next' }}
          </button>
        </footer>

      } @else {
        <!-- Summary view -->
        <header class="summary-header">
          <button
            type="button"
            class="rate-header__back"
            data-test="summary-back"
            (click)="backToRating()"
          >
            &#8592; Edit
          </button>
          <h2 class="summary-header__title" data-test="summary-title">Review</h2>
          <span class="rate-header__spacer"></span>
        </header>

        <div class="summary-list" data-test="summary-list">
          @for (q of questions; track q.index) {
            <div
              class="summary-row"
              [attr.data-test]="'summary-row-' + q.index"
              (click)="jumpToQuestion(q.index)"
            >
              <span class="summary-row__text">{{ q.text }}</span>
              <span class="summary-row__score">{{ scores()[q.index] }}</span>
            </div>
          }
        </div>

        <footer class="rate-footer">
          <button
            type="button"
            class="rate-footer__cta rate-footer__cta--submit"
            data-test="rate-submit"
            [disabled]="submitting()"
            (click)="submit()"
          >
            {{ submitting() ? 'Submitting...' : 'Submit' }}
          </button>
        </footer>
      }

    </ion-content>
  `,
})
export class CheckinRateComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly checkinData = inject(CheckinDataService);

  readonly questions = CHECKIN_QUESTIONS;
  readonly questionCount = QUESTION_COUNT;

  readonly currentIndex = signal(0);
  readonly scores = signal<number[]>(Array.from({ length: QUESTION_COUNT }, () => 0));
  readonly viewMode = signal<ViewMode>('rating');
  readonly submitting = signal(false);
  readonly slideDir = signal<'left' | 'right' | null>(null);

  private sessionId = '';
  private partner: Partner = 'A';

  readonly currentQuestion = computed(() => CHECKIN_QUESTIONS[this.currentIndex()]);
  readonly currentScore = computed(() => this.scores()[this.currentIndex()]);
  readonly isLastQuestion = computed(() => this.currentIndex() === QUESTION_COUNT - 1);

  ngOnInit(): void {
    this.sessionId = this.route.snapshot.paramMap.get('sessionId') ?? '';
    this.partner = (this.route.snapshot.paramMap.get('partner') as Partner) ?? 'A';
  }

  onScore(value: number): void {
    this.scores.update((prev) => {
      const copy = [...prev];
      copy[this.currentIndex()] = value;
      return copy;
    });
  }

  next(): void {
    if (this.currentScore() === 0) return;

    if (this.isLastQuestion()) {
      this.viewMode.set('summary');
      return;
    }

    this.slideDir.set('left');
    this.currentIndex.update((i) => Math.min(i + 1, QUESTION_COUNT - 1));
    // Reset animation class after transition
    setTimeout(() => this.slideDir.set(null), 300);
  }

  prev(): void {
    if (this.currentIndex() === 0) return;

    this.slideDir.set('right');
    this.currentIndex.update((i) => Math.max(i - 1, 0));
    setTimeout(() => this.slideDir.set(null), 300);
  }

  backToRating(): void {
    this.viewMode.set('rating');
    this.currentIndex.set(QUESTION_COUNT - 1);
  }

  jumpToQuestion(index: number): void {
    this.currentIndex.set(index);
    this.viewMode.set('rating');
  }

  async submit(): Promise<void> {
    if (this.submitting()) return;
    this.submitting.set(true);

    try {
      await this.checkinData.submitScores(
        this.sessionId,
        this.partner,
        this.scores(),
      );

      // Success haptic
      if (Capacitor.isNativePlatform()) {
        try {
          await Haptics.notification({ type: NotificationType.Success });
        } catch { /* haptics best-effort */ }
      }

      // Navigate to waiting/results (Task 4 route; fallback to checkin home)
      await this.router.navigate(['/checkin'], { replaceUrl: true });
    } catch (err) {
      this.submitting.set(false);
      // Error handling: Task 6 will add toast/retry. For now, re-enable the button.
      console.error('[CheckinRate] submit failed:', err);
    }
  }
}
```

**SCSS** (`checkin-rate.component.scss`):
```scss
:host {
  display: block;
  --world-bg: var(--page-bg);
}

.rate-content {
  --background: var(--page-bg);
}

// ── Header ─────────────────────────────────────────────────────────────

.rate-header, .summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-4) var(--sp-4) 0;
  padding-top: calc(var(--sp-4) + env(safe-area-inset-top));
}

.rate-header__back {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-family: var(--font-body);
  font-size: 18px;
  padding: var(--sp-2);
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;

  &:disabled {
    opacity: 0.25;
    cursor: default;
  }
}

.rate-header__dots {
  display: flex;
  gap: 6px;
  align-items: center;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--hairline);
  transition: background-color var(--t-in) var(--ease-out), transform var(--t-press) var(--ease-out);

  &--filled {
    background: var(--accent-warm-tint);
  }

  &--active {
    background: var(--accent-warm);
    transform: scale(1.25);
  }
}

.rate-header__spacer {
  width: 36px; // balance the back button
}

// ── Summary header ─────────────────────────────────────────────────────

.summary-header__title {
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--text-primary);
  margin: 0;
}

// ── Body (question + score) ────────────────────────────────────────────

.rate-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 50vh;
  padding: 0 var(--sp-4);
}

.slide-left {
  animation: slideInLeft var(--t-in) var(--ease-out);
}

.slide-right {
  animation: slideInRight var(--t-in) var(--ease-out);
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(40px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(-40px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .slide-left, .slide-right {
    animation: none;
  }
}

// ── Footer ─────────────────────────────────────────────────────────────

.rate-footer {
  padding: var(--sp-6) var(--sp-4);
  padding-bottom: calc(var(--sp-6) + env(safe-area-inset-bottom));
  text-align: center;
}

.rate-footer__cta {
  display: inline-block;
  padding: var(--sp-3) var(--sp-8);
  border: none;
  border-radius: var(--r-pill);
  background: var(--accent-warm);
  color: var(--on-accent-warm);
  font-family: var(--font-body);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition:
    opacity var(--t-in) var(--ease-out),
    transform var(--t-press) var(--ease-out);
  -webkit-tap-highlight-color: transparent;

  &:active {
    transform: scale(0.96);
  }

  &:disabled {
    opacity: 0.4;
    cursor: default;
  }

  &--submit {
    background: var(--success);
    color: #fff;
  }
}

// ── Summary list ───────────────────────────────────────────────────────

.summary-list {
  padding: var(--sp-4);
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--sp-3) var(--sp-4);
  background: var(--surface);
  border-radius: var(--r-sm);
  cursor: pointer;
  transition: background-color var(--t-in) var(--ease-out);
  -webkit-tap-highlight-color: transparent;

  &:active {
    background: var(--surface-elevated);
  }
}

.summary-row__text {
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--text-primary);
  flex: 1;
  margin-right: var(--sp-3);
}

.summary-row__score {
  font-family: var(--font-body);
  font-size: 18px;
  font-weight: 700;
  color: var(--accent-warm);
  min-width: 28px;
  text-align: center;
}
```

**Key behaviors**:
- `currentIndex` signal controls which question is displayed. Back/forward buttons mutate this signal.
- `scores` signal is an array of 10 numbers (initialized to 0). A score of 0 means unanswered. The "Next" button is disabled until the current question has a non-zero score.
- Progress dots in the header show filled/unfilled/active state based on the scores array and currentIndex.
- "Review Answers" replaces "Next" on question 10. Tapping it switches `viewMode` to `'summary'`.
- Summary view lists all 10 questions with their scores. Tapping a row jumps back to that question for editing.
- Submit button disables immediately via `submitting` signal to prevent double-tap. Service call is awaited. On success, navigate away. On failure, re-enable the button and log.
- Post-submit navigation goes to `/checkin` (the home screen, owned by Task 2). If Task 2 is incomplete, this will fall through to the wildcard route. Acceptable for isolated testing.

**Verify**: `npx tsc --noEmit` clean. Component file size under 200 lines (excluding SCSS).

### Step 4: Update barrel exports

**Action**: Add the three new components to the checkin feature barrel file so downstream tasks can import them.

**File**: `src/app/features/checkin/index.ts` (modify)

**Pattern** -- append to existing exports:
```typescript
export { ScoreSelectorComponent } from './components/score-selector.component';
export { QuestionCardComponent } from './components/question-card.component';
export { CheckinRateComponent } from './pages/checkin-rate.component';
```

**Verify**: `npx tsc --noEmit` clean. No circular imports.

### Step 5: Write unit tests

**Action**: Create spec files for all three components. See section 5 for full test bodies.

**Files**:
- `src/app/features/checkin/components/score-selector.component.spec.ts` (new)
- `src/app/features/checkin/components/question-card.component.spec.ts` (new)
- `src/app/features/checkin/pages/checkin-rate.component.spec.ts` (new)

**Verify**: `npm test -- --watch=false --browsers=ChromeHeadless` -- all new tests green, no pre-existing tests regressed.

---

## 5. Tests

Framework: Jasmine + Karma (repo convention). Component tests use `TestBed` with standalone component imports. Mock `CheckinDataService` with jasmine spyObj. Mock `ActivatedRoute` with snapshot params.

### `src/app/features/checkin/components/score-selector.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ScoreSelectorComponent } from './score-selector.component';

describe('ScoreSelectorComponent', () => {
  let fixture: ComponentFixture<ScoreSelectorComponent>;
  let component: ScoreSelectorComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ScoreSelectorComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ScoreSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('renders_10_scoreTargets', () => {
    const buttons = fixture.nativeElement.querySelectorAll('.score-circle');
    expect(buttons.length).toBe(10);
  });

  it('each_target_has_dataTest_attribute', () => {
    for (let i = 1; i <= 10; i++) {
      const el = fixture.nativeElement.querySelector(`[data-test="score-${i}"]`);
      expect(el).toBeTruthy(`Missing data-test for score ${i}`);
    }
  });

  it('tap_emits_scoreChange', () => {
    const spy = spyOn(component.scoreChange, 'emit');
    const btn = fixture.nativeElement.querySelector('[data-test="score-7"]');
    btn.click();
    expect(spy).toHaveBeenCalledWith(7);
  });

  it('selected_value_gets_selected_class', () => {
    component.value = 5;
    fixture.detectChanges();
    const btn = fixture.nativeElement.querySelector('[data-test="score-5"]');
    expect(btn.classList).toContain('selected');
  });

  it('unselected_values_lack_selected_class', () => {
    component.value = 5;
    fixture.detectChanges();
    const btn = fixture.nativeElement.querySelector('[data-test="score-3"]');
    expect(btn.classList).not.toContain('selected');
  });

  it('null_value_no_circle_selected', () => {
    component.value = null;
    fixture.detectChanges();
    const selected = fixture.nativeElement.querySelectorAll('.score-circle.selected');
    expect(selected.length).toBe(0);
  });

  it('radiogroup_role_present', () => {
    const group = fixture.nativeElement.querySelector('[role="radiogroup"]');
    expect(group).toBeTruthy();
  });
});
```

### `src/app/features/checkin/components/question-card.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { QuestionCardComponent } from './question-card.component';

describe('QuestionCardComponent', () => {
  let fixture: ComponentFixture<QuestionCardComponent>;
  let component: QuestionCardComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [QuestionCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(QuestionCardComponent);
    component = fixture.componentInstance;
  });

  it('renders_question_text', () => {
    component.questionText = 'How honest was our communication today?';
    component.currentIndex = 0;
    component.totalCount = 10;
    fixture.detectChanges();

    const text = fixture.nativeElement.querySelector('[data-test="question-text"]');
    expect(text.textContent).toContain('How honest was our communication today?');
  });

  it('renders_progress_label', () => {
    component.questionText = 'Test question';
    component.currentIndex = 4;
    component.totalCount = 10;
    fixture.detectChanges();

    const progress = fixture.nativeElement.querySelector('[data-test="question-progress"]');
    expect(progress.textContent.trim()).toBe('5 of 10');
  });

  it('has_data_test_attribute', () => {
    component.questionText = 'Test';
    component.currentIndex = 0;
    component.totalCount = 10;
    fixture.detectChanges();

    const card = fixture.nativeElement.querySelector('[data-test="question-card"]');
    expect(card).toBeTruthy();
  });
});
```

### `src/app/features/checkin/pages/checkin-rate.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';

import { CheckinRateComponent } from './checkin-rate.component';
import { CheckinDataService } from '../services/checkin-data.service';
import { CHECKIN_QUESTIONS, QUESTION_COUNT } from '../checkin.model';
import { ScoreSelectorComponent } from '../components/score-selector.component';
import { QuestionCardComponent } from '../components/question-card.component';

describe('CheckinRateComponent', () => {
  let fixture: ComponentFixture<CheckinRateComponent>;
  let component: CheckinRateComponent;
  let checkinSpy: jasmine.SpyObj<CheckinDataService>;
  let routerSpy: jasmine.SpyObj<Router>;

  beforeEach(async () => {
    checkinSpy = jasmine.createSpyObj('CheckinDataService', [
      'submitScores',
      'init',
    ]);
    checkinSpy.submitScores.and.resolveTo();

    routerSpy = jasmine.createSpyObj('Router', ['navigate']);
    routerSpy.navigate.and.resolveTo(true);

    await TestBed.configureTestingModule({
      imports: [
        CheckinRateComponent,
        ScoreSelectorComponent,
        QuestionCardComponent,
      ],
      providers: [
        { provide: CheckinDataService, useValue: checkinSpy },
        { provide: Router, useValue: routerSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              paramMap: {
                get: (key: string) => {
                  if (key === 'sessionId') return 'test-session';
                  if (key === 'partner') return 'A';
                  return null;
                },
              },
            },
          },
        },
      ],
      schemas: [CUSTOM_ELEMENTS_SCHEMA], // Allow ion-content
    }).compileComponents();

    fixture = TestBed.createComponent(CheckinRateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  // ── Initial state ────────────────────────────────────────────────────

  it('starts_at_question_0', () => {
    expect(component.currentIndex()).toBe(0);
  });

  it('starts_in_rating_viewMode', () => {
    expect(component.viewMode()).toBe('rating');
  });

  it('all_scores_initialized_to_0', () => {
    const scores = component.scores();
    expect(scores.length).toBe(QUESTION_COUNT);
    expect(scores.every((s) => s === 0)).toBeTrue();
  });

  // ── Score selection ──────────────────────────────────────────────────

  it('onScore_updates_scores_at_currentIndex', () => {
    component.onScore(7);
    expect(component.scores()[0]).toBe(7);
  });

  it('onScore_preserves_other_scores', () => {
    component.onScore(5); // Q0 = 5
    component.currentIndex.set(1);
    component.onScore(8); // Q1 = 8
    expect(component.scores()[0]).toBe(5);
    expect(component.scores()[1]).toBe(8);
  });

  // ── Navigation ───────────────────────────────────────────────────────

  it('next_advances_currentIndex_when_score_set', () => {
    component.onScore(5);
    component.next();
    expect(component.currentIndex()).toBe(1);
  });

  it('next_does_nothing_when_score_is_0', () => {
    component.next();
    expect(component.currentIndex()).toBe(0);
  });

  it('prev_decrements_currentIndex', () => {
    component.onScore(5);
    component.next();
    component.prev();
    expect(component.currentIndex()).toBe(0);
  });

  it('prev_at_0_stays_at_0', () => {
    component.prev();
    expect(component.currentIndex()).toBe(0);
  });

  it('back_preserves_scores', () => {
    component.onScore(7); // Q0 = 7
    component.next();
    component.onScore(4); // Q1 = 4
    component.prev();     // back to Q0
    expect(component.scores()[0]).toBe(7);
    expect(component.scores()[1]).toBe(4);
  });

  // ── Summary transition ───────────────────────────────────────────────

  it('next_on_lastQuestion_switches_to_summary', () => {
    // Fill all 10 scores
    for (let i = 0; i < QUESTION_COUNT; i++) {
      component.onScore(5 + (i % 5));
      if (i < QUESTION_COUNT - 1) component.next();
    }
    component.next(); // on the last question, should switch to summary
    expect(component.viewMode()).toBe('summary');
  });

  it('backToRating_returns_to_lastQuestion', () => {
    for (let i = 0; i < QUESTION_COUNT; i++) {
      component.onScore(7);
      if (i < QUESTION_COUNT - 1) component.next();
    }
    component.next(); // switch to summary
    component.backToRating();
    expect(component.viewMode()).toBe('rating');
    expect(component.currentIndex()).toBe(QUESTION_COUNT - 1);
  });

  it('jumpToQuestion_sets_index_and_returns_to_rating', () => {
    component.viewMode.set('summary');
    component.jumpToQuestion(3);
    expect(component.currentIndex()).toBe(3);
    expect(component.viewMode()).toBe('rating');
  });

  // ── Submission ───────────────────────────────────────────────────────

  it('submit_calls_service_with_correct_args', async () => {
    const scores = [8, 7, 9, 8, 7, 6, 7, 8, 9, 8];
    component.scores.set(scores);

    await component.submit();

    expect(checkinSpy.submitScores).toHaveBeenCalledOnceWith(
      'test-session',
      'A',
      scores,
    );
  });

  it('submit_sets_submitting_true_during_call', () => {
    // Make submitScores hang (never resolve)
    checkinSpy.submitScores.and.returnValue(new Promise(() => {}));

    component.submit(); // fire-and-forget

    expect(component.submitting()).toBeTrue();
  });

  it('submit_navigates_to_checkin_on_success', async () => {
    component.scores.set([8, 7, 9, 8, 7, 6, 7, 8, 9, 8]);
    await component.submit();

    expect(routerSpy.navigate).toHaveBeenCalledWith(
      ['/checkin'],
      jasmine.objectContaining({ replaceUrl: true }),
    );
  });

  it('submit_reEnables_on_failure', async () => {
    checkinSpy.submitScores.and.rejectWith(new Error('DB error'));

    await component.submit();

    expect(component.submitting()).toBeFalse();
  });

  it('submit_prevents_doubleSubmit', async () => {
    checkinSpy.submitScores.and.returnValue(new Promise(() => {}));

    component.submit(); // first call, hangs
    component.submit(); // second call, should bail

    expect(checkinSpy.submitScores).toHaveBeenCalledTimes(1);
  });

  // ── Computed signals ─────────────────────────────────────────────────

  it('currentQuestion_reflects_currentIndex', () => {
    component.currentIndex.set(3);
    expect(component.currentQuestion().text).toBe(CHECKIN_QUESTIONS[3].text);
  });

  it('isLastQuestion_true_at_index_9', () => {
    component.currentIndex.set(QUESTION_COUNT - 1);
    expect(component.isLastQuestion()).toBeTrue();
  });

  it('isLastQuestion_false_at_index_0', () => {
    component.currentIndex.set(0);
    expect(component.isLastQuestion()).toBeFalse();
  });
});
```

---

## 6. Commit Plan

One commit per logical unit:

1. `feat(checkin): add ScoreSelectorComponent — 1-10 horizontal picker` -- `src/app/features/checkin/components/score-selector.component.ts`, `score-selector.component.scss`: standalone component with haptic feedback, ARIA roles, data-test attributes.
2. `feat(checkin): add QuestionCardComponent — question text + progress display` -- `src/app/features/checkin/components/question-card.component.ts`: inline template/styles, pure presentation.
3. `feat(checkin): add CheckinRateComponent — full-screen rating orchestrator` -- `src/app/features/checkin/pages/checkin-rate.component.ts`, `checkin-rate.component.scss`: ten-question flow with summary review and submit.
4. `chore(checkin): export rating components from feature barrel` -- `src/app/features/checkin/index.ts`: add exports for ScoreSelectorComponent, QuestionCardComponent, CheckinRateComponent.
5. `test(checkin): unit tests for rating interface components` -- `score-selector.component.spec.ts`, `question-card.component.spec.ts`, `checkin-rate.component.spec.ts`: navigation, score state, submission, double-submit guard.

**Deviation logging**: if a step deviates from this guide, prefix the commit body with `Deviations:` and one line per deviation. Keep the total to 3 or fewer per commit.

---

## 7. Verification

```bash
npm test -- --watch=false --browsers=ChromeHeadless
npm run build
```

**Expected delta**: `N` (baseline from section 2) to `N + 24` passing (7 score-selector specs + 3 question-card specs + 14 checkin-rate specs). Zero pre-existing tests broken. `npm run build` clean with no new warnings.

**Manual check** (if Task 2 route exists): navigate to `/checkin`, start a session, select Partner A, and complete the ten-question rating flow. Confirm:
1. Each question renders with correct text and progress indicator.
2. Score selector highlights the tapped value and enables the "Next" button.
3. Back button preserves previously entered scores.
4. Question 10 shows "Review Answers" instead of "Next".
5. Summary view lists all 10 questions with entered scores.
6. Tapping a summary row jumps back to that question.
7. Submit button disables during the write and navigates away on success.

**If Task 2 route does NOT exist**: test via Jasmine specs only. The component can be instantiated in isolation with mocked ActivatedRoute and Router. All behavioral assertions are covered by the spec file.

**Type check**: `npx tsc --noEmit` must pass with zero errors.

---

## 8. Rollback

- **Per-step**: each of the 5 commits is independently revertible. `git revert <sha>` on any single commit restores the prior state. The barrel export commit (4) depends on commits 1-3 existing.
- **Per-branch**: if verification fails catastrophically, `git reset --hard <pre-task-sha>` (record the SHA during section 2 Pre-flight) or delete the feature branch.
- **Component isolation**: none of the three new components modify any existing file except `index.ts` (barrel). Reverting does not affect Task 1 artifacts or any other Bubls feature.

---

## 9. Deviations Allowed

- **Swipe gestures not implemented** -- architecture mentions "swipeable cards." This plan uses tap-based forward/back navigation with CSS slide transitions. Swipe can be added later without changing the component API. Log as deviation.
- **Route not registered** -- if Task 2 has not registered the `/checkin` route tree in `app.routes.ts`, the rating component cannot be navigated to in the running app. Tests still pass via TestBed. Do NOT modify `app.routes.ts` in this task. Log as deviation and note that integration requires Task 2.
- **Template extracted to HTML file** -- if the `checkin-rate.component.ts` inline template exceeds 80 lines during implementation, extract to `checkin-rate.component.html`. Update the `@Component` decorator to use `templateUrl` instead of `template`. Log as deviation.
- **Haptics import fails** -- if `@capacitor/haptics` is not installed or causes a build error, remove the haptic feedback calls entirely. The score selector and submit flow work without haptics. Log as deviation.
- **IonContent import issue** -- if `@ionic/angular/standalone` does not export `IonContent` in the installed version, replace with a plain `<div class="rate-content">` wrapper. Log as deviation.
- **CHECKIN_QUESTIONS shape mismatch** -- if the actual model file's `CheckinQuestion` interface differs from what section 4 references (e.g., different property names), adapt the template bindings to match the real interface. The model file at `src/app/features/checkin/checkin.model.ts` is the source of truth, not this plan. Log as deviation.
- **Side-effect required** (push, publish, install new dependency) -- STOP, mark `[REQUIRES APPROVAL]`, ask.

---

## 10. Out of Scope

This task builds the question rating interface and its two child components -- nothing more. It does NOT register routes, modify the shell, build the partner selection flow, or implement post-submit views.

- **Route registration** -- `app.routes.ts` modification belongs to Task 2. No `/checkin/rate/:sessionId/:partner` route added here.
- **Partner selection screen** (`checkin.page.ts`, `partner-select.component.ts`) -- Task 2. This component receives partner identity as a route param; it does not ask the user to select.
- **Waiting screen** (`checkin-waiting.component.ts`) -- Task 4. Post-submit navigation currently goes to `/checkin` generically.
- **Results comparison view** (`checkin-results.component.ts`) -- Task 4. The submit handler navigates away; it does not render results.
- **Trend lines** (`checkin-trends.component.ts`, `sparkline.component.ts`) -- Task 5.
- **Draft persistence** (`checkin_draft` table for crash recovery) -- Task 6. If the app is killed mid-rating, all in-progress scores are lost. Draft persistence is Task 6's responsibility.
- **Submit idempotency guard** (preventing a partner from submitting twice for the same session) -- Task 6. The service allows duplicate writes in v1.
- **Error toast / retry UI** -- Task 6. Current error handling is `console.error` + re-enable submit button.
- **Shell tab bar entry** -- Task 2 or a dedicated shell modification task.
- **Any backend / server changes** -- this feature is local-only, no server code.
- **Custom animations or gesture libraries** -- CSS keyframes only. No Hammer.js, no Angular animations module.

**Rule for the executor**: if a change appears helpful but is listed here, STOP and flag it as a deviation rather than expanding this task's blast radius.

---

## Related Documents

- [Solution Architecture](./architecture.md) -- Task 3 component design, state flow diagram, design principles
- [Epic](./epic.md) -- Task scope, dependencies, success criteria
- [Analysis](./analysis.md) -- Problem statement and open questions
- [Timeline](./timeline.md) -- Status tracking (update after done)
