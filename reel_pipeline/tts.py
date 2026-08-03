"""OpenAI TTS narration generation with local fallback."""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from openai import APIError, AsyncOpenAI, AuthenticationError

from .config import Settings
from .models import SlidePlan, SlideSpec

logger = logging.getLogger(__name__)


async def _openai_tts(
    client: AsyncOpenAI,
    slide: SlideSpec,
    settings: Settings,
    out_path: Path,
) -> Path:
    async with client.audio.speech.with_streaming_response.create(
        model=settings.tts_model,
        voice=settings.tts_voice,
        input=slide.narration,
        response_format="mp3",
    ) as response:
        await response.stream_to_file(out_path)
    return out_path


def _local_tts(slide: SlideSpec, out_path: Path) -> Path:
    """macOS `say` → AIFF → mp3 via ffmpeg (offline fallback)."""
    ffmpeg = shutil.which("ffmpeg")
    say = shutil.which("say")
    if not ffmpeg or not say:
        raise RuntimeError("Local TTS requires both `say` and `ffmpeg` on PATH")

    with tempfile.TemporaryDirectory() as tmp:
        aiff = Path(tmp) / "voice.aiff"
        subprocess.run(
            [say, "-v", "Samantha", "-o", str(aiff), slide.narration],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-i",
                str(aiff),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(out_path),
            ],
            check=True,
            capture_output=True,
        )
    return out_path


async def synthesize_one(
    client: AsyncOpenAI | None,
    slide: SlideSpec,
    settings: Settings,
) -> Path:
    out_path = settings.audio_dir / f"slide{slide.id}.mp3"
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Generating TTS for slide %s (%s)", slide.id, settings.tts_model)

    if client is not None:
        try:
            await _openai_tts(client, slide, settings, out_path)
            logger.info("Wrote OpenAI audio %s", out_path)
            return out_path
        except (AuthenticationError, APIError, Exception) as exc:  # noqa: BLE001
            logger.warning(
                "OpenAI TTS failed for slide %s (%s); using local fallback",
                slide.id,
                exc,
            )

    await asyncio.to_thread(_local_tts, slide, out_path)
    logger.info("Wrote local fallback audio %s", out_path)
    return out_path


async def generate_all_audio(plan: SlidePlan, settings: Settings) -> list[Path]:
    client: AsyncOpenAI | None = None
    if settings.openai_api_key:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
    else:
        logger.warning("OPENAI_API_KEY missing — using local TTS fallback")

    tasks = [synthesize_one(client, slide, settings) for slide in plan.slides]
    paths = await asyncio.gather(*tasks)
    return list(paths)
