I've prepared the updated epic.md content. Here's the complete document:

---

# 🎯 RelateAI – Epic

## Business Value

**Why this matters:**

Dating apps are a $9B market focused on finding partners. But relationships fail at 40-50% rates—not from bad matches, but from communication breakdown. RelateAI addresses the underserved "relationship maintenance" market.

- **Unique positioning**: No competitor owns the "after the swipe" space
- **Recurring revenue**: Relationships are ongoing; so is the subscription
- **High retention potential**: Users invested in relationships stick around
- **Word-of-mouth growth**: Happy couples recommend to other couples
- **Expansion path**: Therapist referrals, couples workshops, corporate wellness

**Target users**: Committed couples (dating 6+ months) who want to improve communication before problems become crises.

---

## Scope

### What's Included (MVP)

- AI Advisor for relationship conversations
- Multiple input methods (chat upload, situation description, manual entry)
- Basic relationship dashboard with health indicators
- Onboarding questionnaire to establish context
- Individual user accounts (single-partner view first)

### What's NOT Included (Post-MVP)

- Partner pairing/shared accounts
- Guided check-ins requiring both partners
- Video/voice input
- Therapist marketplace or referrals
- Native mobile apps (web-first)
- Real-time chat monitoring or integrations
- Couples comparison features
- Historical trend analysis

---

## Tasks

| # | Task | Dependencies | Effort | Priority |
|---|------|--------------|--------|----------|
| 1 | User authentication and accounts | — | M | High |
| 2 | Onboarding questionnaire (attachment style, love language, relationship context) | 1 | M | High |
| 3 | AI Advisor chat interface | 1 | M | High |
| 4 | System prompt with relationship frameworks (Gottman, NVC, attachment theory) | — | S | High |
| 5 | Context persistence (AI remembers user history) | 2, 3 | M | High |
| 6 | Text input for situation descriptions | 3 | S | High |
| 7 | Chat paste/upload parsing (WhatsApp, generic text) | 3 | M | High |
| 8 | Basic dashboard UI (health score placeholder) | 1 | S | Medium |
| 9 | Screenshot OCR for chat extraction | 7 | M | Low |
| 10 | Health scoring algorithm from conversations | 5, 7 | L | Low |
| 11 | Conversation history and session management | 3 | S | Medium |
| 12 | Landing page and positioning | — | S | High |
| 13 | Stripe subscription integration | 1 | M | Medium |
| 14 | Usage limits (free tier: 5 conversations/month) | 3, 13 | S | Medium |

**Effort key**: S = Small (< 1 day), M = Medium (1-3 days), L = Large (3+ days)

---

## Success Criteria

| Metric | Target | Timeframe |
|--------|--------|-----------|
| Users complete onboarding | 70% of signups | Launch + 30 days |
| Return for 2nd conversation | 50% of users | Within 7 days |
| Weekly active users | 100 | Launch + 60 days |
| First paying customer | 1 | Launch + 14 days |
| Free-to-paid conversion | 5% | Launch + 60 days |
| User satisfaction (NPS) | > 40 | Launch + 90 days |

**MVP is successful when**: Users return to talk to the Advisor multiple times, indicating the AI provides value beyond a single interaction.

---

Grant write permission to save this to the existing file at `projects/relateai-1774811052300/epic.md`.