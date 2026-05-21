# Implementation Guide: BullshitBench Eval

## Overview
This epic delivers a reproducible eval harness that feeds all 100 BullshitBench v2 questions through Specview's analysis pipeline using Claude Opus 4.6 for both analysis and judging, and produces aggregate metrics broken down by domain and nonsense technique comparable to the official BullshitBench leaderboard. Tasks are strictly sequential: vendor fixtures and confirm model routing first, then build the runner, then the judge, then reporting, and finally distill results for blog consumption. Each stage depends on validated output from the one before it.

## Shared Pre-flight
- Clone or pull the petergpt/bullshit-benchmark repository locally to access the v2 question set
- Confirm Docker container is running and the project volume is mounted at /home/appuser/projects
- Verify docker exec can reach the running specview container and execute Python inside it
- Confirm adapter.py is importable from within the container and that CHAIN_PROVIDER=cli is set in the environment
- Ensure CLI credentials are configured (CHAIN_PROVIDER=cli always — no SDK, no API key) so adapter.rewrite() can make live calls
- Read the BullshitBench v2 schema to understand the per-question fields: question text, known nonsensical element, domain, technique
- Create the eval package directory at api/evals/bullshit_bench/ with an __init__.py

---

## Task 1: Vendor fixtures & validate model routing  [Effort: 0.5 days]

### What
Vendor the BullshitBench v2 question set into the repository and confirm two critical assumptions before any eval runs: which model CHAIN_PROVIDER=cli actually invokes through adapter.rewrite(), and whether the anonymous analysis path injects builder context or principles. If either assumption is wrong, every subsequent task produces invalid data.

### Files
- **Create**: `api/evals/bullshit_bench/fixtures/questions.v2.json` — vendored copy of the 100-question BullshitBench v2 dataset with question text, known nonsensical element, domain, and technique fields
- **Create**: `api/evals/bullshit_bench/__init__.py` — empty package initializer for the eval module
- **Modify**: No production files modified; this task is read-only investigation plus fixture vendoring

### Steps
1. Download questions.v2.json from the petergpt/bullshit-benchmark repository and place it at api/evals/bullshit_bench/fixtures/questions.v2.json.
2. Validate the vendored file contains exactly 100 questions and that each record includes the four required fields: question text, known nonsensical element, domain classification (one of software, finance, legal, medical, physics), and nonsense technique metadata.
3. Trace the adapter.rewrite() call path when CHAIN_PROVIDER=cli is set, starting from adapter.py through to the CLI subprocess invocation, and confirm the model parameter is passed through correctly — the runner will use `--model` to select the model at call time (default: claude-opus-4-6).
4. Trace the anonymous analysis prompt construction end-to-end to confirm that no builder context, user profile, or engineering principles are injected when there is no authenticated builder — specifically check whether the "no speculative abstractions" principle observed in the manual test was an artifact of builder context leaking in.
5. Record findings about model identity and prompt composition in a short note at the top of the vendored fixture directory so they are available to anyone running the eval later.

### Verify
- api/evals/bullshit_bench/fixtures/questions.v2.json exists, is valid JSON, and contains exactly 100 question records
- Each record in the vendored file has non-empty values for question text, known nonsensical element, domain, and technique
- Running a single adapter.rewrite() call from within the Docker container via docker exec produces a response and the model identity is confirmed in logs or adapter output
- The anonymous analysis prompt path has been traced and the presence or absence of builder context is documented

---

## Task 2: Build eval runner  [Effort: 1.5 days]

### What
Build the CLI script that iterates BullshitBench questions through adapter.rewrite() on the anonymous analysis path, captures raw responses with metadata, and writes per-question results incrementally to a timestamped JSON file. This is the measurement instrument — it must not alter the pipeline in any way.

### Files
- **Create**: `api/evals/bullshit_bench/runner.py` — CLI entry point with argument parsing for --limit, --filter, --dry-run, and --skip-judge flags; orchestrates question iteration and delegates to adapter using Opus 4.6
- **Create**: `api/evals/bullshit_bench/models.py` — data structures for per-question result records (question metadata, raw response, latency, error state, empty score fields) and run header (model identity, provider, CLI flags, timestamp, git commit hash)
- **Create**: `api/evals/bullshit_bench/results/.gitkeep` — empty placeholder to ensure the results directory is tracked

