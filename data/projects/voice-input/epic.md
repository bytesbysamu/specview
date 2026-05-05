---
sidebar_position: 2
---

# 🎯 Voice Input – Epic

**Purpose**: Define scope and tasks for adding on-device voice input to the Bubls Text page.

**Source Analysis**: See [Analysis](./analysis.md) for problems addressed and open questions resolved.

---

## Business Value

Voice Input transforms Bubls from a text rewriter into a voice-to-polished-text tool — a category no iOS competitor occupies. The marketing pitch shifts from "paste your text and improve it" to "talk to your phone, get a polished email in seconds." This is the differentiator for the Reddit product launch post and the App Store listing.

Gating voice input as a Pro feature adds concrete value to the paid tier. Free users see the mic button but hit an upgrade prompt on tap — a natural upsell moment that doesn't interrupt the core rewrite flow. The feature costs nothing to operate (on-device transcription, no API calls), so every Pro conversion from voice input is pure margin.

The implementation is deliberately minimal: one Capacitor plugin, one adapter service, one button, one recording indicator. No streaming transcription, no voice commands, no language picker. Ship the wedge, validate with the Reddit post, iterate from signal.

---

## Scope

### What This Epic Covers

- `VoiceInputService` adapter wrapping `@capacitor-community/speech-recognition` with mock mode
- Microphone button integrated into the Text page textarea
- Recording state management (idle → recording → processing → done)
- On-device transcription with 60-second timeout
- Pulsing mic icon with amplitude-reactive ring as recording indicator
- Haptic feedback on recording start and stop
- Pro feature gate with upgrade prompt for free users
- Reduced-motion accessibility support
- iOS permission handling (`NSSpeechRecognitionUsageDescription`, `NSMicrophoneUsageDescription`)
- Platform detection to hide mic button on web

### What This Epic Does NOT Cover

- ❌ Streaming/live transcription (text appears only after stop)
- ❌ Language selection UI
- ❌ Voice commands ("make it formal")
- ❌ Full waveform visualizer
- ❌ Transcription history or saved recordings
- ❌ Android-specific testing or optimization
- ❌ Append/replace toggle UI (v1 uses smart default: replace if empty, append if text exists)

---

## Tasks

**Note**: Task status is tracked in [Timeline](./timeline.md).

| # | Task | Dependencies | Parallel | Effort | Priority |
|---|------|--------------|----------|--------|----------|
| 1 | **VoiceInputService adapter + mock** | None | — | 0.5 day | High |
| 2 | **iOS permission setup + Capacitor config** | None | 1 | 0.5 day | High |
| 3 | **Mic button + recording indicator component** | 1 | — | 1 day | High |
| 4 | **Text page integration + state wiring** | 1, 3 | — | 0.5 day | High |
| 5 | **Pro feature gate + upgrade prompt** | 4 | 6 | 0.5 day | Medium |
| 6 | **Haptics + reduced-motion + platform detection** | 3 | 5 | 0.5 day | Medium |
| 7 | **Device testing + edge cases** | All | — | 0.5 day | High |

### Task Details

#### Task 1: VoiceInputService Adapter + Mock

Create `VoiceInputService` in the voice-input feature folder following the Adapter pattern. The service wraps `@capacitor-community/speech-recognition` behind a provider-agnostic interface. Exposes: `requestPermission(): Promise<PermissionStatus>`, `startListening(options: VoiceInputOptions): void`, `stopListening(): Promise<string>`, `isListening: Signal<boolean>`, `partialResult: Signal<string>`. Mock mode (`VOICE_INPUT_PROVIDER=mock`) returns canned transcription after a 2-second delay for web development. Real mode delegates to the Capacitor plugin. Error states: permission denied, recognition failed, timeout reached. All exposed as typed results, never thrown exceptions.

#### Task 2: iOS Permission Setup + Capacitor Config

