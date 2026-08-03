"""Shared configuration for the Paw Prints reel agent."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment and project defaults."""

    root: Path = ROOT
    proposal_path: Path = field(default_factory=lambda: ROOT / "project_proposal.md")
    slide_plan_path: Path = field(
        default_factory=lambda: ROOT / "ai_grading" / "slide_plan.json"
    )
    slides_dir: Path = field(default_factory=lambda: ROOT / "slides")
    audio_dir: Path = field(default_factory=lambda: ROOT / "audio")
    renders_dir: Path = field(default_factory=lambda: ROOT / "renders")
    grading_dir: Path = field(default_factory=lambda: ROOT / "ai_grading")
    output_dir: Path = field(default_factory=lambda: ROOT / "output")
    reel_path: Path = field(default_factory=lambda: ROOT / "reel.mp4")

    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "").strip()
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_LLM_MODEL", "gpt-5.6-luna").strip()
    )
    tts_model: str = field(
        default_factory=lambda: os.getenv("OPENAI_TTS_MODEL", "tts-1-hd").strip()
    )
    tts_voice: str = field(
        default_factory=lambda: os.getenv("OPENAI_TTS_VOICE", "nova").strip()
    )

    width: int = 1920
    height: int = 1080
    fps: int = 30
    transition_seconds: float = 0.35

    def ensure_dirs(self) -> None:
        for path in (
            self.slides_dir,
            self.audio_dir,
            self.renders_dir,
            self.grading_dir,
            self.output_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def require_api_key(self) -> None:
        if not self.openai_api_key:
            logger.warning(
                "OPENAI_API_KEY is missing. LLM polish / OpenAI TTS will use local fallbacks."
            )


settings = Settings()
