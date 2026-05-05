# Task 2: Flip forceMock off for voice

## Goal

Enable native speech recognition on real devices now that CocoaPods wires the `@capacitor-community/speech-recognition` plugin.

## Current State

- `src/app/services/voice-input.service.ts` has `forceMock = true` on line 25.
- The plugin was installed via npm but never wired into SPM (no Package.swift in the community plugin). CocoaPods from Task 1 fixes this.

## Changes

1. In `src/app/services/voice-input.service.ts`, change `private forceMock = true` to `private forceMock = false`.
2. The `available()` method already has fallback logic: if the native plugin reports unavailable (simulator), it sets `forceMock = true` at runtime. So web/simulator continue to use mock mode automatically.

## Verification

- `npx ng build --configuration=production` passes.
- On device after pod install: `SpeechRecognition.available()` returns true, native mic works.
- On web/simulator: `useMock` getter still returns true (not native platform), mock flow unchanged.

## Commit

```
feat(voice): enable native speech recognition (CocoaPods unblocks plugin)
```
