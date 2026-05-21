"""BullshitBench eval runner.

Iterates questions from the vendored questions.v2.json fixture through
adapter.rewrite() on the anonymous-analysis path, captures raw responses with
metadata, and writes per-question results incrementally to a timestamped JSON
Lines file under api/evals/bullshit_bench/results/.

Usage (from the api/ directory):

    python -m evals.bullshit_bench.runner [--limit N] [--filter DOMAIN] \
        [--split tuning|holdout|all] [--dry-run] [--skip-judge]

    python -m evals.bullshit_bench.runner --rejudge results/run_<timestamp>.jsonl

Flags:
  --limit N        Process only the first N questions (after filtering).
  --filter DOMAIN  Restrict to questions whose domain_group matches DOMAIN
                   (case-insensitive substring match).
  --split SPLIT    Restrict to questions in the given split: tuning, holdout,
                   or all (default: all).  Requires splits.json to exist.
  --dry-run        Build prompts and write result records without calling the
                   adapter.  The constructed prompt is stored in response_text.
  --skip-judge     Leave judge score fields empty (no scoring pass).  Useful
                   when running a long pipeline that will be scored later via
                   --rejudge or judge.backfill_file().
  --rejudge FILE   Re-score all records in an existing result file using the
                   current judge prompt.  The pipeline is NOT re-run.  Previous
                   scores are overwritten.  Mutually exclusive with normal run
                   flags.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — allow running as `python -m evals.bullshit_bench.runner`
# from the api/ directory.  We insert api/ onto sys.path so that the chain
# adapter import resolves correctly in both direct and module invocation modes.
# ---------------------------------------------------------------------------
_API_DIR = Path(__file__).resolve().parent.parent.parent  # api/
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

from modules.runtime.chain import adapter  # noqa: E402  (import after path tweak)
from modules.runtime.chain.errors import ProviderError  # noqa: E402
from modules.ai.services.public_analyze import _ANALYSIS_SYSTEM, _ANALYSIS_USER  # noqa: E402

from evals.bullshit_bench.models import QuestionResult, RunHeader  # noqa: E402
from evals.bullshit_bench.judge import score_result, rejudge_file  # noqa: E402
from evals.bullshit_bench.reporter import generate_report  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL = "claude-opus-4-6"
MAX_TOKENS = 2048

# _ANALYSIS_SYSTEM and _ANALYSIS_USER are imported from
# modules.ai.services.public_analyze — single source of truth.

_FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures" / "questions.v2.json"
_SPLITS_PATH = Path(__file__).resolve().parent / "fixtures" / "splits.json"
_RESULTS_DIR = Path(__file__).resolve().parent / "results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_git_commit() -> str:
    """Return the short SHA of HEAD, or 'unknown' if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


def _build_prompt(question_text: str) -> str:
    """Construct the user prompt exactly as the anonymous analysis path does."""
    return _ANALYSIS_USER.format(braindump=question_text)


def _load_splits() -> dict[str, str]:
    """Load the splits sidecar mapping question_id → "tuning" | "holdout".

    Returns an empty dict if splits.json does not exist yet.
    """
    if not _SPLITS_PATH.exists():
        logger.warning("splits.json not found at %s — split filtering disabled", _SPLITS_PATH)
        return {}
    with _SPLITS_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _load_questions(
    fixture_path: Path,
    filter_domain: str | None,
    limit: int | None,
    split_filter: str | None = None,
) -> tuple[list[dict], str]:
    """Load and flatten questions from the fixture file.

    Returns (questions, fixture_version).
    Applies split filter, then domain filter (case-insensitive substring),
    then limit cap.  Each question dict gains a "split" key from splits.json.
    """
    with fixture_path.open(encoding="utf-8") as fh:
        data = json.load(fh)

    fixture_version: str = data.get("version", "")

    # Flatten: techniques[*].questions[]
    all_questions: list[dict] = []
    for technique_block in data.get("techniques", []):
        all_questions.extend(technique_block.get("questions", []))

    logger.info("Loaded %d total questions from fixture (version=%s)", len(all_questions), fixture_version)

    # Attach split label from sidecar.
    splits = _load_splits()
    for q in all_questions:
        q["split"] = splits.get(q.get("id", ""), None)

    if split_filter and split_filter != "all":
        before = len(all_questions)
        all_questions = [q for q in all_questions if q.get("split") == split_filter]
        logger.info(
            "After --split %r: %d questions (dropped %d)",
            split_filter,
            len(all_questions),
            before - len(all_questions),
        )

    if filter_domain:
        before = len(all_questions)
        filter_lower = filter_domain.lower()
        all_questions = [
            q for q in all_questions
            if filter_lower in q.get("domain_group", "").lower()
            or filter_lower in q.get("domain", "").lower()
        ]
        logger.info(
            "After --filter %r: %d questions (dropped %d)",
            filter_domain,
            len(all_questions),
            before - len(all_questions),
        )

    if limit is not None:
        all_questions = all_questions[:limit]
        logger.info("After --limit %d: %d questions", limit, len(all_questions))

    return all_questions, fixture_version


def _write_result(result_path: Path, records: list[QuestionResult]) -> None:
    """Overwrite result_path with the full list serialised as JSON Lines.

    One JSON object per line — crash-safe because each line is independent.
    The file is rewritten in full after every question so a crash at question N
    still preserves questions 1 … N-1 from the previous write.
    """
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec.__dict__) + "\n")


def _write_header(header_path: Path, header: RunHeader) -> None:
    """Write the run header as a single JSON file alongside the results."""
    header_path.parent.mkdir(parents=True, exist_ok=True)
    with header_path.open("w", encoding="utf-8") as fh:
        json.dump(header.__dict__, fh, indent=2)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(
    limit: int | None,
    filter_domain: str | None,
    dry_run: bool,
    skip_judge: bool,
    split_filter: str | None = None,
) -> Path:
    """Execute the eval run and write results to disk.

    Returns the path to the written JSONL result file.
    """
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc)
    timestamp_iso = timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")
    run_slug = timestamp.strftime("%Y%m%dT%H%M%SZ")

    result_path = _RESULTS_DIR / f"run_{run_slug}.jsonl"
    header_path = _RESULTS_DIR / f"run_{run_slug}.header.json"

    logger.info(
        "Starting BullshitBench eval run | model=%s dry_run=%s limit=%s filter=%r split=%r",
        MODEL,
        dry_run,
        limit,
        filter_domain,
        split_filter,
    )

    # Load questions
    questions, fixture_version = _load_questions(
        _FIXTURES_PATH, filter_domain, limit, split_filter=split_filter
    )

    if not questions:
        logger.warning("No questions to process — check --filter value.")
        return result_path

    # Resolve provider name for the header
    provider_name = os.environ.get("CHAIN_PROVIDER", "cli")

    header = RunHeader(
        model=MODEL,
        provider=provider_name,
        timestamp_iso=timestamp_iso,
        git_commit=_get_git_commit(),
        flag_limit=limit,
        flag_filter=filter_domain,
        flag_dry_run=dry_run,
        flag_skip_judge=skip_judge,
        fixture_version=fixture_version,
        question_count=len(questions),
    )
    _write_header(header_path, header)
    logger.info("Run header written to %s", header_path)

    records: list[QuestionResult] = []
    total = len(questions)
    cumulative_latency = 0.0

    for idx, q in enumerate(questions, start=1):
        q_id = q.get("id", f"q{idx}")
        question_text = q.get("question", "")
        prompt = _build_prompt(question_text)

        logger.info("[%d/%d] Processing question id=%s", idx, total, q_id)

        if dry_run:
            # Dry-run: store the constructed prompt, skip the adapter call.
            record = QuestionResult(
                question_id=q_id,
                question_text=question_text,
                nonsensical_element=q.get("nonsensical_element", ""),
                domain=q.get("domain", ""),
                domain_group=q.get("domain_group", ""),
                technique=q.get("technique", ""),
                difficulty=q.get("difficulty", ""),
                difficulty_label=q.get("difficulty_label", ""),
                is_control=bool(q.get("is_control", False)),
                split=q.get("split"),
                prompt_sent=prompt,
                response_text=prompt,   # prompt stored in place of response
                latency_seconds=0.0,
                dry_run=True,
                error=None,
            )
            records.append(record)
            _write_result(result_path, records)
            logger.info("[%d/%d] dry-run record written (id=%s)", idx, total, q_id)
            continue

        # Live adapter call
        response_text = ""
        latency_seconds = 0.0
        error_msg: str | None = None

        t0 = time.monotonic()
        try:
            result = adapter.rewrite(
                system=_ANALYSIS_SYSTEM,
                prompt=prompt,
                model=MODEL,
                max_tokens=MAX_TOKENS,
            )
            latency_seconds = time.monotonic() - t0
            response_text = result.text
        except ProviderError as exc:
            latency_seconds = time.monotonic() - t0
            error_msg = f"ProviderError: {exc}"
            logger.warning("[%d/%d] ProviderError for id=%s: %s", idx, total, q_id, exc)
        except Exception as exc:  # noqa: BLE001
            latency_seconds = time.monotonic() - t0
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.warning("[%d/%d] Unexpected error for id=%s: %s", idx, total, q_id, exc)

        cumulative_latency += latency_seconds
        avg_latency = cumulative_latency / idx
        remaining = total - idx
        eta_seconds = avg_latency * remaining

        logger.info(
            "[%d/%d] id=%s latency=%.2fs avg=%.2fs remaining=%d eta=%.0fs",
            idx,
            total,
            q_id,
            latency_seconds,
            avg_latency,
            remaining,
            eta_seconds,
        )

        record = QuestionResult(
            question_id=q_id,
            question_text=question_text,
            nonsensical_element=q.get("nonsensical_element", ""),
            domain=q.get("domain", ""),
            domain_group=q.get("domain_group", ""),
            technique=q.get("technique", ""),
            difficulty=q.get("difficulty", ""),
            difficulty_label=q.get("difficulty_label", ""),
            is_control=bool(q.get("is_control", False)),
            split=q.get("split"),
            prompt_sent=prompt,
            response_text=response_text,
            latency_seconds=latency_seconds,
            dry_run=False,
            error=error_msg,
        )

        # Judge pass — only when the adapter call succeeded and --skip-judge
        # was not set.  Dry-run records are never judged.
        if not skip_judge and error_msg is None:
            logger.info("[%d/%d] Running judge for id=%s", idx, total, q_id)
            j_score, j_label, j_reasoning = score_result(record)
            record.judge_score = j_score
            record.judge_label = j_label
            record.judge_reasoning = j_reasoning

        records.append(record)

        # Incremental write — preserves all completed records on crash.
        _write_result(result_path, records)

    logger.info(
        "Run complete: %d/%d questions processed | results=%s",
        len(records),
        total,
        result_path,
    )
    if not dry_run and records:
        latencies = [r.latency_seconds for r in records if r.error is None]
        if latencies:
            logger.info(
                "Latency stats: min=%.2fs max=%.2fs avg=%.2fs",
                min(latencies),
                max(latencies),
                sum(latencies) / len(latencies),
            )

    errors = [r for r in records if r.error is not None]
    if errors:
        logger.warning("%d question(s) failed with errors", len(errors))
        for r in errors:
            logger.warning("  id=%s error=%s", r.question_id, r.error)

    return result_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m evals.bullshit_bench.runner",
        description="Run BullshitBench questions through the anonymous analysis pipeline.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap the number of questions processed.",
    )
    parser.add_argument(
        "--filter",
        dest="filter_domain",
        default=None,
        metavar="DOMAIN",
        help="Restrict to questions whose domain or domain_group contains DOMAIN (case-insensitive).",
    )
    parser.add_argument(
        "--split",
        dest="split_filter",
        choices=["tuning", "holdout", "all"],
        default="all",
        help=(
            "Restrict to questions in the given split: tuning (~60 questions), "
            "holdout (~40 questions), or all (default: all). "
            "Requires fixtures/splits.json to exist (run split.py first)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Build prompts and write result records without calling adapter.rewrite().",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        default=False,
        help="Leave judge score fields empty (no scoring pass).",
    )
    parser.add_argument(
        "--rejudge",
        metavar="FILE",
        default=None,
        help=(
            "Re-score all records in an existing result JSONL file using the "
            "current judge prompt.  The pipeline is NOT re-run; previous scores "
            "are overwritten.  Mutually exclusive with normal run flags."
        ),
    )
    parser.add_argument(
        "--report",
        action="store_true",
        default=False,
        help=(
            "After the run (and optional judge pass) completes, invoke the reporter "
            "to compute aggregate metrics and write a .summary.json file alongside "
            "the result file.  Has no effect with --dry-run or --skip-judge."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Enable DEBUG-level logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.rejudge:
        result_path = Path(args.rejudge)
        if not result_path.is_absolute():
            # Resolve relative to the results directory for convenience.
            result_path = _RESULTS_DIR / result_path
        if not result_path.exists():
            logger.error("--rejudge: file not found: %s", result_path)
            sys.exit(1)
        logger.info("--rejudge mode: re-scoring %s", result_path)
        rejudge_file(result_path)
        return

    result_path = run(
        limit=args.limit,
        filter_domain=args.filter_domain,
        dry_run=args.dry_run,
        skip_judge=args.skip_judge,
        split_filter=args.split_filter,
    )

    if args.report and result_path is not None:
        if args.dry_run:
            logger.warning("--report skipped: --dry-run produces no scored records")
        elif args.skip_judge:
            logger.warning("--report skipped: --skip-judge means no judge scores to aggregate")
        else:
            logger.info("--report: generating aggregate report for %s", result_path)
            generate_report(result_path)


if __name__ == "__main__":
    main()
