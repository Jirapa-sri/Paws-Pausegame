"""Shared CSS design tokens and HTML helpers for pitch slides."""

from __future__ import annotations

from html import escape

from .models import DesignSystem, SlideSpec


def base_css(ds: DesignSystem) -> str:
    return f"""
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Nunito:wght@500;700;800&family=IBM+Plex+Mono:wght@500&display=swap');
:root {{
  --paper: {ds.paper};
  --paper-2: {ds.paper_2};
  --ink: {ds.ink};
  --ink-soft: #6E5C49;
  --ink-faint: #8C7A66;
  --teal: {ds.teal};
  --teal-deep: {ds.teal_deep};
  --marigold: {ds.marigold};
  --coral: {ds.coral};
  --line: rgba(58,44,34,0.16);
  --line-strong: rgba(58,44,34,0.28);
  --shadow: 0 22px 50px -28px rgba(42,30,18,0.5);
  --display: "{ds.display_font}", ui-rounded, sans-serif;
  --body: "{ds.body_font}", Georgia, serif;
  --mono: "IBM Plex Mono", ui-monospace, monospace;
}}
* {{ box-sizing: border-box; }}
html, body {{
  margin: 0; padding: 0; width: 1920px; height: 1080px; overflow: hidden;
}}
body {{
  color: var(--ink);
  font-family: var(--body);
  background:
    radial-gradient(circle at 10% 12%, var(--paper-2) 0%, transparent 42%),
    radial-gradient(circle at 92% 88%, #E9D2A4 0%, transparent 46%),
    linear-gradient(145deg, #F8EFD9 0%, var(--paper) 48%, #EAD7B0 100%);
}}
.slide {{
  width: 1920px; height: 1080px; padding: 88px 110px;
  display: flex; flex-direction: column; justify-content: center;
  position: relative;
}}
.eyebrow {{
  font-family: var(--mono); font-size: 22px; letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--teal);
  display: flex; align-items: center; gap: 14px; margin-bottom: 22px;
}}
.eyebrow::before {{
  content: ""; width: 34px; height: 3px; background: var(--marigold); border-radius: 2px;
}}
h1, h2 {{
  font-family: var(--display); font-weight: 800; margin: 0; line-height: 1.05;
  text-wrap: balance;
}}
h1 {{ font-size: 118px; letter-spacing: -0.02em; }}
h2 {{ font-size: 74px; }}
.subtitle, .lede {{
  font-size: 34px; line-height: 1.45; color: var(--ink-soft); max-width: 28ch; margin: 22px 0 0;
}}
.badge-row {{ display: flex; flex-wrap: wrap; gap: 14px; margin-top: 34px; }}
.badge {{
  font-family: var(--mono); font-size: 20px; padding: 12px 22px;
  border: 1.5px solid var(--line-strong); border-radius: 999px;
  color: var(--ink-soft); background: rgba(255,255,255,0.42);
}}
.card-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-top: 36px;
}}
.card {{
  background: rgba(255,255,255,0.48); border: 1px solid var(--line);
  border-radius: 28px; padding: 28px 30px; box-shadow: var(--shadow);
}}
.card h3 {{
  font-family: var(--display); font-size: 28px; margin: 14px 0 10px; color: var(--teal-deep);
}}
.card p {{ margin: 0; font-size: 24px; line-height: 1.4; color: var(--ink-soft); }}
.loop-wrap {{
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 40px;
}}
.loop-step {{
  background: rgba(255,255,255,0.48); border: 1px solid var(--line);
  border-radius: 24px; padding: 26px 24px; min-height: 180px;
  display: flex; flex-direction: column; gap: 16px;
}}
.loop-num {{
  width: 42px; height: 42px; border-radius: 50%; background: var(--teal); color: var(--paper);
  font-family: var(--mono); font-size: 18px; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}}
.loop-step span {{ font-family: var(--display); font-weight: 700; font-size: 28px; line-height: 1.25; }}
.check-list {{ display: flex; flex-direction: column; gap: 18px; margin-top: 36px; max-width: 980px; }}
.check-item {{
  display: flex; align-items: center; gap: 18px;
  background: rgba(255,255,255,0.45); border: 1px solid var(--line);
  border-radius: 18px; padding: 20px 24px; font-size: 30px; color: var(--ink);
}}
.check {{
  width: 36px; height: 36px; border-radius: 50%; background: var(--teal);
  display: grid; place-items: center; flex-shrink: 0;
}}
.progress {{
  position: absolute; left: 110px; bottom: 56px; right: 110px;
  height: 8px; background: rgba(58,44,34,0.12); border-radius: 999px; overflow: hidden;
}}
.progress > i {{
  display: block; height: 100%; width: var(--p); background: linear-gradient(90deg, var(--teal), var(--marigold));
}}
.brand {{
  position: absolute; top: 48px; left: 110px;
  display: flex; align-items: center; gap: 12px;
  font-family: var(--display); font-weight: 700; font-size: 24px; color: var(--ink-soft);
}}
.footer-meta {{
  position: absolute; bottom: 48px; right: 110px;
  font-family: var(--mono); font-size: 18px; color: var(--ink-faint);
}}
.closer {{ text-align: center; align-items: center; }}
.closer .lede {{ max-width: 34ch; margin-left: auto; margin-right: auto; }}
.split {{
  display: grid; grid-template-columns: 1.05fr 0.95fr; gap: 48px; align-items: center;
}}
.art {{
  width: 100%; height: 640px; border-radius: 36px; overflow: hidden;
  border: 1px solid var(--line-strong); box-shadow: var(--shadow);
  background: linear-gradient(180deg, #CFE4DF 0%, #B7D3CB 38%, #E8C98A 38%, #D9B56E 100%);
  position: relative;
}}
"""


PAW_SVG = """
<svg viewBox="0 0 24 24" width="28" height="28" fill="#D9705C" aria-hidden="true">
  <circle cx="12" cy="15" r="5"/><circle cx="5.5" cy="8.5" r="2.2"/>
  <circle cx="18.5" cy="8.5" r="2.2"/><circle cx="8.3" cy="4.6" r="2"/>
  <circle cx="15.7" cy="4.6" r="2"/>
</svg>
"""


def progress_bar(index: int, total: int) -> str:
    pct = int((index / total) * 100)
    return f'<div class="progress" aria-hidden="true"><i style="--p:{pct}%"></i></div>'


def brand_header() -> str:
    return f'<div class="brand">{PAW_SVG}<span>Paws &amp; Pause</span></div>'


def wrap_slide(
    *,
    slide: SlideSpec,
    ds: DesignSystem,
    body: str,
    index: int,
    total: int,
    closer: bool = False,
) -> str:
    cls = "slide closer" if closer else "slide"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=1920, height=1080"/>
  <title>{escape(slide.title)} — Paws &amp; Pause</title>
  <style>{base_css(ds)}</style>
</head>
<body>
  {brand_header()}
  <main class="{cls}">
    {body}
  </main>
  <div class="footer-meta">{index:02d} / {total:02d}</div>
  {progress_bar(index, total)}
</body>
</html>
"""


def icon_svg(kind: str) -> str:
    icons = {
        "home": '<svg width="36" height="36" viewBox="0 0 24 24" fill="none"><path d="M4 10L12 4l8 6v9a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1v-9z" stroke="#3E7C74" stroke-width="1.8" stroke-linejoin="round"/></svg>',
        "heart": '<svg width="36" height="36" viewBox="0 0 24 24" fill="none"><path d="M12 20s-7-4.4-9.3-8.9C1.2 8 2.7 5 6 5c2 0 3.3 1.1 4 2.1C10.7 6.1 12 5 14 5c3.3 0 4.8 3 3.3 6.1C15 15.6 12 20 12 20z" stroke="#D9705C" stroke-width="1.8" stroke-linejoin="round"/></svg>',
        "clock": '<svg width="36" height="36" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="8" stroke="#3E7C74" stroke-width="1.8"/><path d="M12 8v4l3 2" stroke="#3E7C74" stroke-width="1.8" stroke-linecap="round"/></svg>',
        "paw": PAW_SVG,
        "check": '<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 12.5l5 5L19 7" stroke="#F5E9D3" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        "shield": '<svg width="36" height="36" viewBox="0 0 24 24" fill="none"><path d="M12 3l8 3v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-3z" stroke="#3E7C74" stroke-width="1.8" stroke-linejoin="round"/><path d="M9 12l2.2 2.2L15.5 10" stroke="#D98F2B" stroke-width="1.8" stroke-linecap="round"/></svg>',
    }
    return icons.get(kind, icons["paw"])


def town_illustration() -> str:
    """Custom HTML/CSS/SVG illustration: cozy town + shelter window."""
    return """
