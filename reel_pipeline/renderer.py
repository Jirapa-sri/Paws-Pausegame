"""Render HTML slides to PNG via Playwright."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from playwright.async_api import async_playwright

from .config import Settings
from .models import SlidePlan

logger = logging.getLogger(__name__)


async def render_one(
    html_path: Path,
    out_path: Path,
    settings: Settings,
) -> Path:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": settings.width, "height": settings.height},
            device_scale_factor=1,
        )
        await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        # Allow Google Fonts a moment to settle
        await page.wait_for_timeout(400)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out_path), full_page=False, type="png")
        await browser.close()
    logger.info("Rendered %s", out_path)
    return out_path


async def _render_with_shared_browser(
    browser,
    html_path: Path,
    out_path: Path,
    settings: Settings,
) -> Path:
    page = await browser.new_page(
        viewport={"width": settings.width, "height": settings.height},
        device_scale_factor=1,
    )
    try:
        await page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        await page.wait_for_timeout(400)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(out_path), full_page=False, type="png")
        logger.info("Rendered %s", out_path)
        return out_path
    finally:
        await page.close()


async def render_all_slides(plan: SlidePlan, settings: Settings) -> list[Path]:
    settings.renders_dir.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            tasks = []
            for slide in plan.slides:
                html_path = settings.slides_dir / slide.filename
                out_path = settings.renders_dir / f"slide{slide.id}.png"
                tasks.append(
                    _render_with_shared_browser(browser, html_path, out_path, settings)
                )
            paths = await asyncio.gather(*tasks)
            return list(paths)
        finally:
            await browser.close()
