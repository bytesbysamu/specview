# Implementation Guide: Landing Page — Hosted Tier & Pricing Surface

**Project**: Landing Page
**Updated**: 2026-05-07
**Status**: Ready to execute — Stripe payment link already live.

---

## Config strings (pre-resolved — use exactly as shown)

| Token | Value |
|-------|-------|
| `AUTH_URL` | `https://app.specview.io/signup` |
| `STRIPE_URL` | `https://buy.stripe.com/test_6oUeVdaA1aVF27s1JVao800` |

Both are WIP / test values. Mark every occurrence with HTML comments so they're easy to swap.

---

## File map

| File | What changes |
|------|-------------|
| `landing/index.html` | HTML structure only — no `<style>` tags, no `<script>` tags |
| `landing/style.css` | All new CSS appended at end of file |

No new files. No new `<link>` or `<script>` tags.

---

## Design system rules (non-negotiable)

Source: `/Users/sam/Projects/specview/docs/design-system.md`

- CSS font tokens: `var(--serif)` = Playfair Display, `var(--body)` = Source Serif 4, `var(--sans)` = Source Sans 3
- No `box-shadow` anywhere
- No `border-radius` on buttons, cards, or panels (square only)
- Hover = `rgba` background fill only — never a border or color change on new elements
- Borders for structure: `3px solid var(--ink)` = major break, `1px solid var(--border)` = divider
- Existing button classes: `.btn-primary` and `.btn-secondary` — reuse, do not add new button classes

---

## Task 1 — Remove self-host section

**Agent**: spec-frontend  
**Effort**: 0.5h  
**Files**: `landing/index.html`

### Steps

1. In the `<nav class="section-bar">`, remove the anchor `<a href="#self-host">Self-host</a>`.

2. Remove the section heading div:
   ```html
   <div class="section-heading" id="self-host">Self-host in minutes</div>
   ```

3. Remove the entire `<section class="steps">` block that follows (the 3-step Clone / Configure / Run section). It ends at `</section>` before `<!-- Footer -->`.

4. In the footer `<nav class="footer-links">`, remove `<a href="http://localhost:8095">Open App</a>`.

5. Do not touch any other section. Do not remove the `#how` steps section — that is the "How it works" section, not self-host.

### Verify

- [ ] `grep -n "self-host" landing/index.html` returns zero results
- [ ] `grep -n "localhost" landing/index.html` returns zero results
- [ ] Page structure: masthead → nav → lede → output → how → demo → pullquotes → footer

---

## Task 2 — Update hero CTAs

**Agent**: spec-frontend  
**Effort**: 0.5h  
**Files**: `landing/index.html`

### Context

The hero currently has:
```html
<div class="cta-row">
  <a href="#self-host" class="btn-primary">Self-host free</a>
  <a href="#how" class="btn-secondary">See how it works</a>
</div>
```

Replace both anchors in place. Keep `.cta-row`, keep the classes.

### Steps

Replace the `<div class="cta-row">` block with:

```html
<div class="cta-row">
  <a href="https://app.specview.io/signup" class="btn-primary">Try it free</a>
  <!-- AUTH_URL -->
  <a href="#pricing" class="btn-secondary">Pricing ↓</a>
</div>
```

No CSS changes needed — `.btn-primary` and `.btn-secondary` already exist in `style.css`.

### Verify

- [ ] Hero has exactly two CTAs: "Try it free" and "Pricing ↓"
- [ ] "Try it free" href = `https://app.specview.io/signup`
- [ ] "Pricing ↓" href = `#pricing`
- [ ] Both use existing classes, no new classes introduced

---

## Task 3 — Add Pricing section

**Agent**: spec-frontend  
**Effort**: 2h  
**Files**: `landing/index.html`, `landing/style.css`

### Step 1 — Add nav link

In `<nav class="section-bar">`, add after `<a href="#output">Output</a>`:

```html
<a href="#pricing">Pricing</a>
```

### Step 2 — Insert pricing HTML

Insert the following block immediately before `<hr class="divider">` (the thick rule before pullquotes):

```html
<!-- ══════════════════════════════════════
     PRICING SECTION
     ══════════════════════════════════════ -->
<div class="section-heading" id="pricing">Pricing</div>

<section class="pricing">
  <div class="pricing-grid">

    <!-- Free tier -->
    <div class="pricing-tier">
      <p class="pricing-tier-name">Free</p>
      <p class="pricing-price">
        <span class="pricing-amount">$0</span>
        <span class="pricing-period">/ month</span>
      </p>
      <p class="pricing-desc">
        For developers exploring AI-structured spec docs. Three projects a month
        gives you room to evaluate the workflow before committing.
      </p>
      <ul class="pricing-features">
        <li>3 projects / month</li>
        <li>Full spec generation pipeline</li>
        <li>Analysis, epic, architecture &amp; timeline</li>
        <li>No credit card required</li>
      </ul>
      <div class="pricing-cta">
        <a href="https://app.specview.io/signup" class="btn-primary">Try it free</a>
        <!-- AUTH_URL -->
      </div>
    </div>

    <!-- 1px column divider -->
    <div class="pricing-divider" aria-hidden="true"></div>

    <!-- Pro tier -->
    <div class="pricing-tier">
      <p class="pricing-tier-name">Pro</p>
      <p class="pricing-price">
        <span class="pricing-amount">$29</span>
        <span class="pricing-period">/ month</span>
      </p>
      <p class="pricing-desc">
        For solo developers and small-team PMs who want unlimited spec generation
        without managing infrastructure. One seat, one decision.
      </p>
      <ul class="pricing-features">
        <li>Unlimited projects</li>
        <li>Full spec generation pipeline</li>
        <li>Analysis, epic, architecture &amp; timeline</li>
        <li>Priority support</li>
      </ul>
      <div class="pricing-cta">
        <a
          href="https://buy.stripe.com/test_6oUeVdaA1aVF27s1JVao800"
          class="btn-primary"
          target="_blank"
          rel="noopener noreferrer"
        >Get Pro — $29/mo</a>
        <!-- STRIPE_URL -->
      </div>
    </div>

  </div>
</section>
```

### Step 3 — Append CSS to `landing/style.css`

Append at the very end of `landing/style.css`:

```css
/* ── Pricing Section ───────────────────────────────── */
.pricing {
  border-bottom: 1px solid var(--border);
  padding: 0 40px 40px;
}

/* 1fr 1px 1fr — middle column IS the divider */
.pricing-grid {
  display: grid;
  grid-template-columns: 1fr 1px 1fr;
  gap: 0 40px;
}

.pricing-divider {
  background: var(--border);
}

.pricing-tier {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 32px 0;
}

.pricing-tier-name {
  font-family: var(--serif);
  font-size: 28px;
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}

.pricing-price {
  margin: 0;
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.pricing-amount {
  font-family: var(--serif);
  font-size: 48px;
  font-weight: 700;
  color: var(--ink);
  line-height: 1;
}

.pricing-period {
  font-family: var(--sans);
  font-size: 13px;
  color: var(--ink-muted);
}

.pricing-desc {
  font-family: var(--body);
  font-size: 15px;
  line-height: 1.65;
  color: var(--ink-light);
  margin: 0;
}

.pricing-features {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pricing-features li {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink);
  padding-left: 16px;
  position: relative;
}

.pricing-features li::before {
  content: '—';
  position: absolute;
  left: 0;
  color: var(--ink-muted);
}

.pricing-cta {
  margin-top: auto;
  padding-top: 8px;
}

/* Mobile */
@media (max-width: 640px) {
  .pricing-grid {
    grid-template-columns: 1fr;
    gap: 0;
  }
  .pricing-divider {
    width: 100%;
    height: 1px;
    margin: 0;
  }
}
```

### Verify

- [ ] `grep -n "pricing" landing/index.html` shows: nav link, section heading, section element
- [ ] Pricing section renders between "How it works" demo area and the pullquotes
- [ ] Two tier columns separated by 1px divider — no card backgrounds, no shadows, no border-radius
- [ ] Correct font tokens: `var(--serif)`, `var(--body)`, `var(--sans)` — grep confirms no `--font-` prefix variants
- [ ] Free CTA: `href="https://app.specview.io/signup"` marked `<!-- AUTH_URL -->`
- [ ] Pro CTA: Stripe URL, `target="_blank"`, marked `<!-- STRIPE_URL -->`
- [ ] Mobile: tiers stack vertically with horizontal divider at ≤640px

---

## Task 4 — QA pass

**Agent**: spec-frontend  
**Effort**: 0.5h  
**Files**: read-only review

### Checks

Run these greps and confirm:

```bash
# No self-host anywhere
grep -n "self-host\|Self-host\|localhost" landing/index.html

# Correct AUTH_URL occurrences (expect 2: hero + pricing free tier)
grep -n "AUTH_URL\|app.specview.io" landing/index.html

# Correct STRIPE_URL (expect 1: pricing pro tier)
grep -n "STRIPE_URL\|buy.stripe.com" landing/index.html

# No forbidden CSS patterns
grep -n "border-radius\|box-shadow\|--font-" landing/style.css | grep -v "^.*:.*\/\*"

# Font tokens correct
grep -n "var(--serif)\|var(--body)\|var(--sans)" landing/style.css | tail -20
```

### Visual checklist

- [ ] Nav: What | How it works | Output | Pricing (no Self-host)
- [ ] Hero: "Try it free" + "Pricing ↓" (no self-host link)
- [ ] Pricing section visible after demo/pullquotes area
- [ ] Footer: GitHub link only (no localhost)
- [ ] No horizontal scroll at 375px
- [ ] Dark mode toggle still works

---

## Integration map

```
landing/index.html
│
├── nav: What | How it works | Output | Pricing
│
├── #what (hero)
│   └── .cta-row
│       ├── "Try it free" → AUTH_URL          <!-- AUTH_URL ×1 -->
│       └── "Pricing ↓"  → #pricing
│
├── #pricing  (NEW — Task 3)
│   ├── Free tier → "Try it free" → AUTH_URL  <!-- AUTH_URL ×2 -->
│   └── Pro tier  → "Get Pro"    → STRIPE_URL <!-- STRIPE_URL ×1 -->
│
└── footer: GitHub only
```

**Two config strings. Two AUTH_URL anchors. One STRIPE_URL anchor.**
