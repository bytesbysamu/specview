# 🎯 Epic: Landing & App Polish — Phase 3

## Business Value

The landing page is Specview's primary conversion surface and the product's strongest argument. The newspaper aesthetic — cream paper, editorial typography, borders not shadows — isn't decoration: it *is* the product claim. Specview produces documents worth reading. Every broken color token, inline style override, and absent section weakens that argument at the exact moment a prospect is deciding whether to sign up. The design system is complete and playground-verified; Phase 3 closes the gap between a fully-specified CSS library and the HTML that hasn't yet consumed it.

The spec-first position is differentiable from Lovable, Bolt, and Kiro, which generate running code. Specview generates documents — persistent, versionable, ownable. The comparison table and pull quotes make that argument on the landing. Each section Phase 3 adds — metrics bar, context cards, update banner, pull quote row — is a beat in a conversion sequence that currently has structural gaps between sections. A complete editorial sequence, rendered at the full newspaper standard, turns a curiosity visit into a signup.

The primary buyer is a solo founder or small-team lead who has already shipped code before a spec existed. The Pro tier at $29/mo is a fast decision for someone who writes specs regularly — but only if the landing communicates that value through to the pricing grid. The update banner creates urgency for early adopters with a pricing lock-in message. The pricing hierarchy clarification (Free as secondary CTA, Pro as primary) removes ambiguity from the conversion decision. Phase 3 completes the commercial argument the landing began in Phase 1.

## Scope

### What This Epic Covers

- **Security gate** — XSS vulnerability and type-erasure failures in the app; gates all app visual tasks
- **Landing markup promotion** — Replace all inline style overrides with design system class equivalents; correct color token misuse; resolve spacing inconsistencies across sections
- **Landing section completion** — Five sections defined in `style.css` but absent from `landing-v2.html`: metrics bar, aside-list file list, second pull quote (additive, not a replacement), update banner, context cards
- **App correctness** — All four Phase 2 critical carry-forwards and four warnings, including signal hygiene, missing CSS class definitions, and the `wordCount` pipe required by the expanded-meta line
- **App design alignment** — Op chip icons, status bar class unification with landing, expanded-meta editorial line, section-group-header border rule

### What This Epic Does NOT Cover

- ❌ **Puppeteer visual regression baseline** — infra work outside current stack; separate spike
- ❌ **Design-system compliance script** — pre-commit tooling, not Phase 3 polish
- ❌ **`IntersectionObserver` for `rise` animation** — page-load stagger is sufficient; observer is speculative complexity
- ❌ **Context cards in the app** — acquisition copy; in-app equivalent is empty-state copy, scoped separately
- ❌ **`thinking-pulse` animation** — color tokens already carry state semantics; a second animation axis competes with color rather than extending it
- ❌ **FAQ micro-CTAs** — converts support copy into a second sales page; re-scope if conversion data supports it
- ❌ **`rise` animation on output cards** — stagger enhancement deferred until all core sections are present and correct

## Tasks

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Security Gate** | None | Task 2 | 0.5 days | High |
| 2 | **Landing Markup Promotion** | None | Task 1 | 1 day | High |
| 3 | **Landing Section Completion** | Task 2 | Task 4 | 1 day | High |
| 4 | **App Correctness & Signal Hygiene** | Task 1 | Task 3 | 1 day | High |
| 5 | **App Design Alignment** | Task 4 | — | 1 day | Low |

## Success Criteria

- ✅ DOMPurify sanitizes all markdown output before Angular's trust bypass — verified by code review
- ✅ Zero `http.get<any>` in `projects.service.ts` — all poll responses carry concrete TypeScript interfaces
- ✅ All four Phase 2 critical carry-forwards closed before any app visual task opens
- ✅ Zero `style=` attributes in `landing-v2.html` where a design system class exists
- ✅ All text in `landing-v2.html` uses semantic color tokens — no border token used as text color
- ✅ Five absent sections now present and rendering: metrics bar, aside-list, pull quote row, update banner, context cards
- ✅ `--status-running` dot renders green in the active status bar — verified in light and dark mode
- ✅ Free tier CTA renders as secondary, Pro tier as primary — pricing hierarchy unambiguous in both themes
- ✅ All op chips display an icon alongside their label — no text-only chips remain
- ✅ `docker compose build landing && docker compose up -d landing` exits 0 before every PR
- ✅ `ng build --configuration production` exits 0 before every PR

## Related Documents

- [Analysis](./analysis.md) — Problems driving this epic
- [Solution Architecture](./architecture.md) — System design and component decisions
- [Timeline](./timeline.md) — Status tracking