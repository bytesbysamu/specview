# 🛠️ BUBLS SYSTEM - IMPROVEMENTS NEEDED

# 🛠️ BUBLS SYSTEM - IMPROVEMENTS NEEDED

## ❌ Current Issues

### 1. **File Structure - Too Scattered**
```
❌ events-2026-03.json (will need monthly rotation)
❌ reminders.json (separate from events)
❌ taste-profile.json (static, not learning)
❌ TODO-tonight.md (in wrong location)
```

**Should be:**
```
✅ bubls.db (SQLite for structured queries)
✅ OR consolidated JSON with indexes
✅ Automatic monthly archiving
```

### 2. **No Match Score Calculation**
- Hardcoded scores (0.95, 0.82, etc.)
- Not dynamically computed
- Can't explain *why* an event matches

**Need:** Algorithm that shows work

### 3. **No People Database**
- This is THE core feature
- Currently missing entirely
- Can't do social matching without it

### 4. **No Automation Hooks**
- Manual reminders only
- No cron integration
- No webhook endpoints

### 5. **No State Management**
- What if process crashes?
- No transaction safety
- No audit trail

### 6. **Missing Integrations**
- Google Calendar API setup incomplete
- No Telegram inline buttons actually working
- No actual event scraping automation

### 7. **No Analytics**
- Can't track: what works, what doesn't
- No A/B testing framework
- No feedback loop

### 8. **Privacy/Consent Missing**
- No GDPR compliance structure
- No opt-in/opt-out flows
- No data retention policy

---

## ✅ PROPOSED FIXES

### Phase 1: Consolidate & Structure (Today)

**1.1 Single Source of Truth**
```
bubls/
├── state.json          # Current state (atomic updates)
├── events/
│   ├── 2026-03.json    # Monthly archives
│   └── index.json      # Fast lookups
├── people/
│   ├── profiles.json   # Indexed people
│   └── graph.json      # Social graph
├── user/
│   ├── profile.json    # Sam's profile
│   ├── history.json    # Attendance/ratings
│   └── preferences.json # Settings
└── system/
    ├── config.json     # System config
    └── logs.json       # Audit trail
```

**1.2 Match Score Algorithm**
```python
def calculate_match(event, user_profile):
    score = 0.0
    reasons = []
    
    # Category match (40%)
    category_weight = user_profile.categories[event.category].weight
    score += category_weight * 0.4
    reasons.append(f"Category: {event.category} ({category_weight})")
    
    # Budget fit (20%)
    if event.price <= user_profile.budget.comfortable:
        score += 0.2
        reasons.append("Budget: comfortable")
    elif event.price <= user_profile.budget.max:
        score += 0.1
        reasons.append("Budget: acceptable")
    
    # Timing fit (15%)
    if is_weekend(event.date) and user_profile.timing.weekends:
        score += 0.15
        reasons.append("Timing: weekend (preferred)")
    
    # Social context (15%)
    friends_going = count_friends_attending(event, user_profile.friends)
    score += min(friends_going / 3, 1.0) * 0.15
    if friends_going > 0:
        reasons.append(f"Social: {friends_going} friends going")
    
    # Location (10%)
    if within_travel_radius(event.venue, user_profile.location):
        score += 0.1
        reasons.append("Location: nearby")
    
    return {
        "score": round(score, 2),
        "reasons": reasons,
        "breakdown": {
            "category": category_weight * 0.4,
            "budget": ...,
            "timing": ...,
            "social": ...,
            "location": ...
        }
    }
```

**1.3 People Database Schema**
```json
{
  "people": {
    "<person-id>": {
      "profile": {
        "name": "Alex Chen",
        "photo": "url",
        "bio": "AI researcher at ETH",
        "location": {"city": "Zurich", "area": "Kreis 6"}
      },
      "sources": [
        {"type": "meetup", "url": "...", "lastUpdated": "..."},
        {"type": "linkedin", "url": "...", "lastUpdated": "..."}
      ],
      "interests": {
        "tech": 0.95,
        "ai": 1.0,
        "startups": 0.85
      },
      "groups": ["AI-ML-Zurich", "Impact-Hub", "ETH-Alumni"],
      "events": {
        "attended": ["event-id-1", "event-id-2"],
        "interested": ["after-the-algorithm-2026-03-20"]
      },
      "socialGraph": {
        "mutualFriends": 2,
        "mutualGroups": 1,
        "connections": ["person-id-2"]
      },
      "privacy": {
        "indexed": true,
        "indexedAt": "2026-03-04T08:00:00Z",
        "source": "public-profile",
        "canContact": false,
        "canSuggest": true
      },
      "computed": {
        "matchScore": 0.87,
        "matchReasons": ["Mutual: Impact Hub", "Both interested in AI"],
        "lastComputed": "2026-03-04T08:00:00Z"
      }
    }
  },
  "index": {
    "byInterest": {
      "ai": ["person-1", "person-3"],
      "startups": ["person-1", "person-2"]
    },
    "byGroup": {
      "Impact-Hub": ["person-1", "person-4"]
    },
    "byEvent": {
      "after-the-algorithm-2026-03-20": ["person-1", "person-3"]
    }
  }
}
```

### Phase 2: Automation (Tomorrow)

**2.1 Cron Integration**
```json
{
  "jobs": [
    {
      "name": "daily-discovery",
      "schedule": "0 9 * * *",
      "task": "discover-events",
      "payload": {"sources": ["all"]}
    },
    {
      "name": "event-reminders",
      "schedule": "0 18 * * *",
      "task": "check-reminders"
    },
    {
      "name": "weekly-digest",
      "schedule": "0 9 * * 1",
      "task": "generate-weekly-digest"
    }
  ]
}
```

**2.2 Event Processing Pipeline**
```
1. Fetch sources (email, web, APIs)
2. Parse events → normalize schema
3. Deduplicate (same event, multiple sources)
4. Enrich (location, venue info, images)
5. Compute match scores
6. Store with indexes
7. Trigger notifications if high match
```

### Phase 3: Integration (This Week)

**3.1 Google Calendar OAuth**
- Store credentials securely
- Token refresh handling
- Bidirectional sync (Bubls → Calendar → Bubls)

**3.2 Telegram Inline Buttons**
- Callback handlers for each action
- State management for multi-step flows
- Error handling + retry logic

**3.3 Event Scraping Automation**
- Playwright/Puppeteer for JS-heavy sites
- Rate limiting + error handling
- Source health monitoring

### Phase 4: Learning (Next Week)

**4.1 Feedback Loop**
```
User Action → Update Weights → Recompute Matches

Actions tracked:
- Event suggestions → views
- Views → interested
- Interested → attended
- Attended → rating

Weight adjustments:
- Attended + high rating → ↑ category weight
- Suggested but ignored → ↓ match threshold
- Price point patterns → adjust budget
```

**4.2 A/B Testing**
```json
{
  "experiments": [
    {
      "name": "match-score-threshold",
      "variants": {
        "control": {"threshold": 0.7},
        "test": {"threshold": 0.8}
      },
      "metric": "attendance-rate",
      "status": "running"
    }
  ]
}
```

---

## 🎯 IMMEDIATE PRIORITIES (Next 2 Hours)

1. **Consolidate files** → single state.json
2. **Build match score calculator** → explainable
3. **Create people DB structure** → ready for indexing
4. **Fix TODO location** → move to memory/
5. **Add state management** → atomic updates

---

## 🚀 WHAT TO BUILD FIRST

**Option A: Perfect the foundation**
- Clean up file structure
- Build proper match algorithm
- Add state management
- **Pro:** Solid base for growth
- **Con:** No new features visible

**Option B: Ship people indexing**
- Keep current structure
- Start scraping Meetup groups
- Build person profiles
- **Pro:** Visible progress, cool demo
- **Con:** Technical debt

**Option C: Hybrid**
- Quick file cleanup (30 min)
- Then start people indexing (90 min)
- **Pro:** Best of both
- **Con:** More work upfront

---

## 💡 MY RECOMMENDATION

**Ship Option C:**

1. **Now (30 min):** Consolidate to state.json + proper structure
2. **Today (2 hours):** Build people indexing for Meetup Zurich
3. **Tonight:** Sam does calendar integration
4. **Tomorrow:** Match algorithm + inline buttons
5. **This week:** Full demo with real data

This gives you:
- Clean foundation ✓
- Visible progress ✓
- Real data to play with ✓
- Demo-able by Friday ✓

---

Want me to execute Option C?

