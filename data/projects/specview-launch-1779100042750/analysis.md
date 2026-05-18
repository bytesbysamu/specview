# 🔍 SpecView Reddit Launch — Analysis

## The Problem
SpecView's r/SideProject debut pulled 618 views in 4 hours then flatlined to zero — no long-tail discovery. The post landed 4 upvotes (100% ratio, no hostility) and 9 comments, but the two highest-signal comments both say the same thing: the pitch is too vague to convert. A privacy objection surfaced unprompted, which means more people thought it and didn't comment.

## Hard Constraints
- spec-doc is the existing product (Flask :3101 + Angular :4201) — "SpecView" is a launch name, not a new build
- Solo founder — no bandwidth for parallel marketing experiments
- No analytics/tracking infrastructure mentioned — view data came from Reddit's dashboard only
- The 12.6% Switzerland traffic is likely self-referral noise, not organic signal

## Open Questions
- **BYOK vs hosted key**: Fun-Foot711 raised this directly. Three paths: (1) BYOK-only removes privacy objection but kills onboarding, (2) hosted key with clear data policy, (3) hybrid with BYOK as premium. Which?
- **Landing page exists?** The post drove 618 views but zero shares. Was there a link to a site, or did all traffic dead-end on the Reddit post? If no landing page, views are worthless.
- **What is the actual conversion funnel?** Reddit post → ??? → user pastes brain dump. The middle step is undefined.
- **Retention signal**: 9 comments, but did anyone actually try the tool? Comments ≠ usage. Is there any way to know?

## Dependencies & Sequencing
- Privacy stance (BYOK vs hosted) blocks the landing page copy, which blocks the next launch attempt
- A "painfully specific" demo (addicted-coffee's feedback) requires picking ONE workflow to showcase — that blocks repositioning the pitch
- Sam's own comment reply articulates the value prop better than the post did — the rewrite should lead with that exact framing

## Explicitly Out of Scope
- **Paid Reddit promotion** — 618 organic views with 100% upvote ratio means the content failed, not the distribution. Paying to amplify a weak pitch wastes money. Re-scope when the pitch converts organically on a smaller sub.
- **Multi-platform launch blitz** — fix the message on one channel first. Re-scope after one post converts >2% to signups.
- **New features** — zero evidence that missing features caused the flatline. The feedback is about messaging and trust, not capability. Re-scope only after a BYOK decision and landing page exist.
- **India market targeting** — 12.8% of 618 views is ~79 people. Not a signal. Ignore until n > 1000.