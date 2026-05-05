---
sidebar_position: 3
---

# 🏗️ GitHub Profile README – Solution Architecture

**Purpose**: Technical design for the GitHub profile README and pinned repo configuration.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This is a content architecture, not a software architecture. The "system" is a single Markdown file (`README.md` in the `bytesbysamu/bytesbysamu` repo) plus GitHub's repo pinning and metadata features. The design decisions are about information hierarchy, content density, and rendering constraints — not services or databases.

The profile README is a static document served by GitHub's Markdown renderer. It has no build step, no dependencies, and no runtime. The constraints are GitHub-Flavored Markdown (GFM) syntax, a maximum rendered width of ~888px on desktop, and the fold line (what's visible without scrolling, roughly 15-20 lines on a standard viewport).

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Proof of work, not resume | Every line references something shipped, measured, or live. No claims without URLs or numbers. |
| 10-second comprehension | The above-the-fold content (hero + shipped products) tells the complete story. Everything below is supporting detail. |
| Text-only, no external assets | No images hosted elsewhere. No badges from shields.io. Unicode characters and GFM tables only. This eliminates broken images, CDN dependencies, and dark-mode rendering issues. |
| Density over length | Under 80 lines total. Every line earns its place. If it doesn't ship, prove, or link — cut it. |
| Funnel, not gallery | Clear next actions: star spec-doc, visit humaniz.me, explore bubls. Not a showcase of everything ever built. |

---

## Component Design

### Task 1: Audit — Profile Repo Check

**Purpose**: Determine current state and create the profile repo if missing.

**Components**:
- `bytesbysamu/bytesbysamu` — GitHub's special profile repo. If a repo with this exact name exists and contains a `README.md`, GitHub renders it on the profile page. Must be public.

**Process**:
```bash
# Check if repo exists
gh repo view bytesbysamu/bytesbysamu

# If not, create it
gh repo create bytesbysamu --public --description "Profile README"

# List all public repos for pin candidates
gh repo list bytesbysamu --public --limit 50 --json name,description,updatedAt,stargazerCount
```

### Task 2: README.md — Content Structure

**Purpose**: The full README content, designed for GitHub's Markdown renderer.

**Components**:
- `README.md` — single file, under 80 lines

**Document Structure** (information hierarchy, top to bottom):

```
┌─────────────────────────────────────────┐
│  HERO (2 lines)                         │  ← Above fold
│  Identity statement + one-liner         │
├─────────────────────────────────────────┤
│  SHIPPED PRODUCTS (table, ~8 lines)     │  ← Above fold
│  Product | What | Status | Link         │
├─────────────────────────────────────────┤
│  METHODOLOGY (text flow, ~8 lines)      │  ← At fold line
│  Braindump → Specs → Code → Product    │
│  Five-Part Agent one-liner              │
├─────────────────────────────────────────┤
│  THE STACK (compact, ~6 lines)          │  ← Below fold
│  Frontend / Backend / AI / Infra        │
├─────────────────────────────────────────┤
│  NUMBERS (3-5 bullets, ~5 lines)        │  ← Below fold
│  Real metrics, defensible claims        │
├─────────────────────────────────────────┤
│  LINKS (2-3 lines)                      │  ← Bottom
│  Landing page, contact                  │
└─────────────────────────────────────────┘
```

**Content Rules**:
- Hero line: "I ship AI products solo." or similar — verb-forward, no "Hi, I'm..."
- Shipped Products table columns: Product, Description (≤10 words), Stack, Status, Link
- Methodology section uses Unicode arrows (`→`) not ASCII (`->`)
- Five-Part Agent: one sentence only. "The Five-Part Agent generates specs, plans tasks, executes code, validates output, and reviews quality — the assembly line behind every product."
- Numbers must be verifiable: live URLs, public repos, commit history. No vanity metrics.
- No horizontal rules (`---`) between sections — use headers only. Horizontal rules add visual weight and waste vertical space.

**Rendering Constraints**:
- GFM tables render with full-width borders on GitHub. Keep columns narrow.
- Emoji in headers render on all platforms. Use sparingly: one per section header max.
- Code blocks (triple backtick) render in a scrollable box. Avoid for the methodology flow — use inline Unicode instead.
- GitHub dark mode inverts some colors. Test any Unicode box-drawing characters.

### Task 3: Pinned Repos — Selection Matrix

**Purpose**: Choose the 6 repos that tell the right story.

**Selection Criteria**:

