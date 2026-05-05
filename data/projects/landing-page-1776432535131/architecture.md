---
sidebar_position: 3
---

# 🏗️ Bubls Landing Page – Solution Architecture

**Purpose**: Technical design for the landing page and email capture backend.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Two components, both deployed on the existing Trendfy Coolify VPS:

1. **Static site** — one `index.html` + one `style.css` + screenshot assets, served by nginx via Coolify's static site deployment. No build step, no bundler, no framework.
2. **Email capture API** — a Flask microservice (~30 lines) exposing `POST /api/email-signup`, connected to the shared Neon Postgres instance (EU Central 1). Rate-limited per IP. Deployed as a Docker container on the same VPS.

The two are independent services behind Coolify's reverse proxy. The landing page's email form makes a `fetch()` call to the API. No server-side rendering, no session state, no auth.

```
Browser ──GET──→ nginx (Coolify) ──→ index.html + assets
Browser ──POST──→ Flask (Coolify) ──→ Neon Postgres
```

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | Static HTML, not Next.js. One Flask endpoint, not a full API framework. No infrastructure before first user |
| No framework magic | Vanilla HTML/CSS/JS. The only dependency is Flask + psycopg2 on the backend |
| Neon Postgres for everything | Email signups go to Neon. No Mailchimp, no Supabase, no third-party services |
| Not-yet-built is the right state | No analytics, no A/B testing, no email sending pipeline. Add each when the signal demands it |
| Rate limiting server-side | Per-IP rate limit on the signup endpoint. Client shows UX feedback, server enforces |
| Feature ≠ 2 weeks | Entire capability ships in one day. Five tasks, all under 3 hours each |

---

## Component Design

### Task 1: Domain + DNS

**Purpose**: Give the landing page a reachable URL with SSL.

**Components**:
- Domain registrar (Namecheap, Cloudflare, or existing registrar) — A record to VPS IP
- Coolify domain config — attach domain to the static site service
- Let's Encrypt — auto-provisioned by Coolify when domain is attached

**Decision**: `.app` TLD enforces HSTS (all traffic over HTTPS). Coolify's built-in Let's Encrypt handles cert provisioning. No Cloudflare proxy needed — direct to VPS.

### Task 2: Screenshot Capture

**Purpose**: Three product images for the landing page hero.

**Components**:
- iPhone screenshots at native resolution (1179×2556 for iPhone 15 Pro)
- `convert.sh` — ImageMagick one-liner to resize to 750px width + WebP conversion
- `assets/` directory: `photoshoot.webp`, `text.webp`, `onboarding.webp` + PNG fallbacks

**Pattern**: `<picture>` element with WebP source and PNG fallback:
```html
<picture>
  <source srcset="assets/photoshoot.webp" type="image/webp">
  <img src="assets/photoshoot.png" alt="AI Photoshoot" loading="lazy" width="750" height="1624">
</picture>
```

### Task 3: Email Capture Backend

**Purpose**: Store email signups in Neon Postgres with rate limiting.

**Components**:
- `app.py` — Flask app (~30 lines), single endpoint
- `requirements.txt` — `flask`, `psycopg2-binary`, `gunicorn`
- `Dockerfile` — Python 3.12 slim, gunicorn, port 5000

**Database schema** (Neon Postgres, shared instance):
```sql
CREATE TABLE bubls_email_signups (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_signups_email ON bubls_email_signups(email);
CREATE INDEX idx_email_signups_ip ON bubls_email_signups(ip_address);
```

**Endpoint contract**:
```
POST /api/email-signup
Content-Type: application/json

Request:  { "email": "user@example.com" }

Responses:
  201  { "status": "ok" }
  400  { "error": "Invalid email" }
  409  { "error": "Already signed up" }
  429  { "error": "Too many requests" }
```

**Rate limiting**: In-memory dict keyed by IP, 5 requests per hour, reset on window expiry. Acceptable to lose state on restart — this is abuse prevention, not billing.

**Pattern**: Flask factory pattern. CORS configured for the landing page domain only. Email validation via regex (RFC 5322 simplified — no need for a library on one field).

### Task 4: Landing Page Build

**Purpose**: The HTML page that distribution links point to.

**Components**:
- `index.html` — semantic HTML5, inline critical CSS or linked `style.css`
- `style.css` — mobile-first responsive, dark palette matching Bubls identity
- `favicon.ico` + `apple-touch-icon.png` — from app icon
- `assets/` — screenshots (WebP + PNG), app icon

**Layout structure**:
```html
<body>
  <header>  <!-- App icon + one-liner + subtitle -->
  <section> <!-- Three screenshots in responsive grid -->
  <section> <!-- TestFlight CTA button -->
  <section> <!-- Email capture form -->
  <footer>  <!-- Minimal -->
</body>
```

**Responsive breakpoints**:
- Mobile (< 768px): screenshots stacked vertically, full-width CTA
- Desktop (≥ 768px): screenshots in a 3-column row, centered content max-width 1080px

**Open Graph tags**:
```html
<meta property="og:title" content="Bubls — [one-liner]">
<meta property="og:description" content="[two-line subtitle]">
<meta property="og:image" content="https://bubls.app/assets/og-image.png">
<meta property="og:url" content="https://bubls.app">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
```

**Email form JS** (~20 lines vanilla):
```javascript
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const res = await fetch('/api/email-signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: input.value })
  });
  // Show success/error based on res.status
});
```

### Task 5: Coolify Deploy + SSL

**Purpose**: Get both services live on the VPS behind HTTPS.

**Components**:
- Coolify static site service — git repo or direct file upload, nginx serving `index.html`
- Coolify Docker service — Flask container, env vars for `DATABASE_URL`
- Coolify reverse proxy — route `/api/*` to Flask, everything else to static
- Let's Encrypt cert — auto-provisioned when domain is attached

**Deployment flow**:
```
git push → Coolify webhook → rebuild static + Flask → live
```

Or for v1, manual deploy via Coolify UI (paste files, click deploy). Automate with webhook after first successful deploy.

---

## Execution Flow

```
[Phase 1 — parallel, no dependencies]
   Task 1 (Domain + DNS)
   Task 2 (Screenshot capture)
   Task 3 (Email capture backend)

[Phase 2 — needs screenshots from Task 2]
   Task 4 (Landing page build)

[Phase 3 — needs all above]
   Task 5 (Coolify deploy + SSL)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Static HTML vs Next.js | Static HTML | One page, no routing, no SSR needed. Framework adds build step, node runtime, and deploy complexity for zero benefit. Migration to Next.js is cheap if a second page materializes |
| Email storage | Neon Postgres | Architecture principles mandate Neon for everything. Shared instance already provisioned. One table, no new infrastructure |
| Rate limiting approach | In-memory per-IP | Good enough for a landing page with low traffic. No Redis, no Neon-backed rate limiter. State loss on restart is acceptable |
| Image format | WebP with PNG fallback | WebP saves ~30% bandwidth on mobile. `<picture>` element handles fallback. No build tool needed — ImageMagick one-liner |
| Hosting | Coolify on Trendfy VPS | Already provisioned, already running other services. No new server, no Vercel, no Netlify |
| Flask vs adding to existing backend | Standalone Flask microservice | Keeps the landing page fully self-contained. Can be deleted without touching other services. ~30 lines |
| CSS approach | Single `style.css`, no Tailwind | One page doesn't need a utility framework. Hand-written CSS is faster to write and has zero build step |
| Domain | `bubls.app` (recommended) | `.app` enforces HTTPS, signals mobile-native, clean brand match. `bubls.ch` is geo-locked. Repurposing `trendfy.me` weakens both brands |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

