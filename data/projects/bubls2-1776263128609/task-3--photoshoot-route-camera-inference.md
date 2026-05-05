# 🛠️ Task 3: /photoshoot route + camera + inference

**Purpose**: Build the lead feature that validates the super app concept — camera capture via Capacitor Camera plugin, photo upload to the Flask API, Replicate LoRA inference using the user's pre-trained personal model, and a before/after result screen with gallery of past generations.

**Effort**: 2 days

**Dependencies**: Task 1 (Shell scaffold + navigation) — the route registry and placeholder `PhotoshootPage` must exist

**Parallel With**: Task 2 (Auth + user model + feature gating) — both build against the shared schema contract for `users`, `lora_models`, and `generations` tables. Converges at integration: this task needs `g.user['id']` to resolve the LoRA model, which Task 2's auth middleware provides.

**Blocks**: Task 4 (Deploy web + iOS), Task 5 (Pre-train 15 LoRA models + invite testers)

**Related**:
- [Solution Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- `CameraService` wrapping Capacitor Camera plugin with web file-input fallback
- `PhotoshootPage` with three states: capture, loading/progress, result
- `PhotoshootApiService` for photo upload and inference result polling
- `GalleryComponent` for before/after comparison and past generations
- Flask `PhotoshootBlueprint` with `/api/photoshoot/generate` endpoint
- `ReplicateService` wrapping the Replicate API for LoRA inference dispatch
- `generations` table writes for result persistence

### What's NOT Included
- Style picker or prompt customization — one default style isolates the LoRA quality variable
- Self-serve LoRA training — models are pre-trained manually in Task 5
- Image persistence to S3/R2 — Replicate output URLs stored in Neon are sufficient for 15 users
- Offline mode or background processing — inference requires network; no queuing system

---

## Prerequisites

Before starting:
- Task 1 complete: shell serves with tab navigation, `PhotoshootPage` placeholder exists at `src/app/pages/photoshoot/photoshoot.page.ts`
- `@capacitor/camera` installed in the project (should already be present from the Bubls codebase)
- Replicate API token provisioned (existing from Trendfy)
- Neon Postgres schema created (Task 2's `schema.sql` defines `lora_models` and `generations` tables)
- At least one test LoRA model trained on Replicate with a known model ID (for local testing)
- Flask backend running with auth middleware from Task 2 (or stub `g.user` for parallel development)

---

## Implementation Steps

### Step 1: Build the CameraService

**File**: `src/app/services/camera.service.ts`

**Purpose**: Abstract the image capture mechanism so the rest of the photoshoot flow doesn't care whether the photo came from a native camera, photo library, or web file input. This is the `CameraService` from the Architecture — it wraps Capacitor Camera for native and falls back to file input on web.

The Capacitor Camera plugin returns different formats depending on platform and configuration. The service normalizes everything to a `Blob` that the upload service can send as multipart form data.

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { Camera, CameraResultType, CameraSource, Photo } from '@capacitor/camera';
import { Capacitor } from '@capacitor/core';

export interface CapturedPhoto {
  blob: Blob;
  previewUrl: string;  // Object URL for local preview
}

@Injectable({ providedIn: 'root' })
export class CameraService {
  private isNative = Capacitor.isNativePlatform();

  async captureFromCamera(): Promise<CapturedPhoto> {
    return this.capture(CameraSource.Camera);
  }

  async pickFromGallery(): Promise<CapturedPhoto> {
    return this.capture(CameraSource.Photos);
  }

  private async capture(source: CameraSource): Promise<CapturedPhoto> {
    const photo: Photo = await Camera.getPhoto({
      resultType: CameraResultType.Uri,
      source,
      quality: 90,
      width: 1024,           // Cap resolution — Replicate doesn't need 4K
      allowEditing: false,
    });

    const blob = await this.photoToBlob(photo);
    const previewUrl = URL.createObjectURL(blob);
    return { blob, previewUrl };
  }

  private async photoToBlob(photo: Photo): Promise<Blob> {
    if (photo.webPath) {
      const response = await fetch(photo.webPath);
      return response.blob();
    }
    // Fallback for base64 (shouldn't hit this with Uri result type, but defensive)
    if (photo.base64String) {
      const byteString = atob(photo.base64String);
      const bytes = new Uint8Array(byteString.length);
      for (let i = 0; i < byteString.length; i++) {
        bytes[i] = byteString.charCodeAt(i);
      }
      return new Blob([bytes], { type: `image/${photo.format}` });
    }
    throw new Error('No image data returned from camera');
  }

  revokePreview(url: string) {
    URL.revokeObjectURL(url);
  }
}
```

On web, the Capacitor Camera plugin automatically presents a file input dialog — no separate fallback code needed. The `CameraSource.Camera` option opens the device camera on iOS; on web it falls back to file selection. This is the risk mitigation from the Architecture: if the native camera integration fails in the Ionic 8 shell, photo library upload via `CameraSource.Photos` is functionally equivalent.

---

### Step 2: Build the PhotoshootApiService

**File**: `src/app/services/photoshoot-api.service.ts`

**Purpose**: Handles communication with the Flask `/api/photoshoot/generate` endpoint. Uploads the captured photo, initiates inference, and polls for results. This is the `PhotoshootApiService` from the Architecture.

The Replicate prediction API is asynchronous — you create a prediction, then poll until it completes. The Flask endpoint can either handle the polling server-side and return the final result (simpler client, longer request) or return the prediction ID and let the client poll (faster perceived response, more client logic). For 15 users, server-side polling with a timeout is simpler.

**Pattern**:
```typescript
import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment';

export interface GenerationResult {
  id: string;
  original_image_url: string;
  result_image_url: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class PhotoshootApiService {
  private baseUrl = `${environment.apiUrl}/api/photoshoot`;

  async generate(photo: Blob, accessToken: string): Promise<GenerationResult> {
    const formData = new FormData();
    formData.append('photo', photo, 'photo.jpg');

    const response = await fetch(`${this.baseUrl}/generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(error.error || `Generation failed (${response.status})`);
    }

    return response.json();
  }

  async getHistory(accessToken: string): Promise<GenerationResult[]> {
    const response = await fetch(`${this.baseUrl}/history`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      throw new Error('Failed to load history');
    }

    return response.json();
  }
}
```

No streaming here — the `/generate` endpoint blocks until Replicate completes (typically 10–30 seconds for LoRA inference). The client shows a loading state during this wait. If latency exceeds 60 seconds (Architecture risk), Step 7 addresses progress polling as a fast-follow.

---

### Step 3: Replace the PhotoshootPage placeholder

**File**: `src/app/pages/photoshoot/photoshoot.page.ts`

**Purpose**: The core UI component with three states: (1) capture — camera/upload buttons, (2) generating — loading indicator with the original photo, (3) result — before/after comparison with save-to-gallery. Replace the Task 1 placeholder entirely.

This is the `PhotoshootPage` from the Architecture with its three entry points: camera capture, photo upload, and gallery view.

**Pattern**:
```typescript
import { Component, signal, computed } from '@angular/core';
import {
  IonContent, IonButton, IonIcon, IonSpinner, IonText,
  IonHeader, IonToolbar, IonTitle, IonSegment, IonSegmentButton, IonLabel,
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { cameraOutline, imageOutline, timeOutline } from 'ionicons/icons';
import { CameraService, CapturedPhoto } from '../../services/camera.service';
import { PhotoshootApiService, GenerationResult } from '../../services/photoshoot-api.service';
import { AuthService } from '../../services/auth.service';
import { GalleryComponent } from '../../components/gallery/gallery.component';

type ViewMode = 'capture' | 'generating' | 'result' | 'history';

@Component({
  selector: 'app-photoshoot',
  standalone: true,
  imports: [
    IonContent, IonButton, IonIcon, IonSpinner, IonText,
    IonHeader, IonToolbar, IonTitle, IonSegment, IonSegmentButton, IonLabel,
    GalleryComponent,
  ],
  template: `
    <ion-header>
      <ion-toolbar>
        <ion-title>Photoshoot</ion-title>
        <ion-segment [value]="activeTab()" (ionChange)="onTabChange($event)" slot="end">
          <ion-segment-button value="capture">
            <ion-icon name="camera-outline"></ion-icon>
          </ion-segment-button>
          <ion-segment-button value="history">
            <ion-icon name="time-outline"></ion-icon>
          </ion-segment-button>
        </ion-segment>
      </ion-toolbar>
    </ion-header>

    <ion-content class="ion-padding">
      @switch (view()) {
        @case ('capture') {
          <div class="capture-area">
            <ion-button expand="block" size="large" (click)="takePhoto()">
              <ion-icon name="camera-outline" slot="start"></ion-icon>
              Take Photo
            </ion-button>
            <ion-button expand="block" fill="outline" (click)="pickPhoto()">
              <ion-icon name="image-outline" slot="start"></ion-icon>
              Choose from Gallery
            </ion-button>
          </div>
        }

        @case ('generating') {
          <div class="generating-area">
            @if (previewUrl()) {
              <img [src]="previewUrl()" alt="Your photo" class="preview-image" />
            }
            <div class="status">
              <ion-spinner name="crescent"></ion-spinner>
              <ion-text><p>Generating your styled photo...</p></ion-text>
            </div>
          </div>
        }

        @case ('result') {
          @if (latestResult()) {
            <div class="result-area">
              <div class="comparison">
                <div class="before">
                  <ion-text color="medium"><p>Original</p></ion-text>
                  <img [src]="latestResult()!.original_image_url" alt="Original" />
                </div>
                <div class="after">
                  <ion-text color="medium"><p>Styled</p></ion-text>
                  <img [src]="latestResult()!.result_image_url" alt="Result" />
                </div>
              </div>
              <ion-button expand="block" (click)="resetCapture()">
                Take Another
              </ion-button>
            </div>
          }
        }

        @case ('history') {
          <app-gallery />
        }
      }

      @if (error()) {
        <ion-text color="danger"><p>{{ error() }}</p></ion-text>
        <ion-button expand="block" fill="clear" (click)="resetCapture()">Try Again</ion-button>
      }
    </ion-content>
  `,
  styles: [`
    .capture-area {
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding-top: 40%;
    }
    .generating-area {
      text-align: center;
    }
    .preview-image {
      max-width: 100%;
      border-radius: 12px;
      margin-bottom: 24px;
    }
    .status {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
    }
    .comparison {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 24px;
    }
    .comparison img {
      width: 100%;
      border-radius: 8px;
    }
  `],
})
export class PhotoshootPage {
  activeTab = signal<'capture' | 'history'>('capture');
  view = signal<ViewMode>('capture');
  previewUrl = signal<string | null>(null);
  latestResult = signal<GenerationResult | null>(null);
  error = signal('');

  constructor(
    private camera: CameraService,
    private api: PhotoshootApiService,
    private auth: AuthService,
  ) {
    addIcons({ cameraOutline, imageOutline, timeOutline });
  }

  onTabChange(event: any) {
    const tab = event.detail.value;
    this.activeTab.set(tab);
    this.view.set(tab);
  }

  async takePhoto() {
    await this.captureAndGenerate(() => this.camera.captureFromCamera());
  }

  async pickPhoto() {
    await this.captureAndGenerate(() => this.camera.pickFromGallery());
  }

  private async captureAndGenerate(captureFn: () => Promise<CapturedPhoto>) {
    this.error.set('');
    try {
      const photo = await captureFn();
      this.previewUrl.set(photo.previewUrl);
      this.view.set('generating');

      const session = await this.auth.getSession();
      if (!session) {
        throw new Error('Not authenticated');
      }

      const result = await this.api.generate(photo.blob, session.access_token);
      this.latestResult.set(result);
      this.view.set('result');

      // Clean up the preview blob URL
      this.camera.revokePreview(photo.previewUrl);
    } catch (err: any) {
      this.error.set(err.message || 'Something went wrong');
      this.view.set('capture');
    }
  }

  resetCapture() {
    this.error.set('');
    this.latestResult.set(null);
    this.previewUrl.set(null);
    this.view.set('capture');
    this.activeTab.set('capture');
  }
}
```

The page manages its own state machine: `capture → generating → result`. No routing between sub-pages — signals drive the view switches. The segment toggle in the header provides quick access to the gallery without leaving the page.

---

### Step 4: Build the GalleryComponent

**File**: `src/app/components/gallery/gallery.component.ts`

**Purpose**: Displays past generations with before/after comparison. Fetches history from the API on init. This is the `GalleryComponent` from the Architecture.

**Pattern**:
```typescript
import { Component, signal, OnInit } from '@angular/core';
import { IonList, IonItem, IonThumbnail, IonLabel, IonText, IonSpinner } from '@ionic/angular/standalone';
import { PhotoshootApiService, GenerationResult } from '../../services/photoshoot-api.service';
import { AuthService } from '../../services/auth.service';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [IonList, IonItem, IonThumbnail, IonLabel, IonText, IonSpinner, DatePipe],
  template: `
    @if (loading()) {
      <div class="center"><ion-spinner name="crescent"></ion-spinner></div>
    } @else if (generations().length === 0) {
      <ion-text color="medium">
        <p class="center">No photos yet. Take your first one!</p>
      </ion-text>
    } @else {
      <ion-list>
        @for (gen of generations(); track gen.id) {
          <ion-item>
            <ion-thumbnail slot="start">
              <img [src]="gen.result_image_url" alt="Generated" />
            </ion-thumbnail>
            <ion-label>
              <p>{{ gen.created_at | date:'medium' }}</p>
            </ion-label>
          </ion-item>
        }
      </ion-list>
    }
  `,
  styles: [`
    .center {
      display: flex;
      justify-content: center;
      padding: 48px 0;
    }
  `],
})
export class GalleryComponent implements OnInit {
  generations = signal<GenerationResult[]>([]);
  loading = signal(true);

  constructor(
    private api: PhotoshootApiService,
    private auth: AuthService,
  ) {}

  async ngOnInit() {
    try {
      const session = await this.auth.getSession();
      if (session) {
        const history = await this.api.getHistory(session.access_token);
        this.generations.set(history);
      }
    } finally {
      this.loading.set(false);
    }
  }
}
```

The gallery is intentionally simple for Month 1 — a list of thumbnails with timestamps. No full-screen viewer, no download button, no sharing. If testers ask for these, they're fast-follow features that validate engagement.

---

### Step 5: Build the Flask PhotoshootBlueprint

**File**: `backend/routes/photoshoot.py`

**Purpose**: The `/api/photoshoot` Blueprint from the Architecture. Two endpoints: `POST /generate` (upload + inference) and `GET /history` (past generations). Uses Task 2's `@require_auth` and `@require_feature('photoshoot')` decorators — the Blueprint can assume an authenticated, authorized user.

This is the server-side half of the Capture-Normalize-Infer pipeline from the Architecture. The endpoint receives the image, resolves the user's LoRA model ID from Neon, dispatches to Replicate, waits for the result, persists the generation record, and returns the result URL.

**Pattern**:
```python
import os
import uuid
import base64
from flask import Blueprint, request, jsonify, g
from middleware.auth import require_auth, require_feature, get_db
from services.replicate_service import generate_with_lora
from psycopg2.extras import RealDictCursor

photoshoot_bp = Blueprint('photoshoot', __name__, url_prefix='/api/photoshoot')


@photoshoot_bp.route('/generate', methods=['POST'])
@require_auth
@require_feature('photoshoot')
def generate():
    """Upload photo → resolve user's LoRA model → Replicate inference → return result."""
    user = g.user

    # 1. Validate upload
    if 'photo' not in request.files:
        return jsonify({'error': 'No photo uploaded'}), 400

    photo_file = request.files['photo']

    # 2. Resolve user's LoRA model
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT replicate_model_id, trigger_word, default_style_prompt '
            'FROM lora_models WHERE user_id = %s ORDER BY created_at DESC LIMIT 1',
            (user['id'],)
        )
        lora_model = cur.fetchone()

    if not lora_model:
        return jsonify({'error': 'No personal model found. Contact Sam.'}), 404

    # 3. Convert photo to base64 data URI for Replicate
    photo_bytes = photo_file.read()
    photo_b64 = base64.b64encode(photo_bytes).decode('utf-8')
    mime_type = photo_file.content_type or 'image/jpeg'
    photo_data_uri = f"data:{mime_type};base64,{photo_b64}"

    # 4. Run inference
    try:
        result_url = generate_with_lora(
            model_id=lora_model['replicate_model_id'],
            input_image=photo_data_uri,
            trigger_word=lora_model.get('trigger_word', ''),
            style_prompt=lora_model.get('default_style_prompt', ''),
        )
    except Exception as e:
        return jsonify({'error': f'Inference failed: {str(e)}'}), 500

    # 5. Persist generation record
    generation_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            'INSERT INTO generations (id, user_id, lora_model_id, original_image_url, result_image_url) '
            'VALUES (%s, %s, %s, %s, %s)',
            (generation_id, user['id'], lora_model.get('id'), photo_data_uri, result_url)
        )
        conn.commit()

    return jsonify({
        'id': generation_id,
        'original_image_url': photo_data_uri,
        'result_image_url': result_url,
        'created_at': 'now',
    })


@photoshoot_bp.route('/history', methods=['GET'])
@require_auth
@require_feature('photoshoot')
def history():
    """Return the user's past generations, most recent first."""
    user = g.user
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT id, original_image_url, result_image_url, created_at '
            'FROM generations WHERE user_id = %s ORDER BY created_at DESC LIMIT 50',
            (user['id'],)
        )
        rows = cur.fetchall()

    return jsonify([{
        'id': str(r['id']),
        'original_image_url': r['original_image_url'],
        'result_image_url': r['result_image_url'],
        'created_at': r['created_at'].isoformat() if r['created_at'] else None,
    } for r in rows])
```

**Important**: The original image is stored as a base64 data URI in the `generations` table. For 15 users generating a handful of photos each, this is fine — a 1MB photo as base64 is ~1.3MB in the database. At scale this is terrible, but at scale you'd have S3/R2 and a proper upload pipeline. Don't build that now.

---

### Step 6: Build the ReplicateService

**File**: `backend/services/replicate_service.py`

**Purpose**: Wrapper around the Replicate API for LoRA inference. This absorbs the inference logic from Trendfy's existing generate module — adapted for the super app's simpler single-model flow.

Replicate's API is asynchronous: you create a prediction, then poll until it completes. The `replicate` Python package handles polling internally via `replicate.run()`.

**Pattern**:
```python
import os
import replicate

REPLICATE_API_TOKEN = os.environ['REPLICATE_API_TOKEN']

# Initialize the client
client = replicate.Client(api_token=REPLICATE_API_TOKEN)


def generate_with_lora(
    model_id: str,
    input_image: str,
    trigger_word: str = '',
    style_prompt: str = '',
) -> str:
    """
    Run LoRA inference on Replicate and return the output image URL.

    Args:
        model_id: Replicate model identifier (e.g., "owner/model-name:version")
        input_image: Base64 data URI of the input photo
        trigger_word: The LoRA trigger word for the personal model
        style_prompt: Default style prompt to apply

    Returns:
        URL of the generated image on Replicate's CDN
    """
    # Build the prompt
    prompt_parts = []
    if trigger_word:
        prompt_parts.append(f"a photo of {trigger_word}")
    if style_prompt:
        prompt_parts.append(style_prompt)
    prompt = ', '.join(prompt_parts) if prompt_parts else 'a professional portrait photo'

    # Run inference (blocks until complete, typically 10-30 seconds)
    output = client.run(
        model_id,
        input={
            'prompt': prompt,
            'image': input_image,
            'num_outputs': 1,
            'guidance_scale': 7.5,
            'num_inference_steps': 30,
        }
    )

    # Replicate returns a list of output URLs
    if isinstance(output, list) and len(output) > 0:
        return str(output[0])
    elif isinstance(output, str):
        return output
    else:
        raise ValueError(f'Unexpected Replicate output format: {type(output)}')
```

**Note on model input schema**: The exact input parameters (`image`, `prompt`, `guidance_scale`, etc.) depend on the LoRA model's base architecture. Flux-based LoRAs have different inputs than SDXL-based ones. Check the specific model's API page on Replicate after training to confirm the parameter names. The pattern above covers the common case — adjust field names to match your trained model's schema.

Install the Replicate package:
```bash
pip install replicate
```

---

### Step 7: Register the Blueprint in app.py

**File**: `backend/app.py`

**Purpose**: Wire the photoshoot Blueprint into the Flask application. This follows the Architecture's pattern where each feature is a Blueprint registered on the app.

**Pattern**:
```python
from routes.photoshoot import photoshoot_bp

app.register_blueprint(photoshoot_bp)
```

Add this alongside the existing auth routes from Task 2. The full `app.py` should now have:
```python
import os
from flask import Flask
from flask_cors import CORS
from middleware.auth import close_db
from routes.photoshoot import photoshoot_bp

app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:8100',
    'http://localhost:4200',
    os.environ.get('WEB_ORIGIN', 'https://your-domain.com'),
])
app.teardown_appcontext(close_db)

# Auth routes (from Task 2)
# ... @app.route('/api/auth/me') ...

# Feature blueprints
app.register_blueprint(photoshoot_bp)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
```

Required environment variables (add to existing ones from Task 2):
```bash
export REPLICATE_API_TOKEN="r8_your_replicate_token"
```

---

### Step 8: Add a test LoRA model for local development

**File**: `backend/seed_test_model.sql`

**Purpose**: Insert a test LoRA model mapping so `/generate` has a model to resolve during development. Use one of the existing Trendfy LoRA models or a public model on Replicate.

**Pattern**:
```sql
-- Insert a test lora_model for the seed user
-- Replace the user_id with the UUID of the seeded test user from Task 2
-- Replace the replicate_model_id with a real trained model or a public one for testing

INSERT INTO lora_models (user_id, replicate_model_id, trigger_word, default_style_prompt)
VALUES (
    (SELECT id FROM users WHERE email = 'tester1@example.com'),
    'owner/model-name:version_hash',   -- Your trained LoRA model on Replicate
    'TOK',                              -- The trigger word used during training
    'professional studio portrait, cinematic lighting, 8k'
)
ON CONFLICT DO NOTHING;
```

For development without a real LoRA model, use a public Flux or SDXL model on Replicate and skip the trigger word. The pipeline works the same — only the output quality differs.

---

### Step 9: Handle the original image URL problem

**Purpose**: The current implementation stores the base64 data URI as the `original_image_url`. This works but makes the gallery load slowly if the original images are large. A practical improvement for Month 1: store a smaller thumbnail.

**File**: `backend/routes/photoshoot.py` (modify the generate endpoint)

Add a thumbnail step before persisting:

```python
import io
from PIL import Image

def make_thumbnail(photo_bytes: bytes, max_size: int = 400) -> str:
    """Create a smaller base64 thumbnail for gallery display."""
    img = Image.open(io.BytesIO(photo_bytes))
    img.thumbnail((max_size, max_size))
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=70)
    thumb_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/jpeg;base64,{thumb_b64}"
```

Use `make_thumbnail(photo_bytes)` as the `original_image_url` stored in the database instead of the full-resolution data URI. The full-resolution image is sent to Replicate for inference but doesn't need to persist.

Install Pillow:
```bash
pip install Pillow
```

This is optional but recommended — it keeps the `generations` table small and the gallery fast.

---

## Verification

### Backend verification:

```bash
# Start Flask
cd backend
export REPLICATE_API_TOKEN="r8_..."
export SUPABASE_JWT_SECRET="..."
export NEON_CONNECTION_STRING="postgresql://..."
flask run --port 5000

# Seed a test user and model (after Task 2 schema + seed)
psql "$NEON_CONNECTION_STRING" -f seed_test_model.sql

# Test with a real JWT (grab from browser devtools after login)
TOKEN="eyJ..."

# Test generate endpoint
curl -X POST http://localhost:5000/api/photoshoot/generate \
  -H "Authorization: Bearer $TOKEN" \
  -F "photo=@test_selfie.jpg"

# Expected: {"id": "...", "result_image_url": "https://replicate.delivery/...", ...}

# Test history endpoint
curl http://localhost:5000/api/photoshoot/history \
  -H "Authorization: Bearer $TOKEN"

# Expected: [{"id": "...", "result_image_url": "...", "created_at": "..."}]
```

### Frontend verification:

```bash
# Start Angular
ionic serve
```

**Test sequence**:
1. Navigate to `/photoshoot` tab
2. Tap "Take Photo" — on web, file picker opens; on iOS, camera opens
3. Select/capture a photo — preview appears with "Generating..." spinner
4. Wait 10–30 seconds — result appears as before/after comparison
5. Tap "Take Another" — returns to capture view
6. Switch to history tab (clock icon) — previous generation appears in the list
7. Generate a second photo — history shows both, most recent first

### Error cases to verify:

- Upload without auth → 401
- Upload with auth but without `photoshoot` in `enabled_features` → 403
- Upload for user with no LoRA model → 404 with "No personal model found"
- Cancel camera capture → returns to capture view, no error

**Expected Result**: A user can take or pick a photo, see it processed by their personal LoRA model in under 60 seconds, view the before/after result, and browse past generations in the gallery.

---

## Integration Notes

### With Task 2 (Auth)

The photoshoot flow depends on Task 2's auth middleware. If building in parallel:
- Frontend: stub `AuthService.getSession()` to return a hardcoded JWT for local testing
- Backend: temporarily skip `@require_auth` decorator and set `g.user` manually in the endpoint

At integration, remove the stubs and verify the full flow: login → navigate to /photoshoot → capture → generate → result.

### With Task 5 (LoRA models)

Task 5 trains 15 personal models and inserts `lora_models` rows. The contract is:
- `lora_models.user_id` matches `users.id` 
- `lora_models.replicate_model_id` is a valid Replicate model identifier (`owner/model:version`)
- `lora_models.trigger_word` is the token used during training (typically `TOK` or a unique string)

Task 3's code doesn't need to change when Task 5 populates the models — the query in the generate endpoint resolves whatever model is mapped to the user.

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 3 done
2. Integration test with Task 2: full auth → photoshoot flow end-to-end
3. Proceed to Task 4 (Deploy) — the `/photoshoot` Blueprint and its dependencies (`replicate`, `Pillow`) need to be in the Docker image
4. Proceed to Task 5 (LoRA models) — the inference endpoint is now ready to consume pre-trained models

---

## Related Documents

- [Solution Architecture](./architecture.md) – /photoshoot Feature component design, Capture-Normalize-Infer pipeline, Pre-seeded Personalization pattern, Replicate latency risk mitigation
- [Epic](./epic.md) – Task 3 scope, success criterion ("/photoshoot captures or accepts a photo and returns a LoRA-styled result within 60 seconds")
- [Timeline](./timeline.md) – Status tracking
- [Task 1: Shell scaffold](./task-1-shell-scaffold-navigation.md) – Foundation this task builds on (route registry, placeholder page)
- [Task 2: Auth + user model](./task-2-auth-user-model-feature-gating.md) – Auth middleware this task's Blueprint sits behind