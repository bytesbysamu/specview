# Implementation Guide: ex-girlfriend

## Overview
This epic moves an ambiguous relationship-restart question through a four-stage decision pipeline (Diagnose → Delta → Signal → Decide) and out the other side as a written yes / no / defer-30-days verdict by end of day Wednesday May 13, 2026. Tasks 1 and 3 run in parallel as the two independent inputs (past cause, present signal); Task 2 consumes Task 1; Task 4 is the gate that consumes 1, 2, and 3; Task 5 translates Task 4 into a question list for the live conversation. Every stage emits one written sentence so the final reasoning is auditable on Wednesday morning and cannot quietly drift toward anniversary-anchored reasoning.

## Shared Pre-flight
- Create the working directory `decision-notes/` at the repo root to hold all five stage artifacts as plain markdown files.
- Confirm the hard deadline on the calendar: end of day 2026-05-13, with the live conversation slot itself blocked off ahead of EOD.
- Block ~2.25 working hours-of-focus across May 9 → May 13, with Stages 1 and 3 done first (in parallel), Stage 2 next, Stage 4 provisional by Tuesday evening, and Stage 5 finalized Wednesday morning.
- Adopt the one-sentence-per-stage rule: if a stage's output cannot fit in one written sentence, it is not done.
- Adopt the symbolic-input exclusion rule: the May 13 anniversary date is not allowed as a justification anywhere in Stages 1–4.
- Write artifacts in plain prose with no shared-doc collaboration layer — Sam is sole reader and writer.
- Pre-commit to the three-outcome space (yes / no / defer-30-days) before drafting any stage so a binary doesn't silently get assumed.
- Keep all old-fight relitigation out of these notes — that material is reserved for the live Wednesday conversation, not the planning artifacts.

---

## Task 1: Diagnose December breakup cause  [Effort: 0.5 days]

### What
Categorize the December 2025 breakup into exactly one of three buckets — resolvable conflict, structural incompatibility, or external circumstance — with a one-line justification. This determines whether a restart is even coherent before any other stage runs.

### Files
- **Create**: `decision-notes/stage-1-cause.md` — the written one-sentence cause classification plus its justification.

### Steps
1. In `decision-notes/stage-1-cause.md`, write down the December 2025 breakup as Sam recalls it in a short unfiltered paragraph at the top of the file, used only as raw input for the categorization that follows.
2. Add a `Categories` section listing the three allowed buckets (resolvable conflict, structural incompatibility, external circumstance) with a one-line definition for each so the choice is forced rather than blurred.
3. Pick exactly one bucket and write the line `cause = <category>` followed by a one-sentence justification that points at a specific behavior, pattern, or event — not a feeling or a date.
4. Re-read the justification and strike it if it relitigates the fight, references the May 13 anniversary, or hedges across two categories; rewrite until it commits to one bucket.

### Verify
- `decision-notes/stage-1-cause.md` exists and contains exactly one `cause = <category>` line.
- The justification sentence names a concrete behavior or circumstance, not a date or a mood.
- The categorization is a single bucket, not "mostly X with some Y."
- Running `grep -i "anniversary\|may 13" decision-notes/stage-1-cause.md` returns no matches.

---

## Task 2: Assess what changed in 5 months  [Effort: 0.5 days]

### What
Identify what concretely changed during the five-month break and name who changed it (her / Sam / both / neither). "Neither changed" is a valid output and must not be sanded down into something more comfortable.

### Files
- **Create**: `decision-notes/stage-2-delta.md` — the written one-sentence delta assessment with a confidence note.
- **Modify**: `decision-notes/stage-1-cause.md` — append a one-line back-reference confirming Stage 2 was anchored to the categorized cause from Stage 1.

### Steps
1. Open `decision-notes/stage-1-cause.md`, copy the `cause = <category>` line into the top of `decision-notes/stage-2-delta.md`, and treat the cause as the variable the delta must move (or fail to move) for a restart to make sense.
2. List observable evidence from the two post-breakup meetings under a `Her side` heading — only what she actually said or did, not what Sam inferred.
3. List Sam's own change log over the five months under a `My side` heading and explicitly mark every entry as low-confidence because self-assessment is the least reliable input in this stage.
4. Write the line `delta = <who> changed <what>` (with `<who>` being one of her / Sam / both / neither and `<what>` being a specific behavior or circumstance), or write `delta = none` if nothing in the evidence supports change.
5. Append a one-line back-reference in `decision-notes/stage-1-cause.md` noting that Stage 2 was completed against this cause, so the audit trail is intact.

### Verify
- `decision-notes/stage-2-delta.md` contains exactly one `delta = ...` line.
- Her-side evidence cites observable behavior from the two meetings, not inference.
- Sam-side entries are explicitly tagged as low-confidence.
- "Neither" was considered as a real option, not skipped — visible in the file as either the chosen output or as a rejected option with one line of why.

---

## Task 3: Review Sunday meeting signals honestly  [Effort: 0.25 days]

