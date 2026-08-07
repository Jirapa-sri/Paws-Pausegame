"""HTML slide generation — premium templates with optional LLM polish."""

from __future__ import annotations

import asyncio
import logging
from html import escape
from pathlib import Path

from pydantic_ai import Agent

from .config import Settings
from .design import icon_svg, town_illustration, wrap_slide
from .html_validate import is_complete_html
from .models import DesignSystem, HtmlSlideResult, SlidePlan, SlideSpec

logger = logging.getLogger(__name__)


def _bullets_html(bullets: list[str]) -> str:
    return "".join(f'<span class="badge">{escape(b)}</span>' for b in bullets)


def render_title(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    subtitle = (
        "A short, warm pause after work or school — earn, adopt, and care for a puppy."
    )
    body = f"""
      <div class="eyebrow">{escape(slide.eyebrow)}</div>
      <h1>{escape(slide.title)}</h1>
      <p class="subtitle">{escape(subtitle)}</p>
      <div class="badge-row">{_bullets_html(slide.bullets)}</div>
    """
    return wrap_slide(slide=slide, ds=ds, body=body, index=index, total=total)


def render_illustration(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    items = "".join(
        f"<li style='font-size:28px;color:var(--ink-soft);margin:10px 0;list-style:none;"
        f"padding-left:28px;position:relative;'>"
        f"<span style='position:absolute;left:0;top:0.45em;width:10px;height:10px;"
        f"border-radius:50%;background:var(--coral);'></span>"
        f"{escape(b)}</li>"
        for b in slide.bullets
    )
    body = f"""
      <div class="split">
        <div>
          <div class="eyebrow">{escape(slide.eyebrow)}</div>
          <h2>{escape(slide.title)}</h2>
          <p class="lede">{escape(slide.main_idea)}</p>
          <ul style="margin:28px 0 0;padding:0;">{items}</ul>
        </div>
        {town_illustration()}
      </div>
    """
    return wrap_slide(slide=slide, ds=ds, body=body, index=index, total=total)


def render_loop(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    steps = "".join(
        f'<div class="loop-step"><div class="loop-num">{i}</div><span>{escape(b)}</span></div>'
        for i, b in enumerate(slide.bullets, start=1)
    )
    body = f"""
      <div class="eyebrow">{escape(slide.eyebrow)}</div>
      <h2>{escape(slide.title)}</h2>
      <p class="lede" style="max-width:40ch;">{escape(slide.main_idea)}</p>
      <div class="loop-wrap">{steps}</div>
    """
    return wrap_slide(slide=slide, ds=ds, body=body, index=index, total=total)


def render_features(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    icons = ["shield", "heart", "paw"]
    titles = ["AI photo match", "Mood & care", "Look together"]
    cards = []
    for i, bullet in enumerate(slide.bullets):
        title = titles[i] if i < len(titles) else f"Beat {i + 1}"
        cards.append(
            f'<div class="card">{icon_svg(icons[i % len(icons)])}'
            f"<h3>{escape(title)}</h3>"
            f"<p>{escape(bullet)}</p></div>"
        )
    body = f"""
      <div class="eyebrow">{escape(slide.eyebrow)}</div>
      <h2>{escape(slide.title)}</h2>
      <p class="lede" style="max-width:42ch;">{escape(slide.main_idea)}</p>
      <div class="card-grid">{''.join(cards)}</div>
    """
    return wrap_slide(slide=slide, ds=ds, body=body, index=index, total=total)


def render_feature_grid(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    icons = ["clock", "heart", "home", "paw"]
    titles = ["Café", "Fishing", "Go-Kart", "Arcade"]
    cards = []
    for i, bullet in enumerate(slide.bullets[:4]):
        title = titles[i] if i < len(titles) else f"Mode {i + 1}"
        cards.append(
            f'<div class="card">{icon_svg(icons[i % len(icons)])}'
            f"<h3>{escape(title)}</h3>"
            f"<p>{escape(bullet)}</p></div>"
        )
    grid = (
        '<div class="card-grid" style="grid-template-columns:repeat(4,1fr);">'
        + "".join(cards)
        + "</div>"
    )
    body = f"""
      <div class="eyebrow">{escape(slide.eyebrow)}</div>
      <h2>{escape(slide.title)}</h2>
      <p class="lede" style="max-width:52ch;">{escape(slide.main_idea)}</p>
      {grid}
      <div class="badge-row" style="margin-top:28px;">
        <span class="badge">Examples — more coming</span>
        <span class="badge">Island news of the day</span>
        <span class="badge">AI world-news digest</span>
        <span class="badge">Fortune ↔ weather</span>
      </div>
    """
    return wrap_slide(slide=slide, ds=ds, body=body, index=index, total=total)


def render_scope(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    checks = "".join(
        f'<div class="check-item"><div class="check">{icon_svg("check")}</div>'
        f"<span>{escape(b)}</span></div>"
        for b in slide.bullets
    )
    body = f"""
      <div class="eyebrow">{escape(slide.eyebrow)}</div>
      <h2>{escape(slide.title)}</h2>
      <p class="lede" style="max-width:40ch;">{escape(slide.main_idea)}</p>
      <div class="check-list">{checks}</div>
    """
    return wrap_slide(slide=slide, ds=ds, body=body, index=index, total=total)


def render_closing(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    lede = "A warm, low-pressure place to spend a little time — for everyone."
    body = f"""
      <div style="display:flex;justify-content:center;margin-bottom:18px;opacity:0.9;">
        <svg viewBox="0 0 24 24" width="72" height="72" fill="#D9705C">
          <circle cx="12" cy="15" r="5"/><circle cx="5.5" cy="8.5" r="2.2"/>
          <circle cx="18.5" cy="8.5" r="2.2"/><circle cx="8.3" cy="4.6" r="2"/>
          <circle cx="15.7" cy="4.6" r="2"/>
        </svg>
      </div>
      <div class="eyebrow" style="justify-content:center;">{escape(slide.eyebrow)}</div>
      <h2>{escape(slide.title)}</h2>
      <p class="lede">{escape(lede)}</p>
      <div class="badge-row" style="justify-content:center;">{_bullets_html(slide.bullets)}</div>
    """
    return wrap_slide(
        slide=slide, ds=ds, body=body, index=index, total=total, closer=True
    )


LAYOUT_RENDERERS = {
    "title_hero": render_title,
    "illustration_split": render_illustration,
    "loop_grid": render_loop,
    "feature_cards": render_features,
    "feature_grid": render_feature_grid,
    "scope_checklist": render_scope,
    "closing_mark": render_closing,
}


def render_slide_html(slide: SlideSpec, ds: DesignSystem, index: int, total: int) -> str:
    renderer = LAYOUT_RENDERERS.get(slide.layout, render_features)
    return renderer(slide, ds, index, total)


def _html_agent(settings: Settings) -> Agent[None, HtmlSlideResult]:
    return Agent(
        f"openai:{settings.llm_model}",
        output_type=HtmlSlideResult,
        system_prompt=(
            "You refine premium 1920x1080 HTML pitch slides for a cozy game called "
            "Paws & Pause. Keep the existing design tokens, Nunito/Libre Baskerville "
            "typography, teal/coral/marigold palette, and SVG-only illustrations. "
            "Never use stock photos or AI image URLs. Return a complete HTML document. "
            "Improve spacing, hierarchy, and visual polish while preserving the main idea."
        ),
    )


async def generate_one_slide(
    slide: SlideSpec,
    plan: SlidePlan,
    settings: Settings,
    proposal_excerpt: str,
) -> HtmlSlideResult:
    index = slide.id
    total = len(plan.slides)
    base_html = render_slide_html(slide, plan.design_system, index, total)

    if not settings.openai_api_key:
        return HtmlSlideResult(
            slide_id=slide.id,
            filename=slide.filename,
            html=base_html,
            notes="Template HTML (no OpenAI key / offline mode).",
        )

    try:
        agent = _html_agent(settings)
        prompt = (
            f"Project: {plan.project}\n"
            f"Proposal excerpt:\n{proposal_excerpt[:1800]}\n\n"
            f"Slide spec JSON:\n{slide.model_dump_json()}\n\n"
            f"Current HTML draft:\n{base_html}\n\n"
            "Polish the HTML if needed. Keep width/height 1920x1080. "
            "If already strong, return it largely unchanged."
        )
        result = await agent.run(prompt)
        polished = result.output
        polished.slide_id = slide.id
        polished.filename = slide.filename
        if not is_complete_html(polished.html):
            polished.html = base_html
            polished.notes = "Fell back to template HTML (invalid/truncated LLM HTML)."
        logger.info("Generated HTML for slide %s", slide.id)
        return polished
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM HTML polish failed for slide %s: %s", slide.id, exc)
        return HtmlSlideResult(
            slide_id=slide.id,
            filename=slide.filename,
            html=base_html,
            notes=f"Template fallback after LLM error: {exc}",
        )


async def generate_all_slides(
    plan: SlidePlan,
    settings: Settings,
    proposal: str,
) -> list[HtmlSlideResult]:
    settings.slides_dir.mkdir(parents=True, exist_ok=True)
    tasks = [
        generate_one_slide(slide, plan, settings, proposal) for slide in plan.slides
    ]
    results = await asyncio.gather(*tasks)
    for item in results:
        path = settings.slides_dir / item.filename
        path.write_text(item.html, encoding="utf-8")
        logger.info("Wrote %s", path)
    return list(results)
