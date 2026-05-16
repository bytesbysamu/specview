# Groad → Specview: Design Case Study Analysis

Source: Groad Food Ordering UI/UX Case Study (Behance, 12 pages, PDF at docs/design-references/)
Cross-referenced with: design-system.md, clawboi-design-system.md, landing-v2.html, static-playground-original.html, specview-landing-wireframe.jsx

---

## 1. How Groad tells its story (the template)

Groad follows a classic Behance case study arc:

1. **Hero** — product name + tagline + hero screenshot
2. **Problem** — one paragraph framing the need
3. **Process** — 5-stage design process (Understand → Research → Sketch → Design → Implement → Evaluate)
4. **Branding** — logo grid + color palette + type specimen
5. **Research** — user interview goals (project goals vs user goals), target user persona
6. **Journey map** — horizontal timeline: trigger → browsing → ordering → waiting → delivery → follow-up
7. **User flow** — branching diagram: Discovery & Choose → Pay → Verify
8. **Screen gallery** — every major screen with annotation labels
9. **Patterns** — UI themes (light/dark), infinite scroll, payment methods
10. **Closing** — logo + follow button

**Key insight:** Groad doesn't just show screens — it explains WHY each screen exists by linking it back to the journey map. Every screen is a station on the user's path.

---

## 2. What Specview already has (from our collected files)

### From landing-v2.html
- Hero: "Write messy. Ship clean." + file generation aside showing analysis.md, epic.md generating in real time
- Stat strip: 44.5s avg generation, 5 files per run, 0 human code lines, Free to start
- "What ships" section with 5-file breakdown
- "See it" section (live demo placeholder)
- Pull quote: "I wrote 3 paragraphs. 47 seconds later I had an analysis, an epic, and an architecture doc."
- Steps: Braindump → Generate → Read & Build

### From design-system.md (the philosophy)
- Dieter Rams minimalism + editorial newspaper layout
- "Information density without clutter"
- "Typography does the heavy lifting — no decorative UI chrome"
- "Borders and whitespace as structure, not decoration"
- "Ink on paper: cream background, near-black ink, no shadows"
- "Interaction is quiet — hover states are barely-there"

### From clawboi-design-system.md (the heritage)
- Identical tokens to specview — shared lineage
- ClawBoi dashboard was the first implementation
- Newspaper grid, editorial voice, Playfair Display headlines originated here
- Specview inherited and extended the system

### From static-playground-original.html (2,304 lines)
- Complete component catalog: 17 subsections
- CSS code snippets for every component
- "App vs Landing" comparison table
- "ClawBoi Origin vs Specview" heritage table
- Live animation demos with Replay buttons
- Every component in every state

### From specview-landing-wireframe.jsx
- Section-based scroll architecture
- Sticky header with progress
- 6 sections: hero, what, how, see-it, pricing, footer

---

## 3. Groad vs Specview — Design language contrast

