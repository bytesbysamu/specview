# ClawMemory Changelog

## March 11, 2026 - Major Release

### Features Added Today

---

#### 1. NYT Cover Page Aesthetic

**What it is:**
A newspaper-inspired design using the New York Times front page as reference. Clean typography, strong visual hierarchy, multi-column layouts.

**Implementation:**
- **Masthead**: Centered title "ClawMemory" with date and tagline "A Personal Record"
- **Typography**: Playfair Display for headlines, Source Serif 4 for body, Source Sans 3 for UI
- **Color palette**: Warm paper background (#FFFEF9), pure black ink (#121212), muted accents
- **Dividers**: Thin rules between sections, thick black rules for major breaks

**Files:**
- `style.css` - Full redesign with CSS variables
- `index.html` - Semantic HTML structure

---

#### 2. Lead Story with Direct Quotes

**What it is:**
The main diary entry displayed as a newspaper lead story. 80%+ of content is direct quotes from the original markdown, not paraphrased.

**Implementation:**
- Extracts first heading from markdown as headline
- Shows `whatHappened` as lead paragraph (direct quote)
- Pulls first substantial paragraph as blockquote
- Lists wins/struggles as direct bullet points
- Extracts "Real Talk" section if present

**Key functions:**
- `extractFirstHeading(content)` - Gets `# Title` from markdown
- `extractSections(content)` - Finds key paragraphs and reflections
- `renderLeadStory(entry)` - Assembles the lead story

---

#### 3. Entry Slider

**What it is:**
Tab-based navigation to browse all diary entries. Each tab shows date + mood score. Click to switch between entries.

**Implementation:**
- Horizontal tabs with date labels
- Active tab highlighted (inverted colors)
- Panel content shows: date, mood, summary, wins, struggles
- "Read full entry →" button to expand

**Key function:**
- `renderEntrySlider(diary, featured)` - Creates tabs and panels

---

#### 4. Mood Chart

**What it is:**
Visual bar chart showing mood scores over time. Bars are color-coded by mood level and clickable to expand that entry.

**Implementation:**
- Bars sized proportionally (mood/10 * 100%)
- Colors: Green (8+), Yellow-green (6-8), Orange (4-6), Red (<4)
- Date labels below, mood scores above
- Click any bar to see full entry

**Key function:**
- `renderMoodChart(diary)` - Creates colored bars with data attributes

---

#### 5. People Extraction

**What it is:**
Automatically detects names mentioned in diary and daily notes. Shows mention count and last seen date.

**Implementation:**
- Known names list: Alina, Krisi, Marcel, Thomas, Mariana, etc.
- Counts occurrences across all content
- Tracks which dates each person was mentioned
- Sorted by mention count (most mentioned first)

**Results today:**
| Person | Mentions | Last Seen |
|--------|----------|-----------|
| Alina | 24 | Mar 11 |
| Krisi | 18 | Mar 11 |
| Mariana | 10 | Mar 11 |
| Hanna | 10 | Mar 11 |
| Marcel | 9 | Mar 11 |
| Johan | 9 | Mar 7 |

**Key function (Python):**
- `extract_people_from_entries()` in `export-memory.py`

---

#### 6. Sticky Navigation

**What it is:**
Fixed navigation bar at top of page. Stays visible while scrolling. Quick links to sections.

**Sections:**
- Today (lead story)
- Entries (slider)
- Mood (chart)
- People (grid)
- Archive (all files)

**Implementation:**
- CSS `position: sticky; top: 0;`
- Anchor links to section IDs
- Active state highlighting

---

#### 7. Inline Expansion (No Modal)

**What it is:**
Clicking any entry expands its full content inline, below the clicked section. No popup modal. Smoother reading flow.

**Implementation:**
- Expanded panel inserted after trigger's parent section
- Smooth scroll to expanded content
- Close button or Escape key to collapse
- Markdown rendered in expansion

**Key function:**
- `showExpanded(title, content, trigger)` - Inserts and scrolls to panel

---

#### 8. Markdown Rendering

**What it is:**
Custom markdown-to-HTML converter for displaying diary content. Handles common markdown syntax.

**Supported:**
- Headers (h1, h2, h3)
- Bold, italic
- Code blocks and inline code
- Blockquotes
- Unordered and ordered lists
- Checkboxes `[x]` and `[ ]`
- Horizontal rules
- Links

**Key function:**
- `renderMarkdown(text)` - Line-by-line parsing
- `processInline(text)` - Bold, italic, code, links

---

### Architecture

```
clawboi/
├── dashboard/
│   ├── index.html          # NYT-style layout
│   ├── style.css           # Typography + components
│   ├── app.js              # Rendering + interactions
│   ├── data/
│   │   └── memory.json     # Synced from VPS
│   ├── docker/
│   │   ├── export-memory.py    # Parses ClawBoi memory
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── sync.sh             # Fetches data from VPS
│   ├── ROADMAP.md          # Future features
│   └── CHANGELOG.md        # This file
```

---

### Data Flow

```
VPS (ClawBoi container)
    │
    ├── /data/.openclaw/workspace/memory/
    │   ├── diary/*.md
    │   ├── 2026-*.md (daily notes)
    │   └── bubls/*.md
    │
    ▼
sync.sh runs export-memory.py inside container
    │
    ▼
memory.json exported with:
    - diary entries (parsed)
    - daily notes (full content)
    - other notes (grouped by folder)
    - people (extracted names)
    - stats (mood average, trends)
    │
    ▼
dashboard/data/memory.json
    │
    ▼
app.js renders to HTML
```

---

### Planned Improvements

#### Short Term
1. **Click person tag** → Show all entries mentioning them
2. **Mood trend line** → Overlay average on chart
3. **Search** → Find entries by keyword
4. **Calendar heatmap** → GitHub-style contribution grid

#### Medium Term
1. **Chat panel** → Talk to ClawBoi in dashboard
2. **Constellation docs integration** → Use specs as agent memory
3. **Deploy to VPS** → Access from anywhere

#### Long Term
1. **PWA** → Install on phone, offline access
2. **Voice input** → Dictate diary entries
3. **Auto-insights** → Weekly AI-generated summaries

---

### Commits Today

1. `cac3dee` - Initial ClawMemory dashboard
2. `f852fac` - Redesign dashboard with car dashboard UX
3. `15b4fdf` - Improve markdown rendering and note organization
4. `5f70fc1` - Redesign with NYT cover page aesthetic
5. `6353624` - Add entry slider and direct quotes
6. `451a732` - Add people extraction, mood chart, navigation, inline expansion

---

### Stats

- **Lines of code**: ~1,500
- **Files created**: 12
- **People extracted**: 20
- **Diary entries**: 2
- **Daily notes**: 5
- **Other notes**: 8
