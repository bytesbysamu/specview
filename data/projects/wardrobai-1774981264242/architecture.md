# 🏗️ Architecture: WardrobAI

**Purpose**: Long-lived system design document for the AI wardrobe application.

**References**: Addresses [Analysis](./analysis.md). See [Epic](./epic.md) for scope.

---

## Architecture Overview

WardrobAI is fundamentally two systems joined at the hip: a conventional closet management application and an AI-powered virtual try-on engine. The closet management side handles photo uploads, garment detection, tagging, and organization — all well-understood problems with mature solutions. The try-on engine is where the complexity lives: taking a person photo and a garment image, then synthesizing a photorealistic composite.

The key architectural insight is that these two concerns have radically different scaling characteristics. Closet management is stateless, fast, and cheap — standard CRUD with some computer vision for tagging. Virtual try-on is stateful (requires GPU context), slow (15-35 seconds per generation), and expensive (GPU compute costs). This asymmetry shapes every design decision: we optimize for keeping the expensive path as narrow as possible while making the cheap path feel instant.

Our approach treats the try-on capability as a "special occasion" feature rather than the default interaction mode. Users browse and organize in the fast layer, then explicitly invoke try-on when they want to see a combination on their body. This matches user intent (you don't need AI try-on for every outfit check) and keeps infrastructure costs viable for a bootstrapped product.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Separate fast and slow paths | Closet browsing is instant; try-on is explicitly requested and shows progress |
| GPU as a service, not infrastructure | No owned GPUs; use inference APIs that bill per-request |
| Progressive enhancement | Core value (organized closet) works without AI; try-on adds delight |
| Licence-aware from day one | Only Apache 2.0 or similar for commercial features; NC models for R&D only |

---

## System Boundaries

### What This System Includes

- Photo upload and garment detection pipeline
- Digital closet with tagging, filtering, and organization
- Outfit combination builder (drag items together)
- Virtual try-on generation for selected combinations
- User accounts and closet persistence

### What This System Does NOT Include

| Excluded | Reason |
|----------|--------|
| Real-time video try-on | Requires streaming GPU inference; prohibitively expensive at scale |
| Social/sharing features | Adds complexity without validating core value proposition first |
| E-commerce integration | Premature optimization; focus on owned-wardrobe use case first |
| Custom model fine-tuning per user | Photo AI approach (personal LoRA) is powerful but operationally complex |

---

## Component Design

### Closet Management Layer

**Purpose**: Handle all non-AI interactions — upload, organize, browse.

**Key Parts**:
- `UploadService` — Accepts photos, normalizes dimensions, stores originals
- `GarmentDetector` — Uses lightweight vision model to identify and crop individual items
- `ClosetRepository` — Persists garments with metadata (type, color, tags, source photo)
- `OutfitBuilder` — Combines garments into outfit proposals without AI rendering

**Patterns**: Standard MVC with repository pattern. Stateless services behind REST endpoints. All operations complete in <500ms.

### Try-On Engine

**Purpose**: Generate photorealistic images of the user wearing selected garments.

**Key Parts**:
- `TryOnOrchestrator` — Coordinates the multi-step generation flow
- `BodyPoseExtractor` — Extracts pose and mask from user reference photo
- `GarmentConditioner` — Prepares garment images for model input
- `InferenceClient` — Calls external GPU inference API (Replicate, Modal, or similar)
- `ResultCache` — Stores generated images to avoid re-computation for same inputs

**Patterns**: Command pattern for try-on requests. Async job queue for long-running generations. Idempotent requests keyed by (user_photo_hash, garment_hashes) tuple.

### Reference Photo System

**Purpose**: Manage the "base" photos of the user that try-on composites onto.

**Key Parts**:
- `ReferencePhotoService` — Upload and validate reference photos
- `PoseAnalyzer` — Extracts body pose, dimensions, and segmentation mask
- `ReferenceStore` — Persists preprocessed reference data for fast try-on

**Patterns**: Preprocessing happens at upload time, not generation time. This moves latency from the critical path (try-on request) to a one-time setup step.

---

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | React Native or Flutter | Cross-platform mobile; wardrobe is phone-first |
| Backend | Node.js or Python FastAPI | Python preferred for ML ecosystem compatibility |
| Data | PostgreSQL + S3-compatible storage | Relational for metadata, object storage for images |
| AI - Detection | YOLO or similar lightweight model | Fast, runs on CPU, handles garment segmentation |
| AI - Try-On | OOTDiffusion via inference API | Apache 2.0 licence, reasonable quality, API-accessible |
| Inference | Replicate or Modal | Pay-per-request GPU, no infrastructure management |

---

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| OOTDiffusion over IDM-VTON | Apache 2.0 licence allows commercial use | Lower quality than IDM-VTON; may need to upgrade later |
| Inference API over owned GPUs | CapEx-free; scales to zero when idle | Higher per-request cost; dependent on third-party availability |
| Preprocess reference photos | Moves latency out of try-on critical path | Storage cost for pose data; reprocessing needed if models change |
| Single reference photo initially | Simplifies UX; reduces edge cases | Less flexibility in poses; limits outfit contexts |
| No real-time preview | Avoids streaming GPU complexity | Generation feels like "submit and wait" rather than instant |

---

## Patterns

### Optimistic Closet Updates

**When to use**: Any closet modification (add garment, edit tags, delete item).

**How it works**: Frontend immediately reflects the change while backend persists asynchronously. Conflicts are rare (single-user closets) and resolved by server state winning.

**Example**: User tags a shirt as "casual" — UI updates instantly, background sync confirms within seconds.

### Generation Queue with Polling

**When to use**: Every try-on request.

**How it works**: Client submits request, receives job ID, polls for completion. Server queues job, calls inference API, stores result, marks complete. Polling interval increases over time (1s → 2s → 5s) to reduce load.

**Example**: User selects jacket + pants → sees "Generating..." with progress indicator → polls until image ready → displays result.

### Input Hash Caching

**When to use**: Repeated try-on requests with identical inputs.

**How it works**: Hash the reference photo ID plus sorted garment IDs. Check cache before invoking inference. Cache hit returns stored image immediately.

**Example**: User re-requests an outfit they generated yesterday → instant result from cache, no GPU cost.

---

## Execution Flow

```
[Upload Phase]
  Photo Upload ──→ Garment Detection ──→ Store Items
                         │
[Organization Phase]     ▼
  Browse Closet ──→ Tag/Filter ──→ Build Outfit
                                        │
[Try-On Phase]                          ▼
  Check Cache ──→ Queue Job ──→ Inference API ──→ Store Result
      │                                                │
      └──── (cache hit) ──────────────────────────────→ Display
```

Upload and organization happen independently and quickly. Try-on is the only path that touches GPU inference. Cache checks happen synchronously; cache misses trigger async job processing.

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Inference API goes down | Graceful degradation — closet features work, try-on shows "temporarily unavailable" |
| Costs spike from heavy usage | Per-user daily generation limits; paid tier for unlimited |
| Model quality insufficient | Abstract inference client allows swapping models without architecture change |
| Licence terms change | Document model versions and licences; maintain fallback options |

---

## Future Considerations

These are explicitly NOT in scope for MVP but inform architectural flexibility:

- **Multiple reference photos**: Support different poses/contexts without rearchitecting storage layer
- **Batch generation**: Generate multiple outfits in parallel for "what to wear this week" feature
- **Model upgrades**: IDM-VTON or successors may get permissive licences; inference client abstraction allows swap

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview