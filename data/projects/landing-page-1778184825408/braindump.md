Brain Dump 1: Landing Page — Add SaaS CTA + Pricing
What
The landing page currently only shows self-host. There's no "Sign up and use it now" path. Add a hosted option above the self-host section. Two buttons in the hero: "Try it free" (goes to the deployed Specview auth page) and "Self-host" (scrolls to current section). Add a simple pricing section: Free (3 projects/month), Pro $29/month (unlimited). Stripe checkout link for Pro.
Why now
The landing page is live but has no conversion path for people who don't want to self-host. Most visitors won't clone a repo. They want to click sign up and try it.
What's missing
Stripe product IDs for $29/month. The Specview app URL to link to. A signup/login route that handles new users.

# Newspaper Design System — UI/UX Snapshot

> Canonical reference for the shared aesthetic across ClawBoi dashboard and Specview landing.
> Preserve and extend from this. Do not drift from these tokens without updating this doc.

---

## Philosophy

**Dieter Rams minimalism + editorial newspaper layout.**

- Information density without clutter
- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace as structure, not decoration
- Ink on paper: cream background, near-black ink, no shadows
- Interaction is quiet — hover states are barely-there, not flashy

---

## Design Tokens

These are identical across ClawBoi and Specview landing. Single source of truth.

### Colors

```css
/* Light mode */
--bg:          #FFFEF9   /* warm off-white, not pure white */
--ink:         #121212   /* near-black, not pure black */
--ink-light:   #5A5A5A   /* secondary text */
--ink-muted:   #999999   /* labels, meta, timestamps */
--border:      #DFDFDF   /* light rule lines */
--border-dark: #121212   /* thick section breaks */
--accent:      #567B95   /* muted slate blue — used sparingly */
--red:         #C41E3A   /* overline labels, badges, alerts */

/* Dark mode */
--bg:          #141414
--ink:         #E8E6E0
--ink-light:   #A0A0A0
--ink-muted:   #606060
--border:      #2E2E2E
--border-dark: #E8E6E0
--accent:      #7BAFC8
--red:         #E05A72
```

### Typography

Three-font stack — each with a clear role:

| Variable | Font | Role |
|----------|------|------|
| `--serif` | Playfair Display | Headlines, titles, pull quotes, numbers |
| `--body`  | Source Serif 4   | Body copy, paragraphs, reading text |
| `--sans`  | Source Sans 3    | Labels, metadata, UI chrome, uppercase tags |

**Rules:**
- Playfair = signal. Use for things that should feel editorial/important.
- Source Serif = reading. Body text, multi-sentence content.
- Source Sans = function. Anything small, uppercase, spaced, or UI-adjacent.
- Never use system fonts for visible content — always assign explicitly.

### Type Scale

```
Masthead title:   56–64px  Playfair 700, tracking -0.02em
Hero headline:    44px     Playfair 700, tracking -0.01em
Section title:    28–36px  Playfair 700
Card title:       18–22px  Playfair 700
Body:             15–17px  Source Serif, line-height 1.65–1.75
Label:            11–12px  Source Sans 600, uppercase, tracking 0.08–0.12em
Meta/muted:       11px     Source Sans 400, tracking 0.04–0.06em
```

---

## Layout System

### Container

```css
.page {
  max-width: 1400px;
  margin: 0 auto;
}
```
- ClawBoi: `padding: 20px 40px`
- Specview landing: no padding on `.page`, padding lives on each section

### Grid Patterns

**Masthead** — 3-column grid, forces perfect title centering:
```css
grid-template-columns: 150px 1fr 150px;
align-items: flex-end; /* bottom-align for editorial feel */
```

**Newspaper column grid** (ClawBoi memory items):
```css
grid-template-columns: repeat(3, 1fr);
/* columns separated by border-right: 1px solid var(--border) */
```

**Hero/Lede** (Specview landing):
```css
grid-template-columns: 1fr 1px 340px; /* main | divider | aside */
```

**Output cards** (Specview landing):
```css
grid-template-columns: repeat(4, 1fr);
/* each card: border-right, last has none */
```

