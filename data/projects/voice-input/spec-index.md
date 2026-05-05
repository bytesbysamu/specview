---
sidebar_position: 0
---

# 📋 Voice Input

> Speak into your phone, get polished text — on-device transcription feeding directly into the rewrite pipeline.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [🎯 Epic](./epic.md) | Scope, tasks, success criteria |
| [🏗️ Architecture](./architecture.md) | Technical design |
| [📅 Timeline](./timeline.md) | Status tracking |

## Overview

Voice Input adds a microphone button to the Text page textarea in Bubls. The user taps to record, speaks naturally, taps again to stop, and the transcribed text appears in the textarea — ready for any rewrite mode (Humanize, Formal, Casual, etc.). The entire transcription happens on-device via `@capacitor-community/speech-recognition`, meaning zero API cost, offline capability, and near-instant results.

This capability is the positioning wedge that separates Bubls from every other AI text rewriter on iOS. No competitor offers voice-to-rewrite as a single flow. Grammarly requires you to type first. Apple Intelligence rewrites but doesn't accept voice. The pitch becomes "talk to your phone, get a polished email" — a new behavior category, not an incremental feature. This is the headline for the Reddit launch post and the App Store screenshots.

Voice Input is gated as a Pro feature, adding tangible value to the paid tier beyond higher usage limits. The implementation follows the established Adapter pattern with `VoiceInputService` wrapping the Capacitor plugin behind a provider-agnostic interface, including mock mode for web development and testing.

## Related Documents

- [Analysis](./analysis.md)

