---
sidebar_position: 3
---

# 🏗️ Voice Demo Script – Solution Architecture

**Purpose**: Technical design for producing the 30-second demo recording of Humaniz.me.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

This is a content production pipeline, not a software system — but it still has components, dependencies, and failure modes that benefit from systematic design. The pipeline has three phases: preparation (script + device validation), production (rehearsal + recording), and post-production (trim + captions + upload). Each phase has a clear input, process, and output, with explicit quality gates between them.

The critical technical risk is the interaction between iOS screen recording and in-app microphone access. iOS screen recording captures the screen buffer and optionally system audio, but the microphone is a contested resource — if screen recording claims it, the web app's `getUserMedia()` call for voice input may fail silently or produce no audio. This must be resolved before any recording attempt.

The secondary technical concern is API response latency. The Humanize endpoint streams via the Claude API. Cold starts or high-traffic moments could push response time beyond the 4–6 second window allocated per beat. The architecture mitigates this with a pre-warming step and fallback timing.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Ship the car, not the engine | No custom recording tools, no video editing pipeline. Use iOS built-in screen recording + one free editing app. The demo is a disposable artifact, not infrastructure. |
| Batch over real-time | Record 3–5 takes, select the best. Don't try to get one perfect take — that's optimizing in real-time. Batch the attempts, pick the winner in post. |
| Mock mode first | If the API is slow or flaky during recording, have a fallback: shorter input text that produces faster responses. Don't build a mock API — just use shorter text as the "mock." |
| One take, one artifact | No compositing, no split-screen, no multi-source editing. Single continuous screen recording. This constraint is a feature — it proves authenticity. |

---

## Component Design

### Task 1: Demo Script

**Purpose**: Define the exact content and timing for each beat of the recording.

**Components**:
- `script.md` — The beat-by-beat script with exact text, timing marks, and expected outputs
- Sample AI text (the paste content) — must trigger instant "that's ChatGPT" recognition
- Spoken sentence — must be short, natural, and produce a transcription that visibly benefits from humanization

**Patterns**: The script follows a problem → solution → differentiator → proof structure compressed into four visual beats. Beat 1–2 is the baseline (every competitor does this). Beat 3–4 is the differentiator (voice input, nobody does this). The script front-loads the familiar so viewers anchor on "I know what this is" before the surprise.

**Text Selection Criteria**:
The pasted text must exhibit at least 3 of the 5 classic ChatGPT tells:
1. "In today's [adjective] [noun]" opener
2. "It's important to note/acknowledge" filler
3. "Whether you're a [X] or [Y]" false inclusivity
4. "Significantly/fundamentally/essentially" adverb stacking
5. Parallel structure with gerunds ("leveraging," "enhancing," "transforming")

The spoken sentence must be:
- Under 10 words (transcription must complete in < 2 seconds)
- Casual register (not formal — the contrast with the humanized output is the point)
- A real use case (meeting notes, email draft, quick message — not lorem ipsum)

### Task 2: iOS Recording Validation

**Purpose**: Confirm the recording method works before investing time in rehearsal.

**Components**:
- iOS Screen Recording (Control Center → Screen Recording)
- Safari/Chrome with Humaniz.me loaded
- In-app microphone via Web Speech API or `getUserMedia()`

**Technical Risk — Mic Contention**:

iOS screen recording and web microphone access compete for the hardware mic. Three scenarios to test:

| Scenario | Screen Recording | Web App Mic | Result |
|----------|-----------------|-------------|--------|
| A: No conflict | Captures screen | Captures voice | ✅ Ideal — use iOS screen recording as-is |
| B: Mic blocked | Captures screen | Fails silently | ❌ Need workaround |
| C: Audio bleed | Captures screen + mic audio | Works but audio leaks into recording | ⚠️ Acceptable if muted in post |

**Workarounds if Scenario B**:
1. **QuickTime mirroring**: Connect iPhone to Mac via USB, use QuickTime Player → New Movie Recording → select iPhone as camera. Mac records the screen, iPhone mic is free for the web app.
2. **Second device**: Use a second phone or iPad to film the iPhone screen. Lower quality but zero technical risk.
3. **Simulator**: Use Xcode iOS Simulator on Mac. No mic conflict but looks less authentic (no status bar, no notch).

