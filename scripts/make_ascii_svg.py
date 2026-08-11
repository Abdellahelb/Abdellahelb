"""
make_ascii_svg.py — Convert data/source-prepped.png to a self-typing ASCII SVG.

Design choices:
  • One color (light gray) — no per-glyph rainbow noise.
  • Density ramp: bright pixels → sparse glyphs, dark → dense.
  • Each row is wrapped in a horizontal clipPath wipe (SMIL), staggered
    top-to-bottom. A blinking block cursor rides the wipe edge.
  • Plays once and freezes. No looping.

Usage:
    python scripts/make_ascii_svg.py        # writes avi-ascii.svg
"""

from pathlib import Path
from xml.sax.saxutils import escape

# ── CONFIG ────────────────────────────────────────────────────────────────────
PREPPED_IMG  = Path("data/source-prepped.png")
OUT_SVG      = Path("avi-ascii.svg")

COLS         = 95        # character columns
CHAR_W       = 7.2       # px per character (monospace cell width)
CHAR_H       = 13.5      # px per character (line height)
FONT_SIZE    = 12
FONT         = "JetBrains Mono, Fira Code, Consolas, monospace"
GLYPH_COLOR  = "#c9d1d9"   # GitHub dark-mode foreground
CURSOR_COLOR = "#58a6ff"   # blue block cursor
BG_COLOR     = "#0d1117"   # GitHub dark background
BORDER_COLOR = "#30363d"

# Brightness → glyph density ramp (bright=sparse, dark=dense)
RAMP = " .`',-:;=+*#cs%@"   # 17 levels, leading space clears background

# Animation timing
ROW_PRINT_MS  = 28    # ms per character in the wipe (sets wipe speed)
ROW_STAGGER   = 0     # extra ms added per row (0 = rows start together after wipe)
BASE_DELAY_MS = 200   # pre-animation pause
CURSOR_BLINKS = 3     # how many times cursor blinks at end
# ─────────────────────────────────────────────────────────────────────────────


def load_grid(img_path: Path, cols: int) -> list[str]:
    """Down-sample the grayscale image to a cols-wide character grid."""
    from PIL import Image
    import numpy as np

    img = Image.open(img_path).convert("L")   # ensure grayscale

    # Maintain aspect ratio (characters are ~2× taller than wide)
    aspect = img.height / img.width
    rows = int(cols * aspect * (CHAR_W / CHAR_H) * 0.9)
    img = img.resize((cols, rows), Image.LANCZOS)

    arr = np.array(img)
    n = len(RAMP) - 1

    lines = []
    for row in arr:
        # Invert: bright pixel → low index (sparse glyph)
        glyphs = "".join(RAMP[int((255 - px) / 255 * n)] for px in row)
        lines.append(glyphs)

    return lines


