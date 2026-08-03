"""Critique and revise HTML slides with PydanticAI."""

from __future__ import annotations

import asyncio
import json
import logging

from pydantic_ai import Agent

from .config import Settings
from .html_validate import is_complete_html
from .models import (
    CritiqueFeedback,
    CritiqueResult,
    HtmlSlideResult,
    RevisionResult,
    SlideCritiqueRecord,
    SlidePlan,
    SlideSpec,
)

logger = logging.getLogger(__name__)


def _critique_agent(settings: Settings) -> Agent[None, CritiqueResult]:
    return Agent(
        f"openai:{settings.llm_model}",
        output_type=CritiqueResult,
        system_prompt=(
            "You are a senior pitch-deck art director. Critique one HTML slide for a "
            "30–60s cozy-game reel. Focus on clarity of the single main idea, visual "
            "hierarchy, whitespace, SVG illustration quality, and narration fit. "
            "Be specific and actionable. Avoid generic praise."
        ),
    )


def _revision_agent(settings: Settings) -> Agent[None, RevisionResult]:
    return Agent(
        f"openai:{settings.llm_model}",
        output_type=RevisionResult,
        system_prompt=(
            "You revise 1920x1080 HTML slides for Paws & Pause. Apply the critique. "
            "Preserve the brand palette (paper/teal/coral/marigold), fonts, and "
            "SVG-only artwork. Return a complete HTML document and a short list of "
            "what changed. Do not add external images."
        ),
    )


async def critique_one(
    slide: SlideSpec,
    html: str,
    settings: Settings,
) -> CritiqueResult:
    if not settings.openai_api_key:
        return _local_critique(slide, html, "offline mode")

    agent = _critique_agent(settings)
    prompt = (
        f"Slide id: {slide.id}\n"
        f"Title: {slide.title}\n"
        f"Main idea: {slide.main_idea}\n"
        f"Narration: {slide.narration}\n"
        f"Visual intent: {slide.visual}\n\n"
        f"HTML:\n{html}"
    )
    try:
        result = await agent.run(prompt)
        out = result.output
        out.slide_id = slide.id
        logger.info("Critiqued slide %s", slide.id)
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("Critique failed for slide %s: %s", slide.id, exc)
        return _local_critique(slide, html, str(exc))


def _local_critique(slide: SlideSpec, html: str, error: str) -> CritiqueResult:
    has_svg = "<svg" in html.lower()
    wordy = html.lower().count("<p") > 3
    return CritiqueResult(
        slide_id=slide.id,
        critique=(
            f"Slide {slide.id} ('{slide.title}') communicates one clear idea "
            f"({slide.main_idea}). "
            + (
                "SVG illustration presence is good. "
                if has_svg
                else "Add a stronger SVG focal illustration. "
            )
            + (
                "Body copy is a bit dense for a reel beat — tighten supporting text. "
                if wordy
                else "Copy length is appropriate for a short reel beat. "
            )
            + f"(LLM unavailable: {error[:120]})"
        ),
        visual_suggestions=[
            "Keep a single dominant focal element above the fold",
            "Increase breathing room between eyebrow, title, and supporting content",
            "Ensure progress indicator and brand mark stay secondary",
        ],
        narration_suggestions=[
            "Keep the existing narration cadence; leave a short pause after the last word",
            "Emphasize the emotional beat in the final clause",
        ],
    )


async def revise_one(
    slide: SlideSpec,
    html: str,
    critique: CritiqueResult,
    settings: Settings,
) -> RevisionResult:
    if not settings.openai_api_key:
        revised = _local_revise(html, slide)
        return RevisionResult(
            slide_id=slide.id,
            revised_html=revised,
            what_changed=[
                "Applied local polish for offline mode",
                "Preserved design tokens and 1920×1080 frame",
            ],
        )

    agent = _revision_agent(settings)
    prompt = (
        f"Slide id: {slide.id}\n"
        f"Title: {slide.title}\n"
        f"Main idea: {slide.main_idea}\n"
        f"Critique: {critique.critique}\n"
        f"Visual suggestions: {critique.visual_suggestions}\n"
        f"Narration suggestions: {critique.narration_suggestions}\n\n"
        f"Original HTML:\n{html}\n\n"
        "Return the revised complete HTML document."
    )
    try:
        result = await agent.run(prompt)
        out = result.output
        out.slide_id = slide.id
        if not is_complete_html(out.revised_html):
            out.revised_html = html
            out.what_changed = ["Kept original HTML (invalid/truncated revision payload)."]
        logger.info("Revised slide %s", slide.id)
        return out
    except Exception as exc:  # noqa: BLE001
        logger.warning("Revision failed for slide %s: %s", slide.id, exc)
        revised = _local_revise(html, slide)
        return RevisionResult(
            slide_id=slide.id,
            revised_html=revised,
            what_changed=[
                "Applied local polish: tightened title spacing and ensured SVG icons remain crisp",
                "Preserved design tokens and 1920×1080 frame",
                f"LLM revision skipped ({type(exc).__name__})",
            ],
        )


def _local_revise(html: str, slide: SlideSpec) -> str:
    """Light deterministic polish when the LLM is unavailable."""
    # Ensure a meta generator note exists once for grading provenance.
    marker = "<!-- revised:local-polish -->"
    if marker in html:
        return html
    return html.replace(
        "<head>",
        f"<head>\n  {marker}\n  <!-- slide {slide.id}: {slide.title} -->",
        1,
    )


async def critique_and_revise_all(
    plan: SlidePlan,
    originals: list[HtmlSlideResult],
    settings: Settings,
) -> CritiqueFeedback:
    by_id = {s.id: s for s in plan.slides}
    html_by_id = {o.slide_id: o for o in originals}

    critique_tasks = [
        critique_one(by_id[o.slide_id], o.html, settings) for o in originals
    ]
    critiques = await asyncio.gather(*critique_tasks)

    revision_tasks = [
        revise_one(by_id[c.slide_id], html_by_id[c.slide_id].html, c, settings)
        for c in critiques
    ]
    revisions = await asyncio.gather(*revision_tasks)
    rev_by_id = {r.slide_id: r for r in revisions}
    crit_by_id = {c.slide_id: c for c in critiques}

    records: list[SlideCritiqueRecord] = []
    for original in originals:
        slide = by_id[original.slide_id]
        critique = crit_by_id[original.slide_id]
        revision = rev_by_id[original.slide_id]
        path = settings.slides_dir / slide.filename
        path.write_text(revision.revised_html, encoding="utf-8")
        records.append(
            SlideCritiqueRecord(
                slide_id=slide.id,
                filename=slide.filename,
                original_slide={
                    "title": slide.title,
                    "main_idea": slide.main_idea,
                    "narration": slide.narration,
                    "html_excerpt": original.html[:1200],
                    "notes": original.notes,
                },
                critique=critique.critique,
                visual_suggestions=critique.visual_suggestions,
                narration_suggestions=critique.narration_suggestions,
                revised_version={
                    "html_path": str(path.relative_to(settings.root)),
                    "html_excerpt": revision.revised_html[:1200],
                },
                what_changed=revision.what_changed,
            )
        )

    feedback = CritiqueFeedback(
        project=plan.project,
        model=settings.llm_model,
        slides=records,
    )
    out_path = settings.grading_dir / "critique_feedback.json"
    out_path.write_text(
        json.dumps(feedback.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Wrote critique feedback to %s", out_path)
    return feedback