**Lead + sidebar** (ClawBoi):
```css
grid-template-columns: 1fr 300px;
```

### Spacing

- Section padding: `40px` horizontal, `32–40px` vertical
- Component padding: `24–32px`
- Dense lists: `10–12px` vertical padding per item
- Gap between grid columns: `0` (borders do the work) or `24–32px`

---

## Border System

The entire visual hierarchy is built on borders, not cards or shadows.

| Use | Rule |
|-----|------|
| Masthead bottom | `1px solid var(--border)` |
| Section nameplate break | `3px solid var(--ink)` (top of section-bar) |
| Between sections | `1px solid var(--border)` |
| Footer top | `3px solid var(--ink)` |
| Widget title underline | `2px solid var(--ink)` |
| Column dividers | `1px solid var(--border)` (border-right on grid children) |
| Expanded panel top | `3px solid var(--ink)` |
| `<hr>` thick | `3px solid var(--border-dark)` |

**Rule:** 3px ink = major structural break. 2px ink = section label underline. 1px border = content divider.

---

## Component Inventory

### Masthead

Both products share this structure:

```
[ Edition/label ]  [ Date / TITLE / Tagline ]  [ Actions ]
                      grid: 150px 1fr 150px
```

- Edition: 11px Source Sans, uppercase, `var(--ink-muted)`
- Date: 11–12px Source Sans, uppercase, `var(--ink-light)`
- Title: 56–64px Playfair 700, tracking -0.02em
- Tagline: 12–13px Source Sans, **italic** (not uppercase)
- Theme toggle: `border: 1px solid var(--border)`, square (no border-radius)

### Section Navigation Bar

```css
display: flex;
justify-content: center;          /* centered, newspaper-authentic */
border-top: 3px solid var(--ink); /* nameplate rule above */
border-bottom: 1px solid var(--border);
```

Links: 11px Source Sans 600, uppercase, tracking 0.08em, `border-right: 1px solid var(--border)` between items.

### Section Heading Label

```css
font: 11px/700 Source Sans, uppercase, tracking 0.12em
padding: 12px 40px
border-bottom: 1px solid var(--border)
```

Used as a full-width label strip before content sections.

### Widget Title (ClawBoi sidebar)

```css
font: 11px/600 Source Sans, uppercase, tracking 0.1em
color: var(--ink-muted)
border-bottom: 2px solid var(--ink)  /* the underline rule */
padding-bottom: 6px
```

### Overline / Badge

```css
/* Overline (Specview) */
font: 11px/600 Source Sans, uppercase, tracking 0.12em
color: var(--red)
display: block
margin-bottom: 14px

/* Badge (ClawBoi badge-new) */
background: var(--red)
color: white
font: 9px/600 Source Sans, uppercase, tracking 0.05em
padding: 2px 6px
border-radius: 2px
```

### Hover State (universal)

```css
transition: background 0.15s;

:hover {
  background: rgba(0,0,0,0.02);   /* light mode */
}

[data-theme="dark"] :hover {
  background: rgba(255,255,255,0.03);
}
```
Used on: memory items, output cards, steps, headline items. Never a border change or scale — just a whisper of background.

### Pull Quote

```css
/* ClawBoi — centered, full-width */
text-align: center;
padding: 32px 60px;
/* decorative " via ::before — 72px Playfair, color: var(--border) */

.pull-quote-text: 24px Playfair italic, line-height 1.4

/* Specview — 2-column grid */
grid-template-columns: 1fr 1px 1fr;
.pullquote-mark: 56px Playfair 700, color: var(--border)
.pullquote-text: 22px Playfair italic
.pullquote-attr: 11px Source Sans uppercase, var(--ink-muted)
```

### Expanded Panel (ClawBoi only)

Frameless inline expansion — inserts into page flow, not a modal:
```css
border-top: 3px solid var(--ink);
border-bottom: 1px solid var(--border);
padding: 40px 0;

.expanded-title: 36px Playfair, max-width 900px
.expanded-body: 16px Source Serif, line-height 1.8
                column-count: 2; column-gap: 48px;
                column-rule: 1px solid var(--border);
```

Close button: `×` character, 32px, `color: var(--ink-muted)`, no border.

