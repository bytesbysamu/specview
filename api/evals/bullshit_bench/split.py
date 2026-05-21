"""Stratified holdout split for BullshitBench.

Reads questions.v2.json, groups questions by (technique, domain_group),
and assigns 60% of each group to the tuning set and 40% to the holdout set
using a fixed random seed for reproducibility.

For groups with fewer than 3 questions, ensures at least one question in
each set by rounding up the holdout allocation.

Writes splits.json — a flat JSON object mapping question_id → "tuning" | "holdout".

Usage (from the api/ directory):

    python -m evals.bullshit_bench.split

"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
_QUESTIONS_PATH = _FIXTURES_DIR / "questions.v2.json"
_SPLITS_PATH = _FIXTURES_DIR / "splits.json"

TUNING_RATIO = 0.6
SEED = 42


def _load_questions() -> tuple[list[dict], list[dict]]:
    """Load and flatten questions from the fixture file.

    Returns (all_questions, techniques) where techniques preserves the
    original list for reference.
    """
    with _QUESTIONS_PATH.open(encoding="utf-8") as fh:
        data = json.load(fh)

    all_questions: list[dict] = []
    for technique_block in data.get("techniques", []):
        for q in technique_block.get("questions", []):
            # Attach technique from the block if not already on the question.
            if "technique" not in q:
                q = dict(q)
                q["technique"] = technique_block["technique"]
            all_questions.append(q)

    return all_questions, data.get("techniques", [])


def _stratified_split(
    all_questions: list[dict],
    tuning_ratio: float,
    seed: int,
) -> dict[str, str]:
    """Assign each question to "tuning" or "holdout" using stratified sampling.

    Stratification key: (technique, domain_group).
    For groups with < 3 questions, ensures at least one in each set.

    Returns a dict mapping question_id → split label.
    """
    rng = random.Random(seed)

    # Group questions by (technique, domain_group).
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for q in all_questions:
        key = (q.get("technique", ""), q.get("domain_group", ""))
        groups[key].append(q)

    splits: dict[str, str] = {}

    for (technique, domain_group), members in groups.items():
        shuffled = list(members)
        rng.shuffle(shuffled)

        n = len(shuffled)
        if n == 1:
            # Singleton group: assign to tuning with probability=tuning_ratio,
            # holdout otherwise.  The shuffled-list rng already consumed one
            # call per-group, so we draw an additional float here.
            n_tuning = 1 if rng.random() < tuning_ratio else 0
        elif n == 2:
            # Two-item group: one each to preserve both sets.
            n_tuning = 1
        else:
            # Standard case: round to nearest int for tuning, remainder to holdout.
            n_tuning = max(1, round(n * tuning_ratio))
            # Ensure holdout also gets at least one.
            if n - n_tuning < 1:
                n_tuning = n - 1

        for i, q in enumerate(shuffled):
            label = "tuning" if i < n_tuning else "holdout"
            splits[q["id"]] = label

    return splits


def _print_distribution(
    all_questions: list[dict],
    splits: dict[str, str],
) -> None:
    """Print a distribution table showing per-technique split counts."""
    by_technique: dict[str, dict[str, int]] = defaultdict(lambda: {"tuning": 0, "holdout": 0})

    for q in all_questions:
        label = splits[q["id"]]
        by_technique[q.get("technique", "?")][label] += 1

    print(f"\n{'Technique':<40} {'Tuning':>8} {'Holdout':>9} {'Total':>7}")
    print("-" * 68)

    grand_tuning = grand_holdout = 0
    for technique in sorted(by_technique):
        counts = by_technique[technique]
        t = counts["tuning"]
        h = counts["holdout"]
        grand_tuning += t
        grand_holdout += h
        print(f"  {technique:<38} {t:>8} {h:>9} {t + h:>7}")

    print("-" * 68)
    grand_total = grand_tuning + grand_holdout
    print(f"  {'TOTAL':<38} {grand_tuning:>8} {grand_holdout:>9} {grand_total:>7}")

    # Also show domain_group distribution.
    by_domain: dict[str, dict[str, int]] = defaultdict(lambda: {"tuning": 0, "holdout": 0})
    for q in all_questions:
        by_domain[q.get("domain_group", "?")][splits[q["id"]]] += 1

    print(f"\n{'Domain Group':<40} {'Tuning':>8} {'Holdout':>9} {'Total':>7}")
    print("-" * 68)
    for domain in sorted(by_domain):
        counts = by_domain[domain]
        t = counts["tuning"]
        h = counts["holdout"]
        print(f"  {domain:<38} {t:>8} {h:>9} {t + h:>7}")
    print()


def main() -> None:
    all_questions, _ = _load_questions()
    print(f"Loaded {len(all_questions)} questions from {_QUESTIONS_PATH}")

    splits = _stratified_split(all_questions, tuning_ratio=TUNING_RATIO, seed=SEED)

    # Verify all questions have been assigned.
    assert len(splits) == len(all_questions), (
        f"Expected {len(all_questions)} splits, got {len(splits)}"
    )

    tuning_count = sum(1 for v in splits.values() if v == "tuning")
    holdout_count = sum(1 for v in splits.values() if v == "holdout")
    print(
        f"Split: {tuning_count} tuning ({tuning_count / len(splits):.0%}), "
        f"{holdout_count} holdout ({holdout_count / len(splits):.0%})"
    )

    _print_distribution(all_questions, splits)

    _SPLITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _SPLITS_PATH.open("w", encoding="utf-8") as fh:
        json.dump(splits, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"Wrote {len(splits)} entries to {_SPLITS_PATH}")


if __name__ == "__main__":
    main()
