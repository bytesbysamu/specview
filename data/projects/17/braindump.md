# Braindump: landing-polish-newspaper

## What this is

Polish the Specview landing page (`landing/index.html` + `landing/style.css`) to fully embody the newspaper aesthetic that the app is being aligned to. The landing page is the reference surface — it established the masthead, overline, and section-bar patterns — but it has its own gaps against the mature design system. This epic applies the same editorial discipline inward: tighten copy, fix typography gaps, add a live demo strip, replace the flat aside list with a visual output grid, and ensure dark mode is as polished as light.

**Playground** (verbatim implementation reference): `http://localhost:8096/playground.html`
All tokens, component states, and CSS snippets there are the contract. Copy values verbatim.

---

## Source: full content of ux-polish-newspaper-1778238000

*Included below verbatim as reference material. This project adapts those decisions for the landing page (static HTML/CSS) rather than the Angular app.*

### Design philosophy

**Dieter Rams minimalism + editorial newspaper layout.**

- Typography does the heavy lifting — no decorative UI chrome
- Borders and whitespace create structure; shadows do not exist here
- Ink on paper: cream (`#FFFEF9`) not white, near-black (`#121212`) not black
- Interaction is quiet — hover is a whisper of background, nothing more
- Density without clutter: if it doesn't communicate something, it doesn't exist

The reader should focus entirely on content and ideas. The interface communicates structure through **semantic UX** — visual hierarchy from typography, spatial rhythm, and color used for meaning only.

### Token system (from playground — copy verbatim)

```css
:root {
  --bg: #FFFEF9;
  --ink: #121212;
  --ink-light: #5A5A5A;
  --ink-muted: #999999;
  --border: #DFDFDF;
  --border-dark: #121212;
  --accent: #567B95;
  --red: #C41E3A;
  --serif: 'Playfair Display', Georgia, serif;
  --body: 'Source Serif 4', Georgia, serif;
  --sans: 'Source Sans 3', system-ui, sans-serif;
}
[data-theme="dark"] {
  --bg: #141414;
  --ink: #E8E6E0;
  --ink-light: #A0A0A0;
  --ink-muted: #606060;
  --border: #2E2E2E;
  --border-dark: #E8E6E0;
  --accent: #7BAFC8;
  --red: #E05A72;
}
```

### Overline pattern (from style.css — already exists in landing, keep as-is)

```css
.overline {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--red);
  margin-bottom: 14px;
  display: block;
}
```

### Masthead spec (from landing HTML — landing is the reference)

```
grid: 3 columns (150px / 1fr / 150px), align-items: flex-end
title: Playfair Display 64px, weight 700, letter-spacing -0.02em
tagline: ** SOURCE SERIF 4 italic 13px ** color: var(--ink-light)  ← gap: currently Source Sans
date label: Source Sans 11px uppercase, letter-spacing 0.08em, ink-muted
```

### Nameplate rule (from landing CSS — already correct)

```css
.section-bar { border-top: 3px solid var(--ink); }
```

### Semantic color rules (non-negotiable from UX spec)

| Token | Meaning | Do not use for |
|-------|---------|----------------|
| `--red` | Error, alert, overline | Neutral decoration |
| `--accent` | Primary interactive action | Decoration |
| `--ink` | Primary content, borders | — |
| `--ink-muted` | Absence of state | Any meaningful state |

**Rule: never use gray for a state.** Gray = no semantic meaning.

### Icon system (from UX spec)

All content icons: 13px / stroke-width 1.75. The landing's aside-list already uses this — keep it.

```css
.aside-list svg { width: 13px; height: 13px; stroke-width: 1.75; }
```

---

## Current landing page — what exists

### Structure (from index.html)

1. **Masthead** — `h1.masthead-title` ("Spec Doc"), `.masthead-tagline` ("All the Specs Fit to Build"), date label, theme toggle
2. **Section bar** — What / How it works / Pricing (3 nav links, centered)
3. **Hero / lede** — 3-column grid: lede-main (overline + headline + deck + CTA row) | 1px divider | lede-aside (output list)
4. **Metrics bar** — 764+ tests · 433 commits · 36 projects · 0 human code lines
5. **How it works** — 3-column step grid with code-block mockups (Braindump / Generate / Build)
6. **Pricing** — Free ($0) vs Pro ($29), 2-column grid with divider
7. **Pullquote** — single centered Playfair italic testimonial
8. **Footer** — brand / copy / GitHub link

