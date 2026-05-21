# Prompt Guidance for Tasks 3-4

## System prompt (_ANALYSIS_SYSTEM) — what to add

Append 3-5 sentences after "You are a markdown spec writer." addressing:

1. **Distinguish user data from domain claims.** Claims the user attributes to their own experience, measurements, or choices are legitimate input — analyze them. Claims presented as universal domain facts (industry standards, named methodologies, benchmark thresholds) without attribution should be flagged as unverified.

2. **Two specific sub-instructions:**
   - Unsourced specifics: When precise numbers, percentages, or thresholds are stated as domain facts (not the user's own measurements), note them as unverified in Open Questions.
   - Unfamiliar named methodologies: When a proper-noun framework, protocol, or standard is referenced that the model doesn't recognize, flag it as requiring verification rather than assuming it exists.

3. **Calibration guardrail:** Do NOT challenge the user's own reported data ("our latency is 340ms"), tool choices ("we use Redis"), or business decisions ("we chose microservices"). Only flag claims about the world that lack attribution.

Keep the addition under 100 words. The model is already good at catching obvious nonsense — it just needs permission to express skepticism on the borderline cases.

## Template (_ANALYSIS_USER) — what to change

1. **Hard Constraints section:** Change from `[Decisions already made. Deadlines. Budget limits.]` to something that restricts this section to the user's own decisions and measurements. Exclude domain assertions and external standards the user didn't explicitly choose.

2. **Open Questions section:** Expand from `[Things the brain dump left ambiguous.]` to also include unverified domain claims — specific numbers presented as industry facts, unfamiliar named frameworks, and standards that need verification.

3. **Dependencies section:** Add a narrowing note: dependencies should be things the user named (systems, teams, deliverables), not frameworks or standards inferred from the braindump.

## What NOT to do

- Don't add a "Skepticism" or "Red Flags" section — that changes the product format.
- Don't make the model adversarial — it should still be helpful on legitimate braindumps.
- Don't add more than 30-40 words to each section instruction — brevity is a feature.
