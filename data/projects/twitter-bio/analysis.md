---
sidebar_position: 1
---

# 🔍 Twitter/X Account Setup – Analysis

**Purpose**: Identify problems and open decisions blocking a credible Twitter/X presence.

**Date**: 2026-04-18

---

## Summary

Problem: Zero Twitter/X presence exists. THE post is ready to distribute, but the profile it links to doesn't exist or is empty. Three categories of issues: identity decisions not yet made, content not yet drafted, and visual assets not yet produced.

## Hard Constraints

- **Bio character limit**: Twitter bios cap at 160 characters. The proposed bio ("I type 3 paragraphs. 4 agents ship 24 commits in 20 minutes. Building in public.") is ~90 characters — fits comfortably with room for a URL or tagline addition.
- **Header image dimensions**: 1500×500px. Must read well on mobile (center-cropped) and desktop (full width). Text in headers is risky on mobile — visual-first is safer.
- **Pinned tweet**: Only one pinned tweet allowed. If using a thread, only the first tweet is pinned; the rest are replies. First tweet must stand alone as a hook.
- **No existing audience**: Cold start. The profile must be self-evidently credible without follower count as social proof.

## Open Questions

| Question | Options | Recommendation |
|----------|---------|----------------|
| Real name or handle? | Real name (Sam) vs. branded handle (@specdoc, @specdriven) | Real name. Building-in-public authenticity requires a face. Branded handles signal a product account, not a builder account. Technical audience follows people, not brands. |
| Profile photo source? | Existing photo vs. AI-generated via Trendfy photoshoot | Existing photo if one is professional enough. AI-generated creates an awkward contradiction — "I build AI tools" + "my photo is AI-generated" reads as gimmick to a technical audience. Use a real photo; save AI photoshoot for product marketing. |
| Header image: dashboard or deviation graph? | Real dashboard screenshot vs. deviation trend graph vs. designed graphic | Deviation trend graph. The dashboard is generic (every dev tool has a dashboard). The deviation graph is unique to spec-doc methodology — it's the visual hook that makes someone ask "what's a deviation budget?" which is exactly the entry point into THE post. |

## Dependencies

- THE post must be written and hosted before the pinned tweet can link to it.
- Profile photo must be selected/taken before account creation.
- Header image requires either a real deviation graph from a shipped project or a designed mockup.

## Explicitly Out of Scope

- Content calendar or posting strategy.
- Follower growth tactics or engagement automation.
- Cross-posting to other platforms (LinkedIn, Threads, Bluesky).
- Twitter/X API integration or automation tooling.

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

