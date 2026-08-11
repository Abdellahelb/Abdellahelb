"""
make_info_card.py — Generate a neofetch-style animated info card SVG.

Each line fades + slides in with a staggered CSS keyframe delay, like a
terminal printing text line by line. Plays once, then freezes.

Set STATIC=1 env var to emit a frozen (no-animation) frame for local preview.

Usage:
    python scripts/make_info_card.py          # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py # frozen frame
"""

import os
from pathlib import Path
from xml.sax.saxutils import escape

# ── CONFIG — edit this block freely ──────────────────────────────────────────
USERNAME   = "Abdellahelb"
FULL_NAME  = "Abdellah Elberkaoui"
SUBTITLE   = "abdellah@github"

FIELDS = [
    # (key, value, value_color)
    ("OS",       "Arch Linux (Developer Edition)",  "#c9d1d9"),
    ("Host",     "github.com/Abdellahelb",          "#58a6ff"),
    ("Role",     "Software Engineer",               "#7ee787"),
    ("Stack",    "Python · TypeScript · React",     "#e3b341"),
    ("Editor",   "VS Code  ⚡",                     "#c9d1d9"),
    ("Focus",    "Full-Stack · AI / ML",            "#f78166"),
    ("Uptime",   "Building in public  🚀",          "#c9d1d9"),
    ("Coffee",   "████████░░  80%",                 "#a371f7"),
]

# Visual settings
W, H           = 490, 300
BG             = "#0d1117"
BORDER         = "#30363d"
TITLE_COLOR    = "#58a6ff"
KEY_COLOR      = "#8b949e"
SEP_COLOR      = "#21262d"
FONT           = "JetBrains Mono, Fira Code, Consolas, monospace"
FONT_SIZE      = 13
LINE_H         = 22
STAGGER_MS     = 120   # ms between each line appearing
BASE_DELAY_MS  = 300   # delay before first line
# ─────────────────────────────────────────────────────────────────────────────

STATIC = os.environ.get("STATIC", "0") == "1"

def make_svg() -> str:
    lines_count = len(FIELDS) + 3  # title + separator + username + fields
    total_h = max(H, 55 + lines_count * LINE_H + 20)

    parts = []

    # ── CSS ───────────────────────────────────────────────────────────────────
    if not STATIC:
        css_rules = []
        for i in range(lines_count):
            delay = BASE_DELAY_MS + i * STAGGER_MS
            css_rules.append(
                f"  .l{i} {{ "
                f"animation: fadein 0.45s ease {delay}ms both; }}"
            )
        css_block = "\n".join(css_rules)
        css = f"""<style>
  @keyframes fadein {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
{css_block}
  .l0, .l1, .l2, .l3, .l4, .l5, .l6, .l7, .l8, .l9, .l10 {{
    animation-fill-mode: both;
  }}
</style>"""
    else:
        css = "<style></style>"

    # ── SVG shell ─────────────────────────────────────────────────────────────
    parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg"
     width="{W}" height="{total_h}" viewBox="0 0 {W} {total_h}"
     role="img" aria-label="Info card for {escape(FULL_NAME)}">
{css}
  <!-- Background -->
  <rect width="{W}" height="{total_h}" rx="8" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>
  <!-- Title bar -->
  <rect width="{W}" height="30" rx="8" fill="#161b22"/>
  <rect y="22" width="{W}" height="8" fill="#161b22"/>
  <!-- Traffic lights -->
  <circle cx="18" cy="15" r="5" fill="#ff5f57"/>
  <circle cx="34" cy="15" r="5" fill="#febc2e"/>
  <circle cx="50" cy="15" r="5" fill="#28c840"/>
  <!-- Window title -->
  <text x="{W//2}" y="20" font-family="{FONT}" font-size="11"
        fill="{KEY_COLOR}" text-anchor="middle">neofetch — abdellah@github</text>''')

    y = 55  # start Y for content

    # ── Username line ─────────────────────────────────────────────────────────
    cls = "" if STATIC else ' class="l0"'
    parts.append(
        f'  <text x="20" y="{y}"{cls} font-family="{FONT}" font-size="{FONT_SIZE+1}"'
        f' font-weight="bold" fill="{TITLE_COLOR}">{escape(FULL_NAME)}</text>'
    )
    y += LINE_H

    # Subtitle @handle
    cls = "" if STATIC else ' class="l1"'
    parts.append(
        f'  <text x="20" y="{y}"{cls} font-family="{FONT}" font-size="{FONT_SIZE-1}"'
        f' fill="{KEY_COLOR}">{escape(SUBTITLE)}</text>'
    )
    y += int(LINE_H * 0.8)

    # Separator line
    cls = "" if STATIC else ' class="l2"'
    sep_text = "─" * 38
    parts.append(
        f'  <text x="20" y="{y}"{cls} font-family="{FONT}" font-size="{FONT_SIZE}"'
        f' fill="{SEP_COLOR}">{sep_text}</text>'
    )
    y += LINE_H

    # ── Field rows ────────────────────────────────────────────────────────────
    for i, (key, value, val_color) in enumerate(FIELDS):
        li = i + 3
        cls = "" if STATIC else f' class="l{li}"'
        # Key (right-aligned in a fixed column)
        key_x = 20
        val_x = 130
        parts.append(
            f'  <g{cls}>'
            f'<text x="{key_x}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}"'
            f' fill="{KEY_COLOR}">{escape(key):>10}:</text>'
            f'<text x="{val_x}" y="{y}" font-family="{FONT}" font-size="{FONT_SIZE}"'
            f' fill="{val_color}">{escape(value)}</text>'
            f'</g>'
        )
        y += LINE_H

    # ── Color palette dots ────────────────────────────────────────────────────
    y += 8
    colors = ["#ff5f57","#febc2e","#28c840","#58a6ff","#a371f7","#e3b341","#7ee787","#f78166"]
    for j, c in enumerate(colors):
        cx = 20 + j * 20
        li = len(FIELDS) + 3
        cls = "" if STATIC else f' class="l{li}"'
        parts.append(f'  <rect x="{cx}" y="{y}"{cls} width="14" height="14" rx="3" fill="{c}"/>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    out = Path("info-card.svg")
    svg = make_svg()
    out.write_text(svg, encoding="utf-8")
    print(f"Written -> {out}  ({'static' if STATIC else 'animated'})")

if __name__ == "__main__":
    main()
