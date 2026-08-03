"""PydanticAI reel agent with explicit tools and structured schemas."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from .config import Settings
from .critique import critique_and_revise_all
from .flow_diagram import generate_agent_flow
from .html_slides import generate_all_slides
from .io_utils import read_proposal, read_slide_plan
from .models import CritiqueFeedback, HtmlSlideResult, SlidePlan
from .renderer import render_all_slides
from .tts import generate_all_audio
from .video import compose_reel

logger = logging.getLogger(__name__)


class PipelineReport(BaseModel):
    """Final structured output from the reel agent."""

    project: str
    slide_count: int
    html_files: list[str]
    audio_files: list[str]
    render_files: list[str]
    critique_path: str
    flow_diagram_path: str
    reel_path: str
    notes: list[str] = Field(default_factory=list)


@dataclass
class AgentDeps:
    settings: Settings
    proposal: str = ""
    plan: SlidePlan | None = None
    originals: list[HtmlSlideResult] = field(default_factory=list)
    feedback: CritiqueFeedback | None = None
    audio_paths: list[Path] = field(default_factory=list)
    render_paths: list[Path] = field(default_factory=list)
    reel_path: Path | None = None
    flow_path: Path | None = None


def build_reel_agent(settings: Settings) -> Agent[AgentDeps, PipelineReport]:
    """Create the top-level PydanticAI agent with tools + output schema."""

    agent: Agent[AgentDeps, PipelineReport] = Agent(
        f"openai:{settings.llm_model}",
        deps_type=AgentDeps,
        output_type=PipelineReport,
        system_prompt=(
            "You are the Paws & Pause reel production agent. "
            "Use the available tools in order to build a 30–60 second pitch reel: "
            "1) load_proposal, 2) load_slide_plan, 3) generate_html_slides, "
            "4) critique_and_revise_slides, 5) synthesize_narration, "
            "6) render_slide_images, 7) compose_video_reel, 8) export_agent_flow. "
            "Then return a PipelineReport summarizing all outputs. "
            "Do not invent file paths; use tool results only."
        ),
    )

    @agent.tool
    async def load_proposal(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Read project_proposal.md into agent memory."""
        text = read_proposal(ctx.deps.settings.proposal_path)
        ctx.deps.proposal = text
        return {
            "path": str(ctx.deps.settings.proposal_path),
            "chars": len(text),
            "excerpt": text[:500],
        }

    @agent.tool
    async def load_slide_plan(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Read ai_grading/slide_plan.json (4–6 slides with description + narration)."""
        plan = read_slide_plan(ctx.deps.settings.slide_plan_path)
        ctx.deps.plan = plan
        return {
            "path": str(ctx.deps.settings.slide_plan_path),
            "slide_count": len(plan.slides),
            "slides": [
                {
                    "id": s.id,
                    "title": s.title,
                    "description": s.description or s.main_idea,
                    "narration": s.narration,
                    "duration_seconds": s.duration_seconds,
                }
                for s in plan.slides
            ],
        }

    @agent.tool
    async def generate_html_slides(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Generate/polish one HTML file per slide in parallel (HTML/CSS/SVG only)."""
        if ctx.deps.plan is None:
            raise ValueError("Call load_slide_plan first")
        originals = await generate_all_slides(
            ctx.deps.plan, ctx.deps.settings, ctx.deps.proposal
        )
        ctx.deps.originals = originals
        return {
            "count": len(originals),
            "files": [o.filename for o in originals],
            "notes": [o.notes for o in originals],
        }

    @agent.tool
    async def critique_and_revise_slides(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Critique each slide and write revised HTML + critique_feedback.json."""
        if ctx.deps.plan is None or not ctx.deps.originals:
            raise ValueError("Call generate_html_slides first")
        feedback = await critique_and_revise_all(
            ctx.deps.plan, ctx.deps.originals, ctx.deps.settings
        )
        ctx.deps.feedback = feedback
        return {
            "path": str(ctx.deps.settings.grading_dir / "critique_feedback.json"),
            "slide_count": len(feedback.slides),
            "model": feedback.model,
        }

    @agent.tool
    async def synthesize_narration(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Generate per-slide narration audio with OpenAI TTS (tts-1-hd)."""
        if ctx.deps.plan is None:
            raise ValueError("Call load_slide_plan first")
        paths = await generate_all_audio(ctx.deps.plan, ctx.deps.settings)
        ctx.deps.audio_paths = paths
        return {"count": len(paths), "files": [p.name for p in paths]}

    @agent.tool
    async def render_slide_images(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Render revised HTML slides to 1920x1080 PNG images in parallel."""
        if ctx.deps.plan is None:
            raise ValueError("Call load_slide_plan first")
        paths = await render_all_slides(ctx.deps.plan, ctx.deps.settings)
        ctx.deps.render_paths = paths
        return {"count": len(paths), "files": [p.name for p in paths]}

    @agent.tool
    async def compose_video_reel(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Stitch PNG slides + narration into reel.mp4 with FFmpeg."""
        if ctx.deps.plan is None:
            raise ValueError("Call load_slide_plan first")
        reel = compose_reel(ctx.deps.plan, ctx.deps.settings)
        ctx.deps.reel_path = reel
        return {"reel_path": str(reel)}

    @agent.tool
    async def export_agent_flow(ctx: RunContext[AgentDeps]) -> dict[str, Any]:
        """Export ai_grading/agent_flow.png flowchart."""
        path = generate_agent_flow(ctx.deps.settings.grading_dir / "agent_flow.png")
        ctx.deps.flow_path = path
        return {"path": str(path)}

    return agent


async def run_via_agent(settings: Settings) -> PipelineReport:
    """Run the full production flow through the PydanticAI tool-calling agent."""
    settings.ensure_dirs()
    settings.require_api_key()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY required to run the PydanticAI tool agent")

    deps = AgentDeps(settings=settings)
    agent = build_reel_agent(settings)
    result = await agent.run(
        "Produce the complete Paws & Pause pitch reel and grading artifacts. "
        "Call every tool in the documented order, then return PipelineReport.",
        deps=deps,
    )
    report = result.output
    logger.info("PydanticAI agent finished: %s", report.model_dump())
    return report
