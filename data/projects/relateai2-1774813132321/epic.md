# 🎯 RelateAI – Epic

**Purpose**: Define scope, tasks, and success criteria.

**Source**: Issues from [Analysis](./analysis.md).

---

## Business Value

Dating apps dominate the "finding someone" market, but there's nothing substantial for the 63% of Americans in relationships who want to make them better. Couples therapy costs $150-300/session and carries stigma. Self-help books are generic. Friends give biased advice. The result: preventable relationship deterioration.

RelateAI captures the "relationship maintenance" market—a $2B opportunity based on therapy and coaching spend. The insight: people already talk to AI about personal problems. We just make it specialized, contextual, and relationship-aware. Unlike chat analyzers (creepy, single-input), we're a relationship companion that learns your dynamic over time.

The wedge: couples who want to improve but won't do therapy. The expansion: become the default "check-in" tool for healthy relationships before problems escalate.

---

## Scope

### What's Included (MVP)

- The Advisor: AI conversation grounded in relationship research (Gottman, attachment theory, NVC)
- Situation description input: free-form text about conflicts, feelings, questions
- Conversation upload: copy-paste any chat format (WhatsApp, iMessage, etc.)
- Basic onboarding: relationship context, communication preferences, attachment style
- Persistent memory: AI remembers history and patterns across sessions

### What's NOT Included

- ❌ OCR/screenshot parsing
- ❌ Guided weekly/monthly check-ins
- ❌ Partner pairing or comparison features
- ❌ Love language/values assessments
- ❌ Mobile apps (web-only MVP)

---

## Tasks

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | Design onboarding flow (3-5 screens) | None | S | High |
| 2 | Build onboarding UI + data model | 1 | M | High |
| 3 | Create system prompt with research grounding | None | M | High |
| 4 | Implement Advisor chat interface | 3 | M | High |
| 5 | Add conversation memory/context persistence | 4 | M | High |
| 6 | Build copy-paste chat parser (multi-format) | None | M | Medium |
| 7 | Integrate parsed chats into Advisor context | 5, 6 | S | Medium |
| 8 | Design situation input UX (templates + freeform) | None | S | Medium |
| 9 | Implement situation input flow | 8 | S | Medium |

**Effort**: S = <1 day, M = 1-3 days, L = 3+ days

---

## Success Criteria

- ✅ User completes onboarding in <3 minutes
- ✅ Advisor provides specific (not generic) advice referencing user's context
- ✅ Chat parser handles WhatsApp, iMessage, and plain text formats
- ✅ Conversation history persists across sessions
- ✅ 5 beta users report "this understood my situation" in feedback

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Thesis](./thesis.md)