**Recommendation**: Test Scenario A first. If it works, stop. If not, QuickTime mirroring is the best fallback — native resolution, no quality loss, and the status bar + notch are visible (proving it's a real device).

### Task 3: Rehearsal Protocol

**Purpose**: Validate timing and identify failure points before the final recording.

**Components**:
- Timer (iOS Clock app, visible on another device or mental count)
- Humaniz.me loaded and pre-warmed (one humanize call completed before rehearsal starts)

**Pre-warming protocol**:
1. Open Humaniz.me in the browser
2. Paste any text, tap Humanize, wait for complete response
3. This ensures the backend connection is established, any cold-start latency is absorbed, and the Claude API has a warm context

**Rehearsal checklist per run**:
- [ ] Total time under 30 seconds?
- [ ] Beat 1 (paste): Text visibly fills textarea? No keyboard blocking the view?
- [ ] Beat 2 (humanize): Streaming response starts within 2 seconds? Completes within 6 seconds?
- [ ] Beat 3 (voice): Mic icon tap is visible? Transcription appears in real-time?
- [ ] Beat 4 (humanize #2): Response is visibly different from spoken text?
- [ ] No dead air longer than 2 seconds at any point?

### Task 4–5: Recording + Post-Production

**Purpose**: Capture the final take and apply minimal polish.

**Components**:
- Validated recording method (from Task 2)
- Rehearsed script (from Task 3)
- CapCut or iMovie (free, iOS) for trim + captions

**Recording environment**:
- Do Not Disturb ON (no notifications during recording)
- Battery above 50% (low battery warning is a demo killer)
- WiFi on strong connection (API latency is load-bearing)
- Clear any notification badges from the status bar
- Close all other browser tabs

**Caption specification**:
- Font: System default (San Francisco on iOS), white, 16pt equivalent
- Background: Black at 60% opacity, rounded corners, 8px padding
- Position: Bottom center, 40px above home indicator
- Duration: Each caption visible for the duration of its beat, no fade in/out
- Three captions total — more than three in 30 seconds creates visual noise

**Export specification**:
- Format: MP4 (H.264)
- Resolution: Native device capture (1170×2532 for iPhone 14/15 Pro, or equivalent)
- Frame rate: 30fps (matches iOS screen recording default)
- No audio track (Reddit autoplays muted; including audio adds file size for no benefit)
- File size target: Under 20MB (Reddit video upload limit is 1GB but smaller = faster processing)

---

## Execution Flow

```
[Phase 1: Preparation]
   Task 1 (Script) ──────┐
   Task 2 (iOS Validate) ─┤
                           │
[Gate: Both pass]          ▼
                           │
[Phase 2: Production]      │
   Task 3 (Rehearse) ──────┤
                           │
[Gate: Timing validated]   ▼
                           │
   Task 4 (Record) ────────┤
                           │
[Phase 3: Post-Production] ▼
                           │
   Task 5 (Captions) ──┐  │
   Task 6 (Post Copy)──┤  │
                        │  │
[Gate: Video + copy]    ▼  │
                           │
   Task 7 (Post) ──────────┘
```

Tasks 1 and 2 run in parallel (no dependency). Task 6 (Reddit post copy) can run in parallel with Tasks 3–5 since it only depends on the script content (Task 1), not the final video.

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Sequential vs side-by-side | Sequential (real-time transformation) | Side-by-side requires compositing, breaks "one continuous take" constraint, and feels like an advertisement rather than a genuine demo. Sequential is what a real user would see. |
| Captions vs no captions | Minimal captions (3 labels) | Reddit autoplays muted. Without any visual labels, a viewer must infer what each tap does. Three short labels ("Paste AI text," "Humanize ✨," "Speak → Humanize") add clarity without visual noise. Full subtitles would overwhelm a 30-second video. |
| Mobile vs desktop recording | Mobile (iPhone screen recording) | The audience (r/ChatGPT users) browses Reddit on mobile. A mobile demo signals "this works on your phone right now." Desktop recordings feel like developer demos, creating distance between the viewer and the product. |
| Audio track vs silent | Silent (no audio) | Reddit autoplays muted. Adding audio narration means the demo is incomprehensible to 90%+ of viewers who never unmute. The demo must be fully self-explanatory from visuals alone. |
| Number of takes | 3–5, select best | Optimizing for one perfect take is high-stress and low-probability. Batch 3–5 attempts, select the cleanest. Total recording time: 5–10 minutes for 30 seconds of output. |
| Editing tool | CapCut (free, iOS) | Already on-device, supports caption overlays, exports MP4 natively. iMovie works too but caption positioning is less flexible. No need for desktop editing software for a 30-second clip. |
| CTA in video vs post body | Post body only | In-video CTAs ("Visit humaniz.me!") feel desperate and get downvoted on Reddit. The URL goes in the post body where interested viewers will find it. The video sells the capability, not the product name. |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

