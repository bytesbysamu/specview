# Task 3: Rating UI with Tap Circles

## 1. Purpose

Build the ten-question rating screen. Each question displays one at a time in a scrollable list. For each question, render ten tap circles numbered 1-10. Tapping a circle selects it (filled state). Allow changing selection before submission. Show a progress indicator ("3 of 10 rated"). Style: dark background, minimal chrome.

---

## 2. Metadata Block

| Field | Value |
|-------|-------|
| **Effort** | 1 day |
| **Dependencies** | Task 1 (domain models + persistence) |
| **Parallel with** | Task 2 (session creation + partner select) |
| **Blocks** | Task 4 (auto-save), Task 5 (submission) |

---

## 3. Context

### Why this task exists

Task 1 delivered the persistence layer (CheckInService with saveResponse). Task 2 delivered session creation and navigation to the rating route with a sessionId param. This task builds the actual rating interaction: ten questions, each answered via tap circles (1-10). The architecture rejects ion-range in favor of custom tap circles for precise integer control and reliable cross-platform behavior.

### Trade-offs

- **Scrollable list instead of one-at-a-time wizard**: All 10 questions are visible in a scrollable ion-content. This avoids pagination complexity and lets the user see context. The progress indicator tracks how many are answered, not which one is "current".
- **Page service encapsulates TanStack Query calls**: Matches the pattern from Task 2 and the tasks domain. The page component stays declarative with signals.
- **Separate tap-circle-rating component**: Reusable and testable in isolation. Emits the selected value via output. The parent question-card composes it with question text.
- **No submission button on this page**: Task 5 adds submission. This page only allows rating and changing ratings. A "Done" / submit affordance is out of scope.
- **Constructor DI instead of `inject()`**: Mirrors all existing ionstarter patterns.

### Rejected alternatives

- **One question at a time with next/prev buttons**: Adds navigation state complexity. Scroll is simpler and familiar.
- **ion-range slider**: Known to be flaky on iOS + web. Custom tap circles give integer precision without drag issues.
- **Star rating or emoji scale**: Doesn't match the 1-10 granularity required by the quality computation formulas.

---

## 4. Pre-flight

Run from the ionstarter project root (`/projects/ionstarter/`):

```bash
# 1. Verify the project builds cleanly
cd /projects/ionstarter && npm run build

# 2. Verify tests pass
cd /projects/ionstarter && npm run test:ci

# 3. Verify Task 1 outputs exist
ls src/app/domains/check-in/services/check-in/check-in.service.ts
ls src/app/domains/check-in/interfaces/check-in.ts

# 4. Verify the rating route exists (Task 2 created placeholder or route)
ls src/app/domains/check-in/check-in.routes.ts

# 5. Verify TanStack Query is installed
node -e "const p = require('./package.json'); console.log('@ngneat/query:', p.dependencies['@ngneat/query'])"

# 6. Create directory scaffold
mkdir -p src/app/domains/check-in/pages/check-in-rating
mkdir -p src/app/domains/check-in/services/check-in-rating-page
mkdir -p src/app/domains/check-in/components/tap-circle-rating
mkdir -p src/app/domains/check-in/components/question-card
```

---

## 5. Files

### To Create

| # | Path | Purpose |
|---|------|---------|
| 1 | `src/app/domains/check-in/constants/questions.ts` | The 10 check-in questions as a typed constant array |
| 2 | `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.ts` | Reusable: renders 10 circles, emits selected value |
| 3 | `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.html` | Template for the 10 circles row |
| 4 | `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.scss` | Styles: 32px circles, 8px gap, border/filled states |
| 5 | `src/app/domains/check-in/components/question-card/question-card.component.ts` | Displays question text + tap-circle-rating |
| 6 | `src/app/domains/check-in/components/question-card/question-card.component.html` | Template for question card |
| 7 | `src/app/domains/check-in/components/question-card/question-card.component.scss` | Styles for question card |
| 8 | `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts` | Rating container page (replaces Task 2 placeholder) |
| 9 | `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.html` | Template: header with progress, scrollable question list |
| 10 | `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.scss` | Dark background, minimal chrome styles |
| 11 | `src/app/domains/check-in/services/check-in-rating-page/check-in-rating-page.service.ts` | TanStack Query page service: load responses, save response mutation |
| 12 | `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.spec.ts` | Unit tests for tap-circle-rating |
| 13 | `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.spec.ts` | Unit tests for rating page |
| 14 | `src/app/domains/check-in/services/check-in-rating-page/check-in-rating-page.service.spec.ts` | Unit tests for page service |

