# 🎯 Epic: Landing Phase 3 — Pure HTML Extraction

## Business Value

The current `landing-v2.html` is a liability — it violates the design system (border-radius, shadows, wrong fonts, inline styles) and undermines the "editorial precision" brand promise that spec-doc sells. Every visitor who sees rounded corners and decorative animations gets a subconscious signal: *this product doesn't follow its own standards.* A tool that generates architecture docs must look architecturally deliberate.

A clean rewrite using only existing `style.css` classes eliminates design debt permanently. The newspaper aesthetic — scan in 30 seconds, understand immediately — converts developer visitors who are allergic to marketing fluff. The comparison table alone ("5 specs vs code", "free vs $20+/mo") positions spec-doc against Lovable/Bolt/Kiro without requiring a demo. This is a one-page sales argument that loads in under a second and requires zero ongoing maintenance.

The free tier CTA drives adoption; the Pro tier plants the monetization seed. A compliant landing page is prerequisite to any paid launch — you can't charge for quality while shipping violations.

## Scope

### What This Epic Covers

- **Full rewrite of landing page** – Clean extraction from playground content into a single `index.html` using only existing `style.css` classes
- **Style.css feasibility audit** – Map available classes to planned sections; cut anything unsupported
- **Content hardcoding** – Extract curated copy from `pg-landing-data.ts` directly into HTML (no JS binding)
- **Design system compliance** – Zero border-radius, zero box-shadow, zero inline styles, token-only colors, three fonts only
- **Dark mode & responsive** – Leveraging existing token overrides and media queries (no new CSS)

### What This Epic Does NOT Cover

- ❌ **New CSS classes or tokens** — If `style.css` can't express it, the section gets cut
- ❌ **JavaScript beyond dark mode toggle** — No scroll animations, intersection observers, or dynamic content
- ❌ **Analytics or A/B testing** — Ship clean first, instrument in a future phase
- ❌ **Competitor research validation** — Use existing claims from playground data as-is
- ❌ **Demo strip or interactive elements** — Too complex for static HTML; belongs in-app
- ❌ **Testimonials or pull quotes** — No real testimonials exist; shipping fake ones harms credibility

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Style.css Audit & Content Extraction** | None | — | 0.5 days | High |
| 2 | **Above-the-Fold HTML (Masthead → Stat Strip)** | Task 1 | — | 1 day | High |
| 3 | **Below-the-Fold HTML (Cards → Footer)** | Task 1 | With Task 2 (same file, sequential sections) | 1 day | High |
| 4 | **Compliance Validation & Dark Mode Verification** | Tasks 2, 3 | — | 0.5 days | High |

## Success Criteria

- ✅ Single `index.html` under 300 lines renders all curated sections
- ✅ Zero design system violations: no `border-radius`, no `box-shadow`, no inline styles, no hardcoded colors
- ✅ Only three font families used: Playfair Display, Source Serif 4, Source Sans 3
- ✅ All colors reference CSS custom properties (`--ink`, `--bg`, `--border`, `--red`, `--accent`)
- ✅ No CSS classes used that don't exist in `style.css` — zero new CSS written
- ✅ Dark mode fully functional via existing `[data-theme="dark"]` token overrides
- ✅ Page loads in under 1 second (HTML + one CSS file + Google Fonts only)
- ✅ Responsive at 768px and 1100px breakpoints using existing media queries
- ✅ Core message communicable in 30-second scan: "paste braindump → get specs → free"
- ✅ Comparison table positions spec-doc against alternatives across six dimensions

## Related Documents

- [Analysis](./analysis.md) – Design system violations and open questions driving this rewrite
- [Solution Architecture](./architecture.md) – Section mapping, class usage, and content extraction strategy
- [Timeline](./timeline.md) – Status tracking