# BYOK vs Hosted Key Model — Decision

## What this is

SpecView needs a privacy stance before anything else ships. One Reddit commenter (Fun-Foot711) raised this unprompted — they wanted to know whether everything runs through our API key or if users bring their own. They admitted that sharing raw project ideas with a third-party tool felt like a real concern, especially when the tool's whole purpose is organizing early-stage thinking. If one person said it, more thought it and didn't comment.

This decision blocks the landing page copy, the pitch rewrite, and every future launch attempt. Nothing else moves until this is resolved.

## The problem (from analysis)

> **BYOK vs hosted key**: Fun-Foot711 raised this directly. Three paths: (1) BYOK-only removes privacy objection but kills onboarding, (2) hosted key with clear data policy, (3) hybrid with BYOK as premium. Which?

> A privacy objection surfaced unprompted, which means more people thought it and didn't comment.

## The three options (from analysis)

1. **BYOK-only** — removes privacy objection entirely but kills onboarding friction. Every new user must have an Anthropic API key before they can try anything.
2. **Hosted key with clear data policy** — easiest onboarding, but requires trust. Must answer "what happens to my data" convincingly.
3. **Hybrid with BYOK as premium** — hosted trial for first impression, BYOK for power users who care about control.

## Architecture's proposed solution (verbatim)

> The decision is a hybrid model weighted toward BYOK. Visitors who arrive from Reddit fall into two camps: those who will never paste proprietary ideas into a hosted tool (BYOK-only), and those who want to try before committing to anything (hosted trial). Serving only one camp loses the other.

> BYOK is the *default* and the *marketed* position — "your key, your data, nothing stored." The hosted trial path exists as a friction reducer: a visitor can generate one spec using the server key without signup, seeing the real output before deciding whether to bring their own key. This is not a freemium tier; it is a single-use demonstration that the tool works.

> The chain adapter already isolates all AI calls behind `adapter.py`. Supporting BYOK means the adapter accepts an optional key parameter and, when present, uses it instead of the server-configured key. The provider selection logic (`cli` vs `claude` vs `mock`) remains unchanged — BYOK only affects which API key is attached to the outbound call. No new provider module is needed.

> Key storage is per-session only. The user's API key lives in the browser (sessionStorage, not localStorage) and is sent per-request via a header. The server never persists it. This is the strongest possible privacy stance and the simplest possible implementation.

## Architecture's design decision (verbatim)

> **BYOK-first with single hosted trial** — Addresses privacy objection head-on while preserving try-before-you-commit; strongest possible trust signal for dev audience. Trade-off: Hosted trial has cost exposure — one free generation per visitor. Acceptable at current traffic levels; add rate limiting if volume exceeds 100/day.

> **Session-only key storage (no server persistence)** — Eliminates the entire class of "what if your database leaks my API key" concerns. Also eliminates the need for key encryption infrastructure. Trade-off: Users must re-enter their key each session. Friction is real but acceptable — browser password managers auto-fill, and the privacy benefit outweighs the convenience cost.

## Technical integration points (verbatim from architecture)

> The BYOK key header flows from Angular's `ai.service.ts` through the Flask API to `adapter.py`. The existing `require_auth` decorator in `modules/auth/` is bypassed for the single anonymous generation endpoint — a new decorator or a flag on the existing one controls this.

## What exists in the codebase

- Chain adapter: `api/modules/runtime/chain/adapter.py` — already abstracts all AI calls
- Auth decorator: `api/modules/auth/decorators.py` — `require_auth`
- Angular AI service: `web-ng/src/app/services/ai.service.ts`
- Provider selection logic already handles `cli` vs `claude` vs `mock`

## Review findings

- **Architecture pre-decided this** — The architecture already commits to "BYOK-first with hosted trial" even though this task is supposed to be the decision point. The actual work here is validating or rejecting that recommendation.
- **Possibly overengineered** — Strategic review says: "One person mentioned privacy in a 9-comment thread. The simpler answer: add one sentence to the landing page ('Your braindumps are processed and not stored. Want full control? BYOK support coming soon.') and move on." Full adapter/sessionStorage/anonymous-auth implementation is real engineering for a hypothetical problem at 0 users.
- **Anonymous-first flow is a product change** — Relaxing the auth requirement for anonymous generation contradicts the epic's exclusion of "new product features."

## Epic context

> **Task 1: Decide BYOK vs hosted key model** — Dependencies: None. Effort: 0.5 days. Priority: High.

> **Success criteria**: Privacy model (BYOK/hosted/hybrid) decided and documented — no ambiguity in any public-facing copy.

## What to actually decide

1. Full BYOK implementation now (adapter changes, sessionStorage, anonymous endpoint) — 2+ days
2. Copy-only promise ("your data is never stored, BYOK coming soon") — 0.5 days, unblocks everything immediately
3. The hybrid the architecture proposes — 2+ days but strongest long-term position

The decision should account for the fact that there are currently 0 users. Engineering effort should match the signal strength.
