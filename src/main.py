"""Main orchestrator for the candidate screening pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .config import PROJECT_ROOT, load_config
from .csv_parser import parse_csv
from .enrichment import enrich_candidate
from .fake_detector import detect_fake
from .models import ScreenedCandidate
from .report import generate_report, save_report
from .scorer import load_job_description, score_candidate

logger = logging.getLogger("candidate_screener")


def _process_one(candidate, job_description, config):
    """Process a single candidate through the full pipeline."""
    name = candidate.name
    logger.info("Processing: %s", name)

    # Step 1: LinkedIn enrichment
    linkedin = enrich_candidate(candidate, config)

    # Step 2: Fake detection
    fake_result = detect_fake(candidate, linkedin, config)

    # Step 3: Score (skip if flagged fake to save API calls)
    if fake_result.risk_level.value in ("definitely_fake", "likely_fake"):
        logger.info("  %s flagged as %s — skipping scoring", name, fake_result.risk_level.value)
        from .models import QualificationScore

        qualification = QualificationScore()
    else:
        qualification = score_candidate(candidate, linkedin, job_description, config)

    return ScreenedCandidate(
        candidate=candidate,
        linkedin=linkedin,
        fake_detection=fake_result,
        qualification=qualification,
    )


def run_pipeline(
    csv_path: str,
    jd_path: str,
    output_path: str | None = None,
    config_path: str | None = None,
) -> Path:
    """Run the full screening pipeline and return the path to the generated report."""
    config = load_config(config_path)

    if not config.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY not set. Add it to .env or environment.")
        sys.exit(1)

    # Parse candidates
    logger.info("Parsing CSV: %s", csv_path)
    candidates = parse_csv(csv_path, config.column_mapping or None)
    logger.info("Found %d candidates", len(candidates))

    if not candidates:
        logger.warning("No candidates found in CSV. Exiting.")
        sys.exit(0)

    # Load job description
    logger.info("Loading JD: %s", jd_path)
    job_description = load_job_description(jd_path)

    # Process candidates in parallel batches
    screened: list[ScreenedCandidate] = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=config.batch_size) as executor:
        futures = {
            executor.submit(_process_one, c, job_description, config): c
            for c in candidates
        }
        for i, future in enumerate(as_completed(futures), 1):
            candidate = futures[future]
            try:
                result = future.result()
                screened.append(result)
                logger.info(
                    "  [%d/%d] %s — score: %.0f, verification: %s",
                    i,
                    len(candidates),
                    candidate.name,
                    result.final_score,
                    result.fake_detection.risk_level.value,
                )
            except Exception as e:
                logger.error("  [%d/%d] %s — FAILED: %s", i, len(candidates), candidate.name, e)

    elapsed = time.time() - start
    logger.info("Processed %d candidates in %.1fs", len(screened), elapsed)

    # Generate report
    if output_path is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = str(PROJECT_ROOT / "output" / f"report_{timestamp}.md")

    report_content = generate_report(screened, jd_path, config)
    report_file = save_report(report_content, output_path)
    logger.info("Report saved to: %s", report_file)

    return report_file


def main():
    parser = argparse.ArgumentParser(
        description="Screen candidates from a Workable CSV export against a job description."
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to the Workable CSV export file",
    )
    parser.add_argument(
        "--jd",
        required=True,
        help="Path to the job description file (markdown or text)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path for the output report (default: output/report_<timestamp>.md)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config.yaml (default: config.yaml in project root)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    run_pipeline(
        csv_path=args.csv,
        jd_path=args.jd,
        output_path=args.output,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
