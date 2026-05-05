# 🛠️ Task 3: Photo capture and generation pipeline

**Purpose**: Wire the end-to-end generation flow — from camera shutter to AI-enhanced result — so that an authenticated user can take or upload a photo, wait with clear expectations, and see their LoRA-enhanced output alongside a gallery of past generations.

**Effort**: 2 days

**Dependencies**: Task 1 (Shell + Auth + Gating) — requires authenticated user identity and user-to-model mapping schema

**Parallel With**: —

**Blocks**: Task 4 (Deploy + Distribute) — testers can't be invited until the capture-to-result flow works end-to-end

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Photo capture via Capacitor Camera plugin (native camera + gallery picker)
- File input fallback for web/browser usage
- `PhotoService` for image encoding and upload to Flask
- Flask `/api/generate` endpoint: receive image + user_id, resolve LoRA model, call Replicate, return result
- `generations` table in Neon for persisting results
- Before/after result screen with slider comparison
- Honest loading UX with timed message sequence addressing 10-60s Replicate latency
- Structured error handling with user-facing failure messages and retry
- Gallery view of past generations

### What's NOT Included
- Style selection or prompt customization — one default style per [Architecture](./architecture.md) design decisions
- Image compression or optimization pipeline — Capacitor returns usable quality; optimize later if needed
- Background generation recovery — if the user leaves mid-generation, the result is lost; acceptable at 15 users
- Pagination on gallery — at 3-5 images per session and 15 users, a flat list is sufficient

---

## Prerequisites

Before starting:
- Task 1 complete: shell running, auth working, `users` table populated, route structure in place
- Task 2 in progress or complete: at least one LoRA model trained and seeded in `lora_models` (your own model is enough for development)
- `lora_models` table created in Neon (see [Task 2](./task-2-pre-train-15-lora-models.md) Step 1)
- Replicate API token in environment (`REPLICATE_API_TOKEN`)
- Neon connection string in environment (`NEON_DATABASE_URL`)
- Capacitor Camera plugin docs reviewed: `@capacitor/camera`
- Flask running locally with access to Neon

---

## Implementation Steps

### Step 1: Create the `generations` table

**File**: `migrations/002_generations.sql` (or run via `psql`)

**Purpose**: Persist every generation event so the gallery view has data and retention analysis has signal.

This table records the full lifecycle of a generation: who requested it, what they submitted, what came back, how long it took, and whether it succeeded. The gallery reads from this table; retention queries (`SELECT COUNT(DISTINCT user_id) FROM generations WHERE created_at > NOW() - INTERVAL '7 days'`) run against it too.

**Pattern**:
```sql
CREATE TABLE IF NOT EXISTS generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lora_model_id UUID REFERENCES lora_models(id),
    original_image_url TEXT,
    result_image_url TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | processing | completed | failed
    error_message TEXT,
    duration_ms INT,
    prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_generations_user_id ON generations(user_id);
CREATE INDEX idx_generations_created_at ON generations(created_at DESC);
```

**Notes**:
- `original_image_url` stores the uploaded image URL (or base64 reference if stored temporarily)
- `result_image_url` is the Replicate-hosted output URL
- `duration_ms` records end-to-end generation time for latency analysis
- `status` enables future async patterns but for Month 1 rows go directly to `completed` or `failed`

---

### Step 2: Install Capacitor Camera plugin

**File**: `package.json` (frontend project root)

**Purpose**: Enable native camera access and photo gallery picking from a single API that works on both iOS and web.

```bash
npm install @capacitor/camera
npx cap sync
```

Add camera permissions to the iOS project. Capacitor 7+ handles the `Info.plist` entries automatically via `npx cap sync`, but verify these exist:

**File**: `ios/App/App/Info.plist`
```xml
<key>NSCameraUsageDescription</key>
<string>Take photos to enhance with your personal AI model</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>Choose photos to enhance with your personal AI model</string>
```

**Verification**: `npx cap sync ios` completes without errors.

---

### Step 3: Build `PhotoService`

**File**: `src/app/services/photo.service.ts`

**Purpose**: Abstract camera capture, gallery selection, and image upload behind a clean service interface. Components call `capture()` or `pickFromGallery()` and get back a File-like blob; they call `generate()` and get back a generation result.

This service handles the Capacitor bridge, image format normalization, and the HTTP call to Flask. Components never touch Capacitor directly.

**Pattern**:
```typescript
import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Camera, CameraResultType, CameraSource } from '@capacitor/camera';
import { firstValueFrom } from 'rxjs';

export interface GenerationResult {
  id: string;
  result_image_url: string;
  original_image_url: string;
  duration_ms: number;
}

export interface GenerationError {
  error: string;
  code: 'no_model' | 'replicate_timeout' | 'replicate_error' | 'rate_limit' | 'unknown';
  retry: boolean;
}

@Injectable({ providedIn: 'root' })
export class PhotoService {
  private http = inject(HttpClient);
  private apiUrl = 'http://localhost:3100/api';

  // Loading state exposed as signals for the component tree
  readonly isGenerating = signal(false);
  readonly generationPhase = signal<string>('');

  async capturePhoto(): Promise<Blob> {
    const image = await Camera.getPhoto({
      quality: 90,
      allowEditing: false,
      resultType: CameraResultType.Uri,
      source: CameraSource.Camera,
    });
    return this.uriToBlob(image.webPath!);
  }

  async pickFromGallery(): Promise<Blob> {
    const image = await Camera.getPhoto({
      quality: 90,
      allowEditing: false,
      resultType: CameraResultType.Uri,
      source: CameraSource.Photos,
    });
    return this.uriToBlob(image.webPath!);
  }

  async generate(imageBlob: Blob, userId: string): Promise<GenerationResult> {
    this.isGenerating.set(true);
    this.generationPhase.set('Uploading your photo...');

    const formData = new FormData();
    formData.append('image', imageBlob, 'photo.jpg');
    formData.append('user_id', userId);

    try {
      this.startPhaseTimer();
      const result = await firstValueFrom(
        this.http.post<GenerationResult>(`${this.apiUrl}/generate`, formData)
      );
      return result;
    } finally {
      this.isGenerating.set(false);
      this.generationPhase.set('');
    }
  }

  async getGallery(userId: string): Promise<GenerationResult[]> {
    return firstValueFrom(
      this.http.get<GenerationResult[]>(`${this.apiUrl}/generations/${userId}`)
    );
  }

  private async uriToBlob(webPath: string): Promise<Blob> {
    const response = await fetch(webPath);
    return response.blob();
  }

  /** Cycle through honest loading messages on a timer */
  private startPhaseTimer(): void {
    const phases = [
      { delay: 0, message: 'Uploading your photo...' },
      { delay: 2000, message: 'Your AI model is creating your photo...' },
      { delay: 8000, message: 'Still working — this usually takes 15-30 seconds' },
      { delay: 20000, message: 'Almost there — your model is finishing up' },
      { delay: 40000, message: 'Taking a bit longer than usual — hang tight' },
    ];

    const timeouts: ReturnType<typeof setTimeout>[] = [];

    for (const phase of phases) {
      const timeout = setTimeout(() => {
        if (this.isGenerating()) {
          this.generationPhase.set(phase.message);
        }
      }, phase.delay);
      timeouts.push(timeout);
    }

    // Clean up timeouts when generation completes
    const cleanup = setInterval(() => {
      if (!this.isGenerating()) {
        timeouts.forEach(clearTimeout);
        clearInterval(cleanup);
      }
    }, 500);
  }
}
```

**Key decisions**:
- `CameraResultType.Uri` avoids base64 bloat — the URI is converted to a Blob for upload
- Signals (not RxJS subjects) for loading state, per [Architecture](./architecture.md) patterns
- The phase timer addresses the honest loading UX pattern: no spinners without context
- `firstValueFrom` bridges RxJS HttpClient to async/await for cleaner control flow

---

### Step 4: Build the Flask `/api/generate` endpoint

**File**: `backend/app.py` (or extend existing Flask app)

**Purpose**: The single orchestration endpoint — receive an image and user ID, resolve the LoRA model, call Replicate, persist the result, return it. Stateless, synchronous, no queue.

**Pattern**:
```python
import os
import time
import uuid
import replicate
import psycopg2
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app, origins=["http://localhost:4201", "https://yourdomain.com"])

NEON_DATABASE_URL = os.environ["NEON_DATABASE_URL"]
REPLICATE_API_TOKEN = os.environ["REPLICATE_API_TOKEN"]

DEFAULT_PROMPT_TEMPLATE = "a professional enhanced photo of {trigger_word}, high quality, natural lighting, sharp detail"


def get_db():
    return psycopg2.connect(NEON_DATABASE_URL)


def resolve_model(user_id: str):
    """Look up the user's LoRA model. Returns (model_id_uuid, replicate_model_id, trigger_word) or None."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT lm.id, lm.replicate_model_id
        FROM lora_models lm
        WHERE lm.user_id = %s AND lm.training_status = 'ready'
    """, (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row  # (lora_model_uuid, replicate_model_id) or None


def save_generation(user_id, lora_model_id, original_url, result_url, status, duration_ms, prompt, error_msg=None):
    """Persist a generation record."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO generations (user_id, lora_model_id, original_image_url, result_image_url,
                                  status, duration_ms, prompt, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (user_id, lora_model_id, original_url, result_url, status, duration_ms, prompt, error_msg))
    gen_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return gen_id


@app.route('/api/generate', methods=['POST'])
def generate():
    user_id = request.form.get('user_id')
    image = request.files.get('image')

    if not user_id or not image:
        return jsonify({"error": "Missing user_id or image", "code": "unknown", "retry": False}), 400

    # 1. Resolve user's LoRA model
    model = resolve_model(user_id)
    if not model:
        return jsonify({
            "error": "No AI model found for your account. You may be on the waitlist.",
            "code": "no_model",
            "retry": False
        }), 404

    lora_model_uuid, replicate_model_id = model

    # 2. Extract trigger word from model name (convention: last segment before version)
    # e.g. "username/photoshoot-alice:version" → "ALICE"
    model_name = replicate_model_id.split("/")[-1].split(":")[0]
    trigger_word = model_name.replace("photoshoot-", "").upper()

    prompt = DEFAULT_PROMPT_TEMPLATE.format(trigger_word=trigger_word)

    # 3. Call Replicate inference
    start_time = time.time()
    try:
        # Read image bytes for Replicate input
        image_bytes = image.read()

        output = replicate.run(
            replicate_model_id,
            input={
                "prompt": prompt,
                "image": image_bytes,
                "num_outputs": 1,
                "guidance_scale": 7.5,
                "num_inference_steps": 28,
            }
        )

        result_url = output[0] if isinstance(output, list) else str(output)
        duration_ms = int((time.time() - start_time) * 1000)

        # 4. Persist result
        gen_id = save_generation(
            user_id=user_id,
            lora_model_id=lora_model_uuid,
            original_url=None,  # Could store uploaded image URL if using cloud storage
            result_url=result_url,
            status='completed',
            duration_ms=duration_ms,
            prompt=prompt
        )

        return jsonify({
            "id": str(gen_id),
            "result_image_url": result_url,
            "original_image_url": None,
            "duration_ms": duration_ms,
        })

    except replicate.exceptions.ReplicateError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_code = "replicate_timeout" if "timeout" in str(e).lower() else "replicate_error"

        save_generation(
            user_id=user_id,
            lora_model_id=lora_model_uuid,
            original_url=None,
            result_url=None,
            status='failed',
            duration_ms=duration_ms,
            prompt=prompt,
            error_msg=str(e)
        )

        return jsonify({
            "error": "Generation didn't complete — tap to try again.",
            "code": error_code,
            "retry": True
        }), 502

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        save_generation(
            user_id=user_id,
            lora_model_id=lora_model_uuid,
            original_url=None,
            result_url=None,
            status='failed',
            duration_ms=duration_ms,
            prompt=prompt,
            error_msg=str(e)
        )

        return jsonify({
            "error": "Something went wrong. Please try again.",
            "code": "unknown",
            "retry": True
        }), 500


@app.route('/api/generations/<user_id>', methods=['GET'])
def list_generations(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, original_image_url, result_image_url, duration_ms, created_at
        FROM generations
        WHERE user_id = %s AND status = 'completed'
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return jsonify([{
        "id": str(row[0]),
        "original_image_url": row[1],
        "result_image_url": row[2],
        "duration_ms": row[3],
        "created_at": row[4].isoformat(),
    } for row in rows])


if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

**Key decisions**:
- Synchronous `replicate.run()` blocks the request. At 15 users this is fine — Python threading handles 2-3 concurrent requests. Per [Architecture](./architecture.md), a queue is premature.
- Trigger word extraction follows the naming convention from Task 2: `photoshoot-alice` → `ALICE`.
- Every generation is persisted regardless of outcome — failed generations are tracked for debugging.
- Structured error responses with `code` and `retry` fields let the frontend render specific messages without parsing error strings.
- The `image` parameter to Replicate may need adjustment depending on the specific model's expected input format (some LoRA models accept `image` for img2img, others are text-to-image only). Adapt based on your trained model's API.

---

### Step 5: Build `PhotoCaptureComponent`

**File**: `src/app/components/photoshoot/photo-capture.component.ts`

**Purpose**: The main capture screen — two buttons (camera and gallery), simple and immediate. This is where the user journey starts on the /photoshoot route.

**Pattern**:
```typescript
import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { IonContent, IonButton, IonIcon, IonSpinner } from '@ionic/angular/standalone';
import { PhotoService } from '../../services/photo.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-photo-capture',
  standalone: true,
  imports: [IonContent, IonButton, IonIcon, IonSpinner],
  template: `
    <ion-content class="ion-padding">
      @if (photoService.isGenerating()) {
        <!-- Loading state: honest UX -->
        <div class="generating-overlay">
          <ion-spinner name="crescent" />
          <p class="phase-message">{{ photoService.generationPhase() }}</p>
        </div>
      } @else if (resultUrl) {
        <!-- Result state: show before/after -->
        <app-result-view
          [originalUrl]="originalUrl"
          [resultUrl]="resultUrl"
          (newPhoto)="reset()"
        />
      } @else {
        <!-- Capture state: camera + gallery buttons -->
        <div class="capture-actions">
          <h2>Take a photo</h2>
          <p>Your personal AI model will enhance it</p>

          <ion-button expand="block" (click)="takePhoto()">
            <ion-icon slot="start" name="camera-outline" />
            Open Camera
          </ion-button>

          <ion-button expand="block" fill="outline" (click)="uploadPhoto()">
            <ion-icon slot="start" name="images-outline" />
            Choose from Gallery
          </ion-button>
        </div>
      }

      @if (error) {
        <div class="error-banner">
          <p>{{ error.error }}</p>
          @if (error.retry) {
            <ion-button size="small" (click)="retry()">Try Again</ion-button>
          }
        </div>
      }
    </ion-content>
  `,
})
export class PhotoCaptureComponent {
  photoService = inject(PhotoService);
  private auth = inject(AuthService);