### What
Convert last Sunday's meeting (and the prior post-breakup meeting) into a classified signal — mutual interest, one-sided interest, or ambiguous — with the specific behaviors that justify the call. Runs in parallel with Task 1 because past cause and present signal are independent variables.

### Files
- **Create**: `decision-notes/stage-3-signal.md` — the written one-sentence signal classification plus the behaviors that justify it.

### Steps
1. In `decision-notes/stage-3-signal.md`, write three columns or sections: what she said, what she did, and what she did not say or do — populating each with concrete observations from the two post-breakup meetings.
2. Under a `Projection check` heading, list any behavior currently being read as positive and explicitly ask whether the same behavior would be read the same way if the hoped-for outcome were the opposite; strike or downgrade any that fail this test.
3. Pick exactly one of mutual / one-sided / ambiguous and write `signal = <class>`, then list the two or three specific behaviors that drove the classification beneath it.
4. If any behavior is genuinely unreadable, force the overall classification to `ambiguous` rather than resolving it through hopeful interpretation — ambiguity is a real and protected output here.

### Verify
- `decision-notes/stage-3-signal.md` contains exactly one `signal = <class>` line.
- Two or three observable behaviors are listed as the justification, each tied to one of the two meetings.
- The `Projection check` section exists and shows at least one behavior was tested for hopeful reading.
- The classification is one of the three allowed values, not a fourth invented one.

---

## Task 4: Define yes/no/defer decision criteria  [Effort: 0.5 days]

### What
Combine cause, delta, and signal into a written decision rule set and run it twice — once provisionally before Wednesday, once finally after the conversation — producing one of yes, no, or defer-30-days. This is the architectural choke point where the symbolic anniversary input is explicitly excluded.

### Files
- **Create**: `decision-notes/stage-4-decision.md` — the declarative decision rules and both the provisional and final outputs.

### Steps
1. In `decision-notes/stage-4-decision.md`, write a `Rules` section that states verbatim: yes requires cause is resolvable or external AND delta names a concrete change in the relevant party AND signal is mutual; no requires cause is structural incompatibility AND delta is none, OR signal is one-sided; defer-30-days is the default whenever any input is ambiguous, when the only yes-reason references the anniversary, or when Wednesday surfaces a mismatch with the Stage 3 signal.
2. Pull the one-sentence outputs from `decision-notes/stage-1-cause.md`, `decision-notes/stage-2-delta.md`, and `decision-notes/stage-3-signal.md` into an `Inputs` section so the gate evaluation is visible and auditable.
3. Run the rules against the inputs and write `provisional decision = <yes|no|defer-30-days>` with a one-line reason that does not mention May 13; if the only available reason for yes references the anniversary, the rules force defer-30-days and the file must reflect that.
4. After Wednesday's conversation, return to the same file and append `final decision = <yes|no|defer-30-days>` plus a one-line reason; if the live conversation contradicts the Stage 3 signal, the rules require either downgrading toward defer or explicitly documenting why the new evidence overrides.
5. If `final decision = defer-30-days`, append the explicit re-evaluation date (30 days from May 13) so the defer cannot become indefinite.

### Verify
- `decision-notes/stage-4-decision.md` contains both a `provisional decision = ...` line (written by Tuesday evening) and a `final decision = ...` line (written by EOD 2026-05-13).
- Running `grep -i "anniversary\|may 13\|four.year" decision-notes/stage-4-decision.md` returns no matches inside any reason line.
- The `Inputs` section quotes the exact one-sentence outputs from Stages 1, 2, and 3.
- If the final output is defer, a concrete re-evaluation date is written down.

---

## Task 5: Prepare Wednesday conversation script  [Effort: 0.5 days]

### What
Translate the Stage 4 rules and the open uncertainties from Stages 1–3 into three to five questions to ask her on Wednesday — questions, not statements, ordered from least to most loaded. The script executes the decision; it does not produce it.

### Files
- **Create**: `decision-notes/stage-5-script.md` — the ordered question list plus the one-level-deep follow-up notes.

### Steps
1. In `decision-notes/stage-5-script.md`, list the open uncertainties remaining from Stages 1, 2, and 3 — for example, an unverified self-assessment from Stage 2 or an ambiguous behavior from Stage 3 — and treat each as a candidate for a question.
2. Draft three to five questions, each phrased as an open question whose answer would either confirm or contradict a Stage 4 input; reject any draft that is actually a statement, a verdict, or a leading question and rewrite it as a real question.
3. Order the questions from least to most loaded so the conversation can end early if early answers already resolve the gate, and so the heaviest question is not the opener.
4. Add at most one level of follow-up note per question (a short prompt for what to listen for), and explicitly do not branch into "if she says X then I say Y" trees deeper than that — over-scripting prevents listening.
5. Add a top-of-file reminder that this is an information-gathering interface, not a verdict-delivery interface, and that any decision-style statement belongs in a follow-up conversation only if Stage 4's final output is yes.

### Verify
- `decision-notes/stage-5-script.md` contains between three and five numbered questions.
- Every entry ends with a question mark and none of them are statements or verdicts.
- Questions are ordered least-to-most loaded, visible from the file's order.
- No branching deeper than one follow-up note per question is present in the file.