def make_svg(lines: list[str]) -> str:
    rows   = len(lines)
    cols   = len(lines[0]) if lines else COLS
    svg_w  = int(cols * CHAR_W + 24)
    svg_h  = int(rows * CHAR_H + 32)

    total_wipe_ms = cols * ROW_PRINT_MS   # time for one row to wipe across

    parts: list[str] = []

    # ── Header ────────────────────────────────────────────────────────────────
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink"\n'
        f'     width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}"\n'
        f'     role="img" aria-label="ASCII portrait of Abdellah Elberkaoui">'
    )

    # ── Background + border ───────────────────────────────────────────────────
    parts.append(
        f'  <rect width="{svg_w}" height="{svg_h}" rx="8" '
        f'fill="{BG_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1.5"/>'
    )

    # ── Title bar ─────────────────────────────────────────────────────────────
    parts.append(f'  <rect width="{svg_w}" height="28" rx="8" fill="#161b22"/>')
    parts.append(f'  <rect y="20" width="{svg_w}" height="8" fill="#161b22"/>')
    parts.append(f'  <circle cx="16" cy="14" r="5" fill="#ff5f57"/>')
    parts.append(f'  <circle cx="32" cy="14" r="5" fill="#febc2e"/>')
    parts.append(f'  <circle cx="48" cy="14" r="5" fill="#28c840"/>')
    parts.append(
        f'  <text x="{svg_w//2}" y="19" font-family="{FONT}" font-size="11" '
        f'fill="#8b949e" text-anchor="middle">portrait.ascii — bash</text>'
    )

    # ── clipPath + text rows ──────────────────────────────────────────────────
    TEXT_Y0 = 42    # top of first text row (below title bar)

    parts.append("  <defs>")

    for r, line in enumerate(lines):
        delay_ms = BASE_DELAY_MS + r * total_wipe_ms
        dur_s    = f"{total_wipe_ms / 1000:.3f}s"
        delay_s  = f"{delay_ms / 1000:.3f}s"
        clip_id  = f"clip{r}"

        parts.append(
            f'    <clipPath id="{clip_id}">'
            f'<rect id="cr{r}" x="12" y="{TEXT_Y0 + r * CHAR_H - 2}" '
            f'width="0" height="{CHAR_H + 2}">'
            f'<animate attributeName="width" from="0" to="{cols * CHAR_W + 4}" '
            f'dur="{dur_s}" begin="{delay_s}" fill="freeze" calcMode="linear"/>'
            f'</rect>'
            f'</clipPath>'
        )

    parts.append("  </defs>")

    # Actual text elements, each clipped by its wipe rect
    for r, line in enumerate(lines):
        y  = TEXT_Y0 + r * CHAR_H + FONT_SIZE
        escaped = escape(line)
        parts.append(
            f'  <text x="12" y="{y}" '
            f'font-family="{FONT}" font-size="{FONT_SIZE}" '
            f'fill="{GLYPH_COLOR}" '
            f'xml:space="preserve" '
            f'clip-path="url(#clip{r})">'
            f'{escaped}'
            f'</text>'
        )

    # ── Cursor block ──────────────────────────────────────────────────────────
    # Cursor slides along the last active row and then blinks/fades at end.
    last_delay_ms  = BASE_DELAY_MS + (rows - 1) * total_wipe_ms
    end_ms         = last_delay_ms + total_wipe_ms
    cursor_y       = TEXT_Y0 + (rows - 1) * CHAR_H
    cursor_dur_s   = f"{total_wipe_ms / 1000:.3f}s"
    last_delay_s   = f"{last_delay_ms / 1000:.3f}s"
    end_s          = f"{end_ms / 1000:.3f}s"
    blink_dur_s    = "0.55s"

    parts.append(
        f'  <rect id="cursor" x="12" y="{cursor_y + 1}" '
        f'width="{CHAR_W:.1f}" height="{CHAR_H - 2}" '
        f'fill="{CURSOR_COLOR}" opacity="0">'
        # Ride the wipe edge of the last row
        f'  <animate attributeName="x" '
        f'from="12" to="{12 + cols * CHAR_W:.1f}" '
        f'dur="{cursor_dur_s}" begin="{last_delay_s}" fill="freeze"/>'
        # Appear at the start of last row's wipe
        f'  <animate attributeName="opacity" '
        f'from="0" to="1" dur="0.01s" begin="{last_delay_s}" fill="freeze"/>'
        # Blink a few times after full print, then disappear
        f'  <animate attributeName="opacity" '
        f'values="1;0;1;0;1;0;0" '
        f'dur="{float(blink_dur_s.rstrip("s")) * CURSOR_BLINKS}s" '
        f'begin="{end_s}" fill="freeze"/>'
        f'</rect>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    if not PREPPED_IMG.exists():
        print(f"Error: '{PREPPED_IMG}' not found.")
        print("Run first: python scripts/prep_photo.py <your-photo.jpg>")
        raise SystemExit(1)

    print(f"Loading '{PREPPED_IMG}' …")
    lines = load_grid(PREPPED_IMG, COLS)
    print(f"Grid: {len(lines)} rows × {len(lines[0])} cols")

    svg = make_svg(lines)
    OUT_SVG.write_text(svg, encoding="utf-8")
    print(f"Written -> {OUT_SVG}")


if __name__ == "__main__":
    main()
