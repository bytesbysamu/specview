---
sidebar_position: 3
---

# 🏗️ AI Tool Directory Submissions – Solution Architecture

**Purpose**: Technical design for directory submission content, asset pipeline, and traffic attribution.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This capability is primarily a content and process architecture, not a software system. The "components" are content artifacts (descriptions, images, URLs) and the "system" is the submission workflow that ensures consistency across 10 directories. The only technical integration point is UTM tracking on inbound URLs, which requires no code changes to humaniz.me — analytics tools (Plausible, Vercel Analytics, or simple server logs) pick up UTM parameters automatically from the query string.

The architecture ensures: (1) one source of truth for positioning, (2) one asset package reused across all directories, (3) trackable attribution per directory, and (4) a documented playbook for repeating this process with future products in under 1 hour.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | No custom dashboard for tracking directory performance — UTM params + existing analytics is enough |
| Batch over real-time | All 10 submissions drafted offline, then submitted in one session — not iterating per-directory |
| No infrastructure before features | No landing page variants, no A/B framework, no attribution database — query string params and a markdown table |
| One source of truth | Positioning doc locks the one-liner and category; asset package is the single folder everything pulls from |

---

## Component Design

### Task 1: Lock positioning and one-liner

**Purpose**: Eliminate per-directory positioning drift by making one decision upfront.

**Components**:
- `directory-positioning.md` — Canonical one-liner, tagline, category, and rationale. All other tasks reference this file.

**Output format**:
```markdown
# Directory Positioning

## Canonical
- **App Name**: Humaniz.me
- **One-liner** (≤80 chars): Make AI text sound human — Claude-powered, from $5/mo
- **Tagline** (≤140 chars): AI text humanizer with streaming rewrite, 6-tool editor, and 3-pass deep mode. Free tier included.
- **Primary Category**: AI Text Humanizer
- **Fallback Category**: AI Writing Tools
- **Competitor anchor**: StealthGPT ($15/mo) — we lead on price ($5/mo) and model quality (Claude)

## Rationale
[Why this positioning wins across the 10 directories]
```

**Patterns**: Decision record pattern — lock the choice, record the why, reference from downstream tasks.

### Task 2: Create asset package

**Purpose**: Single folder with every asset variant any directory could need.

**Components**:
- `assets/logo-256.png` — Square logo, 256x256
- `assets/logo-512.png` — Square logo, 512x512
- `assets/logo-1024.png` — Square logo, 1024x1024
- `assets/screenshot-editor.png` — Hero screenshot, 1280x800, showing SuperEditor with humanized text
- `assets/screenshot-heavy-mode.png` — Screenshot showing 3-pass Heavy mode before/after
- `assets/descriptions.md` — Three variants: 50-word, 100-word, 200-word

**Description structure** (200-word variant):
```
Paragraph 1: What it does (humanize AI-generated text so it reads as natural human writing)
Paragraph 2: How it works (Claude-powered streaming rewrite, 6-tool SuperEditor, 3-pass Heavy mode)
Paragraph 3: Pricing and differentiation (free tier, $5/mo starter, fraction of competitor pricing)
Paragraph 4: Who it's for (students, content creators, professionals who use AI drafts)
```

**Patterns**: Asset package pattern — build once, reference everywhere. No directory-specific asset variants.

### Task 3: Draft 10 directory submissions

**Purpose**: Complete, copy-paste-ready submission for each directory.

**Components**:
- `submissions/product-hunt.md` — Draft listing + maker comment + first comment
- `submissions/theres-an-ai-for-that.md` — Submission fields mapped
- `submissions/futurepedia.md` — Submission fields mapped
- `submissions/ai-tool-guru.md` — Submission fields mapped
- `submissions/topai-tools.md` — Submission fields mapped
- `submissions/toolify-ai.md` — Submission fields mapped
- `submissions/aitoolslist.md` — Submission fields mapped
- `submissions/saas-ai-tools.md` — Submission fields mapped
- `submissions/uneeq-ai.md` — Submission fields mapped
- `submissions/creatie-ai.md` — Submission fields mapped

