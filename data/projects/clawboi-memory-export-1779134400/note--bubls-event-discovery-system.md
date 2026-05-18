# 🦁 Bubls Event Discovery System

# 🦁 Bubls Event Discovery System

**Version:** 1.0  
**Status:** MVP - Events working, People indexing next  
**Last Updated:** March 4, 2026

---

## 🎯 What Bubls Does

**Events are commodities. People are the product.**

Bubls discovers events you'll love and connects you with people you should meet.

### Current Features ✅
- **Event Discovery:** Auto-scrape newsletters, websites, APIs
- **Smart Matching:** Compute personalized match scores (explainable)
- **State Tracking:** Suggested → Interested → Attended → Rated
- **Friend Mapping:** Know who's going where

### Coming Soon 🚧
- **People Indexing:** Find high-match people in Zurich
- **Social Layer:** "Meet Alex at After the Algorithm"
- **Group Formation:** Coordinate meetups with matched people
- **Calendar Sync:** Auto-add to Google Calendar
- **Inline Actions:** Telegram buttons for quick decisions

---

## 📁 File Structure

```
bubls/
├── state.json              # System state & stats
├── events/
│   └── 2026-03.json        # Monthly event archives
├── people/
│   └── index.json          # People database (coming soon)
├── user/
│   ├── profile.json        # Your taste profile
│   └── history.json        # Attendance & ratings
├── system/
│   ├── config.json         # Feature flags & settings
│   └── reminders.json      # Notification system
├── match-algorithm.py      # Scoring engine
└── CHANGELOG.md            # Version history
```

---

## 🎯 How Matching Works

### Match Score Algorithm (v1.0)

Events are scored 0.0-1.0 based on:

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| **Category** | 40% | Interest alignment (tech, music, etc.) |
| **Budget** | 20% | Price vs your saving goals |
| **Timing** | 15% | Weekend/weeknight, morning/evening |
| **Social** | 15% | Friends attending, solo-friendliness |
| **Location** | 10% | Travel distance from home |

**Example Output:**
```json
{
  "event": "After the Algorithm",
  "score": 0.95,
  "reasons": [
    "✓ Category: tech (100% match)",
    "✓ Budget: FREE",
    "✓ Timing: weekend (preferred)",
    "✓ Bonus: aligns with current focus"
  ]
}
```

### Why This Score?
Every score is **explainable**. You can see exactly why an event matched (or didn't).

---

## 🚀 Quick Start

### Run Match Algorithm
```bash
cd /data/.openclaw/workspace/memory/bubls
python3 match-algorithm.py recompute
```

### Check Current State
```bash
cat state.json
```

### View This Week's Events
```bash
cat events/2026-03.json | jq '.events[] | select(.date >= "2026-03-04" and .date <= "2026-03-10") | {title, date, matchScore}'
```

### Generate Calendar File
```bash
./generate-ics.sh fred-wesley-2026-03-05
# Import /tmp/fred-wesley-2026-03-05.ics to Google Calendar
```

---

## 📊 Your Stats

Check `state.json` for:
- Events discovered
- Match accuracy
- Attendance rate
- People indexed
- Connections made

---

## 🔧 Configuration

Edit `system/config.json` to:
- Enable/disable features
- Adjust match weights
- Set notification preferences
- Configure integrations

---

## 🛠️ Development

### Add New Event Source
1. Add scraper to pipeline
2. Normalize to event schema
3. Run match algorithm
4. Events auto-appear in briefs

### Adjust Match Algorithm
1. Edit weights in `system/config.json`
2. Run `python3 match-algorithm.py recompute`
3. Check results

### Enable New Feature
1. Set flag in `system/config.json`
2. Implement feature code
3. Deploy & test

---

## 🎯 Roadmap

**v1.0 (Current):** Event discovery + matching ✅  
**v1.1 (This week):** People indexing + social layer  
**v1.2 (Next week):** Calendar sync + inline buttons  
**v1.3 (Month 2):** Group formation + network effects  
**v2.0 (Month 3):** Full product with virality loops  

---

## 📖 Documentation

- `IMPROVEMENTS.md` - Issues identified & fixes
- `CHANGELOG.md` - Version history
- `this-week-priority.md` - Immediate event focus
- User files in workspace root:
  - `USER.md` - Your profile & goals
  - `HEARTBEAT.md` - Daily check-in routine

---

## 🦁 Philosophy

**Bubls isn't about having ALL the events.**  
**It's about having THE RIGHT event + THE RIGHT people.**

That's what makes you actually show up.

---

**Questions?** Just ask ClawBoi 🦁

