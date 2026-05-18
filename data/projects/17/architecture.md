# 🏗️ Solution Architecture: landing-polish-newspaper

## Architecture Overview

The Specview landing page is a **static, single-document marketing surface** served by `nginx:alpine` from the `landing/` directory. It consists of one HTML file (`landing/index.html`), one stylesheet (`landing/style.css`), and a small inline theme-toggle script. There is no build step, no framework, no data layer — the page is the artifact. This epic does not change that shape; it fills in HTML for component classes the stylesheet already defines and adjusts a single token reference.

The mental model is **CSS-first, HTML-thin**. The design system already lives in the stylesheet as a complete set of tokens, components (`.output-card`, `.demo-strip`, `.step-body`), and dark-mode overrides. The HTML lags behind the CSS — it has not yet rendered the components the stylesheet anticipates. Architecturally this is a wiring epic, not a design epic: the contract (CSS rules, token names, semantic colors) is fixed by the playground reference at `http://localhost:8096/playground.html`, and the work is to project that contract into the index document.

The key insight is that **the stylesheet is the source of truth and the playground is its test harness**. Components are not invented in this epic — they are instantiated. This forces a strict editing discipline: HTML structure must mirror existing CSS selectors verbatim, no new classes are introduced, and any visual question is resolved by reading the existing rule rather than writing a new one. Dark-mode parity is then a verification activity rather than a design activity, because every component already has a `[data-theme="dark"]` rule paired with its base rule.

## Design Principles

| Principle | Application |
|-----------|-------------|
| P4 — No Speculative Abstractions | No new CSS classes, no new tokens, no new font families. Every change instantiates a class that already exists in `landing/style.css`. |
| P7 — File Size & Structure | `landing/index.html` and `landing/style.css` remain the only two surfaces edited. No new files. No JS additions. |
| Editorial discipline (from braindump) | Every section must prove the newspaper thesis through structure, not decoration. Output grid replaces flat list; demo strip shows the product; step bodies add editorial rhythm. |
| Semantic color rules (non-negotiable) | `--red` only for overlines/errors, `--accent` only for interactive, `--ink-muted` only for absence-of-state. No gray as a state color in any new markup. |
| Token verbatim from playground | All values copy from the playground; no values are derived, computed, or invented. Playground is the contract. |
| Channel parity (light + dark) | Every visual change is verified in both themes before sign-off. Dark mode is not a downstream concern — it is a parallel deliverable. |

## Component Design

### Tagline Token Realignment
**Purpose**: Close the typography credibility gap at the masthead. The tagline is the first piece of body copy a visitor reads; rendering it in `var(--sans)` reads as a UI label, while `var(--body)` italic reads as a newspaper deck. This is a single-rule edit in the existing `.masthead-tagline` declaration — no new selector, no new token. The change is structural in effect (it announces the editorial register) but minimal in surface area.

### Hero Output-Card Grid
**Purpose**: Replace the flat `<ul>` inside `.lede-aside` with the existing `.output-grid` / `.output-card` system, instantiated five times — one card per generated artifact (Analysis, Epic, Architecture, Timeline, Implementation Guide). Each card carries an icon, a Playfair title, a monospace filename, and a body sentence. The architectural value is **converting enumeration into demonstration**: the visitor sees five typed deliverables with editorial weight rather than a bullet list. The CSS already defines a 2-column grid layout, hover state, border treatment, and dark-mode override — all reused unchanged.

### Demo Strip Section
**Purpose**: Render the existing `.demo-strip` component — a miniaturized newspaper-style mockup of the app UI (masthead, sidebar, content pane) — as a new section between "How it works" and "Pricing". This is the **highest-conversion component** in the epic because it collapses the gap between the marketing aesthetic and the product aesthetic: the visitor sees the app's newspaper layout living inside the marketing page. The component composes four sub-elements already styled in CSS (`.demo-masthead`, `.demo-body`, `.demo-sidebar`, `.demo-content`); the architectural work is HTML composition, not styling.