**Per-directory template**:
```markdown
# [Directory Name]

## Submission URL
[actual URL to the submit/add-tool page]

## Fields
- **App Name**: Humaniz.me
- **URL**: [UTM-tagged URL from Task 4]
- **One-liner**: [from positioning doc]
- **Category**: [directory's actual category name, mapped from canonical]
- **Description**: [50/100/200 word variant based on directory's length limit]
- **Logo**: [which size from asset package]
- **Screenshots**: [which screenshots]
- **Pricing**: Free / $5 / $12 / $25 per month

## Notes
- Approval process: [instant / review / unknown]
- Editable after submission: [yes / no / unknown]
- [Any directory-specific quirks]
```

**Patterns**: Template pattern — same structure per directory, only the mapping changes.

### Task 4: Add UTM tracking to URLs

**Purpose**: Attribute inbound traffic to specific directories without any code changes.

**Components**:
- `utm-urls.md` — Lookup table of all 10 tagged URLs

**URL format**:
```
https://humaniz.me?utm_source={slug}&utm_medium=directory&utm_campaign=launch-apr-2026
```

**Slug mapping**:
| Directory | Slug |
|-----------|------|
| Product Hunt | `producthunt` |
| There's An AI For That | `theresanaiforthat` |
| Futurepedia | `futurepedia` |
| AI Tool Guru | `aitoolguru` |
| TopAI.tools | `topaitools` |
| Toolify.ai | `toolify` |
| AItoolslist | `aitoolslist` |
| SaaS AI Tools | `saasaitools` |
| Uneeq AI | `uneeqai` |
| Creatie.ai | `creatieai` |

**Technical note**: No backend changes needed. UTM parameters are read by analytics tools (Vercel Analytics, Plausible, Google Analytics) from the query string automatically. If humaniz.me uses client-side routing that strips query params, verify that the analytics script fires before the router cleans the URL.

### Task 5: Submit to 9 directories + PH draft

**Purpose**: Execute all submissions in a single focused session.

**Components**:
- Browser with asset folder open for drag-and-drop uploads
- Submission drafts open side-by-side for copy-paste
- `submission-log.md` — Timestamped record of each submission

**Execution order** (optimized for instant-first):
1. Submit to directories known to be instant-approval first (builds momentum, catches errors early)
2. Submit to review-gated directories second
3. Create Product Hunt draft last (most complex form)

### Task 6: Document directory metadata

**Purpose**: Create reusable reference for future product launches.

**Components**:
- `directory-playbook.md` — Complete reference with per-directory metadata

**Fields per directory**:
```markdown
| Directory | Submitted | Status | Live URL | Monthly Traffic | Editable | Notes |
```

---

## Execution Flow

```
[Phase 1 — Prep]  (Tasks 1 + 4 in parallel)
   Task 1 (positioning) ──→ Task 2 (assets)
   Task 4 (UTM URLs)    ──→ Task 3 (drafts)
                                │
[Phase 2 — Draft]               │
   Task 2 + Task 3 ────────────┤
                                │
[Phase 3 — Ship]                ▼
   Task 5 (submit all) ──→ Task 6 (document)
```

**Total estimated effort**: ~9 hours across 2 sessions (prep + submit).

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Positioning | "AI Text Humanizer" as primary | Matches what the product actually does; "rewriter" is too generic and competes with Quillbot, Wordtune, etc. |
| Product Hunt | Prep only, no launch | PH launches need coordination (timing, upvotes, first-day push). Wasting a PH launch on a quiet day with no prep is worse than not launching at all. |
| UTM tracking | Query params only, no code | Zero engineering effort. Analytics tools read UTMs natively. Adding a tracking table or redirect service is overengineering for 10 directories. |
| Description length | Three variants (50/100/200) | Directories have wildly different length limits. Writing three upfront is cheaper than tailoring on the fly during submission. |
| Submission order | Instant-approval first | Get live listings fast to verify positioning and catch description errors before committing to review-gated directories. |
| Asset sizes | 256/512/1024 PNG | Covers every directory's requirements. SVG would be better but not all directories accept it. |
| Competitor framing | Lead with price, then quality | StealthGPT is $15/mo. Humaniz.me starter is $5/mo. Price is the fastest differentiator in a directory listing where users skim. Claude quality is the second hook for users who click through. |
| No custom landing pages | Same humaniz.me URL for all | Solo founder — maintaining 10 landing page variants is not worth the marginal conversion lift. UTM params give attribution without page proliferation. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