  originalUrl: string | null = null;
  resultUrl: string | null = null;
  error: { error: string; code: string; retry: boolean } | null = null;
  private lastBlob: Blob | null = null;

  async takePhoto(): Promise<void> {
    try {
      const blob = await this.photoService.capturePhoto();
      await this.submitPhoto(blob);
    } catch (e: any) {
      if (e?.message?.includes('User cancelled')) return; // User dismissed camera
      this.error = { error: 'Could not access camera. Check permissions.', code: 'camera', retry: false };
    }
  }

  async uploadPhoto(): Promise<void> {
    try {
      const blob = await this.photoService.pickFromGallery();
      await this.submitPhoto(blob);
    } catch (e: any) {
      if (e?.message?.includes('User cancelled')) return;
      this.error = { error: 'Could not access photos. Check permissions.', code: 'gallery', retry: false };
    }
  }

  async retry(): Promise<void> {
    if (this.lastBlob) {
      this.error = null;
      await this.submitPhoto(this.lastBlob);
    }
  }

  reset(): void {
    this.originalUrl = null;
    this.resultUrl = null;
    this.error = null;
    this.lastBlob = null;
  }

  private async submitPhoto(blob: Blob): Promise<void> {
    this.error = null;
    this.lastBlob = blob;
    this.originalUrl = URL.createObjectURL(blob);

    const userId = this.auth.currentUser()?.id;
    if (!userId) return;

    try {
      const result = await this.photoService.generate(blob, userId);
      this.resultUrl = result.result_image_url;
    } catch (e: any) {
      const body = e?.error;
      this.error = body?.code
        ? body
        : { error: 'Something went wrong. Please try again.', code: 'unknown', retry: true };
    }
  }
}
```

**Key decisions**:
- Three states (capture → loading → result) managed by simple properties, not a state machine. At this complexity, signals and conditional blocks are sufficient.
- `User cancelled` errors from Capacitor are silently ignored — the user dismissed the camera intentionally.
- `lastBlob` enables retry without re-capturing. The user taps "Try Again" and the same image is re-submitted.
- `URL.createObjectURL(blob)` creates the local preview for the "before" side of the comparison.

---

### Step 6: Build `ResultViewComponent`

**File**: `src/app/components/photoshoot/result-view.component.ts`

**Purpose**: Before/after comparison with a draggable slider. This is the "wow" moment — the component must make the transformation feel tangible.

**Pattern**:
```typescript
import { Component, input, output } from '@angular/core';
import { IonButton, IonIcon } from '@ionic/angular/standalone';

@Component({
  selector: 'app-result-view',
  standalone: true,
  imports: [IonButton, IonIcon],
  template: `
    <div class="result-container">
      <div class="comparison-slider" (touchmove)="onSlide($event)" (mousemove)="onSlide($event)">
        <!-- Before (original) -->
        <div class="before" [style.width.%]="sliderPosition">
          <img [src]="originalUrl()" alt="Original" />
          <span class="label">Before</span>
        </div>
        <!-- After (generated) -->
        <div class="after">
          <img [src]="resultUrl()" alt="Enhanced" />
          <span class="label">After</span>
        </div>
        <!-- Slider handle -->
        <div class="slider-handle" [style.left.%]="sliderPosition">
          <div class="handle-line"></div>
        </div>
      </div>

      <div class="actions">
        <ion-button expand="block" (click)="newPhoto.emit()">
          <ion-icon slot="start" name="camera-outline" />
          Take Another
        </ion-button>
      </div>
    </div>
  `,
  styles: [`
    .comparison-slider {
      position: relative;
      width: 100%;
      aspect-ratio: 3/4;
      overflow: hidden;
      border-radius: 12px;
      touch-action: none;
    }
    .before, .after { position: absolute; inset: 0; }
    .before { z-index: 2; overflow: hidden; }
    .after { z-index: 1; }
    .before img, .after img { width: 100%; height: 100%; object-fit: cover; }
    .label {
      position: absolute; bottom: 12px; padding: 4px 12px;
      background: rgba(0,0,0,0.6); color: white; border-radius: 4px;
      font-size: 12px; text-transform: uppercase;
    }
    .before .label { left: 12px; }
    .after .label { right: 12px; }
    .slider-handle {
      position: absolute; top: 0; bottom: 0; z-index: 3;
      width: 3px; background: white;
      transform: translateX(-50%);
    }
    .handle-line {
      position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
      width: 32px; height: 32px; border-radius: 50%;
      background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
  `]
})
export class ResultViewComponent {
  originalUrl = input.required<string>();
  resultUrl = input.required<string>();
  newPhoto = output<void>();

  sliderPosition = 50;

  onSlide(event: TouchEvent | MouseEvent): void {
    const container = (event.target as HTMLElement).closest('.comparison-slider') as HTMLElement;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const clientX = event instanceof TouchEvent ? event.touches[0].clientX : event.clientX;
    const position = ((clientX - rect.left) / rect.width) * 100;
    this.sliderPosition = Math.max(0, Math.min(100, position));
  }
}
```

**Notes**:
- Touch-based slider works on both web and iOS. `touch-action: none` prevents scroll interference.
- The `before` div clips with `width.%` so dragging the slider reveals/hides the original.
- No external slider library — this is ~30 lines of interaction logic. Adding a dependency for this is overhead.

---

### Step 7: Build `GalleryComponent`

**File**: `src/app/components/photoshoot/gallery.component.ts`

**Purpose**: Grid of past generations, loaded from the `/api/generations/:userId` endpoint. Users see their history and can revisit the "wow" moment.

**Pattern**:
```typescript
import { Component, inject, OnInit, signal } from '@angular/core';
import { IonContent, IonGrid, IonRow, IonCol, IonSpinner } from '@ionic/angular/standalone';
import { PhotoService, GenerationResult } from '../../services/photo.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [IonContent, IonGrid, IonRow, IonCol, IonSpinner],
  template: `
    <ion-content class="ion-padding">
      @if (loading()) {
        <ion-spinner name="dots" />
      } @else if (generations().length === 0) {
        <div class="empty-state">
          <p>No photos yet. Take your first one!</p>
        </div>
      } @else {
        <ion-grid>
          <ion-row>
            @for (gen of generations(); track gen.id) {
              <ion-col size="6">
                <div class="gallery-item" (click)="selectGeneration(gen)">
                  <img [src]="gen.result_image_url" [alt]="'Generated ' + gen.created_at" />
                </div>
              </ion-col>
            }
          </ion-row>
        </ion-grid>
      }
    </ion-content>
  `,
  styles: [`
    .gallery-item {
      border-radius: 8px; overflow: hidden; aspect-ratio: 3/4;
    }
    .gallery-item img {
      width: 100%; height: 100%; object-fit: cover;
    }
  `]
})
export class GalleryComponent implements OnInit {
  private photoService = inject(PhotoService);
  private auth = inject(AuthService);

  generations = signal<GenerationResult[]>([]);
  loading = signal(true);

  async ngOnInit(): Promise<void> {
    const userId = this.auth.currentUser()?.id;
    if (!userId) return;

    try {
      const results = await this.photoService.getGallery(userId);
      this.generations.set(results);
    } finally {
      this.loading.set(false);
    }
  }

  selectGeneration(gen: GenerationResult): void {
    // Navigate to a detail/comparison view, or show a modal
    // For Month 1, tapping a gallery item could open the result full-screen
  }
}
```

**Cache invalidation**: When the user completes a new generation in `PhotoCaptureComponent`, the gallery needs to refresh. Two approaches:
1. **Simple**: Call `getGallery()` again on `ionViewWillEnter` — refetches when the gallery tab is tapped. At 15 users, the query is sub-millisecond.
2. **Signal-based**: Share a `generationCount` signal that the gallery watches and refetches when it changes. Only worth it if tab switching feels sluggish.

Start with approach 1. It's fewer lines and the performance cost is negligible.

---

### Step 8: Wire the routing

**File**: `src/app/app.routes.ts` (or wherever the shell routes are configured)

**Purpose**: Register /photoshoot as a tab with two child segments: capture (default) and gallery.

**Pattern**:
```typescript
{
  path: 'photoshoot',
  canActivate: [featureGateGuard('photoshoot')],
  children: [
    {
      path: '',
      redirectTo: 'capture',
      pathMatch: 'full',
    },
    {
      path: 'capture',
      loadComponent: () =>
        import('./components/photoshoot/photo-capture.component')
          .then(m => m.PhotoCaptureComponent),
    },
    {
      path: 'gallery',
      loadComponent: () =>
        import('./components/photoshoot/gallery.component')
          .then(m => m.GalleryComponent),
    },
  ],
}
```

**Tab bar entry** (in the shell's tab component):
```html
<ion-tab-button tab="photoshoot">
  <ion-icon name="camera" />
  <ion-label>Photoshoot</ion-label>
</ion-tab-button>
```

The `featureGateGuard` from Task 1 checks `enabled_features.photoshoot` on the user object. Users without access see the waitlist prompt, not a blank screen.

---

### Step 9: Handle the "no model" boundary

**File**: Affects both `PhotoCaptureComponent` and the Flask endpoint

**Purpose**: User #16 (no pre-trained model) must see a clear explanation, not a crash. This is a success criterion from the [Epic](./epic.md).

**Frontend pattern**: When the Flask endpoint returns `{ "code": "no_model" }`, the component renders a waitlist message instead of an error:

```typescript
// In PhotoCaptureComponent error handling
if (this.error?.code === 'no_model') {
  // Show waitlist UI instead of error banner
}
```

```html
@if (error?.code === 'no_model') {
  <div class="waitlist-prompt">
    <h3>Your AI model is coming soon</h3>
    <p>We're training a personal model just for you. We'll notify you when it's ready.</p>
  </div>
}
```

**Backend**: Already handled in Step 4 — `resolve_model()` returns `None` for users without a `lora_models` entry, and the endpoint returns a 404 with `code: "no_model"`.

---

## Day-by-Day Schedule

| Day | Morning | Afternoon |
|-----|---------|-----------|
| **Day 1** | Create `generations` table. Install Capacitor Camera plugin. Build `PhotoService` with capture, upload, and generate methods. | Build Flask `/api/generate` endpoint with model resolution and Replicate call. Test end-to-end with your own LoRA model (from Task 2). |
| **Day 2** | Build `PhotoCaptureComponent` with loading states and error handling. Build `ResultViewComponent` with before/after slider. | Build `GalleryComponent`. Wire routing. Test the full flow: capture → generate → result → gallery. Handle edge cases (no model, timeout, permissions denied). |

---

## Verification

How to verify this implementation works:

```bash
# 1. Verify generations table exists
psql $NEON_DATABASE_URL -c "\d generations"

# 2. Start Flask backend
cd backend && NEON_DATABASE_URL=$NEON_DATABASE_URL REPLICATE_API_TOKEN=$REPLICATE_API_TOKEN python app.py

# 3. Test generate endpoint directly with curl
curl -X POST http://localhost:5000/api/generate \
  -F "image=@test-photo.jpg" \
  -F "user_id=YOUR_USER_UUID"

# 4. Test gallery endpoint
curl http://localhost:5000/api/generations/YOUR_USER_UUID

# 5. Test no-model boundary (use a UUID with no lora_model)
curl -X POST http://localhost:5000/api/generate \
  -F "image=@test-photo.jpg" \
  -F "user_id=00000000-0000-0000-0000-000000000000"
# Expected: 404 with {"error": "...", "code": "no_model"}

# 6. Start Angular frontend
cd frontend && npm start
# Navigate to /photoshoot, take a photo, verify:
#   - Camera permissions prompt appears (iOS/web)
#   - Loading messages cycle through phases
#   - Result appears with before/after slider
#   - Gallery shows the completed generation
```

**Expected Results**:
- `/api/generate` returns a Replicate-hosted image URL within 10-60 seconds
- `generations` table has a new row with `status = 'completed'`
- Loading messages progress honestly through the wait
- Before/after slider is draggable and shows both images
- Gallery displays past generations in a grid
- User with no model sees waitlist prompt, not an error
- Camera permission denial shows a clear message, not a crash

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 as done
2. Run the full flow on an iOS device via `npx cap run ios` — camera behavior differs between browser and native
3. Coordinate with Task 2 to ensure all 15 models are seeded before Task 4
4. Proceed to Task 4 (Deploy and Distribute)

---

## Related Documents

- [Solution Architecture](./architecture.md) – Design rationale, data model, honest loading UX pattern, and synchronous Replicate decision
- [Epic](./epic.md) – Task scope and success criteria
- [Task 2: Pre-train 15 LoRA models](./task-2-pre-train-15-lora-models.md) – Database schema, model naming conventions, trigger word format
- [Timeline](./timeline.md) – Status tracking