# 🛠️ Task 5: Outfit Saving and Recall

**Purpose**: Enable users to save generated try-on results as named outfits and build a personal library of looks they can revisit, regenerate, or modify.

**Effort**: 1 day

**Dependencies**: Task 4 (Virtual Try-On Integration) must be complete — we need try-on results to save.

**Parallel With**: —

**Blocks**: Future features like outfit sharing, calendar integration, or "what to wear today" suggestions.

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Data model for saved outfits (name, photo, garment references, metadata)
- Save action on try-on result screen
- Gallery view of saved outfits
- Recall functionality (view, regenerate, modify)
- Basic naming and deletion

### What's NOT Included
- Outfit categories or folders — keep first version flat
- Sharing or export — social features come later
- Outfit scheduling or calendar — separate capability
- Duplicate detection — users can save same combo twice

---

## Prerequisites

Before starting:
- Task 4 complete with working try-on generation
- Understanding of the existing data layer (closet items, user photos)
- Familiarity with image storage patterns used for garments

---

## Implementation Steps

### Step 1: Define Outfit Data Model

**File**: `src/models/outfit.ts` (new file)

**Purpose**: Establish the data structure for saved outfits

An outfit is a snapshot of a try-on result. It captures the generated image plus references to the inputs that created it. This allows regeneration without re-uploading.

**Pattern**:
```typescript
interface SavedOutfit {
  id: string;
  userId: string;
  name: string;
  
  // The generated try-on image
  resultImageUrl: string;
  
  // References to inputs (for regeneration)
  personPhotoId: string;
  garmentIds: string[];  // Support multi-garment in future
  
  // Metadata
  createdAt: Date;
  updatedAt: Date;
  
  // Optional context
  notes?: string;
  tags?: string[];
}
```

### Step 2: Create Outfit Storage Service

**File**: `src/services/outfit-service.ts` (new file)

**Purpose**: Handle CRUD operations for saved outfits

Keep this in the "fast layer" per architecture — outfits are just metadata and image references, no GPU work.

**Pattern**:
```typescript
class OutfitService {
  async saveOutfit(params: {
    userId: string;
    name: string;
    resultImageUrl: string;
    personPhotoId: string;
    garmentIds: string[];
  }): Promise<SavedOutfit> {
    // Generate ID, set timestamps, persist
  }
  
  async getUserOutfits(userId: string): Promise<SavedOutfit[]> {
    // Return sorted by createdAt desc (newest first)
  }
  
  async getOutfit(id: string): Promise<SavedOutfit | null> {
    // Single outfit fetch for detail view
  }
  
  async updateOutfit(id: string, updates: Partial<SavedOutfit>): Promise<SavedOutfit> {
    // Name changes, notes, tags
  }
  
  async deleteOutfit(id: string): Promise<void> {
    // Remove outfit record (keep or delete image?)
  }
}
```

**Decision**: When deleting an outfit, delete the generated image too. These images aren't reusable elsewhere, and storage costs add up.

### Step 3: Add Save Action to Try-On Result

**File**: `src/components/try-on-result/try-on-result.component.ts`

**Purpose**: Let users save immediately after generation

The save action should feel lightweight — just a name prompt, not a form. Default to "Outfit - [date]" so users can save quickly.

**Pattern**:
```typescript
// In the try-on result component
async onSaveOutfit(): Promise<void> {
  const defaultName = `Outfit - ${formatDate(new Date(), 'MMM d')}`;
  
  const name = await this.promptService.prompt({
    title: 'Save Outfit',
    placeholder: defaultName,
    confirmLabel: 'Save'
  });
  
  if (name === null) return; // Cancelled
  
  await this.outfitService.saveOutfit({
    userId: this.authService.currentUserId,
    name: name || defaultName,
    resultImageUrl: this.currentResult.imageUrl,
    personPhotoId: this.selectedPersonPhoto.id,
    garmentIds: this.selectedGarments.map(g => g.id)
  });
  
  this.toastService.show('Outfit saved');
}
```

**UI placement**: Add a "Save" button alongside any existing actions (share, download) on the try-on result screen. Heart icon or bookmark icon works well.

### Step 4: Build Outfit Gallery View

**File**: `src/components/outfit-gallery/outfit-gallery.component.ts` (new file)

**Purpose**: Display all saved outfits in a browsable grid

This is the "library of looks" from the epic. Grid layout matches the closet view pattern for consistency.

