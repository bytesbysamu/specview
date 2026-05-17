# MemoryOS Brainstorm

Lightweight architecture combining ClawMemory + constellation-api + FileWatcher.

Date: 2026-03-18

---

## The Ecosystem

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           WHAT WE HAVE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  OpenClaw (ClawBoi)              constellation-api              ClawMemory
│  ─────────────────               ─────────────────              ──────────
│  • Telegram ✅                   • Multi-LLM ✅                 • Dashboard ✅
│  • Memory (md) ✅                • Jobs system ✅               • Mood chart ✅
│  • Sessions ✅                   • Text ops ✅                  • People ✅
│  • Claude API ✅                 • Worker pattern ✅            • Markdown ✅
│  • Heavy overhead ❌             • Auth/Payments ✅             • Docker ✅
│  • WhatsApp broken ❌            • Streaming ✅                 │
│  • Web UI broken ❌              │                              │
│                                  │                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## What Constellation-API Already Has (Reusable)

| Component | Lines | What It Does |
|-----------|-------|--------------|
| `services/llm/provider.py` | 113 | Multi-provider config (Anthropic, OpenAI, Groq, Ollama) |
| `services/llm/factory.py` | 89 | Create LLM client from env |
| `services/llm/adapters/*` | ~150 | Provider-specific implementations |
| `worker.py` | 167 | Job processor (fetch, analyze, report) |
| `api/text.py` | 213 | Rewrite, generate, stream |
| `services/humanizer.py` | ~100 | Multi-pass text processing |

**Total reusable code: ~600 lines**

---

## The Lightweight Vision: MemoryOS

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MemoryOS = ClawMemory + constellation-api LLM + FileWatcher            │
│                                                                          │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐             │
│  │   INPUT      │     │   PROCESS    │     │   OUTPUT     │             │
│  │              │     │              │     │              │             │
│  │ • Telegram   │     │ • Extract    │     │ • Dashboard  │             │
│  │ • Markdown   │────►│   (LLM)      │────►│ • WebSocket  │             │
│  │ • Voice      │     │ • Analyze    │     │ • Telegram   │             │
│  │              │     │ • Pattern    │     │              │             │
│  └──────────────┘     └──────────────┘     └──────────────┘             │
│         │                    │                    │                      │
│         │                    │                    │                      │
│         ▼                    ▼                    ▼                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │  /memory/*.md (the only source of truth)                           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Build vs Reuse Matrix

| Need | Build New | Reuse From | LOC |
|------|-----------|------------|-----|
| **LLM calls** | ❌ | constellation-api/services/llm | 0 |
| **File watcher** | ✅ | - | ~30 |
| **Markdown parser** | ❌ | export-memory.py | 0 |
| **Dashboard** | ❌ | ClawMemory | 0 |
| **WebSocket server** | ✅ | - | ~50 |
| **Telegram input** | ? | OpenClaw OR build 50-line bot | 0-50 |
| **Extraction prompts** | ✅ | - | ~20 |
| **Pattern analysis** | ✅ | - | ~50 |

**New code needed: ~150-200 lines**

---

## Decision: What To Do With OpenClaw?

| Option | Pros | Cons |
|--------|------|------|
| **A: Keep OpenClaw** | Telegram works, memory works | Heavy, broken features |
| **B: Extract memory, drop OpenClaw** | Lightweight | Lose conversation memory |
| **C: Thin wrapper over OpenClaw** | Best of both | Dependency on OpenClaw |
| **D: 50-line Telegram bot + constellation-api** | Ultra lightweight | Build from scratch |

**Recommendation: Option D**

- 50-line Telegram bot for input → saves to markdown
- constellation-api LLM for processing
- ClawMemory dashboard for output
- FileWatcher for reactive updates

---

## The Minimal Stack

```python
# The entire "claw" in ~200 lines:

watcher.py (30 lines)
├── Watch /memory/*.md
├── On change → trigger extract.py
└── Push update via WebSocket

extract.py (50 lines)
├── Import constellation-api/services/llm
├── Parse markdown
├── LLM extract: mood, people, events
└── Update memory.json

telegram_bot.py (50 lines)
├── Receive message
├── Save as /memory/2026-03-18.md
└── Done

server.py (70 lines)
├── Serve dashboard
├── WebSocket for live updates
└── API for search/query
```

---

## What This Unlocks

| Capability | How |
|------------|-----|
| **Live dashboard** | FileWatcher + WebSocket |
| **Multi-provider LLM** | constellation-api (switch via env) |
| **Cheap extraction** | Groq free tier / Ollama local |
| **Pattern detection** | Daily cron + LLM analyze |
| **Telegram input** | 50-line bot |
| **Search/recall** | LLM over markdown corpus |

---

## Key Insight: LLM Not For Chat

The LLM is used for **extraction and analysis**, not conversation:

| Use | Input | Output |
|-----|-------|--------|
| **DiaryParser** | Markdown file | JSON (mood, wins, struggles) |
| **PeopleTracker** | All markdown | People + last seen dates |
| **PatternFinder** | Week of entries | Insights |
| **DailyDigest** | Today's notes | Summary headline |
| **MemorySearch** | Query | Relevant entries |

---

## Parts of OpenClaw We Actually Use

| Feature | Use It? | Notes |
|---------|---------|-------|
| Telegram channel | ✅ Yes | Primary input |
| Memory system (markdown) | ✅ Yes | Core data |
| Claude API | ✅ Yes | But could call directly |
| Session persistence | ⚠️ Overkill | Just need markdown |
| WhatsApp | ❌ No | Broken |
| Web UI | ❌ No | Broken |
| Gateway/pairing | ❌ No | Complexity |
| Multi-agent | ❌ No | Single purpose |

**Insight**: We use ~30% of OpenClaw. The rest is overhead.

---

## Constellation-API LLM Layer

Switch providers via environment variable:

```bash
# Anthropic (default)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Groq (fast, free tier)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...

# Ollama (local)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Next Steps

1. **Copy** `constellation-api/services/llm/` into clawboi
2. **Write** `watcher.py` (30 lines)
3. **Write** `telegram_bot.py` (50 lines)
4. **Wire** dashboard WebSocket
5. **Test** with Ollama (free, local)

---

## Related Files

- `/Users/sam/Projects/clawboi/dashboard/` - ClawMemory dashboard
- `/Users/sam/Projects/2026/constellation-api/backend/services/llm/` - LLM layer
- `/Users/sam/Projects/2026/constellation-api/backend/worker.py` - Job pattern
- `/Users/sam/Projects/clawboi/docs/architecture-rethink/` - DRY decisions
