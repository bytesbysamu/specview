# 🔍 UX Polish — Newspaper Feel, Phase 2 — Analysis

## The Problem
The Specview app (`web-ng/`) drifted from the ClawBoi/landing newspaper aesthetic that defines the product's visual language. Color tokens were aligned 2026-05-05, but masthead typography, the nameplate rule, overline pattern, icon system, dark-mode contrast, and semantic state colors remain inconsistent. This epic closes those gaps and extends the system for app-only patterns (status dots, editor toolbar, op chips).

## Hard Constraints
- Visual reference is the live playground at `http://localhost:8096/playground.html` — code snippets there are verbatim implementation, not approximations.
- `--status-running` stays green (`#22A66A`). Reverting to amber is explicitly forbidden; amber is reserved for a future `--status-attention` token.
- Never use gray (`--ink-muted`) for a state — gray means "no semantic meaning."
- No shadows anywhere except the modal-over-backdrop exception (dark mode only).
- Borders + whitespace + typography carry structure; no decorative chrome.
- Dark mode UI icons must clear 3:1 contrast — `--ink-light` (`#A0A0A0`) is the floor.
- Stack stays Angular standalone + signals; this is CSS/template work in `web-ng/`.

## Open Questions
- Spec file sidebar order — hardcode the canonical sequence (braindump → analysis → epic → architecture → timeline → implementation-guide), or drive from a config/manifest? Unknown files: append alphabetically, or hide?
- Modal dark-mode shadow — what value? (e.g., `0 8px 32px rgba(0,0,0,0.6)` vs. a bordered-only treatment vs. backdrop dim increase). Pick one.
- Op chip icon labels — always show label + icon, or icon-only after N sessions / on hover? Brain dump says "don't need labels after the first few sessions" but doesn't specify the mechanism.
- `--status-attention` token — define now (unused) or defer until the stale-spec feature lands?
- File-type overline in reader — derive from filename (`architecture.md` → "ARCHITECTURE") or from frontmatter?

## Dependencies & Sequencing
- Token additions (status-attention if included, any new icon-color tokens) land before component changes that consume them.
- Overline class must exist before section headers, reader file-type label, and error-state formalization can adopt it.
- Icon size/color standard (`13px / 1.75`, context table) lands before op chip icon mapping is wired.
- Masthead typography fixes (size, tagline font, align-items) and the nameplate rule are independent and can ship in parallel.
- Dark-mode contrast fixes (modal, toolbar border, section nav, icon floor) are independent of the typography work.

## Explicitly Out of Scope
- Implementing `--status-attention` / stale-spec detection — token may be reserved, feature is not in this epic. Trigger: stale-spec UX gets specced.
- Landing page or ClawBoi changes — this epic is app-only (`web-ng/`). Trigger: landing drifts from tokens.
- New components beyond what the playground already shows — this is alignment, not invention. Trigger: a new app surface (e.g., settings page) needs design.
- Markdown rendering engine changes — 2-column flow is CSS only (`column-count: 2`). Trigger: H1/pre span breaks in real specs.
- Accessibility audit beyond the stated 3:1 icon floor — full WCAG pass is its own epic. Trigger: external a11y requirement.
- Animation system overhaul — pulsing dot exists; no new motion. Trigger: status semantics expand.