### To Modify

| # | Path | Change |
|---|------|--------|
| 1 | `src/app/domains/check-in/services/index.ts` | Add barrel export for `check-in-rating-page` service |

### To Leave Alone

- `src/app/domains/check-in/services/check-in/check-in.service.ts` -- Consumed, not modified
- `src/app/domains/check-in/interfaces/` -- Read-only
- `src/app/domains/check-in/check-in.routes.ts` -- Route already exists from Task 2, component import resolves automatically
- `src/app/domains/check-in/pages/check-in-start/` -- Task 2's concern

---

## 6. Implementation Steps

### Step 1: Create the questions constant

**Action**: Define the 10 questions as a typed constant array. Each entry has an index and text.

**File**: `src/app/domains/check-in/constants/questions.ts`

```typescript
export interface CheckInQuestion {
  index: number; // 0-9
  text: string;
}

export const CHECK_IN_QUESTIONS: CheckInQuestion[] = [
  { index: 0, text: 'How directly did I say what I actually thought?' },
  { index: 1, text: "How well did I listen to understand my partner's point?" },
  {
    index: 2,
    text: 'When we disagreed, did it feel like solving something together?',
  },
  { index: 3, text: 'How seriously did I take what my partner said?' },
  { index: 4, text: 'How present was I?' },
  {
    index: 5,
    text: 'How much did my partner feel like my first choice today?',
  },
  { index: 6, text: 'How emotionally open was I?' },
  {
    index: 7,
    text: 'Did I let mistakes stand cleanly without adding "but"?',
  },
  { index: 8, text: 'Do I want this specific person, or just the comfort?' },
  { index: 9, text: 'Would I choose this for the long term?' },
];
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 2: Create the tap-circle-rating component

**Action**: Build the reusable component that renders a row of 10 tap circles. It accepts a `value` input (current selection or null) and emits `valueChange` when a circle is tapped.

**File**: `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-tap-circle-rating',
  templateUrl: './tap-circle-rating.component.html',
  styleUrls: ['./tap-circle-rating.component.scss'],
  imports: [CommonModule],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TapCircleRatingComponent {
  @Input() value: number | null = null;
  @Input() questionIndex = 0;

  @Output() valueChange = new EventEmitter<number>();

  public readonly circles = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  public onTap(score: number): void {
    this.valueChange.emit(score);
  }
}
```

**File**: `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.html`

```html
<div class="tap-circles" [attr.data-test]="'tap-circles-q' + questionIndex">
  @for (score of circles; track score) {
    <button
      class="tap-circle"
      [class.tap-circle--selected]="value === score"
      [attr.data-test]="'circle-q' + questionIndex + '-v' + score"
      [attr.aria-label]="'Score ' + score + ' of 10'"
      [attr.aria-pressed]="value === score"
      type="button"
      (click)="onTap(score)"
    >
      {{ score }}
    </button>
  }
</div>
<div class="tap-circles__labels">
  <span class="tap-circles__label">1</span>
  <span class="tap-circles__label">10</span>
</div>
```

**File**: `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.scss`

```scss
:host {
  display: block;
}

.tap-circles {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 0;
}

.tap-circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  background: transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  -webkit-tap-highlight-color: transparent;
  padding: 0;

  &:active {
    transform: scale(0.9);
  }

  &--selected {
    border-color: var(--ion-color-primary);
    background: var(--ion-color-primary);
    color: var(--ion-color-primary-contrast, #fff);
    font-weight: 700;
  }
}

