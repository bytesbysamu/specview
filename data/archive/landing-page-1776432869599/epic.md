---
sidebar_position: 2
---

# 🎯 Bubls Landing Page – Epic

**Purpose**: Define scope and tasks for the Bubls distribution landing page.

**Source Analysis**: See [Analysis](./analysis.md) for constraints and open questions.

---

## Business Value

Every distribution channel — Reddit posts, Twitter threads, Show HN, DMs to friends, QR codes on slides — needs a URL. Right now Bubls has none. The TestFlight link works for people who already know what they're installing, but it's a dead end for everyone else: no context, no screenshots, no way to capture interest from someone who isn't ready to install on the spot.

The landing page converts "I saw a post about this" into one of two actions: install via TestFlight (high intent) or leave an email (low intent, nurture later). Both are more valuable than a bounce. The email list becomes the distribution primitive — every future launch, update, or pivot starts with "email the list."

**Value proposition**: A live URL turns every mention of Bubls into a measurable funnel. Without it, distribution is a leak. With it, every post compounds.

---

## Scope

### What This Epic Covers

- Domain registration and DNS pointing to Coolify VPS
- Three screenshots captured from the TestFlight build (photoshoot result, text rewrite, onboarding)
- Static HTML landing page: hero + one-liner + screenshots + TestFlight CTA + email capture
- Email capture backend: one Neon table, one Flask endpoint, rate-limited
- Coolify deployment with SSL (Let's Encrypt via Coolify)
- Mobile-responsive layout (the page will be opened from phones via social links)

### What This Epic Does NOT Cover

- ❌ Analytics, tracking pixels, or conversion funnels
- ❌ Multiple pages, blog, or CMS
- ❌ A/B testing or copy experiments
- ❌ Email sending, drip sequences, or newsletter tooling
- ❌ App Store links (TestFlight only)
- ❌ SEO meta beyond basic Open Graph tags for link previews

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Domain + DNS** | None | 2 | 1 hour | Critical |
| 2 | **Screenshot capture** | None | 1 | 1 hour | Critical |
| 3 | **Email capture backend** | None | 1, 2 | 2 hours | High |
| 4 | **Landing page build** | 2 | 3 | 3 hours | Critical |
| 5 | **Coolify deploy + SSL** | 1, 3, 4 | — | 1 hour | Critical |

### Task Details

#### Task 1: Domain + DNS

Register the chosen domain (recommendation: `bubls.app`). Create an A record pointing to the Trendfy Coolify VPS IP. Verify DNS propagation. If repurposing `trendfy.me`, add a subdomain (`bubls.trendfy.me`) instead of hijacking the root. The `.app` TLD enforces HSTS, which means SSL is mandatory — handled by Coolify's Let's Encrypt integration in Task 5.

#### Task 2: Screenshot capture

Open the Bubls TestFlight build on an iPhone. Capture three screenshots at native resolution:
1. **Photoshoot result** — a completed AI photoshoot showing the generated image
2. **Text rewrite** — the text feature showing a before/after or active rewrite
3. **Onboarding** — the first or most visually striking onboarding screen

Export as PNG, then convert to WebP (with PNG fallback) at 750px width for mobile-first display. Use device frames (mockup) if the screenshots look better in context, but don't spend more than 15 minutes on this — raw screenshots are fine for v1.

#### Task 3: Email capture backend

Create a minimal Flask app (or add an endpoint to an existing one) that accepts `POST /api/email-signup` with a JSON body `{ "email": "..." }`. Validate the email format server-side. Insert into a `bubls_email_signups` table in Neon Postgres. Rate limit: 5 signups per IP per hour (in-memory or Neon-backed). Return `201` on success, `409` on duplicate, `429` on rate limit. CORS allow the landing page domain. Total: ~30 lines of Flask code.

#### Task 4: Landing page build

Single `index.html` file with inline CSS (or one `style.css`). No JavaScript framework. Minimal vanilla JS for the email form submission (fetch POST to the Flask endpoint). Layout:

1. **Hero**: App icon + one-liner (under 10 words) + two-line subtitle
2. **Screenshots**: Three phone screenshots in a horizontal row (stacked on mobile)
3. **CTA**: "Get Early Access on TestFlight" button linking to the TestFlight URL
4. **Email capture**: "Stay in the loop" input + submit button, success/error states
5. **Footer**: Minimal — "Built by [name]" or empty

Dark background to match Bubls' visual identity. Mobile-first responsive. Open Graph meta tags (`og:title`, `og:description`, `og:image`) so link previews look good in social posts. Favicon from the app icon.

#### Task 5: Coolify deploy + SSL

Create a new service in Coolify on the Trendfy VPS. Configure as a static site (nginx) serving the `index.html` + assets. Add the Flask email endpoint as a second service (or a route in an existing Flask app on the VPS). Point the domain. Enable Let's Encrypt SSL. Verify: page loads on `https://bubls.app`, email capture works, TestFlight link works, screenshots render on mobile.

---

## Success Criteria

- ✅ `https://bubls.app` (or chosen domain) loads a styled landing page in under 2 seconds on mobile
- ✅ Three product screenshots are visible and render correctly on iPhone and desktop
- ✅ TestFlight link opens the TestFlight install flow on iOS
- ✅ Email capture form submits successfully and stores the email in Neon
- ✅ Duplicate email submission shows a friendly message, not an error
- ✅ Open Graph tags produce a good-looking link preview when pasted into Twitter/Reddit/iMessage
- ✅ Page is live and linkable before the first distribution post goes out

---

## Non-Goals

- ❌ Conversion rate optimization — ship the page, measure later
- ❌ Email verification or double opt-in — capture first, verify when sending
- ❌ Custom domain email (hello@bubls.app) — not needed for a landing page
- ❌ Internationalization — English only
- ❌ Cookie consent banner — no cookies, no tracking, no banner needed

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

