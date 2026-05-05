# 🛠️ Task 3: Reference Photo Capture

**Purpose**: Enable users to upload and manage a full-body "reference photo" that serves as the base image for all virtual try-on generations.

**Effort**: 1 day

**Dependencies**: Task 1 (Project scaffolding), Task 2 (Supabase schema with `user_profiles` table)

**Parallel With**: Task 4 (Garment upload) — different upload flows, no conflicts

**Blocks**: Task 7 (Try-on generation) — cannot generate without a reference photo

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Reference photo upload component with camera/gallery selection
- Photo quality guidance UI (lighting, framing, pose tips)
- Image validation (dimensions, file size, format)
- Supabase Storage integration for secure storage
- Ability to view, replace, or delete reference photo
- Profile state management for reference photo URL

### What's NOT Included
- Automatic pose detection — manual guidance only for MVP
- Multiple reference photos — single photo per user initially
- Body measurements extraction — future enhancement
- Background removal — handled by try-on model, not upload

---

## Prerequisites

Before starting:
- Supabase project configured with Storage enabled
- `user_profiles` table exists with `reference_photo_url` column
- Authentication flow working (user must be logged in)
- Basic understanding of Supabase Storage RLS policies

---

## Implementation Steps

### Step 1: Create Storage Bucket

**File**: Supabase Dashboard or migration script

**Purpose**: Dedicated bucket for reference photos with proper access controls

Create a `reference-photos` bucket with the following characteristics:
- Private bucket (not public)
- File size limit: 10MB
- Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`

**RLS Policy Pattern**:
```sql
-- Users can only access their own reference photos
-- Folder structure: reference-photos/{user_id}/reference.{ext}

CREATE POLICY "Users can upload own reference photo"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'reference-photos' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can view own reference photo"
ON storage.objects FOR SELECT
USING (
  bucket_id = 'reference-photos' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);

CREATE POLICY "Users can delete own reference photo"
ON storage.objects FOR DELETE
USING (
  bucket_id = 'reference-photos' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);
```

### Step 2: Build Photo Guidance Component

**File**: `src/components/reference-photo/PhotoGuidance.tsx`

**Purpose**: Show users what makes a good reference photo before they upload

This component displays visual tips for optimal photo quality. Key guidance points:
- Full body visible (head to feet)
- Neutral pose, arms slightly away from body
- Form-fitting or well-defined clothing
- Good lighting, minimal shadows
- Plain background preferred
- Front-facing camera angle

**Pattern**:
```tsx
// Visual checklist with icons
const guidelines = [
  { icon: "👤", text: "Full body visible", detail: "Head to feet in frame" },
  { icon: "💡", text: "Good lighting", detail: "Even, natural light works best" },
  { icon: "🧍", text: "Neutral pose", detail: "Arms relaxed, slightly away from body" },
  // ...
];

// Show as dismissible overlay or inline tips
// Include example "good" vs "avoid" silhouettes
```

### Step 3: Implement Upload Service

**File**: `src/services/referencePhoto.ts`

**Purpose**: Handle upload, validation, and URL management

The service validates the image client-side before upload, handles the Supabase Storage interaction, and updates the user profile.

**Pattern**:
```typescript
interface UploadResult {
  success: boolean;
  url?: string;
  error?: string;
}

