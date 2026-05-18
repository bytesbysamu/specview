# 🎯 Epic: SpecView Reddit Launch Recovery

## Business Value

SpecView's r/SideProject debut proved the distribution channel works — 618 views in 4 hours with a 100% upvote ratio means zero hostility and decent algorithmic reach. The post didn't fail because people disliked it; it failed because nobody understood what it does well enough to click through, share, or sign up. Zero shares on a 618-view post is a messaging problem, not a product problem.

The two highest-signal comments (addicted-coffee, Fun-Foot711) diagnose the exact blockers: the pitch is generic ("turns braindumps into specs" could mean anything), and there's no answer to the obvious privacy question. Ironically, Sam's own reply comment articulates the value prop better than the post itself — "you sit down to build something and spend the first 1-2 hours turning the mess in your head into something structured" is the hook the original post lacked. The raw materials for a converting pitch already exist; they just need to be reassembled in front of the right audience.

The business case is simple: one successful launch post on a dev subreddit can seed the first 50–100 real users. Without fixing the pitch, the privacy stance, and the conversion funnel, every future launch attempt burns the same way — views that evaporate because there's nowhere for attention to land.

## Scope

### What This Epic Covers

- **Privacy stance decision (BYOK vs hosted)** – Resolves the #1 unprompted objection from the Reddit thread; unblocks all downstream copy and landing page work
- **Landing page with conversion funnel** – Gives views somewhere to go; Reddit post → landing page → tool usage must be a defined path
- **Pitch rewrite with specific workflow pain** – Repositions SpecView around the concrete "1-2 hours of pre-work" pain point using Sam's own comment as the seed
- **Single-workflow demo artifact** – One screencast or annotated walkthrough showing a real braindump → structured spec transformation, not a feature list
- **Targeted relaunch post** – One post on one subreddit, optimized for the rewritten pitch, with the landing page as the CTA

### What This Epic Does NOT Cover

- ❌ **Paid Reddit promotion** — 100% upvote ratio means the content failed, not the distribution. Fix the message before paying to amplify it
- ❌ **Multi-platform launch** — Fix conversion on one channel first. Relaunch on Product Hunt, HN, etc. only after one post converts >2% to signups
- ❌ **New product features** — Zero evidence that missing features caused the flatline. All feedback points to messaging and trust
- ❌ **Analytics/tracking infrastructure** — Useful later, but the immediate problem is "nobody clicks through," not "we can't measure who clicks through"
- ❌ **India or Switzerland market targeting** — Sub-80-person cohorts from a single post are noise, not signal

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Decide BYOK vs hosted key model** | None | — | 0.5 days | High |
| 2 | **Build landing page with CTA funnel** | Task 1 (privacy stance determines copy) | — | 2 days | High |
| 3 | **Rewrite pitch around specific workflow pain** | Task 1 (privacy answer needed in pitch) | ∥ Task 2 | 0.5 days | High |
| 4 | **Create single-workflow demo artifact** | Task 3 (pitch frames which workflow to demo) | — | 1 day | High |
| 5 | **Relaunch on targeted subreddit** | Tasks 2, 3, 4 | — | 0.5 days | Low |

## Success Criteria

- ✅ Privacy model (BYOK/hosted/hybrid) decided and documented — no ambiguity in any public-facing copy
- ✅ Landing page live with a single clear CTA that leads to tool usage
- ✅ Rewritten pitch leads with a specific pain point, not a feature list — validated by at least one external review before posting
- ✅ Demo artifact shows one complete braindump → spec transformation in under 60 seconds
- ✅ Relaunch post achieves >0 shares (baseline: current post has exactly 0)
- ✅ At least 5 users reach the tool from the landing page within 48 hours of relaunch

## Related Documents

- [Analysis](./analysis.md) – Problems driving this epic
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking