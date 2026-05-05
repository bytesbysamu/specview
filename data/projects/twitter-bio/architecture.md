---
sidebar_position: 3
---

# 🏗️ Twitter/X Account Setup – Solution Architecture

**Purpose**: Technical design for the Twitter/X profile assets — content structure, image specifications, and thread composition.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This is a content architecture, not a software architecture. The "system" is a set of coordinated assets (bio, header, thread) that work together as a landing page. The design challenge is information density: conveying methodology, credibility, and follow-motivation within Twitter's rigid format constraints (160-char bio, 1500×500px header, 280-char tweets). Each asset has one job and must not duplicate what the others cover.

The profile functions as a funnel with three layers:
1. **Header + Bio** (0-3 seconds): Visual identity + one-line value prop. Answers "what is this?"
2. **Pinned Thread** (10-60 seconds): Proof + methodology. Answers "why should I care?"
3. **THE Post link** (2-10 minutes): Full deep dive. Answers "how does this actually work?"

Each layer exists to pull the reader into the next. No asset should try to do the job of the layer below it.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Builder, not brand | Profile represents a person building in public, not a product. Real name, real photo, first-person voice. Technical audience follows people who ship, not marketing accounts. |
| Show the system, don't describe it | The header image shows a deviation trend graph — a visual artifact of the methodology. The pinned thread shows real numbers (24 commits, 20 minutes, 0-4 deviations). Evidence over claims. |
| Each asset has ONE job | Bio = identity + hook. Header = visual signature. Thread = proof + link. No duplication across assets. |
| Mobile-first | 80%+ of Twitter consumption is mobile. Header center-crop, bio line breaks, thread readability — all optimized for phone screens first. |
| Cold-start credibility | With zero followers, credibility comes from specificity. Vague claims ("I build AI tools") are invisible. Specific claims ("4 agents ship 24 commits in 20 minutes") are magnetic. |

---

## Component Design

### Task 1: Identity Package

**Purpose**: Establish the human identity behind the account.

**Components**:
- **Handle**: Short, memorable, available. Format: `@firstname_lastname` or `@firstnamelastname`. Check availability on Twitter. Avoid product names in the handle — the account outlives any single product.
- **Display name**: Real first and last name. No titles, no emojis, no "| building X" suffixes. Clean and professional.
- **Profile photo**: Real photo, 400×400px minimum. Natural lighting, neutral or blurred background. Face clearly visible. No sunglasses, no group photos, no logos. JPEG or PNG, under 2MB.
- **Location field**: City name or omit. Do not use joke locations ("the cloud", "localhost").

**Patterns**: Consistency across touchpoints — same name and photo used on GitHub, THE post author byline, and any future platform presence.

### Task 2: Bio Composition

**Purpose**: 160-character value proposition that converts profile visitors into followers.

**Components**:
- **Bio text**: Primary asset. Must answer: "What does this person do?" and "Why is that interesting to me?"
- **Website field**: URL to THE post or humaniz.me. Not in the bio text — Twitter renders it separately.

**Structure (recommended)**:
```
[Specific, surprising claim about workflow] + [Building in public signal]
```

**Candidate variations**:
```
A: "I type 3 paragraphs. 4 agents ship 24 commits in 20 minutes. Building in public."
   (91 chars — room for addition)

B: "Braindump → specs → 24 commits in 20 min. Building the methodology that builds the products."
   (93 chars — names the system)

C: "Shipped a SaaS in a week with 3 paragraphs of input. Now building the system that does it. Building in public."
   (112 chars — outcome-first)
```

**Selection criteria**: Which version makes a technical founder who just read THE post think "yes, this is the person I want to follow"? Version A is the most concrete and surprising. Version B names the system. Version C leads with the outcome. Recommend A as the default — specificity wins on Twitter.

### Task 3: Header Image

**Purpose**: Visual anchor that makes the profile visually distinct and signals "this person thinks in systems."

**Components**:
- **Image file**: 1500×500px, PNG or JPEG, under 5MB
- **Safe zone**: Center 600×500px is visible on all devices. Critical content must be within this zone.

**Design specification**:
```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │         DEVIATION TREND GRAPH                    │    │
│  │                                                  │    │
│  │    5 ┤                                           │    │
│  │    4 ┤         ╭─╮                               │    │
│  │    3 ┤    ╭────╯  ╰──╮                           │    │
│  │    2 ┤───╯           ╰────╮                      │    │
│  │    1 ┤                    ╰──────────             │    │
│  │    0 ┤                               ────────    │    │
│  │      └──┬────┬────┬────┬────┬────┬────┬────┬──   │    │
│  │        t1   t2   t3   t4   t5   t6   t7   t8    │    │
│  │                                                  │    │
│  │  ← safe zone (center 600px) →                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Visual treatment**:
- Background: dark (#0d1117 — GitHub dark theme adjacent, familiar to technical audience)
- Graph line: accent color (#58a6ff or similar blue — signals technical, not marketing)
- Axis labels: subtle, light gray (#8b949e), small font
- No title text on the image — the graph is self-explanatory to anyone who read THE post, and intriguing to anyone who hasn't
- Subtle grid lines for depth
- Optional: faint "spec-doc" watermark in bottom-right corner, very low opacity

**Production options**:
1. **Real data**: Export deviation counts from task-2 commits, plot with a charting library (Chart.js, D3, or even a quick Python matplotlib script), screenshot at 1500×500
2. **Designed mockup**: Create in Figma with representative data points showing the downward trend (specs get better → deviations decrease)

Recommend option 1 if real data exists — authenticity matters for building-in-public. Option 2 if the data isn't clean enough to be self-explanatory at a glance.

### Task 4: Pinned Tweet Thread

**Purpose**: The canonical introduction to the methodology, optimized for Twitter's format.

**Components**:
- **Thread**: 5-7 tweets, each under 280 characters
- **Media**: Deviation graph image attached to tweet 4 or 5

**Thread architecture**:

```
Tweet 1 (HOOK — must work standalone as pinned tweet):
"I mass-produced a methodology.
Then I told AI to run it.
24 commits. 20 minutes. 0 judgment calls.

