# Task 4: Voice Input on Text Page — Implementation Plan (v2)

## 1. Goal

Add a microphone button to the Text page textarea. Tap starts recording with pulse animation + waveform visualizer. Tap again (or 30s timeout) stops recording. On-device transcription via `@capacitor-community/speech-recognition`. Transcribed text fills the textarea. Feature-gated as Pro.

## 2. Files Created / Modified

| File | Action | Purpose |
|------|--------|---------|
| `src/app/services/voice-input.service.ts` | CREATE | Adapter wrapping `@capacitor-community/speech-recognition` + haptics |
| `src/app/services/voice-input.service.spec.ts` | CREATE | TestBed spec for the adapter service |
| `src/app/pages/text/components/mic-button.component.ts` | CREATE | Mic button with pulse ring animation + waveform visualizer |
| `src/app/pages/text/components/mic-button.component.scss` | CREATE | Styles: pulse keyframes, waveform bars, pro badge, reduced-motion |
| `src/app/pages/text/components/mic-button.component.spec.ts` | CREATE | TestBed spec for mic button component |
| `src/app/pages/text/text.page.ts` | MODIFY | Wire mic button, handle transcription callback |
| `src/app/pages/text/text.page.scss` | MODIFY | Textarea wrapper layout for inline mic button |
| `src/app/pages/text/text.page.spec.ts` | MODIFY | Add voice input integration tests |
| `scripts/architecture-acl-check.mjs` | MODIFY | Add `@capacitor-community/speech-recognition` to BANNED list |
| `package.json` | MODIFY | Add `@capacitor-community/speech-recognition` dependency |

## 3. VoiceInputService (adapter)

Wraps `@capacitor-community/speech-recognition` Capacitor plugin. The page never imports the plugin directly (ACL rule).

**Public API:**
- `available(): Promise<boolean>` — checks platform support
- `requestPermission(): Promise<'granted' | 'denied'>` — requests mic permission with rationale
- `hasPermission(): Promise<boolean>` — checks current permission state
- `startListening(lang?: string): Promise<void>` — begins speech recognition
- `stopListening(): Promise<string>` — stops and returns transcript
- `onPartialResult: Signal<string>` — partial transcript for live preview
- `isListening: Signal<boolean>` — recording state signal
- `hapticStart(): Promise<void>` — light impact on start
- `hapticStop(): Promise<void>` — light impact on stop

**Mock mode:** When `!Capacitor.isNativePlatform()` (web), returns fixture transcription ("This is a test transcription from the voice input mock.") after a 1.5s delay. Enables testing without a device.

**30s timeout:** Internal timer auto-calls `stopListening()` after 30 seconds.

## 4. MicButtonComponent

Standalone component placed inline with the textarea.

**Inputs:**
- `disabled: boolean` — mirrors textarea disabled state
- `locked: boolean` — true for free users (shows Pro badge)
- `listening: boolean` — recording state from service signal

**Outputs:**
- `micTap: EventEmitter<void>` — emitted on tap (parent handles permission + start/stop logic)
- `lockedTap: EventEmitter<void>` — emitted when locked mic is tapped

**Template:** Single `<button>` with:
- Microphone icon (inline SVG, no ionicons dependency)
- `data-test="mic-button"`
- `.mic--listening` class when active (pulse ring animation)
- `.mic--locked` class + `data-test="mic-pro-badge"` Pro badge when locked
- Waveform visualizer: 5 bars with CSS animation (height oscillates), visible only when listening
- `data-test="mic-waveform"` on waveform container

**Accessibility:**
- `aria-label="Start voice input"` / `"Stop voice input"` based on state
- `@media (prefers-reduced-motion: reduce)` — disables pulse animation, waveform uses opacity fade instead

## 5. Text Page Integration

Wire into `text.page.ts`:

1. Inject `VoiceInputService`
2. Add signals: `isListening`, `voiceProLocked`, `micPermissionDenied`, `permissionTooltipVisible`
3. Place `<app-mic-button>` adjacent to the textarea (inside a wrapper div)
4. On `micTap`:
   - If listening: stop, get transcript, fill textarea
   - If not listening: check permission, request if needed, start
   - If permission denied: show tooltip with Settings instructions
5. Transcript fill behavior: append if textarea has text (with space separator), replace if empty
6. Permission denied tooltip: `data-test="mic-permission-tooltip"`, explains how to enable in Settings
7. Haptic feedback: delegated to VoiceInputService (start/stop)

## 6. Feature Gate (Pro)

