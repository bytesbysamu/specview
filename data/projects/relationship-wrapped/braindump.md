# Relationship Check-In / Relationship Wrapped — Braindump

## What it is

A local-first, two-person relationship check-in app. After each meetup, both partners independently rate ten questions on a 1–10 scale. Neither sees the other's answers until both have submitted. Results appear side-by-side with four derived quality scores and trend lines over time. No server, no cloud, no AI analysis — just honest measurement.

The project exists in two forms: a Next.js shell at `~/Projects/2026/relationship-wrapped/` (essentially a bootstrapped placeholder) and a more detailed Ionic/ionstarter POC spec at `braindumps/braindump-checkin-ionstarter.md`. The real implementation target is ionstarter (Ionic + Angular + Capacitor), not Next.js.

## Problem it solves

Couples have vague, subjective post-meetup feelings but no structured way to notice slow decline, diverging perceptions, or specific patterns failing. The ten questions target concrete behaviors: directness, listening, presence, genuine choice, emotional openness, accountability. Four aggregate qualities (Communication Honesty, Mutual Respect, Prioritization, Long-term Viability) reduce noise. The blind-until-both-submit mechanic prevents anchoring on a partner's score.

## Current state

Spec-only. The ionstarter POC braindump is fully detailed (architecture, data model, UX decisions) but no code has been written. The Next.js repo at `relationship-wrapped/` is a `create-next-app` scaffold with no domain logic. Implementation is blocked on the ionstarter migration POC being validated first — the check-in is intended to be the POC that proves ionstarter's domain architecture before migrating larger domains (picks, photoshoot, text).

## Key decisions already made

- **Local-first, no server**: All data stays on device. SQLite on native (Capacitor), `localStorage`/`CapacitorPreferences` on web. No backend, no privacy risk.
- **Mirror ionstarter tasks domain exactly**: `CheckInSqliteService`, `CheckInLocalStorageService`, `CheckInService` follow the same structure as `TasksSqliteService`/`TasksLocalStorageService`/`TasksService`. No new abstractions, no adapter interfaces, no Elf store.
- **TanStack Query for page services**: `injectQuery`, `injectMutation`, `injectQueryClient`, `invalidateQueries` on mutation success — same pattern as `TaskListPageService`.
- **1-10 tap circles, not sliders**: `ion-range` is flaky on web/iOS; tap circles are reliable.
- **Blind submission**: Neither partner sees results until both have submitted. Prevents anchoring.
- **Same questions, no asymmetry**: Both partners answer identical questions — no "his perspective" vs "her perspective" framing.
- **48-hour session expiry**: Matches existing bubls check-in behavior.
- **Custom SVG sparkline for trends**: No Chart.js dependency. Dual lines for Partner A + B over last 10 sessions (with "show all" toggle).
- **Partner pairing v1**: Same device; pick Partner A or Partner B before rating. No networking.

## The ten questions and four qualities

Questions: directness (Q1), listening (Q2), collaborative conflict (Q3), taking partner seriously (Q4), presence (Q5), genuine choice (Q6), emotional openness (Q7), clean accountability (Q8), wanting this specific person (Q9), long-term sustainability (Q10).

Qualities: Communication Honesty = avg(Q1, Q7, Q8); Mutual Respect = avg(Q2, Q3, Q4); Prioritization = avg(Q5, Q6, Q9); Long-term Viability = avg(Q3, Q8, Q10).

Interpretation: both above 7 consistently = real progress; any below 5 consistently = that dimension is broken; divergence between partners = experiencing same meetup very differently; declining trend = getting worse despite effort.

## Open questions

- **Next.js vs ionstarter**: The `relationship-wrapped/` directory is Next.js. The braindump targets ionstarter. Which is the actual build target? Probably ionstarter given the POC framing, but the Next.js shell may have been started for a "wrapped" (year-in-review shareable card) variant.
- **"Relationship Wrapped" concept**: The directory name suggests a Spotify Wrapped-style annual summary, not just a per-meetup tracker. Is the MVP the ongoing check-in, the year-end wrapped, or both?
- **Draft persistence**: Auto-save per question tap, restore on reopen — spec'd but not designed in detail.
- **Partner B flow on same device**: Does Partner B need to "unlock" the session after Partner A submits? Needs a concrete UX decision.

## Next steps

- Decide: build on ionstarter or Next.js (resolve the directory mismatch).
- If ionstarter: scaffold `check-in` domain mirroring the tasks domain, implement as the bubls → ionstarter migration POC.
- If Next.js: define whether this is the "Wrapped" annual summary product, and what the MVP data model is.
- Either way: nail the blind-submission UX flow before writing any persistence code.
