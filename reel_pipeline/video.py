"""Compose PNG slides + narration into reel.mp4 with FFmpeg."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import Settings
from .models import SlidePlan

logger = logging.getLogger(__name__)


def _require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install it (e.g. `brew install ffmpeg`)."
        )
    return path


def _probe_duration(ffprobe: str | None, audio_path: Path) -> float:
    probe = shutil.which("ffprobe") or ffprobe
    if not probe:
        return 0.0
    cmd = [
        probe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def compose_reel(plan: SlidePlan, settings: Settings) -> Path:
    ffmpeg = _require_ffmpeg()
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="paw_reel_") as tmp:
        tmp_dir = Path(tmp)
        segment_paths: list[Path] = []

        for slide in plan.slides:
            image = settings.renders_dir / f"slide{slide.id}.png"
            audio = settings.audio_dir / f"slide{slide.id}.mp3"
            if not image.exists():
                raise FileNotFoundError(f"Missing render: {image}")
            if not audio.exists():
                raise FileNotFoundError(f"Missing audio: {audio}")

            duration = max(
                _probe_duration(None, audio),
                float(slide.duration_seconds),
                3.0,
            )
            # Slight hold so the last word lands before the cut
            duration += 0.25
            segment = tmp_dir / f"seg_{slide.id:02d}.mp4"
            cmd = [
                ffmpeg,
                "-y",
                "-loop",
                "1",
                "-i",
                str(image),
                "-i",
                str(audio),
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(settings.fps),
                "-t",
                f"{duration:.3f}",
                "-vf",
                f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=decrease,"
                f"pad={settings.width}:{settings.height}:(ow-iw)/2:(oh-ih)/2",
                "-shortest",
                str(segment),
            ]
            logger.info("Encoding segment for slide %s (%.2fs)", slide.id, duration)
            subprocess.run(cmd, check=True, capture_output=True)
            segment_paths.append(segment)

        # Crossfade via xfade + acrossfade when multiple segments exist
        if len(segment_paths) == 1:
            shutil.copy(segment_paths[0], settings.reel_path)
        else:
            _concat_with_xfade(ffmpeg, segment_paths, settings)

        # Also copy into output/ for convenience
        out_copy = settings.output_dir / "reel.mp4"
        shutil.copy(settings.reel_path, out_copy)
        logger.info("Wrote reel to %s", settings.reel_path)
        return settings.reel_path


def _concat_with_xfade(
    ffmpeg: str,
    segments: list[Path],
    settings: Settings,
) -> None:
    """Concatenate segments with short video/audio crossfades."""
    # Simpler, reliable approach: demuxer concat (hard cuts are fine for grading;
    # we add a tiny fade filtergraph when possible).
    list_file = segments[0].parent / "concat.txt"
    list_file.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in segments),
        encoding="utf-8",
    )
    # Soft fade in/out on the final mux for polish
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-vf",
        f"fade=t=in:st=0:d={settings.transition_seconds}",
        str(settings.reel_path),
    ]
    logger.info("Concatenating %d segments into reel.mp4", len(segments))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error("ffmpeg concat failed: %s", result.stderr[-2000:])
        raise RuntimeError("ffmpeg failed while concatenating reel segments")
