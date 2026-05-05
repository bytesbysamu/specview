---
sidebar_position: 2
---

# 🎯 Landing Page Copy Review – Epic

**Purpose**: Define scope and tasks to turn landing/index.html into a high-conversion page that justifies every visitor sent to it.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

Every distribution experiment — Reddit post, Twitter thread, cold DM, Product Hunt launch — terminates at landing/index.html. The page is a multiplier on all upstream effort. A 2% conversion rate on 1,000 visitors yields 20 signups. A 5% rate on the same traffic yields 50. The difference is copy, trust, and friction — all fixable without changing the product.

Spec Doc's early-adopter audience is technical founders and solo developers who have been burned by vague AI promises. They scan headlines in under 3 seconds, skip anything that smells like marketing fluff, and look for concrete proof that the tool works. The copy must speak their language: specific, honest, outcome-oriented. "Write better specs, get better code" is a strong tagline — the rest of the page needs to match that energy.

This epic also closes technical gaps that silently kill distribution: missing OG tags mean shared links render as blank cards on Twitter/LinkedIn (invisible to the sharer, devastating to click-through), a broken email form means interested visitors bounce with no capture, and slow mobile load means Reddit traffic (80%+ mobile) never sees the page at all.

---

## Scope

### What This Epic Covers

- Headline and subheadline copy audit with specific replacement suggestions
- CTA button copy and placement review
- Trust signal strategy for a pre-user product (builder output metrics)
- OG meta tags (title, description, image, Twitter Card, LinkedIn)
- Email signup form validation (correct endpoint, error handling, success feedback)
- TestFlight link placeholder strategy (waitlist form vs. dead link)
- Mobile responsiveness audit (viewport, touch targets, font sizes)
- Page load speed check (asset sizes, render-blocking resources)
- Specific, implementable copy suggestions — not "make it better" notes

### What This Epic Does NOT Cover

- ❌ A/B testing framework or split-test tooling
- ❌ Analytics or tracking pixel integration
- ❌ Blog, docs, or secondary pages
- ❌ Pricing page or plan comparison UI
- ❌ Backend changes beyond email endpoint verification
- ❌ Custom domain or SSL configuration
- ❌ Design system or component library — this is a single HTML file

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Audit existing copy and write replacements** | None | 2 | 2 hours | High |
| 2 | **Fix OG meta tags and social preview cards** | None | 1 | 1 hour | High |
| 3 | **Validate email form endpoint and add error handling** | None | 1, 2 | 1 hour | High |
| 4 | **Add trust signals section with builder output metrics** | 1 | — | 1 hour | Medium |
| 5 | **Mobile responsiveness and load speed fixes** | 1, 2, 3 | — | 2 hours | Medium |

### Task Details

#### Task 1: Audit existing copy and write replacements

Read landing/index.html end-to-end. Score each text block against three criteria: (a) does it say something specific or could it describe any product, (b) does it match the "technical founder, burned by AI hype" audience, (c) does it push toward the one CTA (email signup). For every block that scores below 2/3, write the replacement copy inline in a diff-ready format. Headline must pass the "cover the logo" test — if you covered the product name, would you still know what this product does? Subheadline must answer "why should I care right now?" CTA button text must be a verb phrase ("Get early access", not "Submit"). Remove or rewrite any filler paragraphs that don't advance the conversion goal.

#### Task 2: Fix OG meta tags and social preview cards

Add or correct all Open Graph and Twitter Card meta tags in the `<head>`: `og:title`, `og:description`, `og:image`, `og:url`, `og:type`, `twitter:card`, `twitter:title`, `twitter:description`, `twitter:image`. The OG image must be a real asset at a production-stable URL (not localhost, not a relative path that breaks when shared). Validate with Twitter Card Validator and LinkedIn Post Inspector. Title should match the page headline. Description should be under 160 characters and include the value prop, not a generic "welcome to our site" string.

#### Task 3: Validate email form endpoint and add error handling

Confirm the email signup form's `action` attribute or fetch URL points to the correct Express endpoint on server.js. Test the happy path (valid email → 200 response → success message shown to user). Test error paths: invalid email format (inline validation before submit), server error (show retry message, not a blank fail), duplicate email (handle gracefully — "you're already on the list" is better than a 409 error). Add a visible success state that replaces the form after submission ("You're in — check your inbox"). Confirm the endpoint actually persists the email to Neon Postgres, not just logs it.

#### Task 4: Add trust signals section with builder output metrics

Since Spec Doc has no users yet, social proof must come from builder credibility. Add a section below the fold with concrete output metrics: "18 epics shipped in 42 hours", "0 judgment calls per commit", or whatever the actual numbers are from the spec-doc pipeline. Format as a clean stats row (3-4 metrics, large numbers, short labels). This section replaces the "testimonials" block that most landing pages use — it's more honest and more compelling to the target audience. If the numbers aren't finalized, use placeholder values with a TODO comment and real formatting.

#### Task 5: Mobile responsiveness and load speed fixes

Test the page on a 375px viewport (iPhone SE — smallest common screen). Check: text readable without zooming, CTA button full-width and thumb-reachable, no horizontal scroll, images responsive, form inputs large enough for touch. Run Lighthouse or PageSpeed Insights — target 90+ performance score. Check for render-blocking CSS/JS, unoptimized images, missing `loading="lazy"` on below-fold images. Fix viewport meta tag if missing (`<meta name="viewport" content="width=device-width, initial-scale=1">`). Verify font loading strategy — system fonts or preloaded web fonts, not layout-shifting FOUT.

---

## Success Criteria

- ✅ Every text block on the page passes the "cover the logo" specificity test — copy could only describe Spec Doc
- ✅ OG meta tags render correct previews on Twitter Card Validator and LinkedIn Post Inspector
- ✅ Email form submits to a working endpoint, persists to Neon, and shows success/error states
- ✅ Trust signals section shows at least 3 concrete, verifiable builder output metrics
- ✅ Page scores 90+ on Lighthouse performance (mobile)
- ✅ Page renders correctly on 375px viewport with no horizontal scroll
- ✅ CTA is visible above the fold on both desktop and mobile
- ✅ No dead links — TestFlight placeholder is a waitlist form, not a broken URL

---

## Non-Goals

- ❌ Conversion rate optimization beyond the first audit — no multivariate testing
- ❌ Video or animation — static content only for v1
- ❌ Internationalization or multi-language support
- ❌ Dynamic content from the backend (feature lists, pricing pulled from API)
- ❌ Cookie consent banners or GDPR compliance UI — no tracking means no consent needed

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

