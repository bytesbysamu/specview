# 🛠️ Task 1: Landing Page

**Purpose**: Establish web presence at trendfy.me with a static page that communicates the virtual try-on value proposition and captures early interest before the full product launches.

**Effort**: 1 day

**Dependencies**: None

**Parallel With**: Task 2 (API scaffolding) can start simultaneously

**Blocks**: Nothing directly—landing page is independent of app development

**Related**:
- [Architecture](./architecture.md)
- [Epic](./epic.md)

---

## Overview

### What's Included
- Single-page static HTML/CSS landing page
- Hero section with value proposition
- Example try-on results gallery (before/after images)
- Email capture form for launch notifications
- Mobile-responsive layout
- Basic SEO meta tags

### What's NOT Included
- Backend functionality — static page only, email form posts to third-party (Formspree/Netlify Forms)
- User accounts — no auth, no database
- Live try-on demo — uses pre-generated example images
- Analytics dashboard — just embed tracking snippet

---

## Prerequisites

Before starting:
- Domain `trendfy.me` configured with DNS pointing to hosting (Vercel, Netlify, or Cloudflare Pages)
- 4-6 high-quality before/after try-on examples prepared (can be generated via Replicate during development)
- Brand decisions: colors, typography, logo (even placeholder)

---

## Implementation Steps

### Step 1: Project Setup

**File**: `landing/index.html`

**Purpose**: Create minimal project structure for static deployment

Set up a simple folder that can deploy to any static host. No build step needed—just HTML, CSS, and assets.

```
landing/
├── index.html
├── styles.css
├── assets/
│   ├── logo.svg
│   ├── examples/
│   │   ├── example-1-before.jpg
│   │   ├── example-1-after.jpg
│   │   └── ...
│   └── og-image.jpg
└── favicon.ico
```

### Step 2: HTML Structure

**File**: `landing/index.html`

**Purpose**: Semantic markup for all page sections

**Pattern**:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Trendfy — AI Virtual Try-On</title>
  <meta name="description" content="See how any outfit looks on you before you buy. AI-powered virtual try-on.">
  
  <!-- Open Graph -->
  <meta property="og:title" content="Trendfy — AI Virtual Try-On">
  <meta property="og:description" content="See how any outfit looks on you before you buy.">
  <meta property="og:image" content="https://trendfy.me/assets/og-image.jpg">
  
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header class="hero">
    <!-- Logo, headline, subhead, CTA -->
  </header>
  
  <section class="examples">
    <!-- Before/after gallery -->
  </section>
  
  <section class="how-it-works">
    <!-- 3-step explanation -->
  </section>
  
  <section class="signup">
    <!-- Email capture form -->
  </section>
  
  <footer>
    <!-- Minimal footer -->
  </footer>
</body>
</html>
```

### Step 3: Hero Section

**File**: `landing/index.html` (hero section)

**Purpose**: Communicate value proposition in 5 seconds or less

The hero needs to answer: "What is this?" and "Why should I care?" immediately.

**Pattern**:
```html
<header class="hero">
  <nav>
    <img src="assets/logo.svg" alt="Trendfy" class="logo">
  </nav>
  
  <div class="hero-content">
    <h1>See how any outfit looks on you</h1>
    <p class="subhead">Upload your photo. Paste any clothing link. Get a realistic try-on in seconds.</p>
    <a href="#signup" class="cta-button">Get Early Access</a>
  </div>
  
  <!-- Hero image: single compelling before/after -->
  <div class="hero-image">
    <img src="assets/examples/hero-result.jpg" alt="Virtual try-on example">
  </div>
</header>
```

### Step 4: Examples Gallery

**File**: `landing/index.html` (examples section)

**Purpose**: Prove the technology works with real results

Show 3-4 diverse examples: different body types, clothing styles, and use cases.

**Pattern**:
```html
<section class="examples">
  <h2>Real Results</h2>
  <div class="examples-grid">
    <div class="example">
      <div class="before-after">
        <img src="assets/examples/example-1-before.jpg" alt="Before">
        <img src="assets/examples/example-1-after.jpg" alt="After try-on">
      </div>
      <p class="caption">Dress from Zara</p>
    </div>
    <!-- Repeat for 3-4 examples -->
  </div>
</section>
```

### Step 5: Email Capture Form

**File**: `landing/index.html` (signup section)

**Purpose**: Collect emails for launch notification without building backend

Use Formspree or Netlify Forms to handle submissions. Zero backend code required.

**Pattern** (Formspree):
```html
<section id="signup" class="signup">
  <h2>Be First to Try It</h2>
  <p>We're launching soon. Get early access.</p>
  
  <form action="https://formspree.io/f/YOUR_FORM_ID" method="POST">
    <input 
      type="email" 
      name="email" 
      placeholder="your@email.com" 
      required
    >
    <button type="submit">Notify Me</button>
  </form>
</section>
```

**Pattern** (Netlify Forms—if hosting on Netlify):
```html
<form name="waitlist" method="POST" data-netlify="true">
  <input type="email" name="email" required>
  <button type="submit">Notify Me</button>
</form>
```

### Step 6: Responsive Styles

**File**: `landing/styles.css`

**Purpose**: Clean, mobile-first styling

Keep CSS minimal. Use system fonts or a single Google Font. The goal is fast load time and readable code.

**Pattern**:
```css
:root {
  --primary: #6366f1;
  --text: #1f2937;
  --bg: #ffffff;
  --gray: #6b7280;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, -apple-system, sans-serif;
  color: var(--text);
  line-height: 1.6;
}

/* Mobile-first hero */
.hero {
  padding: 2rem 1rem;
  text-align: center;
}

.hero h1 {
  font-size: 2rem;
  margin-bottom: 1rem;
}

.cta-button {
  display: inline-block;
  background: var(--primary);
  color: white;
  padding: 0.875rem 2rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 600;
}

/* Desktop breakpoint */
@media (min-width: 768px) {
  .hero {
    padding: 4rem 2rem;
  }
  
  .hero h1 {
    font-size: 3rem;
  }
  
  .examples-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2rem;
  }
}
```

### Step 7: Analytics & Tracking

**File**: `landing/index.html` (before `</head>`)

**Purpose**: Track visits and conversions without building dashboards

Add Plausible (privacy-friendly) or Google Analytics. One snippet, no configuration.

**Pattern** (Plausible):
```html
<script defer data-domain="trendfy.me" src="https://plausible.io/js/script.js"></script>
```

**Pattern** (Google Analytics):
```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### Step 8: Deploy

**Purpose**: Get the page live at trendfy.me

**Option A: Vercel** (recommended for simplicity)
```bash
cd landing
npx vercel --prod
# Configure custom domain in Vercel dashboard
```

**Option B: Netlify**
```bash
# Drag landing/ folder to Netlify dashboard
# Or connect Git repo for auto-deploy
```

**Option C: Cloudflare Pages**
```bash
# Connect repo, set build output to landing/
```

---

## Verification

How to verify this implementation works:

```bash
# Local preview
cd landing
python -m http.server 8000
# Open http://localhost:8000
```

**Manual checks**:
1. Page loads in under 2 seconds (check Network tab)
2. Hero is readable on mobile (use DevTools device mode)
3. Email form submits successfully (check Formspree dashboard)
4. All images load correctly
5. Meta tags render in social preview (use https://metatags.io)

**Expected Result**: 
- trendfy.me shows landing page
- Email submissions appear in Formspree/Netlify
- Page scores 90+ on Lighthouse Performance

---

## Next Steps

After completing this task:
1. Update [Timeline](./timeline.md) to mark Task 1 done
2. Share URL for early feedback on messaging
3. Proceed to Task 2 (API scaffolding) or Task 3 (app scaffold)—both can start independently

---

## Related Documents

- [Architecture](./architecture.md) – Subdomain strategy rationale
- [Epic](./epic.md) – Task scope and MVP definition
- [Timeline](./timeline.md) – Status tracking