### Steps
1. Define the per-question result record structure in models.py with fields for: original question metadata (text, known element, domain, technique), raw pipeline response text, wall-clock latency in seconds, error state if the call fails, and score fields initialized to null for later judge backfill.
2. Define the run header structure in models.py with fields for: confirmed model identity, provider name, CLI flags used, ISO timestamp, and the current git commit hash obtained at runtime.
3. Build the CLI entry point in runner.py using argparse with four flags: --limit N to cap question count, --filter to restrict to a single domain string, --dry-run to construct prompts and write them to result records without calling adapter.rewrite(), and --skip-judge to leave score fields empty. Model is hardcoded to claude-opus-4-6.
4. Implement the question loading function that reads the vendored questions.v2.json, applies --filter and --limit constraints, and returns the ordered list of questions to process.
5. Implement the main iteration loop that processes questions sequentially, calling adapter.rewrite() with model="claude-opus-4-6" for each question using the same prompt format as the anonymous analysis box, measuring wall-clock time per question, and catching errors without aborting the run.
6. Implement incremental result writing so that after each question completes, the full result record is appended to the run's JSON output file under api/evals/bullshit_bench/results/ with a timestamped filename — a crash at question 47 must preserve questions 1 through 46.
7. Add per-question latency logging to stdout so the actual time distribution is visible during the run, and log a running average to help estimate remaining time.
8. Wire up --dry-run mode so it constructs the full prompt that would be sent to adapter.rewrite(), writes that prompt text into the result record's response field with a dry-run flag, and skips the actual adapter call entirely.

### Verify
- Running the runner with --dry-run --limit 3 completes in under ten seconds, produces a timestamped JSON file in api/evals/bullshit_bench/results/, and each result record contains the constructed prompt text
- Running with --limit 1 makes a real adapter.rewrite() call inside the Docker container, produces a result file with a non-empty response and a recorded latency value
- Running with --filter software --limit 2 processes only questions from the software domain
- The result file includes a valid run header with model identity, timestamp, and git commit hash

---

## Task 3: Build judge harness  [Effort: 1 day]

### What
Build the Sonnet-based scoring module that takes each pipeline response, compares it against the known nonsensical element from the BullshitBench rubric, and assigns a 0/1/2 score. The judge must recognize that Specview expresses skepticism through spec-analysis language like "solution looking for a problem" rather than explicit statements like "this is fabricated."

### Files
- **Create**: `api/evals/bullshit_bench/judge.py` — judge module that constructs the scoring prompt, calls adapter with model="claude-opus-4-6", parses the 0/1/2 score from the response, and writes scores back into existing result records
- **Modify**: `api/evals/bullshit_bench/runner.py` — add a combined mode that runs the judge immediately after each pipeline response when --skip-judge is not set, and add a --rejudge flag that re-scores existing result files without re-running the pipeline

### Steps
1. Design the judge prompt that instructs Sonnet to score a pipeline response on the 0/1/2 rubric: 0 means the pipeline accepted the nonsense without challenge, 1 means partial pushback where something seemed off but the pipeline still engaged substantively, and 2 means clear identification and rejection of the nonsensical premise.
2. Anchor the judge prompt on the specific known nonsensical element for each question rather than general response quality — the judge must evaluate whether the pipeline challenged that particular piece of nonsense, not whether the analysis was generically good.
3. Include guidance in the judge prompt that spec-analysis language counts as valid pushback — phrases like "lacks supporting evidence," "consider a simpler solution," or "no established precedent" are how a structured analysis pipeline expresses skepticism, and should be scored as pushback when directed at the known nonsensical element.
4. Implement the scoring function in judge.py that takes a result record, constructs the judge prompt with the question text, known nonsensical element, and pipeline response, calls adapter.rewrite() with model="claude-opus-4-6", and parses the integer score from the response.
5. Implement the backfill capability that reads an existing result file produced with --skip-judge, scores each record that has a null score field, and writes the updated file back with scores populated — this allows judge prompt iteration without re-running the two-hour pipeline.
6. Add the --rejudge flag to runner.py that accepts a path to an existing result file and runs the judge against all records, overwriting previous scores, for use when the judge prompt has been revised.
7. Validate scoring consistency by running the judge twice on the same small set of responses and confirming scores match — target is identical results on repeated runs with the same judge prompt.

### Verify
- Running the judge against a result file produced with --skip-judge --limit 5 populates all five score fields with values of 0, 1, or 2
- Running the judge twice on the same result file produces identical scores for every question
- The judge correctly identifies pushback expressed in spec-analysis language — manually inspect at least two scored responses where the pipeline used indirect skepticism rather than explicit rejection
- The --rejudge flag successfully re-scores an existing result file and the output file contains updated scores

---

