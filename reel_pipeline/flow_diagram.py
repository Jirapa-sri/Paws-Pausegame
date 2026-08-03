"""Generate ai_grading/agent_flow.png flowchart."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

logger = logging.getLogger(__name__)

STEPS = [
    "Project Proposal",
    "Proposal Parser",
    "Slide Planner",
    "HTML Generator",
    "Critique Agent",
    "Revision Agent",
    "TTS Generator",
    "Renderer",
    "Video Composer",
    "Outputs",
]


def generate_agent_flow(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(8.5, 14), dpi=160)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 22)
    ax.axis("off")
    fig.patch.set_facecolor("#F7F4EE")
    ax.set_facecolor("#F7F4EE")

    ax.text(
        5,
        21.2,
        "Paws & Pause Reel Agent Flow",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#244C46",
    )

    box_w, box_h = 6.2, 1.15
    x = (10 - box_w) / 2
    top = 19.6
    gap = 1.7

    for i, label in enumerate(STEPS):
        y = top - i * gap
        color = "#3E7C74" if i in (0, len(STEPS) - 1) else "#FFFFFF"
        edge = "#244C46"
        text_color = "#F5E9D3" if i in (0, len(STEPS) - 1) else "#3A2C22"
        box = FancyBboxPatch(
            (x, y - box_h / 2),
            box_w,
            box_h,
            boxstyle="round,pad=0.02,rounding_size=0.25",
            linewidth=1.6,
            edgecolor=edge,
            facecolor=color,
        )
        ax.add_patch(box)
        ax.text(
            5,
            y,
            label,
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            color=text_color,
        )
        if i < len(STEPS) - 1:
            y_next = top - (i + 1) * gap
            ax.annotate(
                "",
                xy=(5, y_next + box_h / 2 + 0.05),
                xytext=(5, y - box_h / 2 - 0.05),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color="#D98F2B",
                    lw=2.0,
                    mutation_scale=16,
                ),
            )

    ax.text(
        5,
        0.55,
        "Parallel asyncio stages: HTML · Critique · TTS · Render",
        ha="center",
        va="center",
        fontsize=9,
        color="#6E5C49",
    )

    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("Wrote agent flow diagram to %s", out_path)
    return out_path
