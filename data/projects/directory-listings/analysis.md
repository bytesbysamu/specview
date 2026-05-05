---
sidebar_position: 1
---

# 🔍 AI Tool Directory Submissions – Analysis

**Purpose**: Identify problems and open decisions before listing Humaniz.me on directories.

**Date**: 2026-04-18

---

## Summary

- **Total Issues**: 7
- **Critical**: 1
- **High**: 3
- **Medium**: 3

---

## Issue Breakdown

### Positioning Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No settled one-liner or category — "AI text humanizer" vs "AI text rewriter" vs "AI content rewriter" each attract different searchers | CRITICAL | Task 1 |
| Product Hunt listing requires launch-day coordination (upvotes, comments, timing) which is out of scope for passive submissions — mixing them risks a wasted PH launch | HIGH | Task 1 (PH scoped to prep only) |

### Content Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No reusable asset package — each directory wants slightly different logo sizes, screenshots, and description lengths (50-200 words) | HIGH | Task 2 |
| Descriptions need to differentiate from StealthGPT and other humanizers already listed on these directories | MEDIUM | Task 3 |

### Measurement Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| No way to know which directories actually send traffic vs just sit as dead backlinks | HIGH | Task 4 |
| No baseline traffic data to compare against post-submission | MEDIUM | Task 4 |

### Process Issues

| Issue | Severity | Addressed By |
|-------|----------|--------------|
| Some directories require approval/review (days to weeks); others are instant — no inventory of which is which | MEDIUM | Task 5 |

---

## Hard Constraints

- Humaniz.me is live in production — URLs and pricing are real and current
- Product Hunt is prep-only; the actual launch is a separate, coordinated event
- Solo founder — no team to coordinate upvote campaigns or monitor 10 dashboards
- Descriptions must be factually accurate (streaming humanization, 6-tool SuperEditor, 3-pass Heavy mode, Stripe billing)

## Open Questions

1. **Category naming**: Directories use different taxonomies. "AI Writing Tools" is broad. "AI Text Humanizer" is precise but may not exist as a category on every directory. Decision: use the most specific category available, fall back to "AI Writing Tools" or "AI Content Tools."
2. **Pricing display**: Some directories show pricing. List the free tier ($0, 3/day) prominently to maximize click-through, or list the range ($0–$25/mo)?
3. **Competitor differentiation**: StealthGPT is already on most of these directories at $15/mo. Lead with price ($5/mo starter) or quality (Claude-powered, 3-pass)?

## Dependencies

- Live production URL (humaniz.me) — done
- Stripe pricing configured — done
- Logo and brand assets — need to verify current state

## Explicitly Out of Scope

- Product Hunt launch execution (only prep/draft)
- Paid directory placements or sponsored listings
- SEO optimization of humaniz.me itself
- Social media posting (separate capability)
- Directory listings for future portfolio products (Cold Email Writer, etc.)

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