Add `@capacitor-community/speech-recognition` to `package.json`. Add `NSSpeechRecognitionUsageDescription` ("Bubls uses speech recognition to transcribe your voice into text for rewriting") and `NSMicrophoneUsageDescription` ("Bubls needs microphone access to hear your voice for transcription") to `Info.plist`. Register the plugin in `capacitor.config.ts`. Run `npx cap sync ios`. Verify the plugin initializes without crash on simulator.

#### Task 3: Mic Button + Recording Indicator Component

Create `VoiceMicButtonComponent` — a standalone, OnPush component rendering a mic icon button with `data-test="voice-mic-button"`. States: idle (mic icon, neutral), recording (pulsing mic with amplitude ring, red accent), processing (spinner). The pulsing animation uses CSS `@keyframes` with a scale transform on an outer ring element. Amplitude modulation: if partial results are arriving, ring pulses faster; if silence, ring pulses slowly. Component emits `(transcriptionComplete)` event with the final text string. Accepts `[disabled]` input for feature gate integration.

#### Task 4: Text Page Integration + State Wiring

Wire `VoiceMicButtonComponent` into the Text page textarea area. Position the mic button inside the textarea container, bottom-right corner, overlaying the textarea. On `(transcriptionComplete)`: if textarea is empty, set textarea value to transcription; if textarea has content, append a space + transcription. Update the textarea's form control or signal so downstream rewrite operations see the new text. Ensure the mic button doesn't interfere with textarea focus, scrolling, or existing tap targets.

#### Task 5: Pro Feature Gate + Upgrade Prompt

Wrap the mic button tap handler with a feature gate check. If the user's `enabled_features` array does not include `'voice_input'`, show an Ionic alert or modal explaining the feature ("Unlock Voice Input — speak your text instead of typing") with an upgrade button routing to the subscription page. Free users see the mic button (discovery) but cannot activate recording (conversion). The button itself is always visible — the gate fires on interaction, not on render.

#### Task 6: Haptics + Reduced-Motion + Platform Detection

Add haptic feedback via `@capacitor/haptics`: medium impact on recording start, light impact on recording stop. Check `prefers-reduced-motion` media query: if enabled, disable the pulsing animation on the recording indicator (static red dot instead). Platform detection via `Capacitor.isNativePlatform()`: hide the mic button entirely on web builds (no Web Speech API fallback). Ensure mock mode still works in web dev by checking `VOICE_INPUT_PROVIDER` env var — mock mode shows the button on web for testing.

#### Task 7: Device Testing + Edge Cases

Test on physical iOS device: permission prompt flow (first launch, previously denied), recording start/stop, 60-second timeout behavior, transcription accuracy for short phrases and long paragraphs, app backgrounding during recording (should stop gracefully), rapid start/stop tapping (debounce or ignore), textarea append behavior with existing content. Verify haptics fire correctly. Verify reduced-motion removes animation. Verify free user sees upgrade prompt. Verify web build hides mic button.

---

## Success Criteria

- ✅ User taps mic, speaks for up to 60 seconds, taps stop → transcribed text appears in textarea within 1 second of stopping
- ✅ User taps any rewrite mode after voice input → rewrite operates on transcribed text identically to typed text
- ✅ Free user taps mic → sees upgrade prompt, no recording starts
- ✅ Web build → mic button not visible
- ✅ Reduced-motion enabled → no pulsing animation, static indicator instead
- ✅ Haptic feedback on start and stop (verified on physical device)
- ✅ Permission denied → clear error message, button returns to idle state
- ✅ Zero API cost — all transcription on-device
- ✅ App backgrounded during recording → recording stops gracefully, partial transcription delivered if available
- ✅ Unprompted return rate for Pro users with voice input enabled: track as cohort metric in analytics

---

## Non-Goals

- ❌ Real-time streaming transcription (text appearing word-by-word as user speaks)
- ❌ Multi-language support UI (device locale is sufficient)
- ❌ Voice-activated rewrite commands
- ❌ Audio recording storage or playback
- ❌ Custom speech recognition models or fine-tuning
- ❌ Android-specific optimizations

---

## Related Documents

- [Analysis](./analysis.md)
- [Architecture](./architecture.md)
- [Timeline](./timeline.md)

