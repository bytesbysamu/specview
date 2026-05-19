# Targeted Subreddit Relaunch

## What this is

One post on one subreddit, with the rewritten pitch, the new landing page as the only CTA, and the demo artifact embedded or linked. This is the final step — everything else (BYOK decision, landing page, pitch, demo) must be done first. This is also where the strategy needs the most additional thinking, because "post again on Reddit" is not a distribution strategy.

## The original performance (from braindump)

> Three hours after launching my post on r/SideProject — titled "I spent 5 months building a tool that turns messy braindumps into engineering specs in 45 seconds" — the early numbers were already telling a story.

> The post had climbed to #22 on the subreddit for the day and, more surprisingly, ranked as my #6 post of all time. In just those first few hours, it pulled in ~600 views, gaining 152 in the most recent count. The view trajectory showed a quick ramp: 97 views in the first hour, 136 in the second, a spike to 221 in the third, then 152 in the fourth.

> Engagement was modest but encouraging: 4 upvotes with a perfect 100% upvote ratio, and 9 comments. No shares, crossposts, or awards.

> Geographically, the audience was split almost evenly across three regions — the United States and India each accounted for 12.8% of views, with Switzerland close behind at 12.6%. The remaining 61.8% was scattered across the rest of the world.

## Architecture's relaunch design (verbatim)

> One post on one subreddit, optimized for the rewritten pitch, with the landing page as the only link.

> No new backend infrastructure is needed for the relaunch itself. The architectural constraint is that the landing page URL is the *only* link in the post — no direct links to the Angular app, no GitHub repo link, no "also check out" secondary CTAs. Every click goes through the conversion funnel.

> The subreddit selection is a content decision, not an architectural one, but the architecture constrains it: the landing page must be the entry point, and the demo artifact must be embeddable or linkable from the post format the chosen subreddit allows.

## Architecture's design decisions (verbatim)

> **One subreddit, not multi-platform launch** — The first post proved the channel works (618 views, 100% upvotes). Fix conversion on the proven channel before spreading to unproven ones. Trade-off: Slower total reach. Acceptable — 5 conversions from one post beats 0 from five posts.

> **No analytics infrastructure in this iteration** — The success metric is ">=5 users reach the tool within 48 hours." This is countable from server logs and signup records without dedicated analytics. Trade-off: No funnel drop-off data. Acceptable — if fewer than 5 convert, the problem is still obvious enough to diagnose without detailed metrics.

## Dependencies

- Depends on Task 2 (landing page) — the landing page URL is the only link
- Depends on Task 3 (pitch rewrite) — the post uses the rewritten pitch
- Depends on Task 4 (demo artifact) — must be embeddable or linkable from the post

## Epic context

> **Task 5: Relaunch on targeted subreddit** — Dependencies: Tasks 2, 3, 4. Effort: 0.5 days. Priority: Low.

> **Success criteria**: Relaunch post achieves >0 shares (baseline: current post has exactly 0). At least 5 users reach the tool from the landing page within 48 hours of relaunch.

## Explicitly out of scope (from epic)

> - Paid Reddit promotion — 100% upvote ratio means the content failed, not the distribution. Fix the message before paying to amplify it.
> - Multi-platform launch — Fix conversion on one channel first. Relaunch on Product Hunt, HN, etc. only after one post converts >2% to signups.

## Review findings and fixes applied

### Critical: This is the weakest part of the spec

The strategic review raised serious concerns about this task:

**1. "Post again on Reddit" is not a distribution strategy.**
> "One relaunch post is a coin flip. The spec should include at least: (a) commenting helpfully on 5-10 threads where people discuss messy planning workflows, with a natural mention of the tool, (b) posting in a more targeted sub like r/ExperiencedDevs or r/webdev where the pain point is sharper, (c) a 'Show HN' as a parallel bet."

**2. No failure gate.**
> "What if it gets 600 views and 0 conversions again? There should be a decision gate: 'If <5 conversions from relaunch, the next step is X, not Y.'"

**3. Reddit may be the wrong channel entirely.**
> "618 views, 0 conversions, 0 shares. That is not a channel that 'works' — it is a channel that was tried once and failed. The biggest risk is spending 4.5 days optimizing for a second Reddit post when the real problem might be that Reddit r/SideProject is full of builders showing projects, not builders looking for tools."

> "Before building anything, Sam should spend 2 hours lurking in the target subreddit and counting how many posts like his actually convert to users for the tools they promote. If the answer is 'almost none,' the entire epic is pointed at the wrong wall."

**4. Success criteria are too soft.**
> "'5 users reach the tool' is clicks, not conversions. The real question is: does anyone complete a spec generation and come back? The success criteria should be tighter: at least 2 people complete a full braindump-to-spec flow from the relaunch post."

**5. The original post is still live.**
> "Anyone who searches 'specview' or finds it through Reddit history sees the weak pitch. Consider whether to delete it or edit it."

### Recommended additions to scope

- **Pre-relaunch research**: Spend 2 hours in target subreddit. Count tool-launch posts that actually converted. If none do, pick a different channel.
- **Seed distribution**: Before the relaunch post, comment helpfully on 5-10 threads about planning/structuring workflows. Build presence, don't just broadcast.
- **Subreddit targeting**: Consider r/ExperiencedDevs, r/webdev, r/softwaredevelopment instead of or in addition to r/SideProject.
- **Failure gate**: If relaunch gets <2 completed spec generations within 48h, stop Reddit and try Show HN or direct outreach.
- **Fix success criteria**: Change from "5 users reach the tool" to "2+ users complete a full braindump-to-spec flow."
- **Handle the old post**: Decide whether to delete, edit, or leave the original r/SideProject post.
