---
sidebar_position: 2
---

# 🎯 AI Tool Directory Submissions – Epic

**Purpose**: Define scope and tasks for listing Humaniz.me on 10 AI tool directories.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed.

---

## Business Value

AI tool directories are the lowest-effort distribution channel available to a solo founder. A single afternoon of submissions creates permanent listings that surface Humaniz.me to users actively searching for AI writing tools — high-intent traffic that converts better than social media impressions. The SEO backlinks from 10 directories also improve organic Google ranking for "AI text humanizer" and related searches.

The competitive context makes this urgent: StealthGPT ($195K MRR validated) is already listed on most of these directories. Every day Humaniz.me isn't listed is a day where searchers find StealthGPT at $15/mo and never discover the $5/mo alternative. Directories are where comparison shoppers land.

This is a one-time effort with permanent returns. The submission content (descriptions, screenshots, categories) also becomes reusable collateral for future portfolio products — each new product launch can follow the same template and submit to the same 10 directories in under an hour.

---

## Scope

### What This Epic Covers

- Finalize positioning and one-liner for directory use
- Create reusable asset package (logo variants, screenshots, descriptions at 50/100/200 word lengths)
- Draft tailored submissions for all 10 directories
- Add UTM tracking to submission URLs
- Submit to all 9 non-PH directories
- Prepare Product Hunt draft (not launch)
- Document which directories are instant vs review-gated

### What This Epic Does NOT Cover

- ❌ Product Hunt launch-day execution (upvote coordination, timing, comments)
- ❌ Paid/sponsored placements on any directory
- ❌ SEO changes to humaniz.me itself
- ❌ Listings for future portfolio products
- ❌ Ongoing directory monitoring or review responses
- ❌ Social media or Reddit/Twitter posting

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **Lock positioning and one-liner** | None | — | 1 hour | Critical |
| 2 | **Create asset package** | 1 | 3 | 2 hours | High |
| 3 | **Draft 10 directory submissions** | 1 | 2 | 3 hours | High |
| 4 | **Add UTM tracking to URLs** | None | 1,2,3 | 30 min | High |
| 5 | **Submit to 9 directories + PH draft** | 2, 3, 4 | — | 2 hours | High |
| 6 | **Document directory metadata** | 5 | — | 30 min | Medium |

### Task Details

#### Task 1: Lock positioning and one-liner

Decide the canonical positioning for all directory submissions. Choose between "AI Text Humanizer," "AI Text Rewriter," or "AI Content Humanizer" as the primary category label. Write one canonical one-liner (under 80 characters) and one canonical tagline (under 140 characters). Decision criteria: (a) what category exists on the most directories, (b) what StealthGPT uses (to appear in the same searches), (c) what accurately describes the product. Output: a `directory-positioning.md` file with the locked choices and rationale.

#### Task 2: Create asset package

Assemble all visual and text assets needed across 10 directories into a single reusable folder. Includes: logo at 256x256, 512x512, and 1024x1024 PNG; one hero screenshot (1280x800) showing the SuperEditor in action; one screenshot showing the 3-pass Heavy mode result; app name exactly as it should appear ("Humaniz.me"); URL (https://humaniz.me); three description variants at 50 words, 100 words, and 200 words. Each description must mention: Claude-powered, streaming humanization, free tier available, pricing from $5/mo.

#### Task 3: Draft 10 directory submissions

For each of the 10 directories, produce a complete submission draft in a single markdown file. Each entry includes: directory name, submission URL, required fields mapped to asset package content, category selection (from the directory's actual taxonomy), and any directory-specific notes (e.g., Product Hunt requires a "maker comment" draft). Directories: Product Hunt, There's An AI For That, Futurepedia, AI Tool Guru, TopAI.tools, Toolify.ai, AItoolslist, SaaS AI Tools, Uneeq AI, Creatie.ai. Descriptions should differentiate from StealthGPT by leading with price and Claude quality.

#### Task 4: Add UTM tracking to URLs

Create UTM-tagged URLs for each directory so traffic attribution is possible in analytics. Format: `https://humaniz.me?utm_source={directory-slug}&utm_medium=directory&utm_campaign=launch-apr-2026`. Produce a lookup table mapping each directory to its tagged URL. These URLs replace the bare `https://humaniz.me` in every submission draft.

#### Task 5: Submit to 9 directories + PH draft

Execute the actual submissions using the drafted content and asset package. For the 9 non-PH directories: fill out each submission form, upload assets, submit. For Product Hunt: create a draft listing (not published) with maker comment, first comment draft, and scheduled launch date TBD. Record submission timestamps and whether the listing is instant or pending review.

#### Task 6: Document directory metadata

After all submissions, create a reference document listing each directory with: submission date, approval status (instant/pending/approved/rejected), listing URL once live, estimated monthly traffic (from SimilarWeb or directory's own stats if shown), and whether the directory allows editing after submission. This becomes the reusable playbook for future product launches.

---

## Success Criteria

- ✅ All 9 non-PH directories submitted with consistent positioning and UTM-tracked URLs
- ✅ Product Hunt draft created and saved (not launched)
- ✅ Asset package documented and reusable for future products
- ✅ At least 5 of 9 listings are live (instant or approved) within 1 week
- ✅ UTM tracking confirmed working — at least one directory referral visible in analytics within 2 weeks
- ✅ Directory metadata document complete for future product reuse

---

## Non-Goals

- ❌ Optimizing for directory SEO ranking (just get listed, don't game algorithms)
- ❌ Creating directory-specific landing pages on humaniz.me
- ❌ Responding to directory reviews or comments (post-launch activity)
- ❌ A/B testing different descriptions across directories
- ❌ Tracking conversion from directory visit to paid subscription (UTM tracks visits only for now)

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

