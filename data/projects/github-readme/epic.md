---
sidebar_position: 2
---

# 🎯 GitHub Profile README – Epic

**Purpose**: Define scope and tasks for turning the GitHub profile into a proof-of-work landing page.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

Every distribution channel — Reddit posts, Twitter threads, Indie Hackers comments — funnels the technical audience back to GitHub. The profile is the single highest-leverage page for converting curious visitors into followers, stargazers, and eventually users. A blank profile leaks every visitor that distribution brings in.

The GitHub profile README is also the only "landing page" that costs zero to host, zero to maintain, and renders identically for every visitor. It's permanent distribution infrastructure. One hour of work here pays dividends on every future post, forever.

The concrete value: visitors who land on the profile should understand in under 10 seconds that this is a solo builder who ships real products with a repeatable methodology. The call to action is clear — star spec-doc (the methodology tool), visit humaniz.me (the live product), or explore bubls (the design-forward app). This converts passive GitHub visitors into the top of the user funnel.

---

## Scope

### What This Epic Covers

- Audit current GitHub profile and public repo state
- Create the `bytesbysamu/bytesbysamu` profile repo if it doesn't exist
- Write a complete README.md with hero, shipped products, methodology, numbers, and links
- Select and configure 6 pinned repositories
- Polish repo metadata (descriptions, topics) for all pinned repos
- Validate rendering on desktop and mobile, light and dark mode

### What This Epic Does NOT Cover

- ❌ Dynamic README updates (GitHub Actions that auto-refresh stats or activity)
- ❌ GitHub Pages or custom domain setup
- ❌ Rewriting README files inside pinned repos (only repo-level metadata changes)
- ❌ Social preview images (og:image) for repos — deferred until distribution posts need thumbnails
- ❌ GitHub Sponsors or funding.yml setup

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Audit profile + repo state** | None | — | 30 min | High |
| 2 | **Write README.md content** | 1 | — | 2 hours | High |
| 3 | **Select and pin 6 repositories** | 1 | 2 | 30 min | High |
| 4 | **Polish pinned repo metadata** | 3 | — | 30 min | Medium |
| 5 | **Validate rendering + links** | 2, 4 | — | 30 min | Medium |

### Task Details

#### Task 1: Audit profile + repo state
Check whether `bytesbysamu/bytesbysamu` exists. List all public repos. Note current pinned repos, bio, location, website link, and profile photo. Identify which repos have meaningful descriptions and topics vs. which are bare. Record current follower/star counts as a baseline. If the profile repo doesn't exist, create it with an empty README.md. This task produces the raw inventory that Tasks 2-4 consume.

#### Task 2: Write README.md content
Author the full profile README.md. Structure: (1) Hero — one-line identity statement, not "Hi I'm Sam" but "I ship AI products solo." (2) Shipped Products — table with product name, what it does, stack, status, and link. Include humaniz.me (live, $195K MRR validated market), Trendfy (active MVP), Spec Doc (methodology tool). (3) Methodology — the braindump → specs → code → product → feedback flywheel, rendered as a clean text-only flow diagram using Unicode arrows. One-liner about the Five-Part Agent (spec generator → task planner → executor → validator → reviewer). (4) Numbers — real metrics: products shipped, lines of spec generated, repos, whatever is defensible and concrete. (5) Links — landing page URL, Twitter/X handle if public. (6) Contribution graph context — a single sentence above or below the graph that frames it: "The green squares are products, not commits." Keep total length under 80 lines. No emoji spam. No "currently learning" sections. No skills badge walls.

#### Task 3: Select and pin 6 repositories
Pin exactly 6 repos. Confirmed pins: spec-doc (methodology tool — this is the hero pin), bubls (design-forward app — shows range). Candidate pins: humanize-me (live production product — proves shipping), and up to 3 others selected from the audit in Task 1. Selection criteria: does the repo demonstrate shipping (not boilerplate), does it have commits in the last 90 days (active), does it complement the other pins (variety of stack/domain). If fewer than 6 meaningful repos exist, pin what's real — never pad with empty repos.

#### Task 4: Polish pinned repo metadata
For each of the 6 pinned repos, set: (1) Description — one sentence, action-oriented, no "A project that..." phrasing. Examples: "Document-first AI editor — write specs, get code" for spec-doc. "AI text humanizer — live at humaniz.me" for humanize-me. (2) Topics — 3-5 relevant topics per repo (e.g., `ai`, `angular`, `claude-api`, `solo-founder`, `saas`). Topics improve GitHub search discoverability. (3) Website URL — set to the live product URL if one exists (humaniz.me for humanize-me). Do NOT change repo READMEs — only the metadata fields editable from the repo settings page.

#### Task 5: Validate rendering + links
Open the profile in a browser. Check: (1) README renders correctly on desktop and mobile. (2) All links work (landing page, product URLs, repo links). (3) Pinned repos show in the intended order with correct descriptions. (4) Dark mode and light mode both render cleanly — no invisible text, no broken Unicode. (5) The "10 second test" — show the profile to someone unfamiliar and ask what the person does. If the answer isn't "ships AI products solo," revise. Fix any issues found. This is the final gate.

---

## Success Criteria

- ✅ Profile README exists and renders on `github.com/bytesbysamu`
- ✅ Visitor understands "solo builder who ships AI products" within 10 seconds of landing
- ✅ spec-doc and bubls are pinned and visible
- ✅ At least one pinned repo links to a live production URL (humaniz.me)
- ✅ Methodology (braindump → specs → code → product) is visible without scrolling
- ✅ Five-Part Agent gets a one-liner mention
- ✅ No broken links, no rendering issues on desktop/mobile, light/dark mode
- ✅ Total README length under 80 lines — density over length

---

## Non-Goals

- ❌ Auto-updating stats or dynamic content — ship static, iterate later
- ❌ Skills/badge walls (no "I know JavaScript" shields)
- ❌ "Currently learning" or "fun facts" sections — this is proof of work, not a personality quiz
- ❌ Follower/star growth targets — the profile is infrastructure, not a KPI

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