.tap-circles__labels {
  display: flex;
  justify-content: space-between;
  padding: 0 4px;

  .tap-circles__label {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.35);
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 3: Create the question-card component

**Action**: Build the component that displays a single question's text and embeds a tap-circle-rating. It accepts the question text, question index, current score, and emits score changes.

**File**: `src/app/domains/check-in/components/question-card/question-card.component.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TapCircleRatingComponent } from '../tap-circle-rating/tap-circle-rating.component';

@Component({
  selector: 'app-question-card',
  templateUrl: './question-card.component.html',
  styleUrls: ['./question-card.component.scss'],
  imports: [CommonModule, TapCircleRatingComponent],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QuestionCardComponent {
  @Input({ required: true }) questionText = '';
  @Input({ required: true }) questionIndex = 0;
  @Input() score: number | null = null;

  @Output() scoreChange = new EventEmitter<number>();

  public onScoreChange(value: number): void {
    this.scoreChange.emit(value);
  }
}
```

**File**: `src/app/domains/check-in/components/question-card/question-card.component.html`

```html
<div
  class="question-card"
  [attr.data-test]="'question-card-' + questionIndex"
>
  <p class="question-card__number">{{ questionIndex + 1 }}.</p>
  <p class="question-card__text">{{ questionText }}</p>
  <app-tap-circle-rating
    [value]="score"
    [questionIndex]="questionIndex"
    (valueChange)="onScoreChange($event)"
  ></app-tap-circle-rating>
</div>
```

**File**: `src/app/domains/check-in/components/question-card/question-card.component.scss`

```scss
:host {
  display: block;
}

.question-card {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);

  &__number {
    font-size: 13px;
    font-weight: 600;
    color: var(--ion-color-primary);
    margin: 0 0 4px;
  }

  &__text {
    font-size: 15px;
    font-weight: 400;
    color: rgba(255, 255, 255, 0.9);
    margin: 0 0 16px;
    line-height: 1.4;
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 4: Create the check-in-rating-page service

**Action**: Create the TanStack Query page service. It provides: (1) a query that loads existing responses for a session, (2) a mutation that saves a response (calls `CheckInService.saveResponse`), and (3) a computed signal for the progress count.

**File**: `src/app/domains/check-in/services/check-in-rating-page/check-in-rating-page.service.ts`

```typescript
import { Injectable } from '@angular/core';
import { RouterService } from '@app/core';
import {
  MutationResult,
  QueryObserverResult,
  injectMutation,
  injectQuery,
  injectQueryClient,
} from '@ngneat/query';
import { Result } from '@ngneat/query/lib/types';
import { CheckInResponse } from '../../interfaces';
import { CheckInService } from '../check-in/check-in.service';

@Injectable({
  providedIn: 'root',
})
export class CheckInRatingPageService {
  #client = injectQueryClient();
  #mutation = injectMutation();
  #query = injectQuery();

  constructor(
    private readonly checkInService: CheckInService,
    private readonly routerService: RouterService,
  ) {}

  public getResponses(
    sessionId: string,
  ): Result<QueryObserverResult<CheckInResponse[], Error>> {
    return this.#query({
      queryKey: ['check-in-responses', sessionId],
      queryFn: () => this.checkInService.getResponses(sessionId),
    });
  }

  public saveResponse(): MutationResult<
    CheckInResponse,
    Error,
    { sessionId: string; questionIndex: number; score: number },
    unknown
  > {
    return this.#mutation({
      mutationFn: (params: {
        sessionId: string;
        questionIndex: number;
        score: number;
      }) =>
        this.checkInService.saveResponse(
          params.sessionId,
          params.questionIndex,
          params.score,
        ),
      onSuccess: (_data, variables) => {
        void this.#client.invalidateQueries({
          queryKey: ['check-in-responses', variables.sessionId],
        });
      },
    });
  }

  public async navigateBack(): Promise<void> {
    await this.routerService.navigateToCheckInStartPage({
      animationDirection: 'back',
    });
  }
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 5: Create the check-in-rating page component

