---
sidebar_position: 2
---

# 🎯 The Post Thread – Epic

**Purpose**: Define scope and tasks for drafting and publishing the Five-Part Agent Twitter/X thread.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

The Five-Part Agent pattern is unnamed in the wild. Technical founders on Twitter are actively sharing agent orchestration workflows, but nobody has named the braindump-to-shipped-product loop with hard numbers behind it. This thread stakes the claim.

The numbers are the hook: 175 commits, 18 epics, 42 hours. Those numbers are real, verifiable, and impressive — but they decay. A week from now, the commit count is higher and the story is muddier. The thread needs to ship while the numbers are clean and the timeline is tight enough to be visceral.

The value is threefold: (1) name the pattern before someone else does, (2) drive traffic to the landing page and TestFlight, (3) establish credibility in the agent-orchestration conversation that's happening right now on technical Twitter. This isn't a growth hack — it's planting a flag.

---

## Scope

### What This Epic Covers

- Drafting a 10-tweet thread with hook → arc → pattern → proof → CTA structure
- Crystallizing the pattern name (Five-Part Agent or final alternative)
- Anchoring every claim to verifiable numbers from the fact sheet
- One editing pass for tone (war story, not tutorial)
- CTA design pointing to landing page + TestFlight
- LinkedIn cross-post reformatting

### What This Epic Does NOT Cover

- ❌ Building or updating the landing page
- ❌ Recording demo videos or screenshots
- ❌ Follow-up threads or content calendar
- ❌ Paid promotion or ad copy
- ❌ Community engagement strategy (replies, quote tweets)
- ❌ Analytics setup or tracking

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Extract proof points from fact sheet** | None | — | 30 min | High |
| 2 | **Crystallize pattern name** | 1 | — | 30 min | High |
| 3 | **Draft 10-tweet thread** | 1, 2 | — | 2 hrs | High |
| 4 | **CTA + proof anchoring pass** | 3 | 5 | 30 min | High |
| 5 | **Tone + compression edit** | 3 | 4 | 30 min | Medium |
| 6 | **LinkedIn cross-post reformat** | 4, 5 | — | 30 min | Low |

### Task Details

#### Task 1: Extract proof points from fact sheet
Read `docs/the-post-numbers.md` and pull every hard number into a reference list: commits, epics, hours, tasks generated, lines of spec, products shipped, failure count. Tag each number with which tweet slot it belongs in (hook, arc, proof). This is the raw material — nothing gets drafted without a number to back it.

#### Task 2: Crystallize pattern name
Evaluate "Five-Part Agent" against alternatives. The name must pass three tests: (1) a technical founder hears it and wants to know what the five parts are, (2) it's not already claimed by another framework or blog post, (3) it fits in a tweet without explanation. If Five-Part Agent passes all three, ship it. If not, the alternatives are: "Spec-to-Ship Loop", "The Five-Part Loop", "Document-First Agent". Pick one. Write a one-line definition that fits in a single tweet.

#### Task 3: Draft 10-tweet thread
Write all 10 tweets following this arc structure:
- **Tweet 1 (Hook)**: The numbers. 175 commits, 18 epics, 42 hours. One human. Zero lines typed by hand. Something like that — lead with the thing that makes someone stop scrolling.
- **Tweet 2-3 (Failure arc)**: 18 failed projects. What went wrong. The pattern of failure — not the individual projects, but the shape of the failure. Why chat-based AI dev doesn't scale.
- **Tweet 4-5 (System arc)**: What changed. The shift from chatting to specifying. Braindump → specs → code. The moment it clicked.
- **Tweet 6-7 (Pattern)**: Name the Five-Part Agent. Define the five parts. Each part in one line. This is the payload of the thread.
- **Tweet 8-9 (Proof)**: Show receipts. Specific products shipped. Time from braindump to TestFlight. Commit logs. The stuff that makes it real.
- **Tweet 10 (CTA)**: Landing page link. TestFlight mention. One sentence on what they can do right now.

#### Task 4: CTA + proof anchoring pass
Review every tweet for unsupported claims. If a tweet says "ships anything" — does the thread show at least two different products shipped? If it says "42 hours" — is that number in the fact sheet? Replace any soft language ("we built something powerful") with hard language backed by a specific number. Finalize the CTA tweet: primary action is landing page, secondary is TestFlight.

#### Task 5: Tone + compression edit
Read the full thread aloud (mentally). Cut anything that sounds like a tutorial ("here's how you can..."), a product launch ("we're excited to announce..."), or a LinkedIn post ("I'm humbled to share..."). The voice is: founder talking to founders in a bar, showing receipts. Every tweet should feel like it was written by someone who just finished a 42-hour sprint, not someone who's marketing. Compress any tweet over 280 characters. Ensure the thread reads as one continuous story, not 10 disconnected observations.

#### Task 6: LinkedIn cross-post reformat
Take the final thread and reformat for LinkedIn's single-post format. Collapse the 10 tweets into a single post with line breaks. Remove Twitter-specific formatting (thread numbers, "🧵" emoji). Keep the same arc and tone. Add a brief intro line for LinkedIn's audience (slightly less technical, slightly more business-outcome focused). Keep under 3,000 characters.

---

## Success Criteria

- ✅ Thread is exactly 10 tweets, each under 280 characters
- ✅ Every numerical claim traces back to `docs/the-post-numbers.md`
- ✅ The Five-Part Agent pattern (or final name) is defined in tweets 6-7
- ✅ Thread reads as a war story, not a tutorial or product launch
- ✅ CTA tweet includes both landing page URL and TestFlight mention
- ✅ LinkedIn cross-post exists as a single reformatted post
- ✅ Zero instances of "we're excited", "I'm humbled", "here's how you can", or tutorial framing

---

## Non-Goals

- ❌ Optimizing for algorithmic reach (no engagement bait, no "like if you agree")
- ❌ Building a content funnel or drip campaign
- ❌ A/B testing thread variations
- ❌ Scheduling or automating the post (manual publish)
- ❌ Creating visual assets or infographics

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

