"""
Pure-Python SVG badge rendering (no Django imports, easy to unit test).

Renders a flat, shields.io-style badge: a dark "label" box next to a colored
"value" box. Width is estimated from character count rather than measured
(real font metrics would need a rendering library), which is the same
simplification most hand-rolled badge generators use — close enough for a
small label/value pair, not pixel-perfect.
"""
from __future__ import annotations

CHAR_WIDTH_PX = 6.5      # rough average glyph width for Verdana/DejaVu at 11px
PAD_PX = 10               # padding on each side of the text within its box
HEIGHT_PX = 20

COLOR_OK = "#10B981"     # matches --color-pass in the frontend theme
COLOR_WARN = "#F59E0B"   # matches --color-flaky in the frontend theme
COLOR_LABEL = "#2b2b2b"


def _text_width(text: str) -> int:
    return round(len(text) * CHAR_WIDTH_PX)


def render_badge_svg(label: str, value: str, color: str = COLOR_OK) -> str:
    label_w = _text_width(label) + PAD_PX * 2
    value_w = _text_width(value) + PAD_PX * 2
    total_w = label_w + value_w
    label_x = label_w / 2
    value_x = label_w + value_w / 2

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{HEIGHT_PX}" role="img" aria-label="{label}: {value}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#fff" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_w}" height="{HEIGHT_PX}" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_w}" height="{HEIGHT_PX}" fill="{COLOR_LABEL}"/>
    <rect x="{label_w}" width="{value_w}" height="{HEIGHT_PX}" fill="{color}"/>
    <rect width="{total_w}" height="{HEIGHT_PX}" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">
    <text x="{label_x}" y="14">{label}</text>
    <text x="{value_x}" y="14">{value}</text>
  </g>
</svg>'''


def flaky_count_badge(count: int) -> str:
    label = "flaky tests"
    value = str(count)
    color = COLOR_OK if count == 0 else COLOR_WARN
    return render_badge_svg(label, value, color)