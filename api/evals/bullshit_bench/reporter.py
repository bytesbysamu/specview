"""BullshitBench aggregate reporter.

Reads a scored JSONL result file produced by runner.py and computes:
  - Domain-level breakdown (mean score, % >= 1, % == 2) for all five domains.
  - Technique-level breakdown (same three metrics) for all 13 techniques.
  - Two headline numbers:
      * leaderboard_score   — mean_score / 2 × 100 (matches published BullshitBench
                              rankings, e.g. "91%" for Sonnet 4.6)
      * pct_fully_rejected  — percentage of questions scoring exactly 2
  - Outlier records:
      * best_catches  — 3 questions whose score deviates most *above* domain average
      * worst_misses  — 3 questions whose score deviates most *below* domain average

Output is written to a `.summary.json` file alongside the JSONL file.

Usage (standalone):

    python -m evals.bullshit_bench.reporter results/run_<timestamp>.jsonl

Usage (programmatic):

    from evals.bullshit_bench.reporter import generate_report
    generate_report(Path("results/run_<timestamp>.jsonl"))
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

# Path bootstrap — allow running as `python -m evals.bullshit_bench.reporter`
# from the api/ directory.
_API_DIR = Path(__file__).resolve().parent.parent.parent  # api/
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from evals.bullshit_bench.judge import load_records  # noqa: E402 (re-use)
from evals.bullshit_bench.models import QuestionResult  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known dimension values (used for completeness warnings, not hard filtering)
# ---------------------------------------------------------------------------

KNOWN_DOMAINS = {"software", "finance", "legal", "medical", "physics"}
KNOWN_TECHNIQUES = {
    "authoritative_framing",
    "confident_extrapolation",
    "cross_domain_stitching",
    "fabricated_authority",
    "false_granularity",
    "misapplied_mechanism",
    "nested_nonsense",
    "plausible_nonexistent_framework",
    "reified_metaphor",
    "specificity_trap",
    "sunk_cost_framing",
    "temporal_category_error",
    "wrong_unit_of_analysis",
}


# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------

def _compute_group_metrics(records: list[QuestionResult]) -> dict[str, Any]:
    """Compute the three standard metrics over an arbitrary list of records.

    Only records with a non-None judge_score are included in calculations.
    Returns a dict with keys: count, scored_count, mean_score, pct_at_least_1,
    pct_score_2.
    """
    scored = [r for r in records if r.judge_score is not None]
    n = len(scored)
    total = len(records)

    if n == 0:
        return {
            "count": total,
            "scored_count": 0,
            "mean_score": None,
            "pct_at_least_1": None,
            "pct_score_2": None,
        }

    scores = [float(r.judge_score) for r in scored]  # type: ignore[arg-type]
    mean_score = sum(scores) / n
    pct_at_least_1 = 100.0 * sum(1 for s in scores if s >= 1) / n
    pct_score_2 = 100.0 * sum(1 for s in scores if s >= 2) / n

    return {
        "count": total,
        "scored_count": n,
        "mean_score": round(mean_score, 4),
        "pct_at_least_1": round(pct_at_least_1, 2),
        "pct_score_2": round(pct_score_2, 2),
    }


def _domain_breakdown(records: list[QuestionResult]) -> dict[str, Any]:
    """Group by domain_group and compute metrics per group."""
    groups: dict[str, list[QuestionResult]] = {}
    for r in records:
        key = r.domain_group or r.domain or "unknown"
        groups.setdefault(key, []).append(r)

    result: dict[str, Any] = {}
    for domain, recs in sorted(groups.items()):
        result[domain] = _compute_group_metrics(recs)

    # Warn about missing known domains.
    for d in KNOWN_DOMAINS:
        if d not in result:
            logger.warning("Domain %r not found in results", d)

    return result


def _technique_breakdown(records: list[QuestionResult]) -> dict[str, Any]:
    """Group by technique and compute metrics per technique."""
    groups: dict[str, list[QuestionResult]] = {}
    for r in records:
        key = r.technique or "unknown"
        groups.setdefault(key, []).append(r)

    result: dict[str, Any] = {}
    for technique, recs in sorted(groups.items()):
        result[technique] = _compute_group_metrics(recs)

    # Warn about missing known techniques.
    for t in KNOWN_TECHNIQUES:
        if t not in result:
            logger.warning("Technique %r not found in results", t)

    return result


# ---------------------------------------------------------------------------
# Headline numbers
# ---------------------------------------------------------------------------

def _headline_numbers(records: list[QuestionResult]) -> dict[str, Any]:
    """Compute the two top-level aggregate metrics."""
    scored = [r for r in records if r.judge_score is not None]
    n = len(scored)

    if n == 0:
        return {
            "scored_count": 0,
            "total_count": len(records),
            "leaderboard_score": None,
            "pct_fully_rejected": None,
        }

    scores = [float(r.judge_score) for r in scored]  # type: ignore[arg-type]
    mean_score = sum(scores) / n
    # BullshitBench leaderboard format: (mean / 2) × 100
    leaderboard_score = round((mean_score / 2.0) * 100.0, 2)
    pct_fully_rejected = round(100.0 * sum(1 for s in scores if s >= 2) / n, 2)

    return {
        "scored_count": n,
        "total_count": len(records),
        "mean_score": round(mean_score, 4),
        "leaderboard_score": leaderboard_score,
        "pct_fully_rejected": pct_fully_rejected,
    }


# ---------------------------------------------------------------------------
# Outlier detection
# ---------------------------------------------------------------------------

def _outliers(
    records: list[QuestionResult],
    domain_metrics: dict[str, Any],
    top_n: int = 3,
) -> dict[str, Any]:
    """Identify best catches and worst misses relative to domain averages.

    Best catches: records whose (score - domain_avg) is highest (largest positive
    deviation — got it right in a domain that often misses).
    Worst misses: records whose (score - domain_avg) is most negative (largest
    negative deviation — missed in a domain that usually catches it).

    Only records with a non-None judge_score are considered.
    """
    # Build domain average lookup.
    domain_avg: dict[str, float] = {}
    for domain, metrics in domain_metrics.items():
        if metrics["mean_score"] is not None:
            domain_avg[domain] = metrics["mean_score"]

    scored = [r for r in records if r.judge_score is not None]

    annotated: list[dict[str, Any]] = []
    for r in scored:
        key = r.domain_group or r.domain or "unknown"
        avg = domain_avg.get(key, 0.0)
        deviation = float(r.judge_score) - avg  # type: ignore[arg-type]
        annotated.append({"record": r, "deviation": deviation, "domain_avg": avg})

    # Sort by deviation descending for best catches, ascending for worst misses.
    by_deviation_desc = sorted(annotated, key=lambda x: x["deviation"], reverse=True)
    by_deviation_asc = sorted(annotated, key=lambda x: x["deviation"])

    def _serialise_outlier(entry: dict[str, Any]) -> dict[str, Any]:
        r: QuestionResult = entry["record"]
        return {
            "question_id": r.question_id,
            "domain_group": r.domain_group,
            "technique": r.technique,
            "judge_score": r.judge_score,
            "domain_avg": round(entry["domain_avg"], 4),
            "deviation": round(entry["deviation"], 4),
            "question_text": r.question_text,
            "nonsensical_element": r.nonsensical_element,
            "response_text": r.response_text,
            "judge_label": r.judge_label,
            "judge_reasoning": r.judge_reasoning,
        }

    best_catches = [_serialise_outlier(e) for e in by_deviation_desc[:top_n]]
    worst_misses = [_serialise_outlier(e) for e in by_deviation_asc[:top_n]]

    return {"best_catches": best_catches, "worst_misses": worst_misses}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate(
    records: list[QuestionResult],
    domain_metrics: dict[str, Any],
    technique_metrics: dict[str, Any],
) -> list[str]:
    """Run basic sanity checks and return a list of warning strings."""
    warnings: list[str] = []

    # Domain counts should sum to total scored.
    total_in_domains = sum(m["count"] for m in domain_metrics.values())
    if total_in_domains != len(records):
        warnings.append(
            f"Domain counts sum to {total_in_domains} but total records = {len(records)}"
        )

    # Technique counts should also sum to total.
    total_in_techniques = sum(m["count"] for m in technique_metrics.values())
    if total_in_techniques != len(records):
        warnings.append(
            f"Technique counts sum to {total_in_techniques} but total records = {len(records)}"
        )

    # Check all known domains are present.
    missing_domains = KNOWN_DOMAINS - set(domain_metrics.keys())
    if missing_domains:
        warnings.append(f"Missing domains in results: {sorted(missing_domains)}")

    # Check all known techniques are present.
    missing_techniques = KNOWN_TECHNIQUES - set(technique_metrics.keys())
    if missing_techniques:
        warnings.append(f"Missing techniques in results: {sorted(missing_techniques)}")

    return warnings


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_report(result_path: Path) -> Path:
    """Compute aggregate metrics from a scored JSONL file and write a summary JSON.

    The summary is written to the same directory with the `.jsonl` extension
    replaced by `.summary.json`.

    Returns the path to the summary file.
    """
    if not result_path.exists():
        raise FileNotFoundError(f"Result file not found: {result_path}")

    logger.info("Loading records from %s", result_path)
    records = load_records(result_path)
    logger.info("Loaded %d records", len(records))

    if not records:
        raise ValueError(f"No records found in {result_path}")

    scored_count = sum(1 for r in records if r.judge_score is not None)
    logger.info("%d/%d records have judge scores", scored_count, len(records))

    # Compute all metrics.
    domain_metrics = _domain_breakdown(records)
    technique_metrics = _technique_breakdown(records)
    headlines = _headline_numbers(records)
    outliers = _outliers(records, domain_metrics)

    # Validation warnings.
    warnings = _validate(records, domain_metrics, technique_metrics)
    for w in warnings:
        logger.warning("Validation: %s", w)

    summary: dict[str, Any] = {
        "source_file": str(result_path),
        "headline": headlines,
        "domain_breakdown": domain_metrics,
        "technique_breakdown": technique_metrics,
        "outliers": outliers,
        "validation_warnings": warnings,
    }

    # Write summary alongside the JSONL file.
    summary_path = result_path.with_suffix("").with_suffix(".summary.json")
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    logger.info(
        "Report written to %s | leaderboard_score=%.1f%% pct_fully_rejected=%.1f%%",
        summary_path,
        headlines["leaderboard_score"] if headlines["leaderboard_score"] is not None else float("nan"),
        headlines["pct_fully_rejected"] if headlines["pct_fully_rejected"] is not None else float("nan"),
    )

    return summary_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        prog="python -m evals.bullshit_bench.reporter",
        description="Compute aggregate metrics from a scored BullshitBench result file.",
    )
    parser.add_argument(
        "result_file",
        metavar="RESULT_FILE",
        help="Path to the scored JSONL result file (absolute or relative to results/).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )

    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    result_path = Path(args.result_file)
    if not result_path.is_absolute():
        # Resolve relative to the results directory for convenience.
        _RESULTS_DIR = Path(__file__).resolve().parent / "results"
        result_path = _RESULTS_DIR / result_path

    summary_path = generate_report(result_path)
    logger.info("Summary written to: %s", summary_path)


if __name__ == "__main__":
    main()
