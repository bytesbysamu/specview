# 🔍 Specview SaaS Go-to-Market — Analysis

## The Problem
Product works, landing page is live at specview.io with $29/mo Pro tier, but Stripe isn't wired, usage limits aren't enforced, and zero distribution exists. Goal is the first 100 real users via a Show HN-led launch — but the launch can't happen until reliability and billing gates close.

## Hard Constraints
- Stripe must be live and `@check_usage_limit` deployed before any public post
- Phase 4 reliability work (timeouts, error envelopes, polling retries) is a launch gate
- Solo founder — no support staff to absorb a botched HN front-page day
- Telegram/mobile not part of this launch path; web app at app.specview.io only
- "0 human code lines" claim is public on the landing page — framing must survive HN scrutiny

## Open Questions
- Free tier limit — keep 3/month, drop to 2, or replace with a no-auth single-spec playground?
- Pricing — hold $29/mo, add $9 one-time/10-pack, or add $99/mo team tier? Pick one to ship; don't ship all three.
- Launch sequencing — Show HN first (highest yield, one shot), or warm up with r/SideProject + Dev.to to de-risk HN day?
- "0 human code lines" — literal claim or qualified ("AI-generated from AI-written specs, with X")? Decide before any post quotes it.
- Retention thesis — do Pro users pay for unlimited, for non-project planning use, or for team use? Pick the one the analytics will actually measure.

## Dependencies & Sequencing
- Phase 4 reliability → blocks Show HN (concurrent load on a no-timeout skill = fatal)
- Stripe live + usage limits enforced → blocks any paid conversion claim
- Activation analytics (landing → signup → first spec) → blocks post-launch iteration; must exist before traffic arrives
- Email capture on landing page → blocks recovering bounced HN traffic; cheap, do before launch
- Show HN post → unblocks Twitter/X amplification (no audience to seed it otherwise)
- Product Hunt → strictly post-launch, after onboarding is polished

## Explicitly Out of Scope
- No-auth playground — product change, not a GTM task; re-scope only if free→paid conversion stalls after launch
- Team/$99 tier — no validated demand; re-scope after a team inbound or 2nd Pro user from a team context
- One-time $9/10-pack — pricing experiment; re-scope only if free tier shows high hit-rate but low subscription conversion
- Twitter/X as a primary channel — no existing audience; secondary amplification only
- Dev.to/Hashnode SEO post — high ROI but slow; not part of the launch-week scope
- Product Hunt launch — gated on post-Phase-4 polish; not a now event
- Building a retention model before launch — unresolved by design; needs live data first