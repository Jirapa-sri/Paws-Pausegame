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


def _probe_duration(path: Path) -> float:
    probe = shutil.which("ffprobe")
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
        str(path),
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
                _probe_duration(audio),
                float(slide.duration_seconds),
                3.0,
            )
            # Slight hold so the last word lands before the crossfade
            duration += 0.35
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
                "-ar",
                "44100",
                "-ac",
                "2",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(settings.fps),
                "-t",
                f"{duration:.3f}",
                "-vf",
                f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=decrease,"
                f"pad={settings.width}:{settings.height}:(ow-iw)/2:(oh-ih)/2,"
                f"setsar=1",
                "-shortest",
                str(segment),
            ]
            logger.info("Encoding segment for slide %s (%.2fs)", slide.id, duration)
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error("Segment encode failed: %s", result.stderr[-2000:])
                raise RuntimeError(f"ffmpeg failed encoding slide {slide.id}")
            segment_paths.append(segment)

        if len(segment_paths) == 1:
            shutil.copy(segment_paths[0], settings.reel_path)
        else:
            _concat_with_xfade(ffmpeg, segment_paths, settings)

        out_copy = settings.output_dir / "reel.mp4"
        shutil.copy(settings.reel_path, out_copy)
        logger.info("Wrote reel to %s", settings.reel_path)
        return settings.reel_path


def _concat_with_xfade(
    ffmpeg: str,
    segments: list[Path],
    settings: Settings,
) -> None:
    """Concatenate segments with video xfade + audio acrossfade between each pair."""
    durations = [_probe_duration(p) for p in segments]
    if any(d <= 0 for d in durations):
        raise RuntimeError("Could not probe segment durations for xfade")

    td = min(settings.transition_seconds, min(durations) / 3)
    if td < 0.1:
        td = 0.1

    # offset_n = sum(durations[:n+1]) - (n+1)*td
    offsets: list[float] = []
    cumulative = 0.0
    for i in range(len(segments) - 1):
        cumulative += durations[i]
        offsets.append(cumulative - (i + 1) * td)

    n = len(segments)
    inputs: list[str] = []
    for p in segments:
        inputs.extend(["-i", str(p)])

    # Build chained xfade / acrossfade filtergraph
    v_label = "[0:v]"
    a_label = "[0:a]"
    filters: list[str] = []
    for i in range(1, n):
        next_v = f"[{i}:v]"
        next_a = f"[{i}:a]"
        out_v = f"[v{i}]" if i < n - 1 else "[vout]"
        out_a = f"[a{i}]" if i < n - 1 else "[aout]"
        filters.append(
            f"{v_label}{next_v}xfade=transition=fade:duration={td:.3f}:offset={offsets[i - 1]:.3f}{out_v}"
        )
        filters.append(f"{a_label}{next_a}acrossfade=d={td:.3f}:c1=tri:c2=tri{out_a}")
        v_label = out_v
        a_label = out_a

    # Soft bookends on the final stream
    total = sum(durations) - (n - 1) * td
    fade_out_start = max(0.0, total - td)
    filters.append(
        f"[vout]fade=t=in:st=0:d={td:.3f},fade=t=out:st={fade_out_start:.3f}:d={td:.3f}[vfinal]"
    )
    filters.append(
        f"[aout]afade=t=in:st=0:d={td:.3f},afade=t=out:st={fade_out_start:.3f}:d={td:.3f}[afinal]"
    )

    filter_complex = ";".join(filters)
    cmd = [
        ffmpeg,
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vfinal]",
        "-map",
        "[afinal]",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(settings.fps),
        "-movflags",
        "+faststart",
        str(settings.reel_path),
    ]
    logger.info(
        "Crossfading %d segments (td=%.2fs) into reel.mp4 — expected ~%.1fs",
        n,
        td,
        total,
    )
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.error("ffmpeg xfade failed: %s", result.stderr[-3000:])
        raise RuntimeError("ffmpeg failed while crossfading reel segments")
