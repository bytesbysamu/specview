# Task 1: Voice Demo Script

Retroactive receipt — code shipped before plan written. Deviation: task plan should have been written in parallel with execution per atomic task protocol.

## 1. Context
Write a 30-second screen recording script for Bubls iOS app. No voiceover, no cuts — the screen speaks for itself. Demonstrates two flows: paste AI text and humanize it, then voice input with formalize. Includes setup checklist, timing breakdown, and post caption with CTA.

## 2. Files
- **Produced**: `/projects/bubls/docs/distribution/voice-demo-script.md`

## 3. Implementation
- 5 beats timed to 30 seconds: paste AI text (8s), tap Humanize (6s), voice input (8s), tap Formalize (6s), hold on result (2s).
- Beat 1 uses unmistakable ChatGPT paragraph ("rapidly evolving digital landscape") as the hook.
- Beat 3 uses natural spoken sentence ("pushing the deadline back two weeks because the vendor ghosted us").
- Beat 4 uses Formalize instead of Humanize — spoken input is already human, needs professional polish.
- Setup: DND on, default font, empty textarea, screen recording via Control Center.
- Recording checklist: 7 items (empty textarea, clipboard ready, mic permissions, DND, recording started, rehearse spoken line, trim Control Center swipe).
- Post caption template with CTA and TestFlight link placeholder.

## 4. Tests
Manual review: timing adds to 30s, beats flow logically, no CTA on screen (CTA in post caption only).

## 5. Commits
Content authored in a single pass. Shipped as part of the distribution content batch.

## 6. Verification
Timing table sums to 30s. AI text paragraph is recognizably ChatGPT. Spoken sentence is natural and relatable. Beat sequence demonstrates both paste and voice workflows.

## 7. Rollback
Revert the content file. No recording made — script is a draft.

## 8. Deviations
- Task plan written retroactively (protocol requires parallel authoring).

## 9. Out of Scope
Recording the video, editing/trimming, uploading to platforms, creating text overlays or thumbnails.

## 10. Related
- Source: `/projects/bubls/docs/distribution/voice-demo-script.md`
- Used by: Reddit post, Twitter thread (post caption accompanies the video)
