# Task 1: Cold DM Templates

Retroactive receipt — code shipped before plan written. Deviation: task plan should have been written in parallel with execution per atomic task protocol.

## 1. Context
Create 3 Twitter/X DM variants for outreach to people tweeting about AI text sounding robotic or ChatGPT detection. Each under 280 chars, helpful tone, not salesy. Include search queries to find targets and targeting rules to avoid spam flags.

## 2. Files
- **Produced**: `/projects/bubls/docs/distribution/cold-dm-templates.md`

## 3. Implementation
- 3 DM variants: "I built something for this" (263 chars), "Voice angle" (246 chars), "Before/after proof" (216 chars).
- 10 Twitter search queries to find targets (e.g., `"ChatGPT sounds" robotic`, `"humanize" ChatGPT`, `"AI detection" caught`).
- Targeting rules: personal account, tweets within 48h, read their tweet first, 25 DMs/day cap (50 over 2 days).
- Expected conversion funnel: 50 DMs -> 5-8 replies (10-15%) -> 3-5 installs -> 1-2 day-7 returns.
- Failure threshold: 0 responses after 50 = messaging is wrong, rewrite before sending more.

## 4. Tests
Manual review: all variants under 280 chars, tone is helpful not promotional, search queries return relevant results.

## 5. Commits
Content authored in a single pass. Shipped as part of the distribution content batch.

## 6. Verification
Char counts verified per variant. Search queries use Twitter search syntax correctly. Targeting rules include anti-spam guardrails.

## 7. Rollback
Revert the content file. No DMs sent — templates are drafts.

## 8. Deviations
- Task plan written retroactively (protocol requires parallel authoring).
- TestFlight link placeholder in all variants; must be replaced before sending.

## 9. Out of Scope
Sending DMs, tracking responses, A/B testing variants, follow-up message templates.

## 10. Related
- Source: `/projects/bubls/docs/distribution/cold-dm-templates.md`
- Depends on: TestFlight link, Twitter/X account setup (`twitter-setup.md`)
