
```markdown
---
sidebar_position: 3
---

# 🏗️ THE Post — Solution Architecture

**Purpose**: Technical design for content structure, asset pipeline, and conversion flow.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

THE Post is a content artifact with a conversion tail. The architecture has three layers: **content structure** (the narrative arc and how it maps to audience segments), **asset pipeline** (how numbers become verifiable claims and charts), and **conversion flow** (how readers reach the landing page and TestFlight). Each layer is designed so the post works as a standalone distribution event — no follow-up required, no series dependency, no platform lock-in.

The entire pipeline runs on tools already in the stack: git for number extraction, any charting tool for the deviation trend, and the existing landing page + TestFlight infrastructure for conversion. No new infrastructure.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | No blog platform setup. No CMS. Write the post, format it, publish it on one channel. The content is the product |
| Retention is the only metric | Success is not impressions or likes. It's whether someone clicks through to the landing page and installs the TestFlight. Track that one funnel |
| Analysis is a filter, not an audit | The analysis doc killed scope early: no multi-channel, no video, no series. The post is self-contained |
| Not-yet-built is the right state for infrastructure nobody's asked for | No analytics dashboard, no content pipeline, no editorial calendar. One post. If it works, build the pipeline for the second one |

---

## Component Design

### Task 1: Extract and verify numbers

**Purpose**: Turn git history into an auditable stats sheet that backs every claim in the post.

**Components**:
- `stats-extraction.sh` (or manual git commands) — queries against the Bubls session branch/timeframe
- Stats sheet (markdown or plain text) — the single source of truth for all numbers

**Method**:
```bash
# Commit count
git log --oneline --after="YYYY-MM-DD" --before="YYYY-MM-DD" | wc -l

# Lines added/removed
git diff --stat {start-sha}..{end-sha}

# Test count
grep -r "it(" --include="*.spec.ts" | wc -l
# or run the test suite and capture the summary line

# Deviation count per commit
git log --grep="Deviations:" --format="%h %s" --after="YYYY-MM-DD"
```

**Patterns**: Every number in the post gets a footnote-style comment in the draft linking to the command that produced it. If a number can't be reproduced, it doesn't go in the post.

### Task 2: Lock pattern name and channel

**Purpose**: Two irreversible decisions that shape everything downstream.

**Pattern Name Candidates**:

| Candidate | Pros | Cons |
|-----------|------|------|
| Five-Part Agent | Descriptive, enumerates the parts | Generic, "five-part" is forgettable |
| Spec-Driven Agent | Captures the key insight (specs, not chat) | Sounds academic |
| Brain Dump Pipeline | Captures the user experience (dump → ship) | Undersells the sophistication |
| The Constellation Pattern | Ties to existing repo name | Requires explanation |
| Document-First Agent | Mirrors "Spec Doc" philosophy | "Document" is bland |

**Decision criteria**: The name must work as a Twitter headline, a LinkedIn section header, and a concept someone can repeat from memory 24 hours later. Test: "I read this post about ___" — does the blank sound interesting?

**Channel Decision Matrix**:

| Factor | Twitter Thread | LinkedIn Article | Blog Post |
|--------|---------------|-----------------|-----------|
| Reach (AI builders) | High | Medium | Low (no existing blog) |
| Reach (technical founders) | Medium | High | Low |
| Reach (potential users) | Low | Low | Low |
| Format fit (war story) | Constrained but punchy | Natural fit | Best fit |
| Time to publish | 1 hour | 2 hours | 4+ hours (needs hosting) |
| CTA clickthrough | Low (links in threads get buried) | Medium | High (inline) |
| Shareability | High (retweets) | Medium (reshares) | Low (needs distribution) |

**Recommendation**: LinkedIn article. Best balance of audience overlap (technical founders + AI builders both live there), format fit (long-form war story with inline images), and CTA prominence (links are clickable inline, not buried). Twitter thread as a pointer to the LinkedIn article if cross-promotion is added later (out of scope for v1).

### Task 3: Write the post draft

**Purpose**: The actual content artifact.

**Narrative Arc**:

```
HOOK (2-3 sentences)
├── Lead stat: "6 epics, 32 tasks, 102 commits, 9,662 lines, 289 tests. One session."
├── Tension: "Zero regressions."
└── Promise: "Here's exactly how."

CONTEXT (1 paragraph)
├── What Bubls is (2 sentences)
└── Why it matters for this story (1 sentence)

SESSION STORY (3-4 paragraphs)
├── The input: brain dumps, not tickets
├── The pipeline: parallel agents, not serial chat
├── The surprise: deviation count dropping as the system learned
└── The punchline: all 289 tests green, no manual intervention

