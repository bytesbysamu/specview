---
sidebar_position: 1
---

# 🔍 Voice Input – Analysis

**Purpose**: Identify problems driving this capability and surface decisions not yet made.

**Date**: 2026-04-18

---

## Problem

Bubls is currently a text-in, text-out rewriter. That puts it in the same category as Grammarly, Wordtune, and Apple Intelligence — all of which have stronger brand recognition and deeper feature sets. Without a differentiator, Bubls competes on price alone, which is unsustainable for a solo product. Voice-to-rewrite creates a new input modality that no competitor offers, shifting the value proposition from "rewrite text better" to "speak and get polished text."

---

## Hard Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| On-device transcription only | Builder profile: no API cost for input pipeline | Rules out Whisper API, Google Speech-to-Text, Deepgram — must use `@capacitor-community/speech-recognition` which delegates to iOS Speech framework |
| Adapter pattern mandatory | Architecture principles: ACL for external APIs | `VoiceInputService` must wrap the Capacitor plugin; feature code never imports the plugin directly |
| Pro feature gate | Braindump: feature-gated as Pro | Route guard checks `enabled_features` array on user object; free users see upgrade prompt, never a 404 |
| No cross-feature imports | Architecture principles: feature isolation | Voice input lives in its own feature folder; communicates with Text page via signals or events, not direct imports |
| Accessibility: reduced-motion | Braindump: reduced-motion disables pulse animation | `prefers-reduced-motion` media query must suppress the recording indicator animation |

---

## Open Questions

| Question | Options | Recommendation | Impact |
|----------|---------|----------------|--------|
| Append or replace textarea content? | A) Always replace B) Always append C) Replace if empty, append if text exists | **Option C** — replace if empty, append with space separator if text exists. No toggle for v1 (toggle adds UI complexity for an edge case). If users request it, add in v2 | Affects `VoiceInputService.onResult` handler logic |
| Recording timeout duration? | 30s / 60s / configurable | **60 seconds** — a full email dictation can run 45-50 seconds. 30s cuts off mid-thought. Not configurable for v1; hardcoded constant, easy to change later | Affects `SpeechRecognition.start()` options |
| Waveform visualizer or pulsing icon? | A) Canvas waveform B) Pulsing mic icon C) Pulsing mic + amplitude ring | **Option C** — pulsing mic icon with a single amplitude-reactive ring. Simpler than a full waveform, but more alive than a static pulse. Uses `SpeechRecognition` partial results or silence detection to modulate ring scale | Affects recording indicator component complexity |
| Web fallback behavior? | A) Hide mic button B) Show button, explain on tap C) Use Web Speech API | **Option A** — hide the mic button on web. Web Speech API has inconsistent browser support and different privacy implications. Capacitor-only feature. Mock mode for dev/testing uses simulated transcription | Affects platform detection logic |

---

## Dependencies

- `@capacitor-community/speech-recognition` plugin must be installed and configured in `capacitor.config.ts`
- iOS `NSSpeechRecognitionUsageDescription` and `NSMicrophoneUsageDescription` must be added to `Info.plist`
- Text page textarea must expose a signal or method for external text injection (currently may be internal state)
- Pro feature gate infrastructure must exist (user object with `enabled_features`, route guard pattern)

---

## Explicitly Out of Scope

- Continuous/streaming transcription (live text appearing as user speaks) — v1 delivers final transcript on stop
- Language selection UI — uses device locale, no picker
- Voice command interpretation ("make it formal") — voice is input only, user still taps the rewrite mode
- Waveform visualizer — deferred to v2 if users request richer recording feedback
- Transcription history or saved recordings — text goes to textarea and that's it
- Android support — Capacitor plugin supports it, but Bubls is iOS-first; Android is a later concern

---

## Related Documents

- [Epic](./epic.md)
- [Architecture](./architecture.md)