## Task 4: Aggregate reporting & full run  [Effort: 1 day]

### What
Build the reporter that computes aggregate metrics from scored results along domain and nonsense-technique dimensions, then execute the full 100-question eval run with judge scoring to produce the definitive dataset.

### Files
- **Create**: `api/evals/bullshit_bench/reporter.py` — reads completed result files and computes mean score, percentage scoring at least 1, and percentage scoring 2, broken down by domain and nonsense technique; identifies notable outliers; outputs a summary JSON file
- **Modify**: `api/evals/bullshit_bench/runner.py` — add a --report flag that triggers aggregation after a scored run completes, and wire reporter invocation into the CLI

### Steps
1. Implement the domain breakdown in reporter.py that groups scored results by the five domains (software, finance, legal, medical, physics) and computes three metrics per domain: mean score on the 0 to 2 scale, percentage of questions scoring at least 1, and percentage of questions scoring 2.
2. Implement the nonsense-technique breakdown that groups scored results by the 13 BullshitBench technique categories and computes the same three metrics per technique.
3. Compute the two headline numbers: the leaderboard-format score (mean score / 2 × 100, expressed as a percentage — this is how BullshitBench computes "91%" for Sonnet 4.6) as the primary metric for direct comparison against published model rankings, and the percentage-with-pushback framing (percentage of all questions scoring at least 2) as the secondary metric.
4. Implement outlier detection that identifies the three highest-scoring responses (best catches) and three lowest-scoring responses (worst misses), prioritizing responses that deviate most from their domain average — a zero in a domain averaging 1.8 is more notable than a zero in a domain averaging 0.3.
5. Write the reporter output as a summary JSON file alongside the result file, containing all aggregate metrics, both headline numbers, and the outlier records with their full question and response text.
6. Execute a smoke run with --limit 5 including judge scoring and reporting to validate the full pipeline end-to-end before committing to the full run.
7. Execute the full 100-question run with judge scoring enabled, monitor for errors or crashes, and confirm the run completes with all 100 questions scored.
8. Run the reporter against the full result file and validate that domain counts sum to 100, technique counts cover all 13 categories, and the headline metrics are computed correctly.

### Verify
- The summary JSON contains breakdowns for all 5 domains and all 13 nonsense techniques with three metrics each
- Both headline numbers are present: percentage-with-pushback and leaderboard-format score
- The full result file contains exactly 100 scored question records with no null score fields
- Running the reporter a second time against the same result file produces identical output

---

## Task 5: Document results for blog input  [Effort: 0.5 days]

### What
Distill the scored eval results into a structured findings document that the blog post can consume directly — headline metric, domain and technique analysis, and curated notable responses with commentary on what the pipeline caught and what it missed.

### Files
- **Create**: `api/evals/bullshit_bench/results/findings.md` — structured summary of eval results with headline metric, domain-by-domain analysis, technique-by-technique patterns, and annotated notable responses for blog consumption
- **Modify**: No code files modified; this task produces documentation from existing scored data

### Steps
1. State the headline metric prominently: the percentage of BullshitBench questions where Specview's anonymous analysis pushed back on the nonsensical premise, with the leaderboard-compatible score in parentheses for reference.
2. Write a domain-by-domain breakdown identifying the strongest domain (highest pushback rate) and weakest domain (lowest pushback rate) with one sentence explaining why the pipeline might perform differently across domains based on the nature of the questions.
3. Write a technique-by-technique analysis identifying which of the 13 nonsense techniques the pipeline catches most and least reliably, noting any patterns in what makes certain techniques harder to detect through structured spec analysis.
4. Select and annotate three to five notable individual responses: at least one best catch where the pipeline clearly identified the nonsense, at least one worst miss where it accepted nonsense uncritically, and at least one partial-pushback case that illustrates the boundary of the pipeline's skepticism.
5. For each notable response, include the original question, the known nonsensical element, a relevant excerpt from the pipeline's analysis, the judge score, and a one-sentence editorial note on why this response is interesting for the blog narrative.
6. Close with a brief summary of what the results mean for the blog story — whether the narrative is "our analysis layer adds real value" or "here's what we learned about where structured analysis fails" depends on where the headline number lands.

### Verify
- findings.md contains the headline metric, all 5 domain breakdowns, technique-level patterns, and at least 3 annotated notable responses
- Every number cited in findings.md can be traced back to a value in the reporter's summary JSON output
- The document identifies both strengths and weaknesses — it is not exclusively positive or negative
- The document is self-contained: a reader with no access to the raw data can understand the eval's methodology, results, and implications