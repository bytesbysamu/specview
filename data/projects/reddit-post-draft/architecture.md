---
sidebar_position: 3
---

# 🏗️ Reddit Launch Post – Solution Architecture

**Purpose**: Technical design for content creation, recording, and distribution of the r/ChatGPT launch post.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This is a content capability, not a software capability. The "system" is a pipeline of artifacts — post copy, screen recording script, comment templates, and a publish checklist — that produce a single high-conversion Reddit post. The architecture defines the structure of each artifact, the dependencies between them, and the quality gates that prevent publishing a half-baked post.

The pipeline has two phases: **Content Creation** (Tasks 1–3, parallelizable) and **Distribution Prep** (Tasks 4–5, sequential after content is locked). Content creation produces the raw materials. Distribution prep packages them into a publish-ready bundle with timing, fallback, and engagement plans.

The key architectural decision is separating the screen recording script from the actual recording. The script is a spec — it defines every second of the 30-second video. The recording is an execution step that happens after the script is approved. This separation means the script can be reviewed, revised, and locked before anyone picks up a phone.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Show, don't tell | The before/after text and screen recording do the selling. The post copy just frames them. No feature lists, no bullet points about "AI-powered rewriting." |
| Builder tone, not founder tone | "I built this because I had this problem" — not "We're excited to announce." First person singular. No team references (it's a solo build). No roadmap promises beyond what's live. |
| Reddit-native format | No embedded images (Reddit compresses them). Screen recording as a natively uploaded video, not a YouTube link. Text formatted with Reddit markdown, not fancy formatting. |
| One scroll-stopper per post | The before/after text is the hook. The screen recording is the proof. The TestFlight link is the CTA. Three elements, one job each. Don't dilute with feature lists or screenshots. |
| Authentic imperfection | A slightly rough screen recording (real typing speed, real processing time) outperforms a polished demo. The audience is technical — they'll spot and distrust anything that looks rehearsed. |

---

## Component Design

### Task 1: Reddit Post Copy

**Purpose**: Produce the title and body text that will be submitted to r/ChatGPT.

**Components**:
- `post-title.md` — 3 title candidates with character counts. Each follows the pattern: "I [action] and [result]. [Availability]." Final selection marked.
- `post-body.md` — The full post body in Reddit markdown. 200–280 words. Includes the embedded before/after text block.
- `before-after-candidates.md` — 3 before/after text pairs (email, essay, social post). Each pair includes: the original ChatGPT output, the humanized version, and a one-line note on why the contrast works or doesn't.

**Patterns**:
- Before/after text uses Reddit's blockquote formatting (`>`) for the "before" and plain text for the "after" — visual contrast without needing images
- Title candidates are scored against: specificity (does it say what the app does?), curiosity (does it make you want to click?), authenticity (does it sound like a person, not a brand?)

**Quality gate**: The selected before/after pair must pass the "blind test" — if you showed someone just the "after" text with no context, they would not guess it was AI-generated.

### Task 2: Screen Recording Script

**Purpose**: Produce a second-by-second script that can be executed in a single take on an iPhone.

**Components**:
- `recording-script.md` — Timestamped script (0s–30s) with exact actions, exact words to speak, and expected on-screen results at each timestamp.
- `recording-checklist.md` — Pre-recording setup steps: DND, battery, Wi-Fi, app state, screen brightness, font size, status bar cleanup.

**Patterns**:
- Script follows the "hook in 3 seconds" rule — the first frame shows AI text, the third second shows the microphone being tapped. No title cards, no transitions, no explanatory text overlays.
- The spoken words during voice input are scripted but must sound natural. Write them as you'd actually say them, not as grammatically perfect sentences. Contractions, filler reduction, conversational rhythm.
- Processing time is real — script accounts for 2–4 seconds of Claude API latency. This is a feature, not a bug. The audience sees real performance, builds trust.

**Quality gate**: The script is executable by someone who has never used the app — every tap, every swipe, every word is specified. No "then show the rewrite" without saying exactly what appears and where.

### Task 3: Comment Reply Templates

**Purpose**: Pre-draft replies to predictable questions so OP can engage the thread within minutes, not hours.

**Components**:
- `comment-replies.md` — 8 reply templates, each with: the trigger question pattern, the reply text (50–100 words), and a tone note (technical, casual, or defensive-redirect).

**Patterns**:
- Each reply opens by validating the question ("Good question" or "Yeah, fair point") before answering. Never start with "Actually" or "No."
- Technical questions get technical answers (mention Claude API, streaming, voice processing). Non-technical questions get outcome-focused answers ("it makes your AI text sound like you wrote it").
- Defensive questions ("isn't this just a wrapper?") get reframed, not defended. "Wrapper implies it just forwards to ChatGPT. This is a rewriting engine — different model, different approach, different output."

### Task 4: Publish Strategy

**Purpose**: Determine when, where, and how to publish for maximum early engagement.

**Components**:
- `publish-plan.md` — Day/time recommendation, subreddit rules summary, flair selection, fallback subreddit list with adapted titles for each.

**Patterns**:
- Timing is based on r/ChatGPT traffic patterns: Tuesday or Wednesday, 9–11 AM EST. This is when the subreddit has peak active users and the algorithm is most generous to new posts.
- Fallback strategy is pre-planned, not reactive. If the post is removed within 1 hour or has <5 upvotes after 2 hours, execute the fallback to r/ArtificialIntelligence with an adapted title.

### Task 5: TestFlight Comment + Engagement Plan

**Purpose**: Package the CTA and define the first-hour engagement protocol.

**Components**:
- `testflight-comment.md` — The exact comment text to post within 30 seconds of the main post.
- `engagement-protocol.md` — Minute-by-minute engagement plan for the first 60 minutes after posting. Includes reply priority order, upvote behavior, edit triggers, and escalation thresholds.

**Patterns**:
- The TestFlight comment is posted as a reply to the main post, not as an edit to the body. This keeps the post clean and puts the link where Reddit users expect it ("link in comments").
- The engagement protocol treats the first 60 minutes as a sprint. Every reply within 5 minutes. OP engagement signals to Reddit's algorithm that the thread is active and worth promoting.

---

## Execution Flow

```
[Phase 1 — Content Creation]
   Task 1 (Post Copy) ──────┐
   Task 2 (Recording Script) ┤
                              ▼
[Gate: before/after text locked, script reviewed]
                              │
[Phase 2 — Distribution Prep] │
   Task 3 (Comment Replies) ◄─┘
   Task 4 (Publish Strategy) ◄─┘
              │
              ▼
   Task 5 (TestFlight Comment + Engagement Plan)
              │
              ▼
[Gate: all artifacts reviewed, publish window confirmed]
              │
              ▼
   [EXECUTE: Record → Post → Engage]
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| TestFlight link placement | Comment, not body | r/ChatGPT automod frequently flags posts with external links. Placing the link in a comment avoids removal and follows the subreddit's cultural norm ("link in comments"). |
| Screen recording format | Native Reddit video upload | YouTube links get fewer clicks on Reddit. Native video autoplays in-feed on mobile, which is where most r/ChatGPT traffic comes from. |
| Before/after format | Reddit blockquote vs plain text | No images needed. Blockquote (`>`) visually separates the AI original from the human rewrite. Works on mobile and desktop. No compression artifacts. |
| Post length | 200–280 words | r/ChatGPT data shows posts in this range get the best engagement-to-completion ratio. Under 150 looks low-effort. Over 300 gets skimmed and "tl;dr" commented. |
| One subreddit at a time | r/ChatGPT first, fallbacks later | Cross-posting the same day splits engagement and can trigger Reddit's spam detection. One post, full engagement, then adapt for the next subreddit 3–5 days later. |
| Voice line in recording | Scripted but conversational | Unscripted risks rambling past 30 seconds. Over-scripted sounds rehearsed. The script uses natural phrasing with contractions and a deliberate pause — sounds like thinking out loud, not reading. |
| No title card or intro | Start with the app already open | The first 1.5 seconds determine scroll-stop. A title card wastes them. Opening directly on the AI text with the cursor moving to the mic button is immediately engaging. |
| Light mode for recording | Yes | Reddit's default theme is white. A light-mode app screenshot/recording blends with the feed context, reducing cognitive friction. Dark mode looks like a different universe. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

