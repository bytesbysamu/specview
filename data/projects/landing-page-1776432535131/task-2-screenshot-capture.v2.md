The implementation guide is ready to write. Here's what it covers:

| Section | Key Content |
|---------|-------------|
| **Context** | 750px WebP+PNG from native iPhone screenshots; Task 4 consumes via `<picture>` |
| **Trade-offs** | Device frames (deferred), multi-resolution srcset (rejected), WebP+PNG fallback (chosen) |
| **Steps** | 7 steps: create dirs → capture on iPhone [MANUAL] → export to project → write `convert.sh` → run conversion → record dimensions → update timeline |
| **Tests** | 6 bash verification checks: file existence, 750px width, WebP < PNG size, minimum file size, raw preservation, script syntax |
| **Commits** | 3 commits: conversion script, screenshot assets, timeline update |
| **Deviations** | Handles different iPhone models, HEIC export, missing features, ImageMagick v6/v7 |
| **Out of scope** | Device frames, srcset, OG image, App Store assets, automated capture |

Key design decisions:
- **Raw screenshots preserved** in `assets/raw/` so `convert.sh` can regenerate optimized assets without re-capturing from iPhone
- **Script auto-detects** ImageMagick v6 (`convert`) vs v7 (`magick`)
- **Graceful degradation** — if only 2 of 3 features are ready in TestFlight, ship 2 screenshots and note the deviation

Shall I save the file?

---

##### Post-generation review (auto)

**Overall**: 4/5 (silver)

| Dimension | Score | Key Finding |
|-----------|-------|-------------|
| Structural completeness | 4/5 | No formal 'Related Docs' section — only an inline mention of Task 4 |
| Content routing | 3/5 | VIOLATION: 'Key design decisions' section (raw preservation rationale, WebP+PNG fallback strategy) belongs in Architecture, not the implementation guide |
| Pattern application | 3/5 | No Parallel column in the 7-step table — steps like 'create dirs' and 'record dimensions' may be parallelizable or at least should be explicitly marked sequential |
| Rule compliance | 4/5 | No status words leaked into the spec — clean |
| Content quality | 5/5 | Opinionated: 750px width chosen explicitly, srcset rejected (not deferred), graceful degradation policy for partial feature sets |
| Usefulness | 5/5 | MANUAL step clearly flagged — developer knows what requires human action vs script automation |

**Top fixes**:
- Move design decisions (WebP+PNG strategy, raw preservation rationale, srcset rejection) to Architecture doc; this guide should state the chosen approach and link to Architecture for the 'why'
- Add Parallel column to the 7-step table and restructure trade-offs into a proper Decision Justification Table (Option | Pros | Cons | Verdict)
- Add bidirectional cross-references: this guide → Task 4 spec AND Task 4 spec → this guide; include parent epic/task ID in the summary header
