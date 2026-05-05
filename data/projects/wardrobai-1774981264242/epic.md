# 🎯 Epic: WardrobAI

**Purpose**: Capability-definition document.

**Source**: Addresses issues in [Analysis](./analysis.md).

**Status**: Tracked in [Timeline](./timeline.md).

---

## Business Value

WardrobAI addresses a real friction point: people own clothes they forget about, struggle to style, or never combine creatively. The "what should I wear?" decision happens daily, yet existing solutions are either manual (Pinterest boards, spreadsheets) or require expensive professional stylists. An AI-powered digital closet that understands your actual wardrobe and shows you wearing combinations removes this friction entirely.

The market signal is strong. Photo AI and Interior AI proved that Stable Diffusion-based personalization sells—users pay for seeing themselves in new contexts. Fashion is a natural extension: the same technology applied to clothing generates higher engagement (daily use case) and clearer monetization (outfit suggestions, affiliate links, premium try-on features).

**Value Proposition**: Upload your clothes, see yourself wearing any combination—no more "I have nothing to wear."

---

## Scope

### What This Epic Covers

- **Photo-to-closet ingestion** – Upload outfit photos, AI detects and extracts individual garments
- **Digital closet management** – Grid view of all items with automatic tagging (type, color, style)
- **Virtual try-on** – Select items and generate a photorealistic image of yourself wearing the combination
- **Basic outfit saving** – Save and name favorite combinations for quick reference

### What This Epic Does NOT Cover

- ❌ **Shopping recommendations / affiliate integration** — Post-MVP monetization feature
- ❌ **Social sharing / community features** — Requires user base first
- ❌ **Calendar integration / weather-based suggestions** — Nice-to-have, not core loop
- ❌ **Multi-person households** — Single-user MVP validates the core concept

---

## Tasks

> **Note**: Status tracked in [Timeline](./timeline.md). This table shows Priority only.

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Garment detection pipeline** | None | — | 3 days | High |
| 2 | **Digital closet UI** | 1 | 3 | 2 days | High |
| 3 | **Reference photo capture** | None | 2 | 1 day | High |
| 4 | **Virtual try-on integration** | 1, 3 | — | 4 days | High |
| 5 | **Outfit saving and recall** | 2, 4 | — | 1 day | High |

### Task 1: Garment Detection Pipeline

Build the ingestion system that takes an outfit photo and outputs individual garment images with metadata. This includes clothing segmentation (separating shirt from pants from shoes), background removal, and automatic tagging (type: "jacket", color: "navy", style: "casual"). This is the foundation—everything else depends on having clean, tagged garment data.

### Task 2: Digital Closet UI

Create the closet grid interface where users see all their extracted garments. Includes filtering by type/color/style, drag-and-drop organization, and the selection mechanism for choosing items to try on. Should feel like browsing a well-organized physical closet.

### Task 3: Reference Photo Capture

Implement the flow for users to provide their "body reference" photo—a full-body shot used as the base for all try-on generations. Includes guidance for optimal photo quality, storage, and the ability to update/change reference photos. This is the "you" that garments get applied to.

### Task 4: Virtual Try-On Integration

Wire up the VTON model (OOTDiffusion for permissive licensing, or CatVTON for quality) to generate images of the user wearing selected garments. User selects 1-3 items from closet → system composites them onto reference photo → outputs photorealistic result. This is the magic moment.

### Task 5: Outfit Saving and Recall

Allow users to save generated try-on results as named outfits. Simple gallery view of saved combinations with ability to regenerate or modify. Closes the loop—users build a library of "looks" they can reference when getting dressed.

---

## Success Criteria

This epic is complete when:

- ✅ User can upload 5 outfit photos and see 10+ individual garments appear in their closet (correctly segmented and tagged)
- ✅ User can select 2-3 garments and generate a try-on image in under 60 seconds
- ✅ Generated try-on images are photorealistic enough that users share them (qualitative validation)
- ✅ User can save and retrieve at least 10 outfit combinations
- ✅ End-to-end flow works on mobile web (where outfit photos live)

---

## Non-Goals

- ❌ **Perfect garment detection** — 80% accuracy is fine for MVP; users can manually correct
- ❌ **Real-time try-on** — 30-60 second generation is acceptable; optimization comes later
- ❌ **Supporting all garment types** — Focus on tops, bottoms, outerwear, shoes; accessories later
- ❌ **Commercial model licensing** — Use OOTDiffusion (Apache 2.0) or accept non-commercial for validation phase

---

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Architecture](./architecture.md) – System design and VTON model selection
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview