# 🔍 Jenni Playbook Blur Pattern — Analysis

## The Problem
Specview generates a full spec suite but has no conversion mechanism — every visitor gets everything or nothing. Jenni AI proved that showing partial value (blurred citations) creates a psychological itch that converts at 3-4%. Specview needs this suspension-based funnel: free analysis hooks them, blurred spec titles create the itch, paywall converts.

## Hard Constraints
- Engineering specs only. No Life OS, no business plans, no weekly reviews. Until $5K MRR.
- Measure anonymous-analyze → signup conversion before Show HN. Below 3% = fix, don't launch.
- Existing stack: Flask :3101 + Angular :4201. No new infrastructure.
- Telegram response limit (4096 chars) still applies if OpenClaw surfaces specs.

## Open Questions
- **Generate or fake the blurred docs?** Free tier either (a) generates all 5 docs and blurs 4 (real content, high token cost per free user) or (b) generates only the analysis and shows static/template section headers behind blur (cheap but the blur is a lie). Option (a) is honest and lets upgrade feel instant. Option (b) is sustainable. Pick one — they have different architectures.
- **What's the token cost per full generation?** If it's $0.15/run, giving every anonymous user 5 docs kills margin. If it's $0.03, option (a) is fine. This number decides the funnel shape.
- **Auth before or during blur?** Does the user hit the paywall at "upgrade to read" (requires auth + payment in one step) or do they sign up free first, then hit a separate payment wall? Jenni did signup-first. Two-step has higher top-of-funnel but adds a state (signed-up-but-unpaid).
- **How is conversion tracked?** No analytics mentioned. Anonymous session → signup requires at minimum a session ID cookie and an event pipeline. What's the lightweight version — PostHog? Plausible? Raw Flask middleware counting?

## Dependencies & Sequencing
- **Blur UI requires generated (or faked) content** → decision on generate-vs-fake must come first, it shapes both backend and frontend.
- **Conversion measurement requires analytics** → analytics must exist before Show HN, not after.
- **Paywall requires auth + payments** → Stripe integration and user accounts block the blur-to-convert flow.
- **"Codebase context injection" is cited as the moat** → if not yet built, it's a dependency for the narrative, not the blur pattern. Separate it.

## Explicitly Out of Scope
- **Show HN launch** — gated behind 3% conversion proof. Re-scope when metric is hit.
- **Content marketing / SEO** — Jenni did conversion before virality. Same rule applies here.
- **Multi-tenant teams / collaboration** — solo users only until pricing is validated.
- **Codebase context injection buildout** — moat narrative, not blur-pattern work. Separate epic. Re-scope when blur funnel is live and converting.
- **Mobile/Telegram spec delivery** — different surface, different UX. After web converts.