### CSS classes with no HTML usage (dead or planned)

The stylesheet has rules for `.output-grid`, `.output-card`, `.demo-strip`, `.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content` — these are defined but not in the HTML. This is the demo section that hasn't been wired up.

### Typography gap

`.masthead-tagline` uses `font-family: var(--sans)` (Source Sans 3). Per the design system and the app alignment work, it should be `font-family: var(--body)` (Source Serif 4) italic. Source Serif italic at 13px reads as a newspaper deck; Source Sans reads as a UI label.

### Hero aside gap

The lede-aside currently uses a plain `<ul>` list showing the 5 output types (Analysis, Epic, Architecture, Timeline, Implementation Guide) with their subtitles. The CSS has a full `.output-grid` / `.output-card` system that would give each output type a card with an icon, filename, and description. This gives far more editorial weight to what gets generated.

### Demo strip gap

The CSS has a complete `.demo-strip` component — a miniaturized newspaper-style UI mockup (masthead, sidebar, content pane) that shows what the app looks like. It's not in the HTML. This is the highest-conversion element: seeing the app's newspaper aesthetic inside the marketing page proves the product delivers what the landing promises.

### Steps content gap

Step 1 (Braindump) and Step 3 (Build) show realistic code-block mockups. Step 2 (Generate) shows a progress bar. The step bodies have no `<p class="step-body">` — just `.step-code` blocks. Adding a one-sentence body above each code block would give the steps editorial rhythm.

---

## What the polish achieves

**Before:** Landing page establishes the newspaper aesthetic but doesn't demonstrate the product at depth. The output list is flat. The demo section exists in CSS but isn't rendered. The tagline uses the wrong font family.

**After:** Every section proves the thesis. The masthead uses Source Serif italic for the tagline (matching the design system intention). The hero aside becomes an output card grid showing each generated document with its editorial weight. A demo strip section shows the app UI inside the marketing surface — so the user sees what they're buying before they click. The steps gain one-sentence editorial bodies.

Opening the landing should feel like reading a newspaper that has a mission: turn your thoughts into engineering specs. Every section makes that case differently — the masthead declares it, the hero demonstrates it, the demo strip shows it, the steps explain it, the pricing prices it.

---

## Explicit gaps to fix

1. **Tagline font** — `var(--sans)` → `var(--body)` italic. One CSS line change.
2. **Output cards in hero** — replace `.lede-aside` content with a 2-column `.output-grid` of 5 `.output-card` elements (Analysis, Epic, Architecture, Timeline, Implementation Guide). Each card: icon + Playfair title + monospace filename + body text.
3. **Demo strip section** — add a `.demo-strip` section between "How it works" and "Pricing". Shows a miniaturized app UI (masthead with newspaper title, sidebar with file list, content pane with spec preview). Uses existing CSS — just needs the HTML.
4. **Step body text** — add a `<p class="step-body">` above each `.step-code` block with one editorial sentence per step.
5. **Metrics update** — numbers should reflect current state (update tests/commits/projects counts).
6. **Dark mode audit** — verify `.step-code` dark treatment, `.output-card` hover state, `.demo-strip` in dark.
7. **Section nav** — currently only 3 items (What / How it works / Pricing). If a demo section is added, add a "Demo" nav link.

## Explicitly out of scope

- App (`web-ng/`) — handled by `ux-polish-newspaper-1778238000`
- New design tokens — existing token set is sufficient
- Playground HTML changes — playground is a read-only reference
- Responsive overhaul — existing breakpoints are fine
- JS logic changes — only theme toggle exists; no new behaviour

## Hard constraints

- All CSS changes must be in `landing/style.css` — no inline styles
- No shadows anywhere except the existing dark-mode modal exception in the app
- No new font families — Playfair Display, Source Serif 4, Source Sans 3 are the complete set
- The `.overline` class is already correct — do not modify its definition
- `docker compose build landing && docker compose up -d landing` must pass before pushing
