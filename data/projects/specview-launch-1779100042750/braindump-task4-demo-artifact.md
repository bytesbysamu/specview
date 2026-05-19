# Single-Workflow Demo Artifact

## What this is

A recorded artifact — animated screen capture or short video — that shows a real braindump transformed into a structured spec in under 60 seconds. This is the "show, don't tell" piece that the landing page embeds. No interactive playground, no feature tour. One messy input, one structured output. The entire pitch in motion.

## Why this exists (from analysis)

> A "painfully specific" demo (addicted-coffee's feedback) requires picking ONE workflow to showcase — that blocks repositioning the pitch.

The Reddit feedback was clear: devs ignore vague productivity claims but respond to "this removes this annoying workflow." The demo must show the specific workflow being removed, not list features.

## Architecture's demo design (verbatim)

> The demo is a recorded artifact (animated screen capture or short video) embedded directly in the landing page. It shows a real braindump — messy, unstructured, the kind of notes a developer actually has — transformed into a structured spec with analysis, epic, and architecture sections. The entire capture runs under 60 seconds.

> The artifact is a static file served from the `landing/` directory's public assets. No streaming, no player library, no external hosting. For maximum compatibility and instant playback, the primary format is a looping video element with a GIF fallback. File size target is under 5MB to avoid mobile load penalties.

> The pitch rewrite (Task 3) determines *which* workflow to capture — the demo must match the specific pain point the pitch leads with, not showcase breadth.

## Architecture's design decision (verbatim)

> **Single demo artifact, not interactive playground** — The playground (`live-playground.component.*`) demonstrates design system capabilities, not the spec generation workflow. A recorded demo controls the narrative and guarantees the visitor sees the full transformation. Trade-off: A recording can't respond to "but what about my use case." Acceptable — the anonymous trial CTA immediately below the demo lets them try their own input.

## Technology (from architecture)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Demo artifact | Looping video / GIF, self-hosted | No external dependencies, instant playback, works in Reddit embeds |

## What exists in the codebase

- `landing/` directory — where the artifact file lives
- `web-ng/src/app/live-playground.component.ts` — the existing playground (NOT what we're building; this is design system demo, not spec generation demo)

## Specs

- Format: looping video with GIF fallback
- Duration: under 60 seconds
- File size: under 5MB
- Content: real braindump (messy, unstructured) -> structured spec (analysis, epic, architecture)
- Hosting: self-hosted in `landing/` public assets
- No streaming, no player library, no external hosting

## Dependencies

- Depends on Task 3 (pitch rewrite) — the pitch frames which workflow to demo
- Blocks Task 5 (relaunch) — demo must be embeddable or linkable from the post

## Epic context

> **Task 4: Create single-workflow demo artifact** — Dependencies: Task 3 (pitch frames which workflow to demo). Effort: 1 day. Priority: High.

> **Success criteria**: Demo artifact shows one complete braindump -> spec transformation in under 60 seconds.

## Review findings and fixes applied

- **The braindump used for the demo should be genuinely messy.** Not a polished example. The point is: "look at this chaos, look at what comes out." The contrast IS the pitch.
- **Pick the workflow that matches the rewritten pitch hook** — "the first 1-2 hours turning chaos into structure." The demo should literally show someone's raw planning notes going in and a structured epic + architecture coming out.
- **Don't demo the playground** — The existing `live-playground.component` showcases the design system, not the spec generation flow. The demo must show the core product: paste braindump, get specs.