THE PATTERN (1 paragraph + 5 bullets)
├── Builder Profile — who you are, what you've shipped, your stack
├── Architecture Principles — non-negotiable patterns, injected into every spec
├── Codebase Context — the system reads its own code before writing new code
├── Chain/Pipeline — brain dump → analysis → epic → arch → impl guides
└── Correction Loop — deviation tracking, spec quality improves per run

PROOF (1 paragraph + chart)
├── Deviation trend: epic 1 → epic 6
├── What the numbers mean: fewer deviations = better specs
└── The implication: the pipeline self-improves

CTA (2 sentences)
├── "Try Bubls" + landing page URL with UTM
└── "Join the TestFlight" + TestFlight link
```

**Tone guide**: Direct. Numbers first, feelings second. No "I'm excited to share" — start with the stat. No "As AI continues to evolve" — skip the punditry. The reader should feel like they're reading a field report, not a blog post.

**Word count target**: 1,200–1,500 words. Long enough to tell the story, short enough that no one bounces.

### Task 4: Prepare visual assets

**Purpose**: Charts and diagrams that make the numbers land.

**Asset 1 — Deviation Trend Chart**:
- Type: Line chart or bar chart
- X-axis: Epic number (1–6)
- Y-axis: Average deviations per commit
- Data source: Task 1 stats extraction
- Style: Dark background, minimal gridlines, Bubls brand colors if available
- Tool: Any — even a screenshot of a spreadsheet chart is fine. No custom charting infrastructure

**Asset 2 — Pipeline Flow Diagram**:
- Type: Horizontal flow diagram
- Stages: Brain Dump → Spec Generator → [Analysis | Epic | Architecture | Impl Guides] → Parallel Executors → Commits → Test Suite
- Highlight: the parallel fan-out in the middle (multiple agents running simultaneously)
- Tool: Excalidraw, Figma, or even ASCII art rendered as an image

**Asset 3 (optional) — Terminal Screenshot**:
- The test suite summary showing 289 passing tests
- Or the git log showing the density of commits in the session timeframe

### Task 5: Verify conversion tail

**Purpose**: Ensure the CTA doesn't dead-end.

**Checks**:
1. Landing page URL resolves (200 status)
2. Landing page has visible CTA (signup / download / TestFlight)
3. TestFlight link resolves and accepts new testers (not at capacity)
4. UTM parameters don't break the page: `?utm_source=linkedin&utm_medium=organic&utm_campaign=the-post`
5. Mobile rendering — many LinkedIn readers are on phones

### Task 6: Format, proof, and publish

**Purpose**: Ship it.

**LinkedIn-specific formatting** (recommended channel):
- Headline: pattern name + hook stat. Example: "I shipped 9,662 lines and 289 tests in one session. Here's the pattern."
- No hashtags in the first two lines (LinkedIn buries hashtag-heavy posts)
- Max 2 hashtags at the bottom: `#AIEngineering` `#BuildInPublic`
- Images inline at the relevant section, not all at the bottom
- First 3 lines visible in the feed preview — make them count
- Link to landing page ONCE, near the end (LinkedIn penalizes link-heavy posts)

---

## Execution Flow

```
[Phase 1 — Parallel]
   Task 1 (extract numbers) ──┐
   Task 2 (lock name/channel) ─┤
   Task 5 (verify CTA)  ──────┘
                                │
[Phase 2 — Sequential]         ▼
   Task 3 (write draft)  ──→ Task 4 (visual assets, can overlap with draft)
                                │
[Phase 3 — Ship]               ▼
   Task 6 (format + publish)
```

Total estimated wall-clock: 8–10 hours across 1–2 days.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Single channel, not multi | LinkedIn article | Best audience overlap for the three targets. Cross-posting is scope creep. If it works, repurpose later |
| Numbers-first narrative | Hook with stats, not with "I built an app" | War story credibility comes from specificity. Lead with the receipts |
| No custom blog | Publish on LinkedIn directly | "Ship the car, not the engine." Building a blog is infrastructure before users. LinkedIn has the audience already |
| Deviation trend as the proof | Chart showing 6.0 → 2.0 | This is the non-obvious insight: the pipeline self-improves. Everything else (line count, commit count) is impressive but static. The trend is the argument |
| UTM params on CTA | `utm_source=linkedin&utm_campaign=the-post` | Minimum viable attribution. Know if the post drove any landing page traffic. No analytics platform needed — server logs or Coolify analytics suffice |
| No A/B testing | One headline, one format, ship | Time-sensitive content. Testing delays publishing. The post's value decays daily |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)
```

