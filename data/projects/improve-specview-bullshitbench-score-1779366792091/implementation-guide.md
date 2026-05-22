# Implementation Guide: Improve Specview BullshitBench Score

## Overview
This epic recovers 8–10 points on BullshitBench v2 (from 74.2% toward 82–85%) through prompt engineering changes to the anonymous analysis pipeline. Work sequences in five tasks: first, a holdout evaluation split and regression suite setup; then a manual failure-case review produces prompt guidance; then the system prompt gets a calibrated skepticism posture; next the analysis template's section instructions are updated to channel unverified claims into Open Questions; finally the holdout set and regression suite validate that improvements hold without degrading real-world output. All changes flow through the existing single-pass adapter.rewrite() call — no new AI calls, no infrastructure, no model changes.

**Eval model:** Opus 4.6 throughout. Production anonymous analysis uses Haiku 4.5 — this eval measures the pipeline's structural impact on a capable model. Prompt improvements validated on Opus may not transfer 1:1 to Haiku, but the structural fixes (claim channeling, section instructions) are model-agnostic.

## Shared Pre-flight
- Confirm the BullshitBench v2 fixture exists at `evals/bullshit_bench/fixtures/questions.v2.json` and contains 100 questions with technique and domain metadata fields.
- Run the existing eval suite via `evals/bullshit_bench/runner.py` to establish a fresh baseline and verify the runner produces results in `evals/bullshit_bench/results/`.
- Read the current system prompt `_ANALYSIS_SYSTEM` and template `_ANALYSIS_USER` in `modules/ai/services/public_analyze.py` to internalize the existing wording before making changes.
- Confirm that `evals/bullshit_bench/runner.py` duplicates the same system prompt and template as `public_analyze.py` — Task 1 will eliminate this duplication by importing directly.
- Review the scoring rubric in `evals/bullshit_bench/judge.py` to understand how 0/1/2 scores map to full-acceptance, partial-pushback, and full-pushback.
- Verify the adapter call signature in `modules/runtime/chain/adapter.py` at the `rewrite()` function — no changes to this file are planned, but understanding the interface prevents surprises.
- Ensure the generate-spec workflow's template in `modules/ai/workflows/` is noted as a separate code path — changes in this epic target only the anonymous pipeline, not the authenticated workflow.

---

## Task 1: Create Holdout Split, DRY Prompts, and Regression Suite  [Effort: 0.5 days]

### What
Partition the 100-question corpus into a 60-question tuning set and a 40-question holdout set (stratified by technique and domain), eliminate the prompt duplication between runner.py and public_analyze.py, and assemble a regression suite from real Specview braindumps. This prevents overfitting, removes a sync hazard, and gives a clean final-validation boundary.

### Files
- **Create**: `evals/bullshit_bench/fixtures/splits.json` — mapping of `question_id -> "tuning"|"holdout"`, produced by split.py. The vendored `questions.v2.json` stays unmodified.
- **Create**: `evals/bullshit_bench/fixtures/legitimate_braindumps/` — directory containing 10–15 markdown files copied from real projects in `data/projects/*/braindump.md`, covering technical architecture, product features, vague early-stage ideas, real metrics, and niche-but-real frameworks.
- **Create**: `evals/bullshit_bench/split.py` — script that reads `questions.v2.json`, performs stratified partitioning by technique and domain with a fixed random seed, writes `splits.json`, and prints distribution stats.
- **Modify**: `evals/bullshit_bench/runner.py` — (a) accept an optional `--split` flag (tuning, holdout, or all) to run only the selected subset, defaulting to all; (b) remove the duplicated `_ANALYSIS_SYSTEM` and `_ANALYSIS_USER` constants and import them from `modules.ai.services.public_analyze` instead; (c) load `splits.json` in `_load_questions()` and attach the split label to each question dict.
- **Modify**: `evals/bullshit_bench/models.py` — add a `split` field to `QuestionResult` so results can be filtered by split after the fact.

### Steps
1. Write `split.py` to load `questions.v2.json`, flatten techniques, group questions by their `(technique, domain_group)` pair, and assign 60% of each group to tuning and 40% to holdout using `random.seed(42)` for reproducibility. For groups with fewer than 3 questions, ensure at least one in each set. Write the result as `splits.json` — a JSON object mapping question_id to split label.
2. Run `split.py` and verify the printed distribution table shows every technique represented in both sets, with `specificity_trap` splitting 5/3 and `plausible_nonexistent_framework` splitting ~10/6.
3. Create the `legitimate_braindumps/` directory. Browse `data/projects/` and copy 10–15 real `braindump.md` files that represent diverse Specview usage: at least two with genuine metrics/numbers, two vague/early-stage, two referencing real-but-niche frameworks (CQRS, event sourcing, Raft, etc.), and two with finance or legal domain jargon. Rename each to a descriptive filename (e.g., `redis-cache-architecture.md`, `saas-billing-migration.md`).
4. In `runner.py`, remove the `_ANALYSIS_SYSTEM` and `_ANALYSIS_USER` constants entirely. Add `from modules.ai.services.public_analyze import _ANALYSIS_SYSTEM, _ANALYSIS_USER` (these are module-level constants, safe to import). Update `_build_prompt()` and the `run()` function to use the imported versions. This ensures the eval always tests the exact production prompt — no sync risk.
5. Update `_load_questions()` in `runner.py` to load `splits.json` as a sidecar, attach the split label to each question dict, and filter by `--split` flag when provided. Add the `--split` argument to argparse (choices: `tuning`, `holdout`, `all`; default `all`).
6. Add a `split: Optional[str] = None` field to `QuestionResult` in `models.py`, populated from the question's split label during the run loop.
7. Run the updated runner with `--split tuning` and `--split holdout` separately to confirm both subsets execute and produce result files with the expected question counts (60 and 40).

