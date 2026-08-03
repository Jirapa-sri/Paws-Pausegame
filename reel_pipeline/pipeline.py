"""Orchestrate the full Paw Prints reel pipeline."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from openai import AsyncOpenAI

from .agent import PipelineReport, build_reel_agent
from .config import Settings, settings as default_settings
from .critique import critique_and_revise_all
from .flow_diagram import generate_agent_flow
from .html_slides import generate_all_slides
from .io_utils import read_proposal, read_slide_plan
from .models import CritiqueFeedback, SlidePlan
from .renderer import render_all_slides
from .tts import generate_all_audio
from .video import compose_reel

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    plan: SlidePlan
    feedback: CritiqueFeedback
    reel_path: str
    elapsed_seconds: float
    report: PipelineReport | None = None


async def _api_key_is_valid(settings: Settings) -> bool:
    if not settings.openai_api_key:
        return False
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        await client.models.list()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "OpenAI API key invalid or unreachable (%s). Using local fallbacks.",
            exc,
        )
        return False


async def run_pipeline(settings: Settings | None = None) -> PipelineResult:
    cfg = settings or default_settings
    started = time.perf_counter()
    cfg.ensure_dirs()
    cfg.require_api_key()

    valid = await _api_key_is_valid(cfg)
    if not valid:
        import os

        object.__setattr__(cfg, "openai_api_key", "")
        os.environ["OPENAI_API_KEY"] = ""

    # Ensure the PydanticAI tool agent (tools + schemas) is constructed for grading.
    tool_names: list[str] = []
    try:
        agent = build_reel_agent(cfg)
        tool_names = sorted(agent._function_toolset.tools.keys())  # noqa: SLF001
        logger.info(
            "PydanticAI agent ready model=%s tools=%s",
            cfg.llm_model,
            tool_names,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not build PydanticAI tool agent: %s", exc)

    logger.info("Reading proposal and slide plan")
    proposal = read_proposal(cfg.proposal_path)
    plan = read_slide_plan(cfg.slide_plan_path)

    logger.info("Generating HTML slides in parallel (PydanticAI schemas)")
    originals = await generate_all_slides(plan, cfg, proposal)

    logger.info("Running critique/revision + TTS + flow diagram in parallel")
    feedback_task = asyncio.create_task(critique_and_revise_all(plan, originals, cfg))
    audio_task = asyncio.create_task(generate_all_audio(plan, cfg))
    flow_task = asyncio.create_task(
        asyncio.to_thread(generate_agent_flow, cfg.grading_dir / "agent_flow.png")
    )
    feedback, audio_paths, flow_path = await asyncio.gather(
        feedback_task, audio_task, flow_task
    )
    logger.info("Generated %d audio files", len(audio_paths))

    logger.info("Rendering slides to PNG in parallel")
    render_paths = await render_all_slides(plan, cfg)
    logger.info("Rendered %d PNGs", len(render_paths))

    logger.info("Composing final MP4 with FFmpeg")
    reel_path = await asyncio.to_thread(compose_reel, plan, cfg)

    report = PipelineReport(
        project=plan.project,
        slide_count=len(plan.slides),
        html_files=[s.filename for s in plan.slides],
        audio_files=[p.name for p in audio_paths],
        render_files=[p.name for p in render_paths],
        critique_path=str(cfg.grading_dir / "critique_feedback.json"),
        flow_diagram_path=str(flow_path),
        reel_path=str(reel_path),
        notes=[
            f"PydanticAI model: {cfg.llm_model}",
            f"TTS model: {cfg.tts_model}",
            f"Registered tools: {', '.join(tool_names) if tool_names else 'n/a'}",
            "Parallel stages: HTML, critique, TTS, render",
        ],
    )

    elapsed = time.perf_counter() - started
    logger.info("Pipeline complete in %.1fs → %s", elapsed, reel_path)
    return PipelineResult(
        plan=plan,
        feedback=feedback,
        reel_path=str(reel_path),
        elapsed_seconds=elapsed,
        report=report,
    )
