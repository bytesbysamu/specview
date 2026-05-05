# 🛠️ Task 2: Digital Closet UI

**Purpose**: Build the main closet grid interface where users view, filter, and select their extracted garments for outfit creation and virtual try-on.

**Effort**: 2 days

**Dependencies**: Task 1 (Garment Extraction) — needs garment data model and storage

**Parallel With**: Task 3 (Person Photo Upload) — no shared dependencies

**Blocks**: Task 4 (Virtual Try-On Interface) — needs garment selection mechanism

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Responsive grid layout displaying garment thumbnails
- Filter controls (type, color, style tags)
- Multi-select mechanism for choosing items
- Drag-and-drop reordering within categories
- Empty state and loading states
- Garment detail panel (quick view)

### What's NOT Included
- Bulk upload UI — handled in Task 1
- Virtual try-on trigger — handled in Task 4
- Outfit saving/history — future iteration

---

## Prerequisites

Before starting:
- Garment data model defined (Task 1)
- API endpoints for fetching user's garments exist
- Design system/component library chosen (recommend Tailwind + headless UI)
- Understanding of the garment schema: `id`, `imageUrl`, `type`, `colors[]`, `tags[]`, `createdAt`

---

## Implementation Steps

### Step 1: Garment Grid Component

**File**: `src/components/ClosetGrid.tsx`

**Purpose**: Core grid layout that renders garment cards responsively

The grid should adapt from 2 columns on mobile to 4-6 on desktop. Each cell maintains aspect ratio for visual consistency regardless of original photo dimensions.

**Pattern**:
```tsx
// Use CSS Grid with auto-fill for responsive columns
<div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
  {garments.map(garment => (
    <GarmentCard
      key={garment.id}
      garment={garment}
      selected={selectedIds.includes(garment.id)}
      onSelect={handleSelect}
    />
  ))}
</div>
```

### Step 2: Garment Card Component

**File**: `src/components/GarmentCard.tsx`

**Purpose**: Individual garment display with selection state

Cards need three visual states: default, hover (shows quick actions), and selected (persistent highlight). Selection should work via click/tap, with visual feedback that persists.

**Pattern**:
```tsx
interface GarmentCardProps {
  garment: Garment;
  selected: boolean;
  onSelect: (id: string, multi: boolean) => void;
}

// Selection supports both single-click and cmd/ctrl+click for multi-select
const handleClick = (e: MouseEvent) => {
  onSelect(garment.id, e.metaKey || e.ctrlKey);
};

// Visual states via conditional classes
<div className={cn(
  "aspect-square rounded-lg overflow-hidden cursor-pointer transition-all",
  "hover:ring-2 hover:ring-blue-400",
  selected && "ring-2 ring-blue-600 ring-offset-2"
)}>
  <img src={garment.imageUrl} alt={garment.type} className="object-cover w-full h-full" />
</div>
```

### Step 3: Filter Bar Component

**File**: `src/components/ClosetFilters.tsx`

**Purpose**: Allow narrowing visible garments by type, color, and tags

Filters should feel instant — apply client-side against already-fetched data. Use pill/chip UI for active filters so users see what's applied at a glance.

**Pattern**:
```tsx
// Filter state shape
interface FilterState {
  types: string[];      // ['tops', 'bottoms']
  colors: string[];     // ['blue', 'black']
  tags: string[];       // ['casual', 'work']
}

// Derive available filter options from actual garment data
const availableTypes = useMemo(() => 
  [...new Set(garments.map(g => g.type))],
  [garments]
);

// Filter chips with toggle behavior
<div className="flex flex-wrap gap-2">
  {availableTypes.map(type => (
    <FilterChip
      key={type}
      label={type}
      active={filters.types.includes(type)}
      onClick={() => toggleFilter('types', type)}
    />
  ))}
</div>
```

### Step 4: Selection State Management

**File**: `src/hooks/useGarmentSelection.ts`

**Purpose**: Centralize selection logic for use across components

Selection state needs to be accessible from the closet grid and the try-on interface. Extract to a custom hook or context to avoid prop drilling.

**Pattern**:
```tsx
export function useGarmentSelection() {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const select = (id: string, multi: boolean) => {
    setSelectedIds(prev => {
      if (multi) {
        // Toggle in multi-select mode
        return prev.includes(id) 
          ? prev.filter(x => x !== id)
          : [...prev, id];
      }
      // Single select: toggle or replace
      return prev.includes(id) ? [] : [id];
    });
  };

  const clearSelection = () => setSelectedIds([]);

  return { selectedIds, select, clearSelection };
}
```

### Step 5: Drag-and-Drop Reordering

**File**: `src/components/ClosetGrid.tsx` (enhancement)

**Purpose**: Let users manually organize garments within the grid

Use a lightweight DnD library (dnd-kit recommended over react-beautiful-dnd for bundle size). Persist order to backend on drop to survive page refreshes.

**Pattern**:
```tsx
import { DndContext, closestCenter } from '@dnd-kit/core';
import { SortableContext, rectSortingStrategy } from '@dnd-kit/sortable';

// Wrap grid in DnD context
<DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
  <SortableContext items={garmentIds} strategy={rectSortingStrategy}>
    {/* Grid contents */}
  </SortableContext>
</DndContext>

// Persist new order
const handleDragEnd = async (event: DragEndEvent) => {
  const { active, over } = event;
  if (active.id !== over?.id) {
    const newOrder = arrayMove(garmentIds, oldIndex, newIndex);
    setGarmentIds(newOrder);
    await api.updateGarmentOrder(newOrder); // Fire-and-forget, optimistic
  }
};
```

### Step 6: Empty and Loading States

**File**: `src/components/ClosetEmpty.tsx`, update `ClosetGrid.tsx`

**Purpose**: Handle edge cases gracefully

Empty closet should guide users to upload their first items. Loading state should show skeleton cards matching the grid layout to prevent layout shift.

**Pattern**:
```tsx
// In ClosetGrid
if (isLoading) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="aspect-square bg-gray-200 rounded-lg animate-pulse" />
      ))}
    </div>
  );
}

if (garments.length === 0) {
  return <ClosetEmpty onUploadClick={openUploadModal} />;
}
```

### Step 7: Quick View Panel

**File**: `src/components/GarmentDetailPanel.tsx`

**Purpose**: Show garment details without leaving the grid context

Slide-in panel (not modal) that shows larger image, all tags, upload date, and actions (edit tags, delete). Keeps user in browsing flow.

**Pattern**:
```tsx
// Panel appears on garment long-press or dedicated "info" button
<aside className={cn(
  "fixed right-0 top-0 h-full w-80 bg-white shadow-xl transform transition-transform",
  activeGarment ? "translate-x-0" : "translate-x-full"
)}>
  {activeGarment && (
    <>
      <img src={activeGarment.imageUrl} className="w-full aspect-square object-cover" />
      <div className="p-4">
        <h3 className="font-medium">{activeGarment.type}</h3>
        <div className="flex flex-wrap gap-1 mt-2">
          {activeGarment.tags.map(tag => <Tag key={tag}>{tag}</Tag>)}
        </div>
      </div>
    </>
  )}
</aside>
```

---

## Verification

How to verify this implementation works:

```bash
# Start dev server
npm run dev

# Manual testing checklist:
# 1. Upload 5+ garments via Task 1 flow
# 2. Verify grid displays all garments
# 3. Click garment — should show selected state
# 4. Cmd+click multiple — should multi-select
# 5. Apply type filter — grid should filter instantly
# 6. Drag garment to new position — should persist after refresh
# 7. Click garment info — detail panel should slide in
# 8. Clear all garments — empty state should appear
```

**Expected Result**: 
- Grid renders responsively across breakpoints
- Filters apply instantly with no network requests
- Selection state is visually clear and persists during filtering
- Drag-and-drop feels smooth (no jank during drag)
- All states (loading, empty, error) handled gracefully

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 2 done
2. Expose `selectedIds` to parent layout for Task 4 integration
3. Proceed to Task 3 (Person Photo Upload) or Task 4 (Virtual Try-On Interface)

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for closet vs. try-on separation
- [Epic](./epic.md) – Task scope and success criteria
- [Timeline](./timeline.md) – Status tracking