### Verify
- `splits.json` exists and contains exactly 100 entries, each mapping a question_id to either "tuning" or "holdout".
- Every technique appears in both sets (no technique has zero questions in either set).
- Runner with `--split tuning` produces exactly 60 result entries; `--split holdout` produces exactly 40.
- `runner.py` no longer contains `_ANALYSIS_SYSTEM` or `_ANALYSIS_USER` as local constants — grep confirms they are imported from `public_analyze`.
- `legitimate_braindumps/` contains at least 10 markdown files with substantive real braindump content (not stubs or AI-generated filler).

---

## Task 2: Manual Failure-Case Review  [Effort: 0.5 days]

### What
This is a **manual review step**, not an agent task. Examine the 9 partial-pushback responses (score 1) and 21 full-acceptance responses (score 0) from the baseline run to understand exactly how the pipeline fails. The output is two findings documents and a short prompt-guidance note that feeds directly into Tasks 3 and 4.

### Files
- **Modify**: `evals/bullshit_bench/reporter.py` — add a `filter_cases()` function that extracts results by score and technique for easy review.
- **Create**: `evals/bullshit_bench/findings/technique_analysis.md` — structured write-up of failure patterns grouped by technique, with specific phrasing examples from the 30 failing cases.
- **Create**: `evals/bullshit_bench/findings/prompt_guidance.md` — short directive (10–20 lines) summarizing what the system prompt and template changes should say, written by the user after reading the failures.