Here's the system ↓"
(138 chars)

Tweet 2 (THE PROBLEM):
"Chat-based AI dev doesn't scale.

You type 'build me X' → GPT writes code → you debug for 2 hours → you type another prompt.

That's not automation. That's autocomplete with extra steps."
(187 chars)

Tweet 3 (THE SYSTEM):
"What if the spec WAS the source code?

Braindump (3 paragraphs)
→ Analysis (problems + constraints)
→ Epic (scope + tasks)  
→ Architecture (design decisions)
→ Implementation guide (step-by-step)
→ AI executor runs it end-to-end"
(233 chars)

Tweet 4 (THE PROOF):
"Real numbers from the last run:

• 3 paragraphs of input
• 5 spec documents generated
• 24 commits shipped
• 4 total deviations (target: 0-3 per commit)
• 20 minutes wall-clock

The deviation count is the quality metric. 10+ = spec was bad. Fix the prompt, not the code."
(270 chars)

Tweet 5 (THE VISUAL):
"This is what spec quality looks like over time ↓

[attach deviation trend graph]

Each data point = one task run. 
Downward trend = the methodology is learning."
(158 chars — attach header image or variant)

Tweet 6 (THE LINK):
"I wrote the full breakdown — how the pipeline works, why deviation budgets matter, and what happens when you treat prompts as production code.

[THE post URL]"
(~160 chars + URL)

Tweet 7 (CTA):
"Building this in public.

Next: shipping the editor that makes this accessible to every solo dev.

Follow along → every win, every failure, every deviation."
(154 chars)
```

**Thread rules**:
- No "1/" or "🧵" numbering — let the content pull readers through
- Each tweet must be a complete thought that stands alone in someone's timeline
- First tweet is THE hook — if it doesn't work standalone, the thread fails
- Real numbers over vague claims in every tweet
- One media attachment maximum (tweet 5)

### Task 5: Account Creation

**Purpose**: Assemble all assets into a live Twitter/X account.

**Components**:
- Twitter/X account registration
- Profile settings configuration

**Checklist**:
- [ ] Register with preferred handle
- [ ] Set display name (real name)
- [ ] Upload profile photo (400×400px)
- [ ] Upload header image (1500×500px)
- [ ] Set bio text
- [ ] Set website URL
- [ ] Set location (optional)
- [ ] Post thread (all tweets in sequence)
- [ ] Pin first tweet
- [ ] Verify all links work

### Task 6: Funnel Verification

**Purpose**: Walk the full reader journey and fix any broken links or rendering issues.

**Test matrix**:

| Check | Mobile | Desktop |
|-------|--------|---------|
| Header image legible | ☐ | ☐ |
| Bio renders without awkward line breaks | ☐ | ☐ |
| Website link clickable | ☐ | ☐ |
| Pinned thread readable | ☐ | ☐ |
| THE post link in thread works | ☐ | ☐ |
| Profile photo not cropped awkwardly | ☐ | ☐ |
| Thread doesn't break on retweet/quote | ☐ | ☐ |

---

## Execution Flow

```
[Phase 1 — Parallel Prep]
   Task 1 (identity) ──→ ─┐
   Task 3 (header)   ──→ ─┤
   Task 4 (thread)   ──→ ─┤
   Task 2 (bio)      ──→ ─┤
                           │
[Phase 2 — Assembly]       ▼
   Task 5 (create + publish)
                           │
[Phase 3 — Verify]        ▼
   Task 6 (end-to-end check)
```

All four prep tasks can run in parallel. Assembly requires all four to be complete. Verification requires the account to be live.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Real name vs. handle | Real name as display name, short handle | Technical audience follows builders, not brands. Building-in-public requires personal identity. |
| Real photo vs. AI-generated | Real photo | AI-generated photo contradicts the authenticity of building-in-public. Technical audience would notice and it undermines trust. |
| Dashboard vs. deviation graph for header | Deviation trend graph | Dashboard is generic — every SaaS has one. Deviation graph is unique to spec-doc methodology and creates curiosity ("what's a deviation?") that drives readers to THE post. |
| Thread length | 5-7 tweets | Under 5 doesn't have room for proof. Over 7 loses readers. 5-7 is the sweet spot for a "system explainer" thread format. |
| Tweet numbering | No numbering | "1/7" signals "this will take a while" before the reader is hooked. Let content pull, don't announce thread length. |
| Bio style | Specific numbers over vague claims | "4 agents ship 24 commits" is memorable and surprising. "I build AI-powered dev tools" is invisible. Specificity is the differentiator on a platform full of generic bios. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

