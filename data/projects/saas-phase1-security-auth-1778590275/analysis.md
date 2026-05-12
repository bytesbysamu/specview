# 🔍 SaaS Phase 1: Security + Auth Completion — Analysis

## The Problem
spec-doc has a 70%-complete auth system (bcrypt/HS256, login, JWT) but no signup, no interceptor wiring, and hardcoded secrets committed to git history. Real users cannot onboard and the deployed app has exploitable security gaps. This phase finishes auth and closes the holes before any external user touches the system.

## Hard Constraints
- Bcrypt/HS256 stays — Supabase magic-link is rejected; no new auth dependencies
- Neon Postgres is the database; no migration away from it in this phase
- 3-day budget — anything that doesn't fit ships post-launch or not at all
- Blocks Phase 2 (billing needs signup) and Phase 4 (onboarding needs auth pages)
- Depends on P0 credential persistence being stable first
- No email infrastructure available — rules out any flow requiring transactional email

## Open Questions
- **SKIP_AUTH in production?** — Gate behind `FLASK_ENV=development` (recommended) vs. remove entirely vs. leave as-is. One-line fix but currently unscoped in any task.
- **Token refresh strategy?** — Proactive expiry check + 401 fallback (recommended) vs. optimistic replay vs. simple redirect. Determines whether interceptor and refresh are one unit or two.
- **JWT in localStorage vs. httpOnly cookie?** — Keep localStorage (recommended, CSP comes Phase 4) vs. switch to cookies (adds CSRF scope). Decide now because switching later rewires both stacks.
- **Git history with leaked secrets?** — Rotate and move on (recommended) vs. scrub history. Scrubbing breaks clones and is fragile for a solo dev.
- **`auth_user_id` nullable column?** — Ignore for now (recommended) vs. drop migration. Don't build on it either way.
- **Spam registration without email verification or CAPTCHA?** — IP rate limit alone is weak. Add Cloudflare Turnstile (~30 min) or accept the risk until Phase 4.

## Dependencies & Sequencing
- **Secrets rotation before anything else** — new JWT secret invalidates all existing sessions; coordinate with any active test accounts
- **Interceptor + refresh must be built as one unit** — separate implementation creates a 401/refresh race condition
- **CORS lockdown after interceptor is verified working** — tightening CORS before the interceptor attaches tokens will break every authenticated request during dev
- **Signup endpoint before Angular signup page** — frontend mocks against contract, but integration testing needs the real endpoint
- **SKIP_AUTH gating before CORS lockdown** — if SKIP_AUTH leaks to prod, CORS hardening is meaningless

## Explicitly Out of Scope
- **Email verification** — no email infra; revisit Phase 4 onboarding. Trigger: first user lockout from typo'd email
- **Password reset** — requires email infra; defer post-launch. Trigger: support burden from locked-out users
- **Social login (Google/Apple)** — unnecessary for web SaaS launch. Trigger: user acquisition data shows signup friction
- **Content-Security-Policy** — needs tuning for SPA inline styles/scripts; Phase 4. Trigger: XSS incident or pen test
- **Git history scrubbing** — credential rotation is the real fix. Trigger: compliance audit requiring clean history
- **Account lockout** — dangerous without password reset (self-DoS). Trigger: brute-force attempts in logs post-launch

> **Cross-references**: → [Epic](epic.md) for business justification · → [Solution Architecture](architecture.md) for interceptor lifecycle design and secrets management pattern · → Implementation guides for code-level steps