<div class="art" aria-label="Custom town illustration">
  <svg viewBox="0 0 640 640" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#EAF6F3"/>
        <stop offset="100%" stop-color="#B7D3CB"/>
      </linearGradient>
      <linearGradient id="hill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#7FAF7A"/>
        <stop offset="100%" stop-color="#567A52"/>
      </linearGradient>
    </defs>
    <rect width="640" height="260" fill="url(#sky)"/>
    <circle cx="520" cy="90" r="42" fill="#F3D27A" opacity="0.9"/>
    <path d="M0 250 C120 210, 220 280, 340 240 C460 200, 540 250, 640 220 L640 260 L0 260 Z" fill="#9BC2B8"/>
    <path d="M0 360 C140 300, 260 390, 400 330 C520 280, 580 340, 640 320 L640 420 L0 420 Z" fill="url(#hill)"/>
    <rect y="380" width="640" height="260" fill="#E8C98A"/>
    <rect x="70" y="300" width="150" height="130" rx="8" fill="#F7E7C7" stroke="#3A2C22" stroke-width="4"/>
    <polygon points="60,300 145,230 230,300" fill="#D9705C" stroke="#3A2C22" stroke-width="4"/>
    <rect x="95" y="340" width="40" height="50" rx="4" fill="#8EC5D4" stroke="#3A2C22" stroke-width="3"/>
    <rect x="155" y="345" width="36" height="85" rx="4" fill="#6E5C49" stroke="#3A2C22" stroke-width="3"/>
    <rect x="270" y="250" width="210" height="180" rx="10" fill="#F3E2C0" stroke="#3A2C22" stroke-width="4"/>
    <polygon points="255,250 375,170 485,250" fill="#3E7C74" stroke="#3A2C22" stroke-width="4"/>
    <rect x="300" y="290" width="70" height="70" rx="8" fill="#8EC5D4" stroke="#3A2C22" stroke-width="4"/>
    <line x1="335" y1="290" x2="335" y2="360" stroke="#3A2C22" stroke-width="3"/>
    <line x1="300" y1="325" x2="370" y2="325" stroke="#3A2C22" stroke-width="3"/>
    <!-- puppy in window -->
    <circle cx="335" cy="332" r="16" fill="#C68642"/>
    <circle cx="325" cy="318" r="6" fill="#C68642"/>
    <circle cx="345" cy="318" r="6" fill="#C68642"/>
    <circle cx="330" cy="330" r="2" fill="#3A2C22"/>
    <circle cx="340" cy="330" r="2" fill="#3A2C22"/>
    <ellipse cx="335" cy="338" rx="4" ry="2.5" fill="#3A2C22"/>
    <rect x="420" y="300" width="34" height="130" rx="4" fill="#6E5C49" stroke="#3A2C22" stroke-width="3"/>
    <text x="312" y="455" font-family="Nunito, sans-serif" font-size="22" font-weight="700" fill="#3A2C22">SHELTER</text>
    <!-- child silhouette -->
    <ellipse cx="160" cy="500" rx="28" ry="10" fill="#000" opacity="0.12"/>
    <circle cx="160" cy="430" r="22" fill="#3A2C22"/>
    <rect x="142" y="450" width="36" height="55" rx="14" fill="#3A2C22"/>
    <rect x="132" y="468" width="14" height="36" rx="7" fill="#3A2C22"/>
    <rect x="174" y="468" width="14" height="36" rx="7" fill="#3A2C22"/>
    <!-- path -->
    <path d="M0 540 C160 500, 320 560, 640 520 L640 640 L0 640 Z" fill="#D9B56E"/>
    <path d="M40 560 C180 530, 340 580, 620 545" fill="none" stroke="#C49A55" stroke-width="18" stroke-linecap="round"/>
    <!-- floating paw prints -->
    <g fill="#D9705C" opacity="0.35">
      <g transform="translate(500 470) scale(1.1)">
        <circle cx="12" cy="15" r="5"/><circle cx="5.5" cy="8.5" r="2.2"/>
        <circle cx="18.5" cy="8.5" r="2.2"/><circle cx="8.3" cy="4.6" r="2"/>
        <circle cx="15.7" cy="4.6" r="2"/>
      </g>
      <g transform="translate(545 510) rotate(-18) scale(0.85)">
        <circle cx="12" cy="15" r="5"/><circle cx="5.5" cy="8.5" r="2.2"/>
        <circle cx="18.5" cy="8.5" r="2.2"/><circle cx="8.3" cy="4.6" r="2"/>
        <circle cx="15.7" cy="4.6" r="2"/>
      </g>
    </g>
  </svg>
</div>
"""
