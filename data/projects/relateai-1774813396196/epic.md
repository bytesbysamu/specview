# 🎯 RelateAI – Epic

**Purpose**: Define scope, tasks, and success criteria.

**Source**: Issues from [Analysis](./analysis.md).

---

## Business Value

 Dating apps like Tinder, Bumble, and Hinge dominate the "finding someone" phase—collectively generating billions in revenue—but abandon users entirely after that first successful match. Once two people are together, these platforms offer nothing: no communication tools, no conflict resolution guidance, no check-ins to help relationships thrive. The implicit message is that relationships should just work on their own.

Meanwhile, couples therapy costs $150-300/session (often more in major cities) and has significant barriers to entry. Scheduling requires coordinating two busy calendars plus a therapist's availability, often during business hours. The stigma persists—many people still view seeking help as an admission of failure rather than investment in growth. Cost adds up quickly: weekly sessions at $200 each means $10,000/year, pricing out most couples who could benefit. And there's typically a 3-6 week wait to see a qualified therapist in the first place.

There's a gap for an affordable, accessible tool that helps people maintain and improve existing relationships. Consider the use cases: a couple wanting to communicate better before small issues become big ones, partners navigating the stress of a new baby or job change, long-distance relationships needing structured connection rituals, or simply two people who want to be more intentional about appreciating each other. Currently, they have limited options: expensive therapy, self-help books with no personalization, or hoping things work out. An AI-powered relationship coach at $10-25/month could serve millions of couples who fall into this gap—committed enough to want help, but not in crisis enough to justify therapy's cost and friction.
RelateAI targets couples who want to communicate better but aren't in crisis. The product offers AI-powered insights grounded in established research (Gottman, attachment theory, NVC), available 24/7 at a fraction of therapy costs. Early adopters are likely to be self-improvement-oriented millennials and Gen Z in committed relationships.

The multi-input approach (chat uploads, situation descriptions, check-ins) removes friction and meets users where they are. Unlike pure chat analyzers, the relationship context built over time creates defensibility and stickiness.

---

## Scope

### What's Included (MVP)

- The Advisor: AI conversation interface grounded in relationship research
- Context onboarding: Structured questions to build relationship profile
- Conversation input: Copy-paste any chat or describe from memory
- Situation input: Free-form text describing relationship scenarios
- Basic relationship context persistence (remembers previous conversations)
- Single-user access (one partner using the app)

### What's NOT Included

- ❌ WhatsApp export parsing (requires complex file handling)
- ❌ Photo/screenshot OCR extraction
- ❌ Guided check-ins and pulse surveys
- ❌ Dual-partner accounts with comparison views
- ❌ Attachment style / love language assessments
- ❌ Mobile app (web-first)
- ❌ Real-time notifications or reminders

---

## Tasks

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | Design onboarding flow (relationship context questions) | None | S | High |
| 2 | Build conversation input UI (paste text, describe situation) | None | S | High |
| 3 | Create system prompt with Gottman/NVC/attachment grounding | None | M | High |
| 4 | Implement The Advisor chat interface | 2, 3 | M | High |
| 5 | Add context persistence (store relationship profile) | 1, 4 | M | High |
| 6 | Build basic auth (email/password or OAuth) | None | S | Medium |
| 7 | Design landing page with positioning | None | S | Medium |
| 8 | Set up Stripe subscription ($5-15/mo tiers) | 6 | S | Medium |

**Effort**: S = <1 day, M = 1-3 days, L = 3+ days

---

## Success Criteria

- ✅ User can complete onboarding and establish relationship context in <5 minutes
- ✅ User can paste a conversation or describe a situation and receive relevant advice
- ✅ Advisor responses reference established relationship research appropriately
- ✅ Context persists across sessions (advisor remembers relationship details)
- ✅ 10 beta users complete onboarding and have 3+ advisor conversations each
- ✅ NPS > 30 from beta cohort

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Thesis](./thesis.md)