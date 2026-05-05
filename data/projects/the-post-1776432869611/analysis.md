
```markdown
---
sidebar_position: 1
---

# 🔍 THE Post — Analysis

**Purpose**: Surface the problems and open decisions that must be resolved before writing begins.

**Date**: 2026-04-17

---

## Summary

Five sections per the analysis filter: Problem, Hard Constraints, Open Questions, Dependencies, Explicitly Out of Scope.

---

## Problem

The Bubls session produced extraordinary numbers (6 epics, 32 tasks, 102 commits, 9,662 lines, 289 tests, zero regressions) but those numbers exist only in git history. Without a public narrative, the methodology dies in a private repo. The post is the distribution — no post means no awareness of the pattern, no traffic to the landing page, no TestFlight installs.

---

## Hard Constraints

| Constraint | Source | Implication |
|-----------|--------|-------------|
| Numbers must be verifiable | Builder principles ("retention is the only metric" — no vanity) | Every stat in the post must trace to a git log query. No rounding up, no "about X". Exact counts or don't claim it |
| Post must end with working CTA | Braindump ("Ends with a link to the landing page and a TestFlight invite") | Landing page must be live and TestFlight link must be active BEFORE publish. Not "coming soon" |
| One channel, committed | Braindump ("pick one, commit") | No cross-posting strategy. Choose Twitter thread OR LinkedIn article OR blog post. Format for that medium only |
| Ship fast | "Every day that passes makes the story less urgent" | Total capability budget: 2–3 days max from spec to published. No polish loops |

---

## Open Questions

| # | Question | Decision needed | Impact if deferred |
|---|----------|-----------------|--------------------|
| 1 | **Pattern name**: "Five-Part Agent" or something else? | Before writing starts — the name appears in the headline and structures the middle section | Weak name = forgettable post. The name IS the meme |
| 2 | **Channel**: Twitter thread, LinkedIn article, or standalone blog? | Before formatting starts — structure differs radically between 280-char chunks vs. 2000-word article | Wrong format = rewrite. Pick before draft |
| 3 | **Deviation trend data**: is 6.0 → 2.0 the exact trajectory, and from which epics? | Before the "proof" section — this is the punchline chart | Approximate data undermines the "war story with numbers" premise |

---

## Dependencies

| Dependency | Blocks | Status |
|-----------|--------|--------|
| Landing page URL live | Task 5 (publish) — CTA must resolve | Verify |
| TestFlight link active | Task 5 (publish) — CTA must resolve | Verify |
| Git history accessible | Task 1 (number extraction) — all stats come from here | Available |
| Deviation logs in commit bodies | Task 2 (proof section) — deviation trend is the money chart | Verify format |

---

## Explicitly Out of Scope

- **Multi-channel distribution**: no cross-posting, no repurposing for a second platform. One channel, one format
- **Video or audio companion**: no podcast episode, no YouTube walkthrough. Text only
- **Paid promotion**: no boosted posts, no ads. Organic only for v1
- **Follow-up series**: this is THE post, not "part 1 of N". Standalone
- **Bubls product documentation**: the post is a war story, not a user guide

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)
```

