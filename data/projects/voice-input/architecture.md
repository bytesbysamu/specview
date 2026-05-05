---
sidebar_position: 3
---

# 🏗️ Voice Input – Solution Architecture

**Purpose**: Technical design for on-device voice input on the Bubls Text page.

**Epic Reference**: See [Epic](./epic.md) for scope and business context.

---

## Architecture Overview

Voice Input introduces a single new feature module (`voice-input`) containing an adapter service, a mic button component, and supporting types. The adapter wraps `@capacitor-community/speech-recognition` behind a provider-agnostic interface, following the established ACL pattern. The Text page consumes the mic button component and receives transcription results via an output event — no cross-feature imports, no shared state. Recording state is managed entirely within the voice-input feature via Angular signals.

The Capacitor plugin delegates to iOS's native `SFSpeechRecognizer`, which runs on-device for supported languages (English, Spanish, French, German, and others on iOS 17+). No network call is made for transcription. The plugin handles microphone access, audio session management, and speech recognition lifecycle. The adapter normalizes the plugin's callback-based API into a signal-driven interface that fits Angular's reactive patterns.

Platform detection gates the feature to native iOS builds only. Web builds hide the mic button entirely. Mock mode (env-flag gated) simulates transcription for development and testing on web, returning canned responses after a configurable delay.

---

## Design Principles

| Principle | Application |
|-----------|-------------|
| Adapter (ACL) | `VoiceInputService` wraps `@capacitor-community/speech-recognition`; feature code never imports the plugin directly. Mock mode via `VOICE_INPUT_PROVIDER=mock` env flag |
| Feature = Bounded Context | `features/voice-input/` owns its service, component, model, mock, and tests. Text page imports only the component, receives data via `@Output()` |
| Standalone + OnPush | `VoiceMicButtonComponent` is standalone with OnPush change detection. Internal state via signals |
| Feature Guard with Null Object | Free users see the mic button but hit an upgrade prompt on tap. Button is never hidden for free users — it's a discovery/conversion surface |
| No infrastructure before features | No voice command parsing, no transcription history, no language router. Ship the mic button, validate with users |

---

## Component Design

### Task 1: VoiceInputService Adapter

**Purpose**: Provider-agnostic interface for speech recognition with mock mode for web development.

**Components**:
- `features/voice-input/voice-input.service.ts` — Adapter service with `startListening()`, `stopListening()`, `requestPermission()`, signals for `isListening` and `partialResult`
- `features/voice-input/voice-input.model.ts` — Types: `VoiceInputOptions` (maxDuration, language), `VoiceInputResult` (text, isFinal, confidence), `VoiceInputError` (permissionDenied, recognitionFailed, timeout)
- `features/voice-input/voice-input.mock.ts` — Mock data: canned transcriptions, simulated delays, error scenarios
- `features/voice-input/voice-input.service.spec.ts` — Tests with mock provider

**Patterns**: Adapter (wraps Capacitor plugin), Strategy (mock vs real provider via env flag)

**Interface**:
```typescript
// voice-input.service.ts
export class VoiceInputService {
  private speechRecognition = inject(SpeechRecognition); // or mock
  
  readonly isListening = signal(false);
  readonly partialResult = signal('');
  readonly error = signal<VoiceInputError | null>(null);

  requestPermission(): Promise<PermissionStatus> { ... }
  startListening(options?: VoiceInputOptions): void { ... }
  stopListening(): Promise<VoiceInputResult> { ... }
}
```

### Task 2: iOS Permission Setup

**Purpose**: Configure Capacitor plugin and iOS permissions for speech recognition and microphone access.

**Components**:
- `package.json` — Add `@capacitor-community/speech-recognition` dependency
- `capacitor.config.ts` — Plugin registration (if required by plugin version)
- `ios/App/App/Info.plist` — `NSSpeechRecognitionUsageDescription` and `NSMicrophoneUsageDescription` entries

**Patterns**: Standard Capacitor plugin integration. No custom native code.

### Task 3: VoiceMicButtonComponent

**Purpose**: Self-contained mic button with recording state visualization.

**Components**:
- `features/voice-input/components/voice-mic-button/voice-mic-button.component.ts` — Standalone component: mic icon, pulsing ring, state management
- `features/voice-input/components/voice-mic-button/voice-mic-button.component.scss` — Pulsing animation keyframes, reduced-motion media query, amplitude ring styles

**Patterns**: Standalone + OnPush. Signals for internal state. `@Output()` for transcription result. `data-test` selectors on all interactive elements.

