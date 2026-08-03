"""HTML validation helpers for LLM slide outputs."""

from __future__ import annotations


def is_complete_html(html: str) -> bool:
    """Reject truncated or incomplete LLM HTML documents."""
    text = (html or "").strip().lower()
    return (
        text.startswith("<!doctype html")
        and "</html>" in text
        and "<body" in text
        and len(html) > 800
    )