### Step Editorial Bodies
**Purpose**: Insert a one-sentence `<p class="step-body">` above each `.step-code` block in the three "How it works" columns. The step columns currently jump from heading to code mockup; a body sentence creates editorial rhythm and lets the code mockup function as evidence rather than as primary content. The `.step-body` class is already styled — this is markup-only.

### Section Nav + Metrics
**Purpose**: Two small surface-area updates triggered by the demo strip and live system state. The section bar gains a fourth link ("Demo") to keep nav and content in sync. The metrics bar (tests / commits / projects) is refreshed against current repository counts so the numerical claims are accurate at landing time. Both are content edits, not structural.

### Dark-Mode Parity Audit
**Purpose**: A verification component, not a code component. After all visual changes land, every new or modified element is opened in `[data-theme="dark"]` and checked against its light-mode counterpart for: border contrast, hover-state visibility, icon stroke legibility, and text contrast. The audit is a pass/fail gate — failures route back to the relevant component, not into new dark-mode-specific CSS.

## Technology Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Markup | Static HTML5 (`landing/index.html`) | Single-file marketing surface, no framework needed; consistent with current shape. |
| Styling | Vanilla CSS with custom properties (`landing/style.css`) | Token system + dark-mode overrides already complete; no preprocessor or framework adds value. |
| Fonts | Playfair Display, Source Serif 4, Source Sans 3 | Complete set per builder constraints; no new families introduced. |
| Theme switching | Existing inline JS (`data-theme` attribute) | Already shipping; no changes required. |
| Hosting | `nginx:alpine` via `docker compose` | Existing pipeline; rebuild via `docker compose build landing && docker compose up -d landing`. |
| Reference contract | `http://localhost:8096/playground.html` | Verbatim source for tokens, component states, and CSS snippets. |

## Design Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Wire HTML to existing CSS rather than restyle | The stylesheet already encodes the design system; the gap is rendered components, not new components. Lower risk, smaller diff. | Cannot evolve component shape in this epic — if a CSS rule is wrong, it is fixed in place rather than redesigned. |
| Use `.output-card` for hero aside | Cards give editorial weight per artifact and reuse hover/border/dark-mode rules already defined. | More vertical space than a bullet list; hero becomes denser. Acceptable because density-without-clutter is a stated principle. |
| Demo strip as static HTML mock, not iframe of app | Static HTML guarantees aesthetic parity, loads instantly, and stays under solo-dev maintenance burden. An iframe would require auth, dev-server availability, and cross-origin handling. | Demo can drift from the live app over time; mitigated by treating the demo strip as a stylistic mock, not a screenshot of current state. |
| Add "Demo" nav link only after demo strip lands | Nav and content stay in sync; Task 4 explicitly depends on Task 3. | Nav must remain visually balanced at four items — verified during the parity audit. |
| Refresh metrics counts inline rather than dynamically | Static counts match the static-page philosophy and avoid introducing any JS data fetch. | Counts go stale between deploys; acceptable given low cadence and that they are positioning numbers, not live telemetry. |
| Dark mode as audit gate, not separate task per component | Every component already has a paired dark-mode rule; auditing once at the end is faster than reverifying per change. | Risk of finding multiple issues at the end; mitigated because audit is the final gate before the build verification step. |
| No inline styles, no new classes | Hard constraint from braindump; preserves the CSS-as-source-of-truth invariant. | Forces any unanticipated styling need to be resolved by reading existing rules rather than adding new ones — slower in edge cases, faster in aggregate. |
| Single `landing/style.css` edit point (tagline only) | The only CSS change is the `.masthead-tagline` font-family swap; everything else is HTML-only. | Concentrates risk on one rule; mitigated by it being a single-token reassignment with a pre-existing dark-mode-safe target. |

## Related Documents

- [Analysis](./analysis.md) – Problems driving design
- [Epic](./epic.md) – Scope and tasks
- [Timeline](./timeline.md) – Status tracking