### Steps
1. Add a `filter_cases()` function to `reporter.py` that accepts a results JSONL path and optional filters for score range and technique name, then prints each matching case with the question text, nonsensical element, full pipeline response, judge score, and judge reasoning — formatted for easy reading.
2. Run `filter_cases()` against the baseline results to extract all 21 score-0 cases. **Read each one.** For each, note: (a) what the fabricated element was (number, framework name, jargon), (b) which output section absorbed it (Hard Constraints, Dependencies, or elsewhere), (c) whether any hint of awareness appeared.
3. Extract the 9 score-1 cases. For each, identify where the partial pushback landed (usually Open Questions) and what phrasing the model used. Note what distinguishes these from the score-0 cases — what made the model hesitate?
4. Write `technique_analysis.md` summarizing findings per technique with quoted examples from actual responses. Focus on `specificity_trap` and `plausible_nonexistent_framework` — what makes each technique succeed against the pipeline.
5. Write `prompt_guidance.md` — a short directive (not a draft prompt, but guidance for the agent in Tasks 3-4) specifying: (a) what the system prompt skepticism posture should address, (b) what the template section instructions should change, (c) what to explicitly NOT flag (user's own measurements, real frameworks). This is the user's judgment call based on reading the actual failures.

### Verify
- `technique_analysis.md` contains at least one concrete quoted example per failing technique.
- `prompt_guidance.md` exists and provides specific direction for Tasks 3 and 4.
- `filter_cases()` correctly returns 21 entries for score 0 and 9 for score 1.

---

## Task 3: Revise System Prompt with Calibrated Skepticism  [Effort: 1 day]

### What
Add a skepticism posture to the system prompt that restores the model's natural pushback on unsourced metrics and unfamiliar named methodologies, without triggering false positives on legitimate braindump content. This directly addresses the detection gap — the model currently suppresses its skepticism because the "helpful analyst" identity doesn't include a questioning mandate.

### Files
- **Modify**: `modules/ai/services/public_analyze.py` — revise `_ANALYSIS_SYSTEM` to append a calibrated skepticism posture after the existing identity statement.
- No changes to `runner.py` needed — it now imports from `public_analyze` (Task 1).

### Steps
1. Read `evals/bullshit_bench/findings/prompt_guidance.md` to understand the user's specific direction for the skepticism posture.
2. Draft the skepticism posture as a short paragraph (3–5 sentences) to append after "You are a markdown spec writer." The posture should instruct the model to distinguish between claims the user presents as their own data or choices (legitimate, analyze them) and claims presented as universal domain facts without attribution (flag them as unverified). Use the guidance from `prompt_guidance.md`.
3. Include two targeted sub-instructions: one for unsourced specifics (precise numbers, percentages, thresholds stated as domain facts rather than user measurements) and one for unfamiliar named methodologies (proper-noun frameworks or protocols the model does not recognize). These map to `specificity_trap` and `plausible_nonexistent_framework`.
4. Add a calibration guardrail sentence that explicitly tells the model not to challenge claims the user attributes to their own experience, measurements, or tool choices.
5. Run the eval runner with `--split tuning` to score the revised system prompt against the 60-question tuning set. Compare overall score and per-technique means against baseline, focusing on `specificity_trap` and `plausible_nonexistent_framework`.
6. Run the pipeline manually against 3–4 braindumps from `legitimate_braindumps/` and confirm no false-positive skepticism appears.
7. If the tuning-set score does not improve by at least 3 points or if false positives appear, revise the posture wording and repeat steps 5–6. Expect 2–3 iterations.

### Verify
- `_ANALYSIS_SYSTEM` in `public_analyze.py` contains the new skepticism posture.
- Run eval with `--split tuning` and confirm overall tuning-set score is at least 3 points above 74.2% baseline.
- Run pipeline against a legitimate braindump with real metrics and confirm the output contains no skepticism flags — analysis is purely constructive.
- System prompt addition is under 150 words.

---

## Task 4: Update Analysis Template Claim Channeling  [Effort: 1 day]

### What
Modify the analysis template's section instructions so that unverifiable claims are routed into Open Questions rather than absorbed into Hard Constraints or Dependencies. This gives the model a structural mechanism to express the skepticism that the revised system prompt now triggers.

### Files
- **Modify**: `modules/ai/services/public_analyze.py` — revise `_ANALYSIS_USER` template to narrow Hard Constraints admission criteria and expand Open Questions scope to include unverified claims.
- No changes to `runner.py` needed — it imports from `public_analyze`.

### Steps
1. Read `evals/bullshit_bench/findings/prompt_guidance.md` and `findings/technique_analysis.md` to understand which claims were misrouted and where.
2. In `_ANALYSIS_USER`, revise the Hard Constraints section instruction to specify that this section accepts only requirements the user explicitly states as their own constraints or measurements — not domain assertions, benchmark numbers, or industry thresholds presented without attribution.
3. Revise the Open Questions section instruction to explicitly include two new item types: unsourced specifics that need validation and unfamiliar named frameworks or methodologies. Add a brief directive that these items should be phrased as questions or flagged as unverified.
4. Review the Dependencies section instruction and add a similar narrowing: dependencies should reference concrete systems, teams, or deliverables the user named, not frameworks or standards inferred from the braindump.
5. Run the eval runner with `--split tuning` to score the combined system prompt plus template changes. Target: overall tuning-set score >= 78%, `specificity_trap` mean >= 0.75, `plausible_nonexistent_framework` mean >= 1.3.
6. Run the pipeline against the full `legitimate_braindumps/` regression suite (all 10–15 files). Confirm legitimate user metrics remain in Hard Constraints and real frameworks are not flagged in Open Questions.
7. If misrouting persists, adjust the section instruction wording and re-run. Expect 1–2 iterations.

### Verify
- `_ANALYSIS_USER` in `public_analyze.py` contains the revised section instructions.
- Eval with `--split tuning`: `specificity_trap` mean >= 0.75 (up from 0.25).
- Eval with `--split tuning`: `plausible_nonexistent_framework` mean >= 1.3 (up from 1.06).
- Legitimate braindump with real metrics: metrics appear in Hard Constraints, not Open Questions.

---

## Task 5: Validate Against Holdout Set and Regression Suite  [Effort: 0.5 days]

### What
Run the finalized pipeline against the 40-question holdout set (never used during tuning) and the full legitimate-braindump regression suite. This is the single-shot validation that confirms improvements generalize and real-world output quality is preserved.

### Files
- **Modify**: `evals/bullshit_bench/reporter.py` — add a `compare_runs()` function that takes two results files (baseline and current) and prints a side-by-side table of overall score, per-technique means, and acceptance rate.
- **Create**: `evals/bullshit_bench/results/holdout_validation.md` — final validation report with holdout scores, regression suite results, and pass/fail on each success criterion.

### Steps
1. Run the eval runner with `--split holdout` against the finalized pipeline. This is the first and only time the holdout set is used — no further tuning permitted regardless of result.
2. Run the eval runner with `--split all` to generate a full 100-question score for the headline number.
3. Use `compare_runs()` to generate a side-by-side table comparing baseline vs. holdout validation, broken down by overall score, per-technique means (especially `specificity_trap` and `plausible_nonexistent_framework`), per-domain means (especially finance and legal), and acceptance rate.
4. Run the pipeline against every file in `legitimate_braindumps/`. Read each output and confirm no legitimate braindump triggers false-positive skepticism.
5. Evaluate against success criteria: holdout score >= 82%, `specificity_trap` mean >= 1.0, `plausible_nonexistent_framework` mean >= 1.5, acceptance rate (score 0) below 12%, zero false positives on legitimate braindumps.
6. Write `holdout_validation.md` documenting scores, regression suite outcomes, and pass/fail for each criterion.

### Verify
- Holdout-set overall score >= 82%.
- Acceptance rate (score 0) on holdout set < 12%.
- Every legitimate braindump produces output with zero false-positive skepticism flags.
- `holdout_validation.md` exists with explicit pass/fail for all five success criteria.