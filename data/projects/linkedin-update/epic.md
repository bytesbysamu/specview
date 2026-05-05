---
sidebar_position: 2
---

# 🎯 LinkedIn Profile Rewrite – Epic

**Purpose**: Define scope and tasks for repositioning LinkedIn from Java developer to AI builder.

**Source Analysis**: See [Analysis](./analysis.md) for positioning decisions and constraints resolved.

---

## Business Value

Every LinkedIn profile visit is a conversion event. Right now it converts to "oh, a Java developer" — which is the wrong signal for someone shipping AI SaaS products and building a methodology that generates 18 epics in 42 hours. The rewrite changes what every profile visit converts to: an AI builder with a live product (Humaniz.me), a named methodology (Five-Part Agent / Spec Doc), and a credible arc from enterprise engineering to solo AI product builder.

This matters now because LinkedIn is the professional credibility layer for the audience that matters most — other builders, potential collaborators, and users who want to understand who's behind the product. The current positioning is actively misleading. Every day it stays up is a missed conversion.

The total effort is under 30 minutes of execution. The ROI is permanent — every future profile visit benefits from the rewrite. This is the highest-leverage positioning task available.

---

## Scope

### What This Epic Covers

- LinkedIn headline rewrite (220-char limit, mobile-first)
- LinkedIn about section rewrite (3 paragraphs, CTA)
- Positioning decision: pure indie builder (no employer mention)
- Product mention strategy (Humaniz.me only as proof point)
- CTA strategy (landing page + methodology post link)

### What This Epic Does NOT Cover

- ❌ Experience section rewrite
- ❌ Featured section curation
- ❌ LinkedIn banner/cover image design
- ❌ Content strategy or posting cadence
- ❌ Skills/endorsements cleanup
- ❌ LinkedIn SEO optimization beyond headline keywords

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Draft headline variants** | None | — | 15 min | High |
| 2 | **Write about section arc** | None | 1 | 20 min | High |
| 3 | **Craft CTA block** | 2 | — | 10 min | High |
| 4 | **Review against constraints** | 1, 2, 3 | — | 10 min | Medium |
| 5 | **Publish to LinkedIn** | 4 | — | 5 min | High |

### Task Details

#### Task 1: Draft headline variants

Write 3–5 headline variants that fit the 220-character LinkedIn limit. Each must communicate: AI builder identity, the methodology hook (brain dumps → shipped products), and the named system (Five-Part Agent). Test each against the 120-character mobile truncation point — the core message must survive truncation. Recommended structure: `[Identity] — [Method/Hook] — [Proof]`. Example direction: "AI builder | Brain dump → shipped product in hours | Building the Five-Part Agent". Evaluate which variant front-loads the strongest signal for the target audience (builders and potential users, not recruiters).

#### Task 2: Write about section arc

Three paragraphs, 2,600-character max. Paragraph 1: The arc — 10 years of Java/Angular enterprise engineering, the shift to AI, the realization that methodology matters more than tools. Paragraph 2: What the methodology is — Spec Doc / Five-Part Agent, the numbers (18 epics, 42 hours), what it actually produces (brain dump → specs → code → shipped product). Mention Humaniz.me as the live proof point with revenue context (live in production, $5–25/mo tiers). Paragraph 3: The thesis — same code many products, the moat is positioning not technology, shipping the car not the engine. Keep tone accessible but earned — the numbers do the credibility work, not adjectives.

#### Task 3: Craft CTA block

Final lines of the about section. Two links: (1) Humaniz.me landing page as the live product, (2) the methodology post as the deep-dive. Frame as invitation, not pitch: "See it live" / "Read how it works" energy. Keep under 200 characters so it doesn't get lost in the paragraph above. Consider emoji-free formatting (aligns with builder aesthetic over LinkedIn-bro energy).

#### Task 4: Review against constraints

Check all copy against the constraints from the analysis: headline within 220 chars (test 120-char mobile truncation), about section within 2,600 chars, no employer mention, only Humaniz.me named as product, tone is accessible-with-proof not recruiter-bait. Read the full profile as a stranger would — does the positioning land in 10 seconds? Is the arc clear? Is there a reason to click through?

#### Task 5: Publish to LinkedIn

Copy finalized headline and about section to LinkedIn profile. Verify rendering on both desktop and mobile (LinkedIn mobile app truncates differently). Screenshot before/after for records. Check that links in the about section are clickable (LinkedIn sometimes strips URLs — may need to use the "website" field in the contact info section as backup).

---

## Success Criteria

- ✅ Headline communicates AI builder + methodology in ≤120 characters (mobile-safe)
- ✅ About section tells the complete arc in 3 paragraphs (Java → AI → methodology)
- ✅ Humaniz.me is named as live proof point with revenue context
- ✅ Five-Part Agent / Spec Doc methodology is named and quantified (18 epics, 42 hours)
- ✅ CTA links to landing page and methodology post
- ✅ No employer mention — pure indie builder positioning
- ✅ Total copy passes the "stranger test" — a first-time visitor understands who this person is and why they should care within 10 seconds
- ✅ Published and verified on desktop + mobile

---

## Non-Goals

- ❌ Optimizing for recruiter search / LinkedIn SEO keywords
- ❌ Building a content calendar or posting strategy
- ❌ Redesigning the visual profile (banner, headshot)
- ❌ Rewriting the Experience section or job descriptions
- ❌ A/B testing headline variants over time (might be valuable later, not now)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