### Chat Panel (ClawBoi only)

Fixed bottom-right floating panel:
- Mode toggle: ⚡ Haiku (fast) / 🦁 Sonnet (full context)
- Input: `→` send button (arrow character)
- Not a modal — overlaps page, dismissable

### 2-Column Body Text (ClawBoi)

Used in lead story and expanded panel:
```css
column-count: 2;
column-gap: 32–48px;
column-rule: 1px solid var(--border);
```
Authentic newspaper column layout for long-form content.

### Step Numbers (Specview landing)

```css
font: 64px/1 Playfair 700
color: var(--border)  /* intentionally faint — decorative, not informational */
```

### Code/Terminal Blocks (Specview landing)

```css
font-family: 'SF Mono', Consolas, monospace;
font-size: 12px;
background: var(--border);
border-left: 3px solid var(--ink-muted);
padding: 10px 14px;
```

### Mood Chart (ClawBoi only)

Bar chart of historical moods:
```css
display: flex; align-items: flex-end; gap: 4px; height: 60px;
/* bars: var(--mood-10) #2E7D32 → var(--mood-0) #C62828 */
/* tooltip via ::after on hover */
```

### Person/Tag Pills (ClawBoi sidebar)

```css
font: 12px Source Sans
padding: 4px 10px
border: 1px solid var(--border)
border-radius: 2px   /* only place radius appears */
background: var(--bg)
```

### Markdown Headings (ClawBoi expanded content)

```css
h1: 24px Playfair 700
h2: 20px Playfair 700
h3: 13px Source Sans 600, uppercase, tracking 0.05em, color: var(--ink-light)
```
H3 deliberately uses sans — signals a sub-label, not a headline.

---

## Interaction Principles

1. **No shadows** — depth comes from borders and typography size, not elevation
2. **No border-radius on structural elements** — buttons, inputs, panels are square
3. **2px radius only on pill tags** — the one exception, for inline labels
4. **Transitions: 0.15s max** — subtle, never animated
5. **Hover = `rgba` fill** — never a border change, color change, or movement
6. **Close/dismiss = `×` character** — not an icon, 28–32px, weight 300
7. **Theme toggle = icon in button** — square border, no background fill

---

## Specview Landing vs ClawBoi — Where They Differ

| Aspect | ClawBoi | Specview Landing |
|--------|---------|-----------------|
| Purpose | Live app dashboard | Static marketing page |
| Container | `max-width: 1400px` `.page` wrapper | Same, added 2026-05 |
| Masthead border | `1px solid var(--border)` | `1px solid var(--border)` (aligned 2026-05) |
| Nameplate rule | `div.divider.thick` below nav | `border-top: 3px` on `.section-bar` |
| Tagline | Italic | Italic (aligned 2026-05) |
| Section nav | Centered | Centered (aligned 2026-05) |
| Content | Dynamic JS-rendered data | Static HTML |
| Chat panel | Floating bottom-right | Not present |
| 2-col body text | Yes (lead + expanded) | Not present |
| Expanded panel | Inline frameless | Not present |
| Icons | Emoji (chat mode toggles) | Lucide SVG (added 2026-05) |

---

## Do Not

- Do not use `box-shadow` anywhere
- Do not add border-radius to cards, buttons, or panels
- Do not use color for hierarchy — use font-weight and font-size
- Do not use `--accent` (#567B95) heavily — it is a one-off highlight color
- Do not replace `--red` with a softer color — it is intentional for overlines/badges
- Do not change the font stack — all three fonts are load-bearing
- Do not use `font-weight: 400` for Playfair headlines — always 700
- Do not animate layout — transitions on `background` only

---

## Enhancements to Consider

- **2-column body text** in Specview landing lede (matches ClawBoi lead-body)
- **`section-badge`** count pattern on section headings (ClawBoi: gray pill `border-radius: 2px`)
- **Inline expansion** pattern for output cards (click → expand in place, no modal)
- **Time-labeled grids** ("This Week" / "Earlier") for any chronological content
- **Lucide icons** replacing remaining emoji in ClawBoi (chat mode toggles, chat button)