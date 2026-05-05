---
sidebar_position: 1
---

# 🔍 Reddit Launch Post — Analysis

**Purpose**: Identify problems and constraints driving this capability.

**Date**: 2026-04-18

---

## Summary

- **Total Issues**: 6
- **Critical**: 2
- **High**: 2
- **Medium**: 2

---

## Issue Breakdown

### Content Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No screen recording script exists — without it, the demo will ramble or miss the hook in the first 3 seconds | CRITICAL | Task 2 |
| No before/after text pair selected — generic examples won't land with the r/ChatGPT audience who already know what "AI slop" looks like | CRITICAL | Task 1 |
| Post timing unresolved — Reddit's algorithm buries posts published at low-traffic hours; r/ChatGPT peaks Tuesday–Wednesday 9–11 AM EST | HIGH | Task 4 |
| No comment engagement plan — Reddit rewards OP participation in the first 60 minutes; ghosting the thread kills momentum | HIGH | Task 5 |

### Distribution Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| r/ChatGPT automod may flag posts with external links — TestFlight URL could trigger removal if placed in the body | MEDIUM | Task 1 |
| No fallback subreddits identified if r/ChatGPT post gets removed or buried | MEDIUM | Task 4 |

---

## Hard Constraints

- **Tone**: First-person builder narrative. No startup jargon ("disrupting," "leveraging AI"). No calls to action that read like ads. The post must pass the "would I upvote this if I didn't build the app" test.
- **Length**: Reddit posts that perform well on r/ChatGPT are 150–300 words in the body. Longer gets skimmed. Shorter looks low-effort.
- **Link placement**: TestFlight link goes in a comment, not the body. This avoids automod and lets the post stand on its own merit. Pin the comment by posting it immediately after submission.
- **Screen recording**: 30 seconds max. No intro card, no music, no editing. Phone screen capture → voice input → watch it rewrite → done. Raw and real beats polished and produced.
- **No fake engagement**: No asking friends to upvote. No cross-posting within the same hour. One post, one subreddit, organic engagement only.

---

## Open Questions

| Question | Impact | Resolution Path |
|----------|--------|-----------------|
| Which before/after text resonates most with r/ChatGPT users? | Determines whether the post gets upvotes or "so what" | Test 3 candidates in Task 1; pick the one with the most jarring contrast |
| Should the screen recording show the full voice-to-rewrite flow or start mid-dictation? | Affects hook speed — first 3 seconds decide scroll-stop | Task 2 scripts both; pick the faster hook |
| Does r/ChatGPT allow TestFlight links in comments? | If not, need an alternative landing page | Check subreddit rules before publishing in Task 4 |

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