| Slot | Repo | Rationale |
|------|------|-----------|
| 1 | `spec-doc` | Hero pin. The methodology tool. Shows the system behind the products. |
| 2 | `bubls` | Design-forward app. Shows range beyond CLI/backend work. |
| 3 | `humanize-me` | Live production product. Proves shipping to real users with real payments. |
| 4-6 | TBD from audit | Criteria: active commits (last 90 days), demonstrates shipping, complements slots 1-3 |

**Pin Order**: GitHub displays pinned repos in a 2×3 grid (desktop) or 1×6 list (mobile). First row (slots 1-3) gets 80% of attention. spec-doc goes slot 1 (top-left, highest visibility).

### Task 4: Repo Metadata — Description + Topics

**Purpose**: First-impression text for each pinned repo.

**Description Pattern**: `{What it does} — {proof of life}`

| Repo | Description | Topics |
|------|-------------|--------|
| `spec-doc` | Document-first AI editor — write specs, ship code | `ai`, `spec-driven`, `claude-api`, `angular`, `developer-tools` |
| `bubls` | [From audit — app description] | `ios`, `angular`, `ionic`, `capacitor` |
| `humanize-me` | AI text humanizer — live at humaniz.me | `ai`, `saas`, `nextjs`, `flask`, `stripe` |

**Metadata Fields** (set via GitHub UI or API):
```bash
# Set description
gh repo edit bytesbysamu/spec-doc --description "Document-first AI editor — write specs, ship code"

# Set topics
gh api -X PUT repos/bytesbysamu/spec-doc/topics -f names='["ai","spec-driven","claude-api","angular","developer-tools"]'

# Set homepage URL
gh repo edit bytesbysamu/humanize-me --homepage "https://humaniz.me"
```

### Task 5: Validation Checklist

**Purpose**: Final gate before considering the capability done.

**Automated checks**:
```bash
# Verify README exists and is public
gh api repos/bytesbysamu/bytesbysamu/readme --jq '.name'

# Verify pinned repos (GitHub GraphQL)
gh api graphql -f query='{ user(login: "bytesbysamu") { pinnedItems(first: 6) { nodes { ... on Repository { name } } } } }'

# Check all links in README
# Extract URLs from README, curl each, check for 200
grep -oP 'https?://[^\s\)]+' README.md | while read url; do
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  echo "$status $url"
done
```

**Manual checks**:
- Open `github.com/bytesbysamu` in Chrome (desktop, light mode)
- Open in Chrome (desktop, dark mode)
- Open on mobile (or Chrome DevTools responsive mode)
- The "10-second test": can a stranger tell what this person does?

---

## Execution Flow

```
[Phase 1: Discovery]
   Task 1 (audit) ─────────────────────┐
                                        │
[Phase 2: Content — parallel]           ▼
   Task 2 (write README) ──────► Task 5 (validate)
   Task 3 (pin repos) ──► Task 4 (metadata) ──┘
```

Tasks 2 and 3 can run in parallel after Task 1 completes. Task 4 depends on Task 3 (need to know which repos are pinned before polishing metadata). Task 5 depends on both Task 2 and Task 4 being complete.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Text-only, no images | No badges, no screenshots, no diagrams as images | Images break in dark mode, depend on external CDNs, and add visual clutter. Text scales to every device and theme. A methodology diagram can be added later as a linked image if distribution posts need a visual hook. |
| Under 80 lines | Hard cap on README length | GitHub profiles that scroll are profiles that lose readers. Every line below the fold has diminishing returns. Density > length. The profile is a teaser, not documentation. |
| Table for shipped products | GFM table with Product / Description / Status / Link columns | Tables are the densest way to show multiple products. Lists waste vertical space. Tables also align naturally with the proof-of-work framing — it reads like a ledger, not a diary. |
| Unicode arrows for methodology | `→` not `->` or mermaid diagrams | Inline Unicode renders everywhere, costs no vertical space, and works in both light and dark mode. Mermaid diagrams are not supported in GitHub profile READMEs. ASCII arrows look unprofessional. |
| spec-doc as pin slot 1 | Top-left position in the 2×3 grid | spec-doc is the methodology tool — it's the "how" behind every product. Leading with the system (not any single product) positions the profile as a builder, not a one-product founder. humanize-me proves shipping; spec-doc proves repeatability. |
| No dynamic content | Static README, no GitHub Actions updating it | Dynamic READMEs (auto-updated stats, recent activity) add maintenance burden, break when APIs change, and signal "I spent time on my profile" instead of "I spent time shipping." Ship static. If it needs updating, update it manually when something ships. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