**Action**: Build the rating page that loops through all 10 questions, renders question-card components, and shows a progress indicator. Replace the placeholder created by Task 2.

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts`

```typescript
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import {
  IonBackButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import {
  CHECK_IN_QUESTIONS,
  CheckInQuestion,
} from '../../constants/questions';
import { QuestionCardComponent } from '../../components/question-card/question-card.component';
import { CheckInRatingPageService } from '../../services/check-in-rating-page/check-in-rating-page.service';

@Component({
  selector: 'app-check-in-rating',
  templateUrl: './check-in-rating.page.html',
  styleUrls: ['./check-in-rating.page.scss'],
  imports: [
    CommonModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonBackButton,
    IonContent,
    QuestionCardComponent,
  ],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CheckInRatingPage {
  public readonly sessionId: string;
  public readonly questions: CheckInQuestion[] = CHECK_IN_QUESTIONS;

  // Local state: map of questionIndex -> score
  public readonly scores = signal<Map<number, number>>(new Map());

  // Computed progress
  public readonly ratedCount = computed(() => this.scores().size);
  public readonly totalQuestions = CHECK_IN_QUESTIONS.length;

  // TanStack Query
  private readonly responsesResult;
  private readonly saveResponseMutation;

  constructor(
    private readonly activatedRoute: ActivatedRoute,
    private readonly checkInRatingPageService: CheckInRatingPageService,
  ) {
    this.sessionId = this.activatedRoute.snapshot.params['sessionId'];
    this.responsesResult = this.checkInRatingPageService.getResponses(
      this.sessionId,
    ).result;
    this.saveResponseMutation = this.checkInRatingPageService.saveResponse();

    // Pre-fill scores from existing responses when query resolves
    // Use effect-like pattern: check on init
    this.loadExistingResponses();
  }

  public getScore(questionIndex: number): number | null {
    return this.scores().get(questionIndex) ?? null;
  }

  public onScoreChange(questionIndex: number, score: number): void {
    // Update local state immediately (optimistic)
    const updated = new Map(this.scores());
    updated.set(questionIndex, score);
    this.scores.set(updated);

    // Persist via mutation
    this.saveResponseMutation.mutate({
      sessionId: this.sessionId,
      questionIndex,
      score,
    });
  }

  private async loadExistingResponses(): Promise<void> {
    try {
      const responses =
        await this.checkInRatingPageService['checkInService'].getResponses(
          this.sessionId,
        );
      if (responses.length > 0) {
        const map = new Map<number, number>();
        for (const r of responses) {
          map.set(r.questionIndex, r.score);
        }
        this.scores.set(map);
      }
    } catch {
      // Silently fail — user will just see empty circles
    }
  }
}
```

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.html`

```html
<ion-header [translucent]="true">
  <ion-toolbar>
    <ion-buttons slot="start">
      <ion-back-button defaultHref="/check-in"></ion-back-button>
    </ion-buttons>
    <ion-title>Check-In</ion-title>
    <ion-buttons slot="end">
      <span class="progress-label" data-test="progress-label">
        {{ ratedCount() }} of {{ totalQuestions }}
      </span>
    </ion-buttons>
  </ion-toolbar>
</ion-header>

<ion-content [fullscreen]="true">
  <div class="rating-list">
    @for (question of questions; track question.index) {
      <app-question-card
        [questionText]="question.text"
        [questionIndex]="question.index"
        [score]="getScore(question.index)"
        (scoreChange)="onScoreChange(question.index, $event)"
      ></app-question-card>
    }
  </div>
</ion-content>
```

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.scss`

```scss
:host {
  --ion-background-color: #0d0d0d;
  --ion-toolbar-background: #0d0d0d;
  --ion-toolbar-color: #ffffff;
}

ion-toolbar {
  --border-color: rgba(255, 255, 255, 0.08);
}

.progress-label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  padding-inline-end: 16px;
}

.rating-list {
  padding-bottom: env(safe-area-inset-bottom, 16px);
}
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 6: Update the services barrel export

**Action**: Add the rating page service to the check-in services barrel.

**File**: `src/app/domains/check-in/services/index.ts`

**Append**:

```typescript
export * from './check-in-rating-page/check-in-rating-page.service';
```

**Verify**:

```bash
cd /projects/ionstarter && npx tsc --noEmit
```

---

### Step 7: Verify the route resolves correctly

**Action**: Ensure `check-in.routes.ts` already has the `rating/:sessionId` path pointing to `CheckInRatingPage`. Task 2 created this route with a placeholder. Since we now have the real component at the same path, no route change is needed. Verify that the lazy-loaded import path matches:

```typescript
{
  path: 'rating/:sessionId',
  loadComponent: () =>
    import('./pages/check-in-rating/check-in-rating.page').then(
      m => m.CheckInRatingPage,
    ),
},
```

If Task 2's placeholder used a different export name, update the route to match `CheckInRatingPage`.

**Verify**:

```bash
cd /projects/ionstarter && npm run build
```

---

## 7. Tests

### Test 1: `tap-circle-rating.component.spec.ts`

**File**: `src/app/domains/check-in/components/tap-circle-rating/tap-circle-rating.component.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TapCircleRatingComponent } from './tap-circle-rating.component';

describe('TapCircleRatingComponent', () => {
  let component: TapCircleRatingComponent;
  let fixture: ComponentFixture<TapCircleRatingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TapCircleRatingComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(TapCircleRatingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render 10 circle buttons', () => {
    const el = fixture.nativeElement as HTMLElement;
    const circles = el.querySelectorAll('.tap-circle');
    expect(circles.length).toBe(10);
  });

  it('should display numbers 1 through 10', () => {
    const el = fixture.nativeElement as HTMLElement;
    const circles = el.querySelectorAll('.tap-circle');
    circles.forEach((circle, i) => {
      expect(circle.textContent?.trim()).toBe(String(i + 1));
    });
  });

  it('should emit valueChange when a circle is tapped', () => {
    spyOn(component.valueChange, 'emit');

    component.onTap(7);

    expect(component.valueChange.emit).toHaveBeenCalledWith(7);
  });

  it('should mark the selected circle with --selected class', () => {
    component.value = 5;
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const selected = el.querySelector('.tap-circle--selected');
    expect(selected).toBeTruthy();
    expect(selected?.textContent?.trim()).toBe('5');
  });

  it('should not mark any circle as selected when value is null', () => {
    component.value = null;
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const selected = el.querySelectorAll('.tap-circle--selected');
    expect(selected.length).toBe(0);
  });

  it('should have data-test attributes on each circle', () => {
    component.questionIndex = 3;
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const circle5 = el.querySelector('[data-test="circle-q3-v5"]');
    expect(circle5).toBeTruthy();
  });

  it('should update selection when value input changes', () => {
    component.value = 3;
    fixture.detectChanges();

    let el = fixture.nativeElement as HTMLElement;
    let selected = el.querySelector('.tap-circle--selected');
    expect(selected?.textContent?.trim()).toBe('3');

    component.value = 8;
    fixture.detectChanges();

    selected = el.querySelector('.tap-circle--selected');
    expect(selected?.textContent?.trim()).toBe('8');
  });

  it('should set aria-pressed on the selected circle', () => {
    component.value = 6;
    component.questionIndex = 0;
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const circle6 = el.querySelector('[data-test="circle-q0-v6"]');
    expect(circle6?.getAttribute('aria-pressed')).toBe('true');

    const circle5 = el.querySelector('[data-test="circle-q0-v5"]');
    expect(circle5?.getAttribute('aria-pressed')).toBe('false');
  });
});
```

### Test 2: `check-in-rating-page.service.spec.ts`

**File**: `src/app/domains/check-in/services/check-in-rating-page/check-in-rating-page.service.spec.ts`

```typescript
import { TestBed } from '@angular/core/testing';
import { RouterService } from '@app/core';
import { CheckInRatingPageService } from './check-in-rating-page.service';
import { CheckInService } from '../check-in/check-in.service';
import { CheckInResponse } from '../../interfaces';

describe('CheckInRatingPageService', () => {
  let service: CheckInRatingPageService;
  let checkInSpy: jasmine.SpyObj<CheckInService>;
  let routerSpy: jasmine.SpyObj<RouterService>;

  function fakeResponse(
    overrides: Partial<CheckInResponse> = {},
  ): CheckInResponse {
    return {
      id: 'resp-1',
      sessionId: 'sess-1',
      questionIndex: 0,
      score: 5,
      answeredAt: new Date().toISOString(),
      ...overrides,
    };
  }

  beforeEach(() => {
    checkInSpy = jasmine.createSpyObj('CheckInService', [
      'getResponses',
      'saveResponse',
    ]);
    checkInSpy.getResponses.and.resolveTo([]);
    checkInSpy.saveResponse.and.callFake(
      (sessionId: string, questionIndex: number, score: number) =>
        Promise.resolve(fakeResponse({ sessionId, questionIndex, score })),
    );

    routerSpy = jasmine.createSpyObj('RouterService', [
      'navigateToCheckInStartPage',
    ]);
    routerSpy.navigateToCheckInStartPage.and.resolveTo(true);

    TestBed.configureTestingModule({
      providers: [
        CheckInRatingPageService,
        { provide: CheckInService, useValue: checkInSpy },
        { provide: RouterService, useValue: routerSpy },
      ],
    });
    service = TestBed.inject(CheckInRatingPageService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should navigate back to start page', async () => {
    await service.navigateBack();

    expect(routerSpy.navigateToCheckInStartPage).toHaveBeenCalledWith({
      animationDirection: 'back',
    });
  });
});
```

### Test 3: `check-in-rating.page.spec.ts`

**File**: `src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.spec.ts`

```typescript
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { CheckInRatingPage } from './check-in-rating.page';
import { CheckInRatingPageService } from '../../services/check-in-rating-page/check-in-rating-page.service';
import { CheckInService } from '../../services/check-in/check-in.service';

describe('CheckInRatingPage', () => {
  let component: CheckInRatingPage;
  let fixture: ComponentFixture<CheckInRatingPage>;

  beforeEach(async () => {
    const checkInSpy = jasmine.createSpyObj('CheckInService', [
      'getResponses',
      'saveResponse',
    ]);
    checkInSpy.getResponses.and.resolveTo([]);
    checkInSpy.saveResponse.and.resolveTo({
      id: 'r1',
      sessionId: 'sess-1',
      questionIndex: 0,
      score: 5,
      answeredAt: new Date().toISOString(),
    });

    const pageServiceSpy = jasmine.createSpyObj(
      'CheckInRatingPageService',
      ['getResponses', 'saveResponse', 'navigateBack'],
      { checkInService: checkInSpy },
    );
    pageServiceSpy.getResponses.and.returnValue({
      result: jasmine.createSpy().and.returnValue({
        data: [],
        isLoading: false,
      }),
    });
    pageServiceSpy.saveResponse.and.returnValue({
      mutate: jasmine.createSpy(),
      mutateAsync: jasmine.createSpy().and.resolveTo(),
    });

    await TestBed.configureTestingModule({
      imports: [CheckInRatingPage],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { params: { sessionId: 'test-session-1' } } },
        },
        { provide: CheckInRatingPageService, useValue: pageServiceSpy },
        { provide: CheckInService, useValue: checkInSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CheckInRatingPage);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should read sessionId from route params', () => {
    expect(component.sessionId).toBe('test-session-1');
  });

  it('should have 10 questions', () => {
    expect(component.questions.length).toBe(10);
  });

  it('should start with 0 rated', () => {
    expect(component.ratedCount()).toBe(0);
  });

  it('should update ratedCount when a score is set', () => {
    component.onScoreChange(0, 7);
    expect(component.ratedCount()).toBe(1);

    component.onScoreChange(1, 5);
    expect(component.ratedCount()).toBe(2);
  });

  it('should not double-count when same question is re-rated', () => {
    component.onScoreChange(0, 7);
    component.onScoreChange(0, 9);
    expect(component.ratedCount()).toBe(1);
  });

  it('should return the correct score via getScore', () => {
    expect(component.getScore(3)).toBeNull();

    component.onScoreChange(3, 8);
    expect(component.getScore(3)).toBe(8);
  });

  it('should render 10 question cards', () => {
    const el = fixture.nativeElement as HTMLElement;
    const cards = el.querySelectorAll('app-question-card');
    expect(cards.length).toBe(10);
  });

  it('should display progress label', () => {
    const el = fixture.nativeElement as HTMLElement;
    const label = el.querySelector('[data-test="progress-label"]');
    expect(label?.textContent?.trim()).toContain('0 of 10');
  });
});
```

---

## 8. Commit Plan

| # | Message | Files |
|---|---------|-------|
| 1 | `feat(check-in): add check-in questions constant` | `constants/questions.ts` |
| 2 | `feat(check-in): add tap-circle-rating component` | `components/tap-circle-rating/tap-circle-rating.component.ts`, `.html`, `.scss`, `.spec.ts` |
| 3 | `feat(check-in): add question-card component` | `components/question-card/question-card.component.ts`, `.html`, `.scss` |
| 4 | `feat(check-in): add rating page service and page with progress` | `services/check-in-rating-page/check-in-rating-page.service.ts`, `.spec.ts`, `pages/check-in-rating/check-in-rating.page.ts`, `.html`, `.scss`, `.spec.ts`, `services/index.ts` |

---

## 9. Verification

After all steps are complete, run from `/projects/ionstarter/`:

```bash
# 1. TypeScript compilation
npx tsc --noEmit
# Expected: 0 errors

# 2. Full build
npm run build
# Expected: Build succeeds

# 3. Lint
npm run lint
# Expected: 0 errors, 0 warnings

# 4. Unit tests
npm run test:ci
# Expected: All tests pass, including:
#   - TapCircleRatingComponent: 8 specs
#   - CheckInRatingPageService: 2 specs
#   - CheckInRatingPage: 9 specs

# 5. Verify file structure
ls -la src/app/domains/check-in/constants/
# Expected: questions.ts

ls -la src/app/domains/check-in/components/tap-circle-rating/
# Expected: tap-circle-rating.component.ts, .html, .scss, .spec.ts

ls -la src/app/domains/check-in/components/question-card/
# Expected: question-card.component.ts, .html, .scss

ls -la src/app/domains/check-in/pages/check-in-rating/
# Expected: check-in-rating.page.ts, .html, .scss, .spec.ts

ls -la src/app/domains/check-in/services/check-in-rating-page/
# Expected: check-in-rating-page.service.ts, .spec.ts

# 6. Serve and verify UI
ionic serve &
# Navigate to http://localhost:8100/check-in → select partner → rating page
# Expected:
#   - Dark background
#   - 10 questions visible in scrollable list
#   - Each question has 10 tap circles
#   - Tapping a circle fills it with accent color
#   - Progress label shows "X of 10" and updates on each tap
#   - Can change selection by tapping a different circle
```

---

## 10. Rollback

Changes are isolated to new files plus one line added to the services barrel. To revert:

```bash
# Option 1: Git revert all commits (if pushed)
git log --oneline -4  # find the 4 commit SHAs
git revert <sha4> <sha3> <sha2> <sha1>

# Option 2: Hard reset (if not pushed)
git reset --hard HEAD~4

# Option 3: Manual cleanup
rm -rf src/app/domains/check-in/constants/
rm -rf src/app/domains/check-in/components/tap-circle-rating/
rm -rf src/app/domains/check-in/components/question-card/
rm -rf src/app/domains/check-in/pages/check-in-rating/
rm -rf src/app/domains/check-in/services/check-in-rating-page/
# Then revert the barrel export addition
git checkout -- src/app/domains/check-in/services/index.ts
# If Task 2 placeholder existed, restore it:
# git checkout HEAD~4 -- src/app/domains/check-in/pages/check-in-rating/check-in-rating.page.ts
```

---

## 11. Deviations Allowed

| Area | Allowed Deviation |
|------|-------------------|
| **Scrollable vs. one-at-a-time** | Executor may implement a wizard/stepper that shows one question at a time with next/prev buttons instead of a scrollable list. Both achieve the same goal. |
| **Signal-based inputs vs @Input** | Executor may use Angular signal inputs (`input()`, `input.required()`) instead of decorator-based `@Input()`. Both are valid in Angular 17+. |
| **Output vs model()** | Executor may use `model()` for two-way binding instead of separate `@Input()` + `@Output()`. |
| **loadExistingResponses approach** | The guide uses a direct service call in the constructor. Executor may instead use an `effect()` watching the TanStack query result signal to pre-fill scores when the query resolves. Either approach works. |
| **Inline templates** | Executor may use inline `template` strings instead of separate `.html` files for small components like tap-circle-rating. |
| **Progress format** | Executor may show "3/10" instead of "3 of 10", or use progress dots. The key requirement is visual progress feedback. |
| **Circle size** | Executor may use 28px-36px circles if 32px doesn't fit well on small screens. Gap of 6-10px is acceptable. |
| **i18n** | Executor may hardcode English strings instead of transloco keys. Questions are already in English; no i18n needed for this task. |
| **Haptic feedback** | Executor may add `Haptics.impact({ style: ImpactStyle.Light })` on circle tap. Not required but welcome. |
| **Constants file location** | Executor may place the questions array directly in the rating page component file or in the interfaces folder instead of a separate `constants/` directory. |

---

## 12. Out of Scope

- **Session creation / partner selection** -- Task 2
- **Draft auto-save persistence logic** -- Task 4 (this task calls `saveResponse` but the upsert/restore mechanism is Task 4's refinement)
- **Session expiry logic** -- Task 4
- **Submit button / submission flow** -- Task 5
- **Quality computation from scores** -- Task 6
- **Trend visualization** -- Task 7
- **Divergence detection** -- Task 8
- **Animations between questions** -- Nice-to-have, not required
- **Offline queue / retry on save failure** -- Future concern
- **Tab bar integration** -- Separate task
- **Dark mode toggle** -- This page is always dark per spec; no toggle needed
- **i18n JSON translation files** -- Not required; questions are English constants