**Pattern**:
```typescript
@Component({
  selector: 'app-outfit-gallery',
  template: `
    <div class="gallery-header">
      <h2>Saved Outfits</h2>
      <span class="count">{{ outfits.length }} looks</span>
    </div>
    
    <div class="outfit-grid">
      @for (outfit of outfits; track outfit.id) {
        <div class="outfit-card" (click)="openOutfit(outfit)">
          <img [src]="outfit.resultImageUrl" [alt]="outfit.name">
          <div class="outfit-name">{{ outfit.name }}</div>
          <div class="outfit-date">{{ outfit.createdAt | relativeTime }}</div>
        </div>
      }
      
      @empty {
        <div class="empty-state">
          <p>No saved outfits yet</p>
          <p class="hint">Try on an outfit and tap Save to start your collection</p>
        </div>
      }
    </div>
  `
})
export class OutfitGalleryComponent implements OnInit {
  outfits: SavedOutfit[] = [];
  
  async ngOnInit() {
    this.outfits = await this.outfitService.getUserOutfits(
      this.authService.currentUserId
    );
  }
}
```

**Navigation**: Add "Saved Outfits" to main nav, likely alongside "My Closet".

### Step 5: Implement Outfit Detail View

**File**: `src/components/outfit-detail/outfit-detail.component.ts` (new file)

**Purpose**: Show single outfit with actions (regenerate, modify, delete)

This is where users can act on a saved outfit. Keep it simple: big image, name, and action buttons.

**Pattern**:
```typescript
@Component({
  template: `
    <div class="outfit-detail">
      <img [src]="outfit.resultImageUrl" class="result-image">
      
      <div class="outfit-info">
        <h2 (click)="editName()">{{ outfit.name }}</h2>
        <p class="created">Saved {{ outfit.createdAt | relativeTime }}</p>
      </div>
      
      <div class="garment-refs">
        <h3>Items Used</h3>
        @for (garment of referencedGarments; track garment.id) {
          <img [src]="garment.thumbnailUrl" class="garment-thumb">
        }
      </div>
      
      <div class="actions">
        <button (click)="regenerate()">Regenerate</button>
        <button (click)="tryWithDifferentPose()">Different Pose</button>
        <button (click)="delete()" class="danger">Delete</button>
      </div>
    </div>
  `
})
export class OutfitDetailComponent {
  async regenerate(): Promise<void> {
    // Navigate to try-on with same inputs pre-selected
    this.router.navigate(['/try-on'], {
      queryParams: {
        personPhotoId: this.outfit.personPhotoId,
        garmentIds: this.outfit.garmentIds.join(','),
        regenerate: true
      }
    });
  }
  
  async tryWithDifferentPose(): Promise<void> {
    // Navigate to try-on with garments pre-selected, but prompt for new pose
    this.router.navigate(['/try-on'], {
      queryParams: {
        garmentIds: this.outfit.garmentIds.join(',')
      }
    });
  }
}
```

### Step 6: Handle Regeneration Flow

**File**: `src/components/try-on/try-on.component.ts` (existing)

**Purpose**: Pre-populate try-on screen when coming from saved outfit

When regenerating, the try-on screen should feel like "picking up where you left off."

**Pattern**:
```typescript
async ngOnInit() {
  const params = this.route.snapshot.queryParams;
  
  if (params.personPhotoId) {
    this.selectedPersonPhoto = await this.photoService.getPhoto(params.personPhotoId);
  }
  
  if (params.garmentIds) {
    const ids = params.garmentIds.split(',');
    this.selectedGarments = await this.closetService.getGarmentsByIds(ids);
  }
  
  if (params.regenerate === 'true') {
    // Auto-start generation if regenerating
    this.startTryOn();
  }
}
```

### Step 7: Add Delete Confirmation

**File**: `src/components/outfit-detail/outfit-detail.component.ts`

**Purpose**: Prevent accidental deletions

Deleting is destructive — the generated image is gone. Confirm first.

**Pattern**:
```typescript
async delete(): Promise<void> {
  const confirmed = await this.confirmService.confirm({
    title: 'Delete Outfit?',
    message: `"${this.outfit.name}" will be permanently removed.`,
    confirmLabel: 'Delete',
    confirmClass: 'danger'
  });
  
  if (!confirmed) return;
  
  await this.outfitService.deleteOutfit(this.outfit.id);
  this.router.navigate(['/outfits']);
  this.toastService.show('Outfit deleted');
}
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Generate a try-on result (from Task 4)
# 2. Tap Save, enter a name
# 3. Navigate to Saved Outfits gallery
# 4. Verify the outfit appears with correct image and name
# 5. Tap the outfit to open detail view
# 6. Verify garment references are shown
# 7. Tap Regenerate, verify try-on starts with same inputs
# 8. Go back to saved outfit, delete it
# 9. Verify it's removed from gallery
```

**Expected Result**: 
- Saving feels instant (no loading state needed)
- Gallery loads quickly (this is "fast layer" per architecture)
- Regeneration pre-populates correctly
- Deleted outfits and their images are removed

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 5 as done
2. Consider quick wins for v1.1:
   - Outfit rename from gallery (long-press)
   - Sort options (newest, alphabetical)
   - Simple search by name

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale (fast vs. slow layer)
- [Epic](./epic.md) – Task scope and context
- [Timeline](./timeline.md) – Status tracking