async function uploadReferencePhoto(file: File, userId: string): Promise<UploadResult> {
  // 1. Validate file type and size
  const validation = validateImage(file, {
    maxSizeMB: 10,
    allowedTypes: ['image/jpeg', 'image/png', 'image/webp'],
    minDimensions: { width: 400, height: 600 }
  });
  
  if (!validation.valid) {
    return { success: false, error: validation.error };
  }

  // 2. Generate storage path: {userId}/reference.{ext}
  const ext = file.name.split('.').pop();
  const path = `${userId}/reference.${ext}`;

  // 3. Delete existing photo if present (replace flow)
  await supabase.storage.from('reference-photos').remove([`${userId}/*`]);

  // 4. Upload new photo
  const { error: uploadError } = await supabase.storage
    .from('reference-photos')
    .upload(path, file, { upsert: true });

  if (uploadError) {
    return { success: false, error: 'Upload failed' };
  }

  // 5. Get signed URL (or public URL if bucket is public)
  const { data: urlData } = await supabase.storage
    .from('reference-photos')
    .createSignedUrl(path, 60 * 60 * 24 * 365); // 1 year

  // 6. Update user_profiles table
  await supabase
    .from('user_profiles')
    .update({ reference_photo_url: urlData.signedUrl })
    .eq('id', userId);

  return { success: true, url: urlData.signedUrl };
}
```

### Step 4: Build Upload UI Component

**File**: `src/components/reference-photo/ReferencePhotoUpload.tsx`

**Purpose**: The main upload interface with preview and state management

Component states: empty → selecting → uploading → complete. Show the current reference photo if one exists, with clear "Change Photo" action.

**Pattern**:
```tsx
// Core states
const [status, setStatus] = useState<'empty' | 'selecting' | 'uploading' | 'complete'>('empty');
const [preview, setPreview] = useState<string | null>(null);

// File selection handler
const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (file) {
    setPreview(URL.createObjectURL(file));
    setStatus('selecting');
  }
};

// Upload confirmation (user reviews preview before committing)
const handleConfirm = async () => {
  setStatus('uploading');
  const result = await uploadReferencePhoto(file, userId);
  // Handle result...
};

// UI structure:
// - If no photo: Show guidance + upload button
// - If selecting: Show preview + confirm/cancel
// - If uploading: Show progress indicator
// - If complete: Show current photo + change button
```

### Step 5: Add Dimension Validation

**File**: `src/utils/imageValidation.ts`

**Purpose**: Ensure uploaded images meet minimum quality requirements

Read image dimensions client-side before upload to catch unsuitable images early.

**Pattern**:
```typescript
function getImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      resolve({ width: img.naturalWidth, height: img.naturalHeight });
      URL.revokeObjectURL(img.src);
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

// Validation: minimum 400x600, aspect ratio roughly portrait
// Warn (don't block) if image seems landscape-oriented
```

### Step 6: Wire Into Profile/Onboarding Flow

**File**: `src/app/profile/page.tsx` or `src/app/onboarding/page.tsx`

**Purpose**: Integrate the upload component into the user journey

The reference photo capture should appear:
1. During onboarding (after account creation)
2. In profile settings (to view/change)

**Pattern**:
```tsx
// Onboarding step
<OnboardingStep step={2} title="Your Reference Photo">
  <PhotoGuidance />
  <ReferencePhotoUpload 
    userId={user.id}
    existingUrl={profile.reference_photo_url}
    onComplete={() => router.push('/onboarding/step-3')}
  />
</OnboardingStep>

// Profile settings section
<SettingsSection title="Reference Photo">
  <ReferencePhotoUpload 
    userId={user.id}
    existingUrl={profile.reference_photo_url}
    onComplete={() => toast.success('Photo updated')}
  />
</SettingsSection>
```

---

## Verification

How to verify this implementation works:

```bash
# 1. Check storage bucket exists
# Supabase Dashboard → Storage → reference-photos bucket should exist

# 2. Test upload flow
# - Log in as test user
# - Navigate to profile or onboarding
# - Upload a test image
# - Verify it appears in Supabase Storage under {user_id}/reference.*

# 3. Verify RLS policies
# - Try accessing another user's reference photo URL → should fail
# - Try uploading to another user's folder → should fail

# 4. Check profile update
SELECT reference_photo_url FROM user_profiles WHERE id = '{test_user_id}';
# Should return the signed URL
```

**Expected Result**: 
- User can upload a full-body photo
- Photo appears in their profile with ability to change
- Photo URL is stored in `user_profiles.reference_photo_url`
- Other users cannot access the photo

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 complete
2. Proceed to Task 4 (Garment upload) or Task 7 (Try-on generation) depending on parallel workstreams

---

## Related Documents

- [Architecture](./architecture.md) – Design rationale for storage decisions
- [Epic](./epic.md) – Task scope and MVP boundaries
- [Timeline](./timeline.md) – Status tracking