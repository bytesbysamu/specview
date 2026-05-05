---
sidebar_position: 2
---

# 🎯 Reddit Launch Post – Epic

**Purpose**: Define scope and tasks for drafting, scripting, recording, and publishing the r/ChatGPT launch post for Humaniz.me.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

r/ChatGPT is 7M+ subscribers who discuss AI-generated text daily. "How do I make ChatGPT sound less like ChatGPT" is a recurring thread. Humaniz.me solves that problem — and the voice-to-rewrite flow is a visual differentiator no text-based competitor can match in a Reddit post.

A single well-crafted post on r/ChatGPT can generate 10K–50K impressions in 24 hours at zero cost. The conversion funnel is: scroll-stop on before/after text → watch 30-sec screen recording → click TestFlight link in comments → install. Every step needs to be crafted, not improvised.

This is the first public distribution push for Humaniz.me. The post also becomes reusable content: the screen recording works on Twitter/X, the before/after text works on LinkedIn, and the copy template adapts to r/ArtificialIntelligence, r/writing, and r/ChatGPTPro. Getting this right once compounds across channels.

---

## Scope

### What This Epic Covers

- Writing the Reddit post (title + body) in first-person builder tone
- Selecting and formatting 3 before/after text candidates, picking the strongest
- Scripting a 30-second screen recording showing voice-to-rewrite on iOS
- Defining the recording checklist (notifications off, battery full, clean home screen)
- Writing the TestFlight comment to post immediately after submission
- Determining optimal publish timing (day of week, hour, timezone)
- Writing 5–8 pre-drafted comment replies for predictable questions ("How does it work?", "Is this just ChatGPT with a wrapper?", "What about privacy?", "Will this stay free?")
- Identifying 2 fallback subreddits if r/ChatGPT post is removed or underperforms

### What This Epic Does NOT Cover

- ❌ Actually recording the screen recording (that's a separate execution step after the script is locked)
- ❌ Building a landing page or website changes
- ❌ Paid Reddit promotion or ads
- ❌ Cross-posting to Twitter/X, LinkedIn, or other platforms (future capability)
- ❌ Analytics setup or tracking UTM parameters
- ❌ App Store listing optimization

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Draft Reddit post copy** | None | 2 | 2 hours | Critical |
| 2 | **Script 30-sec screen recording** | None | 1 | 1 hour | Critical |
| 3 | **Write pre-drafted comment replies** | 1 | — | 1 hour | High |
| 4 | **Define publish strategy** | 1, 2 | — | 30 min | High |
| 5 | **Write TestFlight comment + engagement plan** | 1, 3 | — | 30 min | Medium |

### Task Details

#### Task 1: Draft Reddit post copy

Write the full Reddit post: title and body. The title must work as a standalone hook in a feed — it should communicate what the app does and that it's free, without sounding like an ad. Format: "I [did something relatable] and [surprising result]. [Free/TestFlight/etc.]"

Body structure: (1) One paragraph identifying with the problem — you use ChatGPT, the output sounds robotic, you've tried editing it manually. (2) One paragraph on what you built — voice-to-rewrite on your phone, paste AI text, talk naturally, it rewrites to match your voice. (3) Before/after text example — the scroll-stopper. Pick a universally relatable input (email, essay intro, or LinkedIn post). Show the ChatGPT output, then the humanized version side by side. (4) One line inviting people to try it — "Free on TestFlight, link in comments."

Produce 3 before/after text candidates. Each should use a different content type (email, essay, social post). The winning pair has the most jarring contrast between "obviously AI" and "obviously human." Select the strongest and embed it in the post body.

Word count target: 200–280 words for the body. Title under 120 characters.

#### Task 2: Script 30-sec screen recording

Write a second-by-second script for a 30-second iOS screen recording that demonstrates the voice-to-rewrite flow. This is the visual proof that makes the post believable.

Script structure:
- **0–3s**: Open the app. Screen shows the editor with a pasted ChatGPT paragraph (the "before" text from Task 1).
- **4–8s**: Tap the microphone button. Start speaking naturally: "Make this sound like I actually wrote it — casual, confident, no filler."
- **9–15s**: Voice input processes. The rewrite appears in the editor, streaming in real-time.
- **16–22s**: Scroll through the rewritten text. Pause on a sentence that's clearly different from the original.
- **23–28s**: Quick swipe to show the before/after toggle or split view.
- **28–30s**: End on the app name visible on screen.

Include a pre-recording checklist: Do Not Disturb on, battery at 80%+, Wi-Fi connected (not cellular — latency matters), clean status bar, no personal notifications visible, app in light mode (better contrast on Reddit's default white theme).

#### Task 3: Write pre-drafted comment replies

Write 5–8 reply templates for predictable questions the post will generate. These aren't copy-paste scripts — they're talking points with the right tone and facts so you can reply within 2 minutes of each comment.

Must-have replies:
1. "How does this work?" — Claude API rewrites to match natural speech patterns. Not just synonym swapping.
2. "Is this just a ChatGPT wrapper?" — No. It's a rewriting engine. You paste any AI text, speak your intent, it rewrites. Different model (Claude), different approach (voice-guided rewriting vs. chat).
3. "What about privacy?" — Text is processed, not stored. No account required for the free tier. Voice is processed on-device (Whisper/Apple Speech), only the transcript hits the API.
4. "Will it stay free?" — Free tier stays free (3 rewrites/day). Paid plans for heavy users coming soon.
5. "Does it work for [language/use case]?" — English first. Academic, professional, and casual tones. More languages coming based on demand.
6. "How is this different from QuillBot/Grammarly?" — Those fix grammar. This rewrites for voice and tone. Paste a ChatGPT essay, talk to it, get something that sounds like you wrote it.
7. "Can I see the source code?" — Not open source, but happy to explain the architecture. Claude API + streaming rewrite + voice input on iOS.
8. "Android?" — iOS first (TestFlight now). Android depends on demand — upvote if you want it.

#### Task 4: Define publish strategy

Determine the optimal publish window and fallback plan.

**Timing**: r/ChatGPT peaks Tuesday and Wednesday, 9–11 AM EST. Posts published in this window get maximum early engagement, which feeds Reddit's ranking algorithm. Avoid weekends (lower engagement per post, more competition from meme content) and Friday afternoons (thread dies before Monday).

**Subreddit rules check**: Before publishing, verify r/ChatGPT's current rules on self-promotion, external links in comments, and flair requirements. Check if TestFlight links are allowed in comments or if an alternative (e.g., linking to a profile with the TestFlight URL) is needed.

**Fallback subreddits**: If r/ChatGPT removes the post or it gets zero traction in 2 hours:
- r/ArtificialIntelligence (1.5M members, more technical audience, adjust tone)
- r/writing (2M members, focus the post on "making AI drafts sound like your voice")
- r/SideProject (150K members, builder audience, lean into "I built this" angle)

**One post per subreddit per week.** Never cross-post the same day. Adapt the title and before/after example for each audience.

#### Task 5: Write TestFlight comment + engagement plan

Write the comment that goes live immediately after the post is published. This comment contains the TestFlight link and a short call to action. It must be posted within 30 seconds of the main post to appear at the top of the thread.

Comment format: "TestFlight link: [URL]. Free, no account needed. 3 rewrites/day on the free tier. Would love feedback — especially on the voice input flow. DM me or reply here."

Engagement plan for the first 60 minutes:
- Reply to every comment within 5 minutes. Reddit's algorithm weighs early OP engagement heavily.
- Upvote genuine questions (not your own comments).
- If someone posts a negative comparison ("just use QuillBot"), reply with a specific difference — don't get defensive.
- If the post hits 50 upvotes in the first hour, edit the body to add "Edit: wow, didn't expect this. Adding a few answers to common questions below" and paste the top 3 FAQ answers inline. This signals authenticity and keeps the thread useful.
- Do NOT edit the post to add more links or promotional content. Ever.

---

## Success Criteria

- ✅ Reddit post title scores 8+/10 on the "would I click this in my feed" test — specific, personal, curiosity-driving
- ✅ Before/after text example produces a visible "wow" contrast — the humanized version reads like a real person wrote it from scratch
- ✅ Screen recording script is executable in one take — no cuts, no retakes needed, 30 seconds flat
- ✅ Post copy passes the "would r/ChatGPT upvote this if I didn't build the app" test — value-first, not promo-first
- ✅ All 5 pre-drafted comment replies are factually accurate and match the builder tone
- ✅ Publish strategy includes verified subreddit rules and a tested fallback plan
- ✅ TestFlight comment is ready to paste within 30 seconds of post going live

---

## Non-Goals

- ❌ Viral growth — one good post with 50–200 upvotes and 10+ TestFlight installs is a win
- ❌ Paid acquisition — this is organic only
- ❌ Multi-platform launch — Reddit first, other channels are a separate capability
- ❌ A/B testing post titles — pick the best one and ship it
- ❌ Video editing or production — raw screen recording only
- ❌ Building a dedicated landing page — TestFlight link is the landing page for now

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

