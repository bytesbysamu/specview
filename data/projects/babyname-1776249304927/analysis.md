# 🔍 Analysis: babyname

**Purpose**: Evidence-based problem identification driving the [Epic](./epic.md).

**Date**: 2026-04-15

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 3 |
| HIGH | 4 |
| MEDIUM | 4 |

---

## The Core Problem

Choosing a baby name is one of the most emotionally loaded decisions parents make, yet every tool available treats it like a dictionary lookup. Existing iOS apps are static databases — alphabetical lists filtered by origin or gender — forcing parents to scroll through thousands of names with no understanding of what *they* actually want. The result: a 6-to-9-month search process driven by fatigue, not confidence.

The gap is personalization. No existing app asks "what matters to you?" and generates names that fit. Parents resort to combining multiple apps, spreadsheets, Reddit threads, and family group chats to approximate a workflow that should be one product. The search term "baby names" has massive evergreen volume on the App Store, but every result delivers the same commodity experience — a database with filters.

Consider: it's like searching for a restaurant by browsing every menu in the city alphabetically, instead of telling someone "I want something spicy, casual, near me" and getting three perfect recommendations.

---

## Symptoms

Users experience:

- **Decision paralysis** from browsing thousands of undifferentiated names in list form
- **Repeated dead-end searches** across 3-5 apps that all surface the same static data
- **No explanation of fit** — names are listed without context for why they match preferences
- **Partner misalignment** — no shared workspace to converge on a shortlist together
- **Cultural blind spots** — static databases lack nuanced origin/meaning accuracy for non-Western names
- **Pronunciation uncertainty** — parents discover mispronunciation problems after falling in love with a name
- **Sibling disharmony** — no tool considers how a new name sounds alongside existing children's names
- **Stale popularity data** — apps show outdated rankings that don't reflect current naming trends

---

## Issue Breakdown

### Critical Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Static databases dominate the category — zero AI personalization exists | Mobbin audit shows no AI-powered baby name apps; top results are all filter-and-browse | Task: AI generation engine |
| Preference capture is nonexistent | No competitor asks for style, meaning preference, or cultural weight before showing results | Task: Preference input flow |
| 6-9 month search cycle indicates broken discovery | Parent forums and Reddit threads document months-long searches using multiple apps simultaneously | Task: Personalized name generation |

### High Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| No "why it fits" explanation per name | Existing apps show name + origin + meaning but never connect it to what the parent asked for | Task: Name card rationale |
| Partner collaboration is fragmented | Parents share names via screenshots and texts; no shared list or voting mechanism in any top app | Task: Favorites sharing |
| Sibling name harmony is ignored | Parents manually check how names sound together; no app offers this as an input | Task: Sibling name input |
| Pronunciation is an afterthought | Most apps show phonetic spelling at best; parents discover pronunciation issues from friends/family after committing | Task: Pronunciation guidance |

### Medium Priority Issues

| Issue | Evidence | Addressed By |
|-------|----------|--------------|
| Popularity data lags reality | App Store reviews cite outdated SSA data; name trend cycles move faster than annual database updates | Task: Popularity context |
| Cultural depth is shallow | Non-Western names often have incorrect or oversimplified meanings in English-first databases | Task: Cultural accuracy in generation |
| No preference refinement over time | Each search session starts from scratch; the app never learns what the parent gravitates toward | Task: Favorites-based learning (future) |
| Free-to-paid conversion timing is unclear | No market data on optimal free tier limit for name generation apps; risk of over-giving or gate-keeping too early | Task: Paywall threshold testing |

---

## Issues NOT Addressed (Out of Scope)

| Issue | Reason |
|-------|--------|
| Name legality by jurisdiction | Requires per-country legal databases; later phase if demand signals appear |
| Family tree integration | Genealogy features are a different product category |
| Name trend forecasting | Requires historical data pipeline; consider post-validation if retention is strong |
| Partner voting/swipe mechanics | Collaborative features beyond basic sharing are post-MVP scope |
| Cultural deep-dive content (articles, history) | Content-heavy feature better suited for engagement expansion after PMF |
| Multilingual UI | English-first per distribution strategy; localization is a scale decision |

---

## Related Documents

- [Epic](./epic.md) – Scope and tasks addressing these issues
- [Solution Architecture](./architecture.md) – System design
- [Timeline](./timeline.md) – Status tracking
- [Spec Index](./spec-index.md) – Document overview