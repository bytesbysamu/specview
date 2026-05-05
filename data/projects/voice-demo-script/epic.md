---
sidebar_position: 2
---

# 🎯 Voice Demo Script – Epic

**Purpose**: Define scope and tasks for producing a 30-second screen recording demo of Humaniz.me for the Reddit launch post.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

The Reddit launch post is Humaniz.me's first distribution moment. The product is live, pricing is set, Stripe is wired up — but zero humans outside the builder have seen it work. Every day without a public demo is a day the $195K MRR market (validated by StealthGPT) doesn't know Humaniz.me exists at $5/mo.

Video posts on r/ChatGPT consistently outperform text posts by 10x on engagement. A 30-second demo that shows paste → humanize → voice → humanize proves the product works faster than any copywriting can. The voice input flow is the scroll-stopping differentiator — no competitor shows this. One good demo post can drive the first 200 users needed for validation signal.

The secondary value is reusability. This script becomes the template for every future product launch in the portfolio (Cold Email Writer, LinkedIn Post Generator, Cover Letter Writer). Same structure, swap the sample text. One hour of work here amortizes across five products.

---

## Scope

### What This Epic Covers

- Selecting exact sample text (obviously-AI paragraph to paste, natural sentence to speak)
- Writing the beat-by-beat recording script with timing marks
- Pre-recording technical validation (screen recording + mic interaction on iOS)
- Recording protocol (device setup, app state, rehearsal count)
- Minimal post-production (trim + 3 caption labels)
- Reddit post title and body text to accompany the video

### What This Epic Does NOT Cover

- ❌ Building new features in Humaniz.me for the demo
- ❌ Multiple video variants or A/B testing
- ❌ Paid promotion or boosting the Reddit post
- ❌ Analytics dashboard for tracking post performance
- ❌ Demo videos for other subreddits or platforms (Twitter, LinkedIn)
- ❌ Professional video editing, motion graphics, or branding overlays

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Write the demo script with exact text** | None | — | 1 hour | Critical |
| 2 | **Validate iOS screen recording + mic** | None | 1 | 30 min | Critical |
| 3 | **Rehearse and time the recording** | 1, 2 | — | 1 hour | High |
| 4 | **Record the final take** | 3 | — | 30 min | High |
| 5 | **Add captions and trim** | 4 | — | 30 min | Medium |
| 6 | **Write Reddit post copy** | 1 | 5 | 1 hour | High |
| 7 | **Post to r/ChatGPT** | 5, 6 | — | 15 min | High |

### Task Details

#### Task 1: Write the demo script with exact text

Define the four-beat script with precise timing targets. Select the "obviously AI" paragraph — it must be instantly recognizable as ChatGPT without any label. Classic tells: "In today's fast-paced world," "It's important to note that," "Whether you're a student or professional," stacked in 3–4 sentences. Select the spoken sentence — short (under 10 words), natural, something a real person would dictate into their phone ("Hey can you clean up my meeting notes"). Define what the humanized output should approximately look like for each beat so the recording can be validated.

**Exact text to paste:**
> In today's rapidly evolving digital landscape, it is essential to acknowledge that artificial intelligence has fundamentally transformed the way we approach content creation. Whether you're a student working on academic papers or a professional crafting business communications, leveraging AI tools can significantly enhance your productivity and output quality.

**Exact sentence to speak:**
> "Remind my team the deadline moved to Friday"

**Beat timing:**
- Beat 1 (0:00–0:08): Open app, paste text into textarea. Text visibly fills the input.
- Beat 2 (0:08–0:16): Tap Humanize. Streaming response appears. Pause briefly on the natural-sounding result.
- Beat 3 (0:16–0:22): Clear textarea. Tap mic icon. Speak the sentence. Transcription fills textarea.
- Beat 4 (0:22–0:28): Tap Humanize. Streaming response transforms the spoken text. Hold on result for 2 seconds.
- End (0:28–0:30): Natural end. No outro card, no logo, no CTA. The URL is in the Reddit post body.

#### Task 2: Validate iOS screen recording + mic

Before any rehearsal, confirm that iOS screen recording can capture the Humaniz.me interface while simultaneously allowing the in-app microphone to function. Test on the target device (iPhone). If there's a conflict (iOS screen recording captures system audio and blocks the mic), identify the workaround: use a second device to record the screen externally, or use macOS QuickTime mirroring. Document the working recording method.

#### Task 3: Rehearse and time the recording

Run through the script 3–5 times with a timer. Identify dead-air moments — the biggest risk is the Humanize API response time. If streaming takes longer than 4 seconds, the beat timing breaks. Solutions: (a) ensure the API is warm (hit it once before recording), (b) have shorter sample text as a fallback, (c) accept slightly longer video (up to 35 seconds). Record each rehearsal, review timing, adjust beat boundaries if needed.

#### Task 4: Record the final take

With the validated recording method and rehearsed timing, record 3–5 final takes in sequence. Select the cleanest one — no fumbled taps, no API errors, no transcription glitches. Criteria: under 30 seconds, all four beats clearly visible, humanized output is genuinely better than input (if the AI produces a bad result, re-record — the output is not scripted but must be good).

#### Task 5: Add captions and trim

Using CapCut (free, iOS) or iMovie, trim head and tail dead frames. Add three minimal caption labels — white text, dark semi-transparent background, bottom of screen:
- "Paste AI text" (Beat 1)
- "Humanize ✨" (Beat 2)
- "Speak → Humanize" (Beats 3–4)

No other overlays. No music. No transitions. Export at native resolution (1170×2532 for iPhone or whatever the device captures). Export as MP4 for Reddit upload.

#### Task 6: Write Reddit post copy

Write the post title and body for r/ChatGPT. Title must not be self-promotional — frame it as showing a tool, not selling one. Examples: "I built a thing that rewrites ChatGPT text so it doesn't sound like ChatGPT" or "Made an app that humanizes AI text — here's 30 seconds of it working." Body includes: one-line description, link to humaniz.me, note that it has a free tier (3/day), and an invitation for feedback. No price list, no feature dump, no "we" language — first person singular ("I built," "I made").

#### Task 7: Post to r/ChatGPT

Upload the video and post copy to r/ChatGPT. Post during peak hours (weekday, 9–11 AM EST or 6–8 PM EST based on subreddit activity patterns). Flair appropriately. Monitor for the first 2 hours — respond to every comment within 30 minutes to boost algorithmic ranking.

---

## Success Criteria

- ✅ Final video is ≤ 30 seconds, single continuous take, no editing cuts
- ✅ All four beats are clearly visible: paste → humanize → voice → humanize
- ✅ Humanized output is genuinely different from and better than the AI input (not a subtle rewording — a visible transformation)
- ✅ Voice transcription works visibly on screen (viewer sees text appear as words are spoken)
- ✅ Video is self-explanatory on mute (no audio narration needed to understand what's happening)
- ✅ Reddit post goes live on r/ChatGPT with video embedded
- ✅ Post title is framed as showing, not selling

---

## Non-Goals

- ❌ Viral reach — the goal is a credible demo, not gaming the algorithm
- ❌ Professional production quality — authentic screen recording is the aesthetic
- ❌ Multi-platform launch — Reddit only for this round
- ❌ Conversion tracking — no UTM params, no analytics, just the URL in the post body
- ❌ Polished landing page or marketing site changes before posting

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