**State machine**:
```
idle ──[tap]──→ requesting_permission ──[granted]──→ recording ──[tap/timeout]──→ processing ──[result]──→ idle
                                       ──[denied]──→ error ──[dismiss]──→ idle
recording ──[error]──→ error ──[dismiss]──→ idle
```

**Recording indicator CSS**:
```scss
.voice-ring {
  animation: pulse 1.5s ease-in-out infinite;
  
  @media (prefers-reduced-motion: reduce) {
    animation: none;
    opacity: 0.8; // static visible ring instead
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.3); opacity: 0.2; }
}
```

### Task 4: Text Page Integration

**Purpose**: Wire mic button into existing Text page without cross-feature coupling.

**Components**:
- Text page template — Add `<app-voice-mic-button>` inside textarea container
- Text page component — Handle `(transcriptionComplete)` event, update textarea signal/form control

**Patterns**: Observer pattern via Angular `@Output()`. No shared state. Text page doesn't know about speech recognition — it receives a string and puts it in the textarea.

**Textarea injection logic**:
```typescript
onTranscriptionComplete(text: string): void {
  const current = this.textareaContent();
  if (current.trim() === '') {
    this.textareaContent.set(text);
  } else {
    this.textareaContent.set(current + ' ' + text);
  }
}
```

### Task 5: Pro Feature Gate

**Purpose**: Gate voice input behind Pro subscription with upgrade prompt as conversion surface.

**Components**:
- `VoiceMicButtonComponent` — Check `enabled_features` before starting recording
- Upgrade prompt — Ionic `AlertController` or modal with feature description and upgrade CTA

**Patterns**: Registry (feature flags). Null Object (button visible but gated). Never 404, always upgrade path.

### Task 6: Haptics + Accessibility + Platform

**Purpose**: Polish layer — tactile feedback, accessibility compliance, platform-appropriate rendering.

**Components**:
- `VoiceInputService` or `VoiceMicButtonComponent` — Haptic calls via `@capacitor/haptics`
- `VoiceMicButtonComponent` — `prefers-reduced-motion` check, `Capacitor.isNativePlatform()` check

**Patterns**: Progressive enhancement. Feature exists on native, absent on web. Graceful degradation for accessibility preferences.

---

## Execution Flow

```
[Phase 1 — Foundation]     (parallelizable)
   Task 1 (Adapter) ─────┐
   Task 2 (iOS setup) ────┤
                           │
[Phase 2 — UI]             ▼
   Task 3 (Mic button) ──→ Task 4 (Integration)
                                │
[Phase 3 — Polish]              ▼  (parallelizable)
   Task 5 (Feature gate) ──┐
   Task 6 (Haptics/a11y) ──┤
                            │
[Phase 4 — Validation]     ▼
   Task 7 (Device testing)
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Transcription engine | `@capacitor-community/speech-recognition` (iOS `SFSpeechRecognizer`) | On-device, zero API cost, offline capable. Plugin is maintained, 400+ GitHub stars, Capacitor 6+ compatible. No Whisper API — that's a per-request cost we don't need |
| Recording timeout | 60 seconds hardcoded | 30s too short for email dictation. Configurable adds UI complexity for no validated need. Hardcoded constant is trivial to change later |
| Textarea behavior | Replace if empty, append if text exists | Most intuitive default. No toggle UI for v1 — toggle is scope creep for an unvalidated edge case |
| Recording indicator | Pulsing mic icon with amplitude ring | Full waveform is overengineered for v1. Static icon is too subtle — users need clear "I'm listening" feedback. Pulsing ring with CSS-only animation is the sweet spot |
| Web behavior | Hide mic button entirely | Web Speech API has inconsistent browser support, different privacy model, and would require a second adapter branch. Not worth the complexity. Mock mode serves dev needs |
| Feature gate UX | Button visible, gate on tap | Invisible features can't convert. Showing the button to free users creates discovery moments. Gate fires on interaction, not render — user sees what they're missing |
| State management | Signals within feature | No global state. `isListening`, `partialResult`, `error` are signals on `VoiceInputService`. Text page reads the transcription result via `@Output()` event, doesn't subscribe to voice state |
| Provider switching | Env flag `VOICE_INPUT_PROVIDER` | Consistent with existing adapter pattern across the codebase. `mock` for web dev/tests, default (real) for native builds |

---

## Related Documents

- [Epic](./epic.md)
- [Analysis](./analysis.md)