| Aspect | Groad | Specview |
|--------|-------|---------|
| **Philosophy** | Friendly, approachable, food = comfort | Editorial, authoritative, newspaper = trust |
| **Corners** | Rounded (16px radius) | Sharp (0-2px radius) |
| **Elevation** | Card shadows throughout | Borders only, zero shadows (except modal intentionally) |
| **Color strategy** | Warm coral accent (#FF6B6B), multi-color payment cards | Muted slate blue (#567B95), monochrome with red for alerts |
| **Typography** | SF Pro Text (single family, 3 weights) | 3-font stack: Playfair Display, Source Serif 4, Source Sans 3 |
| **Layout** | Card grid with generous padding | Newspaper grid with hairline borders as dividers |
| **Nav pattern** | Bottom tab bar (mobile-first) | Section pill bar with count badges (desktop-first) |
| **Onboarding** | Illustration-heavy (3 splash screens) | Content-first (landing pitch IS the onboarding) |
| **Dark mode** | Driver dashboard only | Full-page toggle, every component flips |
| **Empty states** | Illustrations + friendly copy | Minimal text only |
| **Status indicators** | Color-coded dots + progress bars | 4-state status bar with CSS animation |
| **Data density** | Low — generous whitespace, one action per screen | High — newspaper column layout, multi-file sidebar, metadata overlines |

---

## 4. What to steal from Groad (adapt to newspaper aesthetic)

### Narrative structure ✅ steal
Groad's problem → process → branding → journey → screens arc is universal. Specview's playground should follow the same narrative flow, just with newspaper styling instead of card-based mobile UI.

### Journey map ✅ steal
Groad's horizontal timeline (trigger → browsing → ordering → waiting → delivery) maps directly to Specview's pipeline (braindump → analysis → epic → architecture → impl guide). Visualize this as a horizontal newspaper-style timeline.

### Before/after transformation ✅ steal
Groad shows raw ingredients → finished dish. Specview shows messy braindump → structured documents. The transformation IS the value prop. Show it explicitly.

### Screen annotation pattern ✅ steal
Groad labels every screen with what it does and why. The playground's screen gallery should annotate each component: "This is the reader panel — it renders specs in a 2-column newspaper layout because information density matters for engineers reading technical docs."

### Process visualization ✅ steal
Groad's 5-stage process bar is clean and scannable. Specview's 5-step pipeline (braindump → analysis → epic → architecture → impl guide) should be visualized the same way — horizontal, with icons, clickable.

### Design token showcase ✅ already built
Groad shows its color palette and type specimens. Our pg-tokens component already does this — just needs narrative context.

### User goals framing ✅ steal
Groad splits into "Project Goals" and "User Goals." For Specview:
- **Product goal:** Generate structured engineering docs from unstructured input
- **User goal:** Think before coding without the friction of writing formal documents

---

## 5. What NOT to steal from Groad

### Mobile-first patterns ❌
Bottom nav bar, full-screen modals, swipe gestures — Specview is desktop-first. Keep the section nav bar, modal overlays, and click interactions.

### Illustration-heavy onboarding ❌
Groad uses 3 splash screens with custom illustrations. Specview's landing pitch IS the onboarding — the product demonstrates itself. No illustrations needed.

### Rounded corners ❌
Sharp corners are a core design principle. "No radius" is part of the newspaper identity.

### Shadow elevation ❌
"Borders and whitespace as structure, not decoration." The modal's intentional shadow is the only exception.

### Warm/friendly tone ❌
Groad is comfort food. Specview is a broadsheet newspaper. The editorial voice stays.

---

## 6. The narrative arc for Playground 2.0

Combining Groad's structure with Specview's design language:

### Act 1: The Hook (above the fold)
**Groad equivalent:** Hero + problem statement
**Specview:** "Write messy. Ship clean." + live generation demo running in background. Stat strip: 44.5s / 5 files / 0 code / Free.

### Act 2: The Method (how it works)
**Groad equivalent:** Design process + branding
**Specview:** The 5-step pipeline visualized as a horizontal newspaper-style flow. Each step is clickable — shows the actual document. Below: the design language section (tokens, typography, borders) with the philosophy quote.

### Act 3: The Journey (user flow)
**Groad equivalent:** Journey map + user flow diagram
**Specview:** The path from anonymous visitor to power user. Land → try playground → sign up → create project → generate → read → iterate → upgrade → share. Each station is a mini-demo.

### Act 4: The Product (screen gallery)
**Groad equivalent:** All screens annotated
**Specview:** Every major screen as a live component with editorial annotation. Project grid, expanded reader, status bar states, AI ops, billing flow. "This is the reader panel — it uses a 2-column newspaper layout because..."

### Act 5: The System (design patterns)
**Groad equivalent:** UI themes + patterns summary
**Specview:** Border catalog, animation gallery, state matrix, dark mode toggle. Already built — just needs the narrative wrapper.

### Act 6: The Heritage (where it came from)
**Groad equivalent:** (doesn't have this — we add it)
**Specview:** ClawBoi → Specview evolution. The newspaper grid's origin. Why Playfair Display. Why no shadows. The design system as a living document.
