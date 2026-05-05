---
sidebar_position: 1
---

# 🔍 Relationship Check-In – Analysis

**Purpose**: Identify problems driving this capability and surface decisions not yet made.

**Date**: 2026-04-19

---

## Problem

Two partners have a scoring model (ten questions → four qualities) and an interpretation framework (thresholds, divergence, decline). They lack a container that makes rating frictionless after each meetup, comparison instant once both submit, and trends visible over time. Paper or spreadsheets fail on privacy (both partners see each other's scores before submitting), convenience (friction kills consistency), and trend visibility (no charts, no alerts).

## Hard Constraints

| Constraint | Source | Status |
|------------|--------|--------|
| Must be a Bubls module, not a standalone app | Braindump recommendation + existing infrastructure | ✅ Aligned — SQLite service, Capacitor base, dark theme already shipped |
| No server, no cloud sync | Braindump requirement | ✅ Aligned — SQLite local-only storage |
| No AI, no advice | Braindump requirement | ✅ Aligned — pure measurement, interpretation thresholds are static |
| Dark-only, no theme toggle | Bubls design direction (feedback memory) | ✅ Aligned — Bubls convention |
| Feature = bounded context with lazy-loaded route | Architecture principles | ✅ Aligned — `/checkin` route, own folder |
| Standalone components, OnPush, Signals | Architecture principles | ✅ Aligned — Angular 19 patterns |

## Open Questions

| Question | Options | Recommendation |
|----------|---------|----------------|
| How do partners pair on a single device? | (A) Selection screen (Partner A / Partner B tap), (B) QR code link, (C) PIN-based lock | **A for v1** — simplest, no networking. Partner taps their name, rates, hands device to partner. QR/PIN deferred. |
| How is a "meetup session" created? | (A) Explicit "Start Check-In" button, (B) Auto-create on first rating | **A** — explicit creation prevents accidental partial sessions and gives a clear timestamp anchor. |
| Should partners be able to edit after submitting? | (A) No edits, (B) Edit until both submit, (C) Edit anytime | **A** — immutability preserves honesty. Once submitted, locked. |
| How are trend charts rendered? | (A) Canvas-based charting lib, (B) SVG inline, (C) Ionic chart component | **B** — no dependency, full dark-theme control, simple line/sparkline rendering. Charting lib is overkill for four trend lines. |
| What happens when only one partner submits and the other never does? | (A) Session stays open forever, (B) Auto-expire after 48h, (C) Manual close | **B** — stale open sessions clutter the UI. 48h expiry with a "waiting for partner" indicator. |

## Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| Bubls SQLite service | ✅ Shipped | Direct reuse — no new infrastructure |
| Bubls Capacitor base service | ✅ Shipped | Direct reuse for platform detection, preferences |
| Bubls routing (`app.routes.ts`) | ✅ Shipped | One line addition for `/checkin` lazy route |
| Bubls dark theme tokens | ✅ Shipped | Direct reuse — CSS custom properties |

## Explicitly Out of Scope

- Cloud sync between two devices (v1 is single-device, partner-selection-screen model)
- AI-generated relationship advice or coaching
- Customizable questions (the ten questions are fixed)
- Export/share functionality
- Push notifications or reminders
- Partner pairing via QR code, Bluetooth, or network

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

