# Task 1: Landing Page Copy Review

Retroactive receipt — code shipped before plan written. Deviation: task plan should have been written in parallel with execution per atomic task protocol.

## 1. Context
Audit bubls.app landing page (landing/index.html + style.css) for copy quality, conversion mechanics, trust signals, mobile responsiveness, OG tags, and tracking. Score each area and produce actionable fixes with effort estimates.

## 2. Files
- **Produced**: `/projects/bubls/docs/distribution/landing-review.md`

## 3. Implementation
- Scorecard: 7 areas scored (headline 8/10, CTA 6/10, trust 3/10, mobile 8/10, OG 7/10, speed 9/10, overall 6.8/10).
- 4 critical issues identified: TestFlight PLACEHOLDER links, zero trust signals, competing hero CTAs, relative OG image path.
- 4 copy improvements with before/after rewrites (hero sub-headline, feature 1, feature 3 title, waitlist sub-copy).
- Trust signal addition: HTML snippet for social proof bar using verified session stats (140 commits, 343 tests, 23h).
- Email form endpoint verified (`/api/waitlist/signup`). Missing `waitlist_submit` tracking event flagged.
- Priority table: 7 changes ordered P0-P2 with effort estimates (5min to 20min).

## 4. Tests
Manual review: scores justified with evidence, code snippets reference actual markup, effort estimates realistic.

## 5. Commits
Content authored in a single pass. Shipped as part of the distribution content batch.

## 6. Verification
All issues traceable to specific HTML/CSS. Copy improvements show concrete before/after diffs. Priority ordering actionable.

## 7. Rollback
Revert the content file. Landing page itself is unchanged by this review doc.

## 8. Deviations
- Task plan written retroactively (protocol requires parallel authoring).
- Review only; no code changes applied to landing page yet.

## 9. Out of Scope
Applying the recommended changes to landing/index.html, redesign work, A/B testing setup.

## 10. Related
- Source: `/projects/bubls/docs/distribution/landing-review.md`
- Target: `landing/index.html`, `landing/style.css`
