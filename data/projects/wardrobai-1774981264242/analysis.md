# 🔍 Analysis: WardrobAI

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-03-31

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 4 |
| MEDIUM | 4 |

---

## The Core Problem

People own clothes they forget exist. The average person wears 20% of their wardrobe 80% of the time—not because the rest is bad, but because mental recall fails. You stand in front of a full closet feeling like you have "nothing to wear" because you can't visualize combinations you haven't already tried. The creative potential of your existing wardrobe remains locked.

The deeper problem: you can't preview an outfit without physically putting it on. This makes experimentation costly (time, effort, laundry) and most people default to safe, familiar combinations. Fashion inspiration from social media or stores doesn't translate to "what would this look like on *me*, with *my* body, in *my* style?"

Consider: It's like having a kitchen full of ingredients but no ability to taste-test recipes before cooking. You'd stick to the same five meals forever.

---

## Symptoms

Users experience:

- Standing in front of a full closet feeling they have "nothing to wear"
- Buying duplicate items because they forgot what they own
- Wearing the same 10 outfits on rotation despite owning 50+ items
- Inability to visualize how a new purchase would integrate with existing pieces
- Decision paralysis when trying to assemble outfits for specific occasions
- Shopping regret from items that looked good in-store but don't work with their wardrobe
- No memory of which combinations they've already tried and liked/disliked
- Difficulty articulating their personal style to others (stylists, partners, AI)

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No way to see outfit on your body without wearing it | Core user pain; physical try-on is the only current option | Task: Virtual try-on generation |
| Licensing blocks commercial VTON deployment | IDM-VTON and CatVTON are CC BY-NC-SA (non-commercial); only OOTDiffusion is Apache 2.0 | Task: Model selection and licensing review |
| High compute requirements for quality output | IDM-VTON needs 16GB VRAM, 20s per image; scales poorly for consumer product | Task: Infrastructure architecture |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Accurate clothing detection from photos is non-trivial | Must segment, classify, and tag items from varied photo quality and angles | Task: Garment detection pipeline |
| Users don't have clean "flat lay" garment photos | VTON models expect isolated garment images; users have outfit photos | Task: Garment extraction from outfit photos |
| Body/pose consistency across generations | Diffusion models can drift; user needs to recognize themselves | Task: Identity preservation system |
| No standard format for digital wardrobe data | No interoperability; user data locked per-app | Task: Closet data model design |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Style tagging is subjective and inconsistent | "Casual" vs "smart casual" vs "business casual" varies by person | Task: Style taxonomy definition |
| Users won't upload every item individually | Friction kills adoption; need batch/automatic capture | Task: Bulk upload and detection flow |
| Outfit history and preferences not tracked | Users can't remember what worked; no learning loop | Task: Outfit logging and rating system |
| Results can look uncanny or obviously AI-generated | Diffusion artifacts break trust; users need believable output | Task: Quality thresholds and regeneration |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Shopping recommendations / affiliate integration | Later phase; core product must work first |
| Social sharing / community features | Different product (social network); focus on personal utility |
| Physical closet organization (IoT hangers, etc.) | Hardware product; out of scope for software MVP |
| Sustainability scoring / ethical fashion | Feature addition after core loop validated |
| Multi-person wardrobe (family/household) | Complexity multiplier; single-user first |
| Weather-based outfit suggestions | Requires location services and external APIs; later enhancement |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview