"""Pydantic models for slide planning, critique, and grading artifacts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DesignSystem(BaseModel):
    paper: str = "#F5E9D3"
    paper_2: str = "#EEDCB8"
    ink: str = "#3A2C22"
    teal: str = "#3E7C74"
    teal_deep: str = "#244C46"
    marigold: str = "#D98F2B"
    coral: str = "#D9705C"
    display_font: str = "Nunito"
    body_font: str = "Libre Baskerville"


class SlideSpec(BaseModel):
    id: int
    filename: str
    title: str
    eyebrow: str
    layout: str
    description: str = ""
    main_idea: str
    bullets: list[str] = Field(default_factory=list)
    visual: str = ""
    narration: str
    duration_seconds: float = 8.0


class SlidePlan(BaseModel):
    project: str
    format: str = "16:9 reel"
    resolution: dict[str, int] = Field(
        default_factory=lambda: {"width": 1920, "height": 1080}
    )
    target_duration_seconds: float = 48
    fps: int = 30
    design_system: DesignSystem = Field(default_factory=DesignSystem)
    slides: list[SlideSpec]


class HtmlSlideResult(BaseModel):
    slide_id: int
    filename: str
    html: str
    notes: str = ""


class CritiqueResult(BaseModel):
    slide_id: int
    critique: str
    visual_suggestions: list[str] = Field(default_factory=list)
    narration_suggestions: list[str] = Field(default_factory=list)


class RevisionResult(BaseModel):
    slide_id: int
    revised_html: str
    what_changed: list[str] = Field(default_factory=list)


class SlideCritiqueRecord(BaseModel):
    slide_id: int
    filename: str
    original_slide: dict[str, Any]
    critique: str
    visual_suggestions: list[str]
    narration_suggestions: list[str]
    revised_version: dict[str, Any]
    what_changed: list[str]


class CritiqueFeedback(BaseModel):
    project: str
    model: str
    slides: list[SlideCritiqueRecord]
