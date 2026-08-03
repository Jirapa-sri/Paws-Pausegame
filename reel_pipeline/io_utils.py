"""Load proposal and slide plan artifacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import SlidePlan

logger = logging.getLogger(__name__)


def read_proposal(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Proposal not found: {path}")
    text = path.read_text(encoding="utf-8").strip()
    logger.info("Loaded proposal (%d chars) from %s", len(text), path)
    return text


def read_slide_plan(path: Path) -> SlidePlan:
    if not path.exists():
        raise FileNotFoundError(f"Slide plan not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    plan = SlidePlan.model_validate(data)
    logger.info("Loaded slide plan with %d slides from %s", len(plan.slides), path)
    return plan
