# 🔍 Anonymous Landing Analyze — Analysis

## The Problem
Specview's landing page is a brochure — visitors read *about* structured analysis but never experience it. Conversion depends entirely on copy persuasion. Adding an unauthenticated analysis box lets visitors run the product on their own thinking before signing up, turning the landing page into a product demo.

## Hard Constraints
- One Flask route: `POST /api/public/analyze` — analysis doc only, not the full five-doc pipeline
- No auth required on this endpoint
- Rate limit: 3 per day per IP
- No Redis, no Postgres — rate limiting must use in-process state (module-level dict + `threading.Lock`)
- Frontend is static HTML + vanilla JS — not part of the Angular app
- Claude API call behind this route — every anonymous request has direct AI cost

## Open Questions
- **How is the static landing page served?** (a) Flask serves it via `send_from_directory` (b) nginx serves it as a separate static site (c) it replaces the current Angular landing route
- **What happens when gunicorn restarts and the in-process rate-limit dict resets?** Accept the leak, or persist counts to a flat file?
- **Does a signup flow exist yet?** The CTA says "sign up free" — if auth isn't built, the conversion moment dead-ends
- **Max input length?** Unbounded braindump → unbounded token cost. What's the character cap? 5k? 10k?
- **What prompt/system-prompt drives the public analysis?** Same as the authenticated pipeline's analysis step, or a trimmed version that teases the full output?

## Dependencies & Sequencing
- The analysis prompt must already work reliably in the existing pipeline before exposing it unauthenticated — **this is not the place to iterate on prompt quality**
- The CTA conversion path (signup → dashboard → full spec) must exist or the funnel leaks at the moment of highest intent
- Rate limiter must be in place *before* the route goes live — an unprotected Claude-calling endpoint is a cost vulnerability, not a bug

## Explicitly Out of Scope
- **Full five-doc generation for anonymous users** — brain dump says "one call, one document" explicitly; re-scope only if free-tier conversion data demands it
- **Angular integration or SPA routing** — this is a static page; pulling it into the Angular app adds build complexity for zero user benefit right now
- **Email capture before analysis** — the whole point is zero-friction; adding a gate before the result kills the thesis; re-scope only if abuse makes rate limiting insufficient
- **Streaming response** — nice for 45s waits but adds SSE complexity to a vanilla-JS page; re-scope if user testing shows abandonment during the wait