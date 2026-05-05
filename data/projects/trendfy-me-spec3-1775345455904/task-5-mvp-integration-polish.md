# 🛠️ Task 5: MVP Integration + Polish

**Purpose**: Wire all components together into a seamless user journey from trend discovery through wardrobe matching, with proper loading states, error handling, and polish that makes the MVP feel complete.

**Effort**: 1 day

**Dependencies**: Tasks 1-4 (trend display, outfit breakdowns, wardrobe upload, matching algorithm)

**Parallel With**: —

**Blocks**: Launch readiness

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Navigation flow connecting all screens
- Loading states and skeleton screens
- Error boundaries and fallback UI
- Empty states for first-time users
- Basic onboarding hint (non-blocking)
- Mobile-responsive polish pass

### What's NOT Included
- User accounts/authentication — deferred to post-MVP
- Analytics/tracking — add after validating core flow
- Performance optimization — functional first, fast later
- Animations/transitions — ship plain, add polish if users engage

---

## Prerequisites

Before starting:
- Tasks 1-4 complete and individually working
- All components accessible via routes or imports
- Test data available (sample trends, sample wardrobe items)

---

## Implementation Steps

### Step 1: Define Main Navigation Structure

**File**: `src/app/app.routes.ts` (or equivalent router config)

**Purpose**: Establish the core user journey as explicit routes

The navigation follows the natural discovery flow: see trends → explore outfit → check wardrobe → view matches. Each route should load independently (deep-linkable).

**Pattern**:
```typescript
const routes = [
  { path: '', component: TrendFeedComponent },
  { path: 'trend/:id', component: TrendDetailComponent },
  { path: 'outfit/:id', component: OutfitBreakdownComponent },
  { path: 'wardrobe', component: WardrobeComponent },
  { path: 'matches', component: MatchResultsComponent },
];
```

### Step 2: Add Shared Layout with Navigation

**File**: `src/app/components/layout/layout.component.ts`

**Purpose**: Consistent header/footer with quick access to wardrobe

Users need persistent access to their wardrobe from any screen. The header should show wardrobe item count as a visual anchor.

**Pattern**:
```typescript
@Component({
  template: `
    <header class="sticky top-0 z-50 bg-white border-b">
      <nav class="flex justify-between items-center px-4 py-3">
        <a routerLink="/" class="font-bold text-xl">Trendfy</a>
        <a routerLink="/wardrobe" class="flex items-center gap-2">
          <span>My Pieces</span>
          <span class="badge">{{ wardrobeCount }}</span>
        </a>
      </nav>
    </header>
    <main class="min-h-screen">
      <router-outlet />
    </main>
  `
})
```

### Step 3: Implement Loading States

**File**: `src/app/components/skeleton/` (new directory)

**Purpose**: Reduce perceived wait time with content-shaped placeholders

Each major content type needs a skeleton: trend cards, outfit grids, wardrobe items. Skeletons should match the layout of real content to prevent layout shift.

**Pattern**:
```typescript
// trend-card-skeleton.component.ts
@Component({
  template: `
    <div class="animate-pulse">
      <div class="bg-gray-200 aspect-[3/4] rounded-lg"></div>
      <div class="mt-2 h-4 bg-gray-200 rounded w-3/4"></div>
      <div class="mt-1 h-3 bg-gray-200 rounded w-1/2"></div>
    </div>
  `
})
export class TrendCardSkeletonComponent {}
```

Use in parent components:
```html
@if (loading) {
  @for (i of [1,2,3,4,5,6]; track i) {
    <app-trend-card-skeleton />
  }
} @else {
  @for (trend of trends; track trend.id) {
    <app-trend-card [trend]="trend" />
  }
}
```

### Step 4: Add Error Boundaries

**File**: `src/app/components/error-state/error-state.component.ts`

**Purpose**: Graceful failure with actionable recovery

When API calls fail, users need to understand what happened and how to fix it. Provide retry capability inline.

**Pattern**:
```typescript
@Component({
  selector: 'app-error-state',
  template: `
    <div class="text-center py-12">
      <p class="text-gray-600 mb-4">{{ message }}</p>
      <button (click)="retry.emit()" class="btn-secondary">
        Try Again
      </button>
    </div>
  `
})
export class ErrorStateComponent {
  @Input() message = 'Something went wrong';
  @Output() retry = new EventEmitter<void>();
}
```

### Step 5: Create Empty States

**File**: `src/app/components/empty-state/empty-state.component.ts`

**Purpose**: Guide first-time users toward the happy path

Empty wardrobe and no matches are not errors—they're opportunities to guide users. Each empty state should have a clear CTA.

**Pattern**:
```typescript
// Wardrobe empty state
<app-empty-state
  icon="wardrobe"
  title="Your wardrobe is empty"
  description="Upload photos of your clothes to see how they match current trends"
  actionLabel="Upload First Piece"
  (action)="openUpload()"
/>

// No matches empty state
<app-empty-state
  icon="search"
  title="No matches yet"
  description="Add more pieces to your wardrobe to find trend matches"
  actionLabel="Add More Pieces"
  (action)="navigateToWardrobe()"
/>
```

### Step 6: Wire the Complete User Flow

**File**: `src/app/pages/trend-detail/trend-detail.component.ts`

**Purpose**: Connect trend viewing to wardrobe matching

The key integration point: from any trend, users can check matches against their wardrobe. This is where the value proposition becomes tangible.

**Pattern**:
```typescript
// In trend detail or outfit breakdown
checkMyWardrobe(outfitPiece: OutfitPiece) {
  // Pass the piece type to the matching screen
  this.router.navigate(['/matches'], {
    queryParams: {
      category: outfitPiece.category,
      trendId: this.trendId
    }
  });
}
```

### Step 7: Add First-Time User Hint

**File**: `src/app/components/onboarding-hint/onboarding-hint.component.ts`

**Purpose**: One-time tooltip pointing to wardrobe upload

Non-blocking, dismissible hint that appears once. Store dismissal in localStorage.

**Pattern**:
```typescript
@Component({
  template: `
    @if (showHint) {
      <div class="fixed bottom-4 right-4 bg-black text-white p-4 rounded-lg max-w-xs">
        <p class="text-sm">Upload your wardrobe to see which trends match your style</p>
        <button (click)="dismiss()" class="text-xs underline mt-2">Got it</button>
      </div>
    }
  `
})
export class OnboardingHintComponent {
  showHint = !localStorage.getItem('hint-dismissed');
  
  dismiss() {
    localStorage.setItem('hint-dismissed', 'true');
    this.showHint = false;
  }
}
```

### Step 8: Mobile Responsive Polish

**File**: Various component templates

**Purpose**: Ensure usable experience on phone screens

Most fashion content consumption happens on mobile. Grid layouts should collapse appropriately, touch targets should be large enough.

**Pattern**:
```css
/* Trend grid: 2 cols mobile, 3 tablet, 4 desktop */
.trend-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

@media (min-width: 768px) {
  .trend-grid { grid-template-columns: repeat(3, 1fr); }
}

@media (min-width: 1024px) {
  .trend-grid { grid-template-columns: repeat(4, 1fr); }
}

/* Touch-friendly tap targets */
.btn, a { min-height: 44px; }
```

### Step 9: Integration Smoke Test

**File**: Manual testing checklist

**Purpose**: Verify the complete flow works end-to-end

Walk through as a new user would:

1. Land on trend feed → see trends loading then appearing
2. Tap trend → see outfit breakdown
3. Tap "Check My Wardrobe" → see empty state (if new)
4. Upload a piece → see it appear in wardrobe
5. Return to trend → tap "Check My Wardrobe" → see matches
6. Error case: disconnect network → see error states with retry

---

## Verification

How to verify this implementation works:

```bash
# Start dev server
npm run dev

# Open in browser
open http://localhost:4200
```

**Manual Test Script**:
1. Load homepage — should see trend cards (or skeletons, then cards)
2. Click any trend — should navigate to detail with outfit breakdown
3. Click "My Pieces" in header — should see wardrobe (empty state if new)
4. Upload an image — should appear in wardrobe grid
5. Navigate back to a trend, click "Find Matches" — should show results
6. Kill API server, refresh — should see error state with retry button
7. Test on mobile viewport (DevTools) — layout should adapt

**Expected Result**: Complete flow from discovery to matching with no dead ends, crashes, or confusing states.

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 5 complete
2. Run through the flow 3x on different devices/browsers
3. Note any rough edges for post-MVP polish backlog
4. Prepare for launch (Task 6 if exists, or ship)

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for pipeline approach
- [Epic](./epic.md) – Full task list and MVP scope
- [Timeline](./timeline.md) – Status tracking