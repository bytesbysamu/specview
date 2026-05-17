# ClawMemory Dashboard - Roadmap

## Current State (v1.0)
- NYT cover page aesthetic with Playfair Display + Source Serif
- Lead story with auto-generated headline, quotes, and summary
- Status sidebar (mood, days since, priority)
- Wins/Struggles columns
- Archive with grouped notes
- Markdown rendering in modals

---

## Phase 2: OpenClaw Chat Integration

### Vision
Add a chat interface to talk with ClawBoi directly through the dashboard. This creates a "ClawBoi distro" - a better UI for the OpenClaw agent.

### Components

**2.1 Chat Panel**
- Slide-out or bottom-docked chat panel
- Connect to OpenClaw API (WebSocket or REST)
- Message history persistence
- Markdown rendering in chat bubbles

**2.2 Context-Aware Chat**
- Click any entry/note → "Ask about this"
- Reference current memory in conversations
- ClawBoi can read the dashboard data

**2.3 Quick Actions**
- "Write today's diary" → guided entry
- "What should I focus on?" → priorities from patterns
- "Who haven't I seen recently?" → people insights

### Technical Requirements
- OpenClaw API endpoint for chat
- Authentication/session management
- WebSocket for real-time responses
- Message queue for long responses

---

## Phase 3: Constellation Docs Integration

### Vision
Use Constellation documentation as memory/context for the agent. Best context usage = agent relying on spec docs.

### Components

**3.1 Docs as Memory**
- Index Constellation Docusaurus pages
- RAG (Retrieval Augmented Generation) for context
- "What does our architecture say about X?"

**3.2 Simple Integration**
- Embed docs viewer in dashboard
- Search across all docs
- Link docs to conversation topics

**3.3 Agent Specialization**
- Agent persona based on docs content
- Auto-suggest relevant docs during chat
- "According to our strategy..."

### Technical Requirements
- Docs parsing/indexing (static JSON export)
- Vector embeddings for semantic search
- Integration with OpenClaw memory system

---

## Phase 4: Enhanced Personalization

### 4.1 Multiple Entry Types
- Diary entries (current)
- Quick thoughts (shorter format)
- Meeting notes
- Decision logs

### 4.2 Smart Insights
- Weekly/monthly summaries auto-generated
- Mood trend analysis with charts
- Pattern recognition improvements
- "This week vs last week"

### 4.3 People Tracking
- Extract names from diary entries
- Relationship context
- "When did I last see X?"
- Social network visualization

### 4.4 Calendar Integration
- Sync events from bubls
- Show today's schedule
- Event reminders in chat

---

## Phase 5: Mobile & PWA

### 5.1 Progressive Web App
- Offline support
- Install to home screen
- Push notifications for reminders

### 5.2 Mobile-First Mode
- Condensed view for phone
- Quick entry from mobile
- Voice input for diary entries

---

## Design Principles

1. **Newspaper Aesthetic** - Clean typography, strong hierarchy
2. **Editorial Voice** - Auto-generated headlines, summaries
3. **Density Without Clutter** - Information-rich but scannable
4. **Personal Yet Professional** - This is YOUR record
5. **Progressive Disclosure** - Overview first, details on demand

---

## Implementation Priority

| Phase | Effort | Value | Priority |
|-------|--------|-------|----------|
| 2.1 Chat Panel | Medium | High | 1 |
| 4.3 People Tracking | Low | Medium | 2 |
| 3.1 Docs as Memory | High | High | 3 |
| 4.2 Smart Insights | Medium | Medium | 4 |
| 5.1 PWA | Medium | Medium | 5 |

---

## Next Steps

1. **Today**: Commit NYT redesign
2. **Next**: Design chat panel UI mockup
3. **Then**: Research OpenClaw API integration
4. **Goal**: Chat working within 1 week

---

## Notes

- Keep the editorial/newspaper feel throughout
- Chat should feel like talking to a smart editor
- Docs integration = agent has deep context
- Mobile is important but not urgent
