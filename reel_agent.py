#!/usr/bin/env python3
"""Paws & Pause reel agent — entry point.

Reads the existing proposal + slide plan, generates HTML slides, critiques and
revises them, synthesizes TTS narration, renders PNGs, and composes reel.mp4.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from reel_pipeline.config import settings
from reel_pipeline.pipeline import run_pipeline


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a 30–60s Paws & Pause pitch reel from proposal + slide plan."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)
    log = logging.getLogger("reel_agent")

    try:
        result = asyncio.run(run_pipeline(settings))
    except KeyboardInterrupt:
        log.error("Interrupted")
        return 130
    except Exception as exc:  # noqa: BLE001
        log.exception("Pipeline failed: %s", exc)
        return 1

    log.info(
        "Done. slides=%d reel=%s elapsed=%.1fs",
        len(result.plan.slides),
        result.reel_path,
        result.elapsed_seconds,
    )
    print(f"\n✓ reel written to {result.reel_path}")
    print("✓ grading artifacts in ai_grading/")
    if result.report is not None:
        print(f"✓ PydanticAI report: {result.report.slide_count} slides via tool agent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