- `voiceProLocked` signal: `true` for free users
- Mic button shows grayed out with "Pro" badge via `locked` input
- Tapping locked button emits `lockedTap` -> shows upgrade toast (existing `showUpgradeToast()`)
- Gate source: hardcoded `signal(false)` for now (Pro = unlocked during dev), with TODO comment for Stripe integration

## 7. Styles

In `mic-button.component.scss`:
- `.mic-btn`: 40x40 circle, transparent bg, icon color `var(--text-secondary)`
- `.mic-btn--listening`: accent border, pulse ring animation (`@keyframes pulse-ring`)
- `.mic-waveform`: 5 bars, `@keyframes waveform-bar` with staggered delays
- `.mic-btn--locked`: opacity 0.45, cursor not-allowed
- `.pro-badge`: same style as typewriter-keys Pro badge
- `@media (prefers-reduced-motion: reduce)`: no animation, static visual indicator

In `text.page.scss`:
- `.textarea-wrap`: relative container for textarea + mic button positioning
- Mic button positioned bottom-right of textarea area

## 8. ACL Compliance

- `@capacitor-community/speech-recognition` added to BANNED list in `architecture-acl-check.mjs`
- VoiceInputService lives in `src/app/services/` (not under pages), so ACL passes
- Haptics calls happen inside VoiceInputService, not in the page (ACL compliant)

## 9. Commit Plan

| # | Commit message | Files |
|---|----------------|-------|
| 1 | `feat(voice): add @capacitor-community/speech-recognition dependency` | `package.json` |
| 2 | `feat(voice): add VoiceInputService adapter with mock mode` | `voice-input.service.ts`, `voice-input.service.spec.ts` |
| 3 | `feat(voice): add MicButtonComponent with pulse + waveform` | `mic-button.component.ts`, `.scss`, `.spec.ts` |
| 4 | `feat(voice): wire mic button into Text page` | `text.page.ts`, `text.page.scss`, `text.page.spec.ts` |
| 5 | `feat(voice): add speech-recognition to ACL banned list` | `architecture-acl-check.mjs` |

## 10. Test Inventory (target: 12+ tests)

### VoiceInputService (4 tests)
1. `webPlatform_startListening_returnsMockTranscription`
2. `webPlatform_isListeningSignal_togglesDuringMockRecording`
3. `requestPermission_returnsGranted_onWebPlatform`
4. `stopListening_after30sTimeout_autoStops`

### MicButtonComponent (4 tests)
5. `idle_rendersMicButton_withStartLabel`
6. `listening_showsPulseAndWaveform`
7. `locked_showsProBadge_andEmitsLockedTap`
8. `reducedMotion_noPulseAnimation`

### TextPage voice integration (4+ tests)
9. `tapMic_permissionGranted_recordingState_stop_textareaFilled`
10. `permissionDenied_tooltipShown`
11. `freeUser_micLocked_proBadgeShown`
12. `existingText_transcriptionAppends`

## Actual Results

### Commits (5)

| # | SHA | Message |
|---|-----|---------|
| 1 | `ec75c00` | `feat(voice): add @capacitor-community/speech-recognition dependency` |
| 2 | `a71dcd0` | `feat(voice): add VoiceInputService adapter with mock mode` |
| 3 | `585cd11` | `feat(voice): add MicButtonComponent with pulse + waveform` |
| 4 | `27142fd` | `feat(voice): wire mic button into Text page` |
| 5 | `ee974b4` | `feat(voice): add speech-recognition to ACL banned list` |

### Files Changed (10)

| File | Action |
|------|--------|
| `package.json` | MODIFIED (added dependency) |
| `src/app/services/voice-input.service.ts` | CREATED |
| `src/app/services/voice-input.service.spec.ts` | CREATED |
| `src/app/pages/text/components/mic-button.component.ts` | CREATED |
| `src/app/pages/text/components/mic-button.component.scss` | CREATED |
| `src/app/pages/text/components/mic-button.component.spec.ts` | CREATED |
| `src/app/pages/text/text.page.ts` | MODIFIED |
| `src/app/pages/text/text.page.scss` | MODIFIED |
| `src/app/pages/text/text.page.spec.ts` | MODIFIED |
| `scripts/architecture-acl-check.mjs` | MODIFIED |

### Test Count: 24 new tests

- VoiceInputService: 9 tests
- MicButtonComponent: 8 tests
- TextPage voice integration: 7 tests

### Deviations (1)

1. **Append/replace toggle omitted.** The spec called for a configurable toggle for append vs. replace behavior. Implemented a simpler default: append when textarea has text, replace when empty. A toggle can be added as a follow-up if user testing shows demand. Logged in commit 4 body.
