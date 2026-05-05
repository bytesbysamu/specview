---
sidebar_position: 2
---

# 🎯 Twitter/X Account Setup – Epic

**Purpose**: Define scope and tasks for establishing a credible Twitter/X presence that converts THE post readers into followers.

**Source Analysis**: See [Analysis](./analysis.md) for identity decisions and constraints.

---

## Business Value

Twitter/X is where technical founders, indie hackers, and AI-augmented developers congregate. The building-in-public movement lives on Twitter — it's the native habitat for the exact audience that would adopt spec-doc methodology. Every other distribution channel (HN, Reddit, newsletters) ultimately drives people back to a Twitter profile as the "home base" for following ongoing work.

Currently, that home base doesn't exist. Someone reads THE post, wants to follow the journey, clicks through to... nothing. That's the highest-intent moment in the entire funnel — a reader who just consumed a long-form piece about the methodology and is actively looking for more — and it dead-ends. The conversion cost of fixing this is near zero (a few hours of content creation), but the opportunity cost of not fixing it compounds with every reader lost.

The profile serves a single function: convince a post reader in under 10 seconds that following this account will give them ongoing access to the methodology, the results, and the journey. Bio says what you do. Header shows the system. Pinned tweet is the deep dive. Three assets, one job.

---

## Scope

### What This Epic Covers

- Finalize identity decisions (handle, display name, profile photo)
- Write and validate the Twitter bio (under 160 characters)
- Design and produce the header image (deviation trend graph concept)
- Draft the pinned tweet thread (THE post condensed into tweet-sized hooks)
- Create the account and publish all assets
- Verify the full funnel: THE post → profile → follow

### What This Epic Does NOT Cover

- ❌ Content calendar or posting schedule
- ❌ Engagement strategy (replies, quote tweets, spaces)
- ❌ Follower growth targets or tactics
- ❌ Twitter/X API integration or bots
- ❌ Cross-platform syndication (LinkedIn, Threads, Bluesky)
- ❌ Twitter Blue/Premium subscription decisions
- ❌ Analytics setup or tracking

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Finalize identity: handle, display name, photo** | None | — | 1 hour | High |
| 2 | **Write and refine bio** | 1 | 3 | 1 hour | High |
| 3 | **Design header image (deviation trend graph)** | None | 2 | 2 hours | High |
| 4 | **Draft pinned tweet thread** | None | 2, 3 | 2 hours | High |
| 5 | **Create account and publish all assets** | 1, 2, 3, 4 | — | 30 min | High |
| 6 | **Verify end-to-end funnel** | 5 | — | 30 min | Medium |

### Task Details

#### Task 1: Finalize identity — handle, display name, photo

Resolve the three open identity decisions. **Handle**: check availability of preferred handles (@sam + last name, or a short memorable handle). Avoid branded handles (@specdoc) — the account represents a builder, not a product. **Display name**: real first + last name. **Photo**: select an existing professional-quality photo. If none exists, take one — phone camera, natural light, neutral background. No AI-generated photos. Deliverable: handle reserved, display name chosen, photo cropped to 400×400px.

#### Task 2: Write and refine bio

Start from the proposed bio: "I type 3 paragraphs. 4 agents ship 24 commits in 20 minutes. Building in public." Validate character count (must be under 160). Test three variations: (a) the original, (b) one that names the product/methodology, (c) one that leads with the outcome ("Ship a SaaS in a week"). Pick the one that best answers "why should I follow this person?" for a technical founder who just read THE post. Include the humaniz.me or spec-doc URL in the website field, not in the bio text. Deliverable: final bio text, website URL.

#### Task 3: Design header image (deviation trend graph)

Create a 1500×500px header image featuring the deviation trend graph — the visual signature of spec-doc methodology. Options: (a) screenshot a real deviation graph from a shipped project (e.g., the chain primitive task-2 run), (b) create a clean designed version using a charting tool or Figma. The image must be legible on mobile (center 600px is the safe zone). Minimal text — let the graph speak. Muted dark background, accent color on the trend line. Deliverable: header image file at 1500×500px, optimized for both mobile and desktop viewing.

#### Task 4: Draft pinned tweet thread

Condense THE post into a 5-7 tweet thread. Structure: (1) Hook — the most counterintuitive claim ("I mass-produced a methodology. Then I told AI to run it. 24 commits, 0 judgment calls."), (2) The problem — why chat-based AI dev doesn't scale, (3) The system — braindump → specs → tasks → execute, (4) The proof — real numbers (deviation count, commit count, wall-clock time), (5) The visual — embed the deviation graph or a before/after, (6) The link — THE post URL for the full deep dive, (7) CTA — "Follow for the journey. Next: [upcoming product]." Each tweet must stand alone as a complete thought. No "1/" numbering — let the content flow. First tweet must work as a standalone pinned tweet even if no one reads the thread. Deliverable: complete thread draft, all tweets under 280 characters each.

#### Task 5: Create account and publish all assets

Create the Twitter/X account with the finalized handle, display name, and photo. Upload the header image. Set the bio and website URL. Post the pinned tweet thread and pin the first tweet. Set location field if relevant (city or "building in public"). Leave the birth date and other optional fields empty. Deliverable: live account with all assets published.

#### Task 6: Verify end-to-end funnel

Walk the full reader journey: (1) open THE post in an incognito browser, (2) click the Twitter link in the post, (3) land on the profile — does the bio make sense in 5 seconds? (4) read the pinned thread — does it hook and deliver? (5) check mobile rendering — is the header cropped well? Is the bio readable? (6) check that the website link works. Fix anything that breaks the flow. Deliverable: confirmed working funnel from post to profile to follow.

---

## Success Criteria

- ✅ Twitter/X account exists with handle, display name, real photo, bio, header image, and website link
- ✅ Bio is under 160 characters and communicates the building-in-public + AI-augmented methodology angle
- ✅ Header image features the deviation trend graph and is legible on mobile
- ✅ Pinned tweet thread is 5-7 tweets, links to THE post, and the first tweet works standalone
- ✅ End-to-end funnel works: THE post → profile click → profile loads with full assets → clear follow motivation
- ✅ A technical founder landing on the profile cold can answer "what does this person do and why should I follow them" in under 10 seconds

---

## Non-Goals

- ❌ Optimizing for virality or algorithmic reach — the profile is a landing page, not a growth engine
- ❌ Establishing a posting cadence — that's a separate capability
- ❌ Building an audience before THE post is published — the post is the launch event
- ❌ A/B testing bio variations — pick one, ship it, iterate later based on signal
- ❌ Twitter Premium/Blue features — evaluate after the account has traction

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

