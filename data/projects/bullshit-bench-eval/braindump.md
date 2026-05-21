we found BullshitBench — open source benchmark (1.6k stars, MIT, petergpt/bullshit-benchmark on github) that tests whether AI models push back on nonsensical questions instead of confidently answering them. 100 questions across 5 domains (software 40, finance 15, legal 15, medical 15, physics 15), 13 nonsense techniques like fabricated frameworks, causal chimeras, reified metaphors etc. Scores on 3 levels: 0 accepted nonsense, 1 partial challenge, 2 clear pushback.

Claude dominates their leaderboard — top 8 models are all Claude, Sonnet 4.6 leads at 91%. GPT-5.4 at 48%, Gemini 3 Pro at 48%.

We already tested one question manually — pasted a "Causal Dependency Fingerprinting" question (fabricated SRE methodology) into specview.dev's anonymous analysis box. The analysis caught the scale mismatch, called it "a solution looking for a problem", applied the user's own no-speculative-abstractions principle, and recommended a spreadsheet instead. 71.6 seconds. It passed.

Now we want to formalize this as a structured eval. Run all 100 BullshitBench questions through Specview's analysis pipeline, score the responses, get aggregate metrics we can publish. This proves Specview's core value prop — the analysis step doesn't just structure your thinking, it challenges it.

The pipeline we want to eval is the public anonymous analysis — same as what runs on specview.dev. It's adapter.rewrite() with haiku, the "You are a markdown spec writer / filter between a messy brain dump and a structured analysis" prompt. No builder context, no principles injection, just raw braindump in, analysis out.

For judging we use Claude Sonnet through the same adapter — give it the question, the known nonsensical element, and the response, score 0/1/2. Single judge is fine for our purposes, we're not trying to reproduce their full 3-judge panel.

The eval script lives inside specview/api/evals/bullshit_bench/. Runs inside the docker container via docker exec using the read-only mount at /home/appuser/projects — no rebuild needed. CHAIN_PROVIDER=cli as always.

Questions vendored as fixtures/questions.v2.json so runs are reproducible and version-pinned. Results output as JSON with aggregate stats by domain and technique.

CLI: --limit N for smoke tests (3 questions in 2 min), --filter domain for partial runs, --dry-run to verify prompt construction, --skip-judge for manual review. Full benchmark is 100 questions, ~30-50 min, ~$0.50-1.00.

The output becomes a blog post: "We ran BullshitBench against our spec pipeline. Here's what it caught and what it missed." Tag Peter Gostev. Content that writes itself.
