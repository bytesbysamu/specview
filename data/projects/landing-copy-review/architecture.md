---
sidebar_position: 3
---

# 🏗️ Landing Page Copy Review – Solution Architecture

**Purpose**: Technical design for auditing and improving landing/index.html as a standalone conversion surface.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

The landing page is a static HTML file — no Angular, no build step, no framework. This is intentional: the page loads fast, deploys anywhere, and has zero JavaScript dependencies for core content. The architecture is simple by design: one HTML file, one CSS file (inline or linked), one optional JS file for form handling, and the Express backend for email capture.

The system has three layers: the static page (what the visitor sees), the email capture endpoint (Express on server.js), and the persistence layer (Neon Postgres). Changes in this capability touch all three but keep them decoupled — the page can render fully without JavaScript, the form degrades gracefully without the backend, and the backend stores emails independent of the page's existence.

OG meta tags and social previews are a deployment concern — the image URL must resolve from any context (Twitter's crawler, LinkedIn's scraper, a browser on someone's phone). This means absolute URLs with the production domain, not relative paths or localhost references.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | No landing page framework, no CMS, no component library. One HTML file that converts. |
| Neon Postgres for everything | Email signups persist to Neon, same shared instance as all other products. No Supabase, no Mailchimp, no third-party form service. |
| Flask minimal (adapted to Express) | Email endpoint is ~15 lines in server.js. Validate, insert, respond. No middleware chain. |
| Mock external, test real logic | OG tag validation uses external tools (Twitter Card Validator). Form submission is tested against the real Express endpoint locally. |
| Explicit over implicit | No magic form handlers. The form's fetch call explicitly targets the endpoint, explicitly handles success/error, explicitly updates the DOM. |

---

## Component Design

### Task 1: Audit Existing Copy and Write Replacements

**Purpose**: Replace generic or weak copy with specific, conversion-oriented text targeted at technical founders.

**Components**:
- `landing/index.html` — All copy lives inline in the HTML. No CMS, no templating, no external content source.

**Patterns**: Copy audit follows the "cover the logo" test — each text block must be specific enough that covering the product name still tells you what this is. Replacement copy is written as direct HTML diffs, not abstract suggestions.

**Copy structure**:
```
HERO SECTION
├── Headline — what this is (specific, under 8 words)
├── Subheadline — why you should care right now (one sentence)
├── CTA button — verb phrase ("Get early access")
└── Supporting line — who this is for ("For solo founders shipping with AI")

BELOW THE FOLD
├── How it works — 3 steps, concrete, no abstraction
├── Trust signals — builder output metrics (see Task 4)
├── Secondary CTA — email signup form
└── Footer — minimal, links to docs/GitHub
```

### Task 2: Fix OG Meta Tags and Social Preview Cards

**Purpose**: Ensure shared links render rich previews on Twitter, LinkedIn, Slack, and iMessage.

**Components**:
- `landing/index.html` `<head>` section — meta tags live here
- `landing/og-image.png` (or hosted URL) — the preview image asset, 1200x630px

**Required meta tags**:
```html
<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:url" content="https://specdoc.dev">
<meta property="og:title" content="Spec Doc — Write better specs, get better code">
<meta property="og:description" content="Document-first AI editor. Braindump to shipped code in hours, not weeks.">
<meta property="og:image" content="https://specdoc.dev/og-image.png">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Spec Doc — Write better specs, get better code">
<meta name="twitter:description" content="Document-first AI editor. Braindump to shipped code in hours, not weeks.">
<meta name="twitter:image" content="https://specdoc.dev/og-image.png">
```

**Validation**: Twitter Card Validator (cards-dev.twitter.com/validator) and LinkedIn Post Inspector (linkedin.com/post-inspector/).

### Task 3: Validate Email Form Endpoint and Add Error Handling

**Purpose**: Ensure the email signup form captures leads reliably with clear user feedback.

**Components**:
- `landing/index.html` — form markup and inline JS for submission
- `server.js` — Express endpoint for email capture (`POST /api/signup` or equivalent)
- Neon Postgres — `email_signups` table (email, created_at, source)

**Form submission flow**:
```
[User types email] → [Inline validation: regex + empty check]
        │
        ▼
[Submit button click] → [fetch POST /api/signup {email, source: "landing"}]
        │
        ├── 200 OK → Replace form with "You're in — check your inbox"
        ├── 409 Conflict → Show "You're already on the list"
        ├── 422 Unprocessable → Show "Please enter a valid email"
        └── 5xx / network error → Show "Something went wrong — try again"
```

**Backend endpoint** (~15 lines in server.js):
```javascript
app.post('/api/signup', async (req, res) => {
  const { email, source } = req.body;
  // validate email format
  // INSERT INTO email_signups (email, source) VALUES ($1, $2)
  // ON CONFLICT (email) DO NOTHING — return 409 if already exists
  // return 200 with { message: "subscribed" }
});
```

**Database table**:
```sql
CREATE TABLE IF NOT EXISTS email_signups (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  source TEXT DEFAULT 'landing',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Task 4: Add Trust Signals Section

**Purpose**: Replace traditional social proof with builder output metrics that demonstrate the product works.

**Components**:
- `landing/index.html` — new section between "how it works" and footer

**Design**:
```html
<section class="trust-signals">
  <div class="stats-row">
    <div class="stat">
      <span class="stat-number">18</span>
      <span class="stat-label">epics generated</span>
    </div>
    <div class="stat">
      <span class="stat-number">42</span>
      <span class="stat-label">hours braindump→code</span>
    </div>
    <div class="stat">
      <span class="stat-number">0–3</span>
      <span class="stat-label">judgment calls per commit</span>
    </div>
  </div>
</section>
```

**Patterns**: Stats row is a common trust signal pattern — large numbers with short labels. No testimonial quotes, no company logos, no "trusted by" language. The numbers are verifiable from the repo's git history.

### Task 5: Mobile Responsiveness and Load Speed

**Purpose**: Ensure the page performs on mobile devices where most social media traffic originates.

**Components**:
- `landing/index.html` — viewport meta tag, responsive CSS
- Any linked CSS file — media queries, touch target sizing
- Any images — compression, lazy loading, responsive srcset

**Performance checklist**:
```
Viewport:     <meta name="viewport" content="width=device-width, initial-scale=1">
Fonts:        System font stack (no web font loading delay)
Images:       WebP format, loading="lazy" for below-fold, max-width: 100%
CSS:          Inline critical CSS in <head>, defer non-critical
JS:           Only for form handling, loaded with defer attribute
Touch:        All interactive elements ≥ 44x44px
Text:         Body ≥ 16px, heading hierarchy, adequate line-height
CTA:          Full-width on mobile (max-width: 480px), sticky or repeated
```

**Target scores**:
- Lighthouse Performance: 90+
- Lighthouse Accessibility: 95+
- First Contentful Paint: < 1.5s
- Largest Contentful Paint: < 2.5s

---

## Execution Flow

```
[Phase 1 — parallel]
   Task 1 (copy audit) ──────────────────┐
   Task 2 (OG meta tags) ────────────────┤
   Task 3 (email form endpoint) ─────────┘
                                          │
[Phase 2 — depends on Phase 1]           ▼
   Task 4 (trust signals — needs copy direction from Task 1)
                                          │
[Phase 3 — final pass]                   ▼
   Task 5 (mobile + speed — tests the complete page)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Static HTML, no framework | Single .html file | Landing page has no dynamic content. No build step = instant deploys, zero JS overhead for content rendering. Framework would add complexity for zero conversion benefit. |
| Neon Postgres for email signups | Direct INSERT via Express | Consistent with architecture principles — Neon for everything, no third-party form services (Mailchimp, Typeform). Email list is a first-party asset. |
| System font stack | `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | Eliminates font loading delay entirely. No FOUT, no CLS from late-loading web fonts. The audience cares about speed, not typography nuance. |
| Builder metrics over fake social proof | "18 epics shipped in 42 hours" | No users yet, so testimonials would be dishonest. Builder output metrics are verifiable from git history and speak directly to the technical founder audience. More credible than "trusted by 0 companies." |
| Waitlist form for TestFlight | Email capture with "iOS coming soon" | Dead TestFlight link is a broken promise. "Coming soon" with no capture is a wasted touchpoint. Waitlist captures intent and creates a launch day distribution list. |
| Inline form JS, no library | Vanilla fetch + DOM manipulation | Form handling is ~20 lines of JS. Adding a library for this is overhead that slows the page and adds a dependency for no benefit. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

