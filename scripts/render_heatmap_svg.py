"""
render_heatmap_svg.py — Render data/contributions.json as an animated SVG.

Animation: CSS keyframes, diagonal (column-by-column) slide-down reveal.
Plays once on load, then freezes. No looping glow.

Usage:
    python scripts/render_heatmap_svg.py   # writes contrib-heatmap.svg
"""

import json
from datetime import date as date_cls, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

# ── CONFIG ────────────────────────────────────────────────────────────────────
DATA_FILE = Path("data/contributions.json")
OUT_SVG   = Path("contrib-heatmap.svg")

CELL      = 13    # px: width & height of each box
GAP       = 3     # px: gap between boxes
RADIUS    = 2     # border-radius on each box
LABEL_W   = 28    # px: left margin for weekday labels
TOP_PAD   = 32    # px: top margin for month labels
BOT_PAD   = 52    # px: bottom for stats footer

# GitHub-ish green ramp (level 0..5)
PALETTE = [
    "#161b22",   # 0  empty
    "#0e4429",   # 1  very light
    "#006d32",   # 2  light
    "#26a641",   # 3  medium
    "#39d353",   # 4  heavy
    "#69f0a0",   # 5  max (neon top)
]

BG       = "#0d1117"
FG       = "#c9d1d9"
DIM      = "#8b949e"
BORDER   = "#30363d"
FONT     = "JetBrains Mono, Fira Code, Consolas, monospace"
FONT_S   = 11

DAYS_OF_WEEK = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

# Column animation timing
COL_STAGGER_MS  = 18     # ms between each column appearing
COL_ANIM_DUR_MS = 300    # ms for a single column's slide-down
BASE_DELAY_MS   = 200
# ─────────────────────────────────────────────────────────────────────────────


def load_data() -> dict:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"'{DATA_FILE}' not found. Run fetch_contributions.py first."
        )
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def build_grid(days: list[dict]):
    """
    Return (weeks, month_labels) where:
      weeks        = list of 53 columns, each a list of (date_str, level, count) × 7
      month_labels = list of (col_index, month_name)
    """
    if not days:
        return [], []

    # Build lookup by date string
    by_date = {d["date"]: (d["level"], d["count"]) for d in days}

    # Find the Sunday on or before the first day
    first = date_cls.fromisoformat(days[0]["date"])
    start = first - timedelta(days=first.weekday() + 1)  # back to Sunday
    if start.weekday() != 6:   # weekday 6 = Sunday in isoweekday? No: Mon=0
        # Python weekday: Mon=0 … Sun=6
        # Go back to the most recent Sunday
        dow = (first.weekday() + 1) % 7   # 0=Sun, 1=Mon, … 6=Sat
        start = first - timedelta(days=dow)

    weeks: list[list[tuple]] = []
    month_labels: list[tuple[int, str]] = []
    prev_month = -1

    for col in range(53):
        col_cells = []
        for row in range(7):
            cur = start + timedelta(weeks=col, days=row)
            ds  = cur.isoformat()
            lvl, cnt = by_date.get(ds, (0, 0))
            # Cap level at 4 for palette index (levels scraped are 0-4)
            col_cells.append((ds, min(lvl, 4), cnt))

            if row == 0 and cur.month != prev_month:
                MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
                               "Jul","Aug","Sep","Oct","Nov","Dec"]
                month_labels.append((col, MONTH_NAMES[cur.month - 1]))
                prev_month = cur.month
        weeks.append(col_cells)

    return weeks, month_labels


def level_to_color(level: int) -> str:
    return PALETTE[min(level, len(PALETTE) - 1)]


def make_svg(data: dict) -> str:
    days         = data.get("days", [])
    total        = data.get("total", 0)
    stats        = data.get("stats", {})
    cur_streak   = stats.get("current_streak", 0)
    long_streak  = stats.get("longest_streak", 0)
    best_day     = stats.get("best_day", {})
    best_count   = best_day.get("count", 0)

    weeks, month_labels = build_grid(days)

    num_cols = len(weeks)
    cell_step = CELL + GAP

    total_w = LABEL_W + num_cols * cell_step + GAP + 20
    total_h = TOP_PAD + 7 * cell_step + GAP + BOT_PAD

    parts: list[str] = []

    # ── CSS animations ────────────────────────────────────────────────────────
    anim_rules = []
    for c in range(num_cols):
        delay_ms = BASE_DELAY_MS + c * COL_STAGGER_MS
        anim_rules.append(
            f"  .wk{c} {{ "
            f"animation: slidedown {COL_ANIM_DUR_MS}ms ease "
            f"{delay_ms}ms both; }}"
        )

    css = "\n".join(anim_rules)

    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     width="{total_w}" height="{total_h}" '
        f'viewBox="0 0 {total_w} {total_h}"\n'
        f'     role="img" aria-label="Contribution heatmap for Abdellahelb">\n'
        f'<style>\n'
        f'  @keyframes slidedown {{\n'
        f'    from {{ opacity: 0; transform: translateY(-8px); }}\n'
        f'    to   {{ opacity: 1; transform: translateY(0); }}\n'
        f'  }}\n'
        f'{css}\n'
        f'</style>'
    )

    # ── Background ────────────────────────────────────────────────────────────
    parts.append(
        f'<rect width="{total_w}" height="{total_h}" rx="8" '
        f'fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>'
    )

    # ── Title bar ─────────────────────────────────────────────────────────────
    parts.append(f'<rect width="{total_w}" height="28" rx="8" fill="#161b22"/>')
    parts.append(f'<rect y="20" width="{total_w}" height="8" fill="#161b22"/>')
    parts.append(f'<circle cx="16" cy="14" r="5" fill="#ff5f57"/>')
    parts.append(f'<circle cx="32" cy="14" r="5" fill="#febc2e"/>')
    parts.append(f'<circle cx="48" cy="14" r="5" fill="#28c840"/>')
    parts.append(
        f'<text x="{total_w//2}" y="19" font-family="{FONT}" font-size="{FONT_S}" '
        f'fill="#8b949e" text-anchor="middle">contributions.sh — bash</text>'
    )

    # ── Month labels ──────────────────────────────────────────────────────────
    for col, mname in month_labels:
        x = LABEL_W + col * cell_step
        parts.append(
            f'<text x="{x}" y="{TOP_PAD - 6}" '
            f'font-family="{FONT}" font-size="{FONT_S}" fill="{DIM}">{mname}</text>'
        )

    # ── Weekday labels ────────────────────────────────────────────────────────
    for row in range(7):
        if row % 2 == 1:   # show Mon, Wed, Fri only (odd rows)
            y = TOP_PAD + row * cell_step + CELL
            parts.append(
                f'<text x="0" y="{y}" '
                f'font-family="{FONT}" font-size="{FONT_S - 1}" '
                f'fill="{DIM}">{DAYS_OF_WEEK[row]}</text>'
            )

    # ── Contribution boxes ────────────────────────────────────────────────────
    for c, col_cells in enumerate(weeks):
        x = LABEL_W + c * cell_step
        parts.append(f'<g class="wk{c}">')
        for row, (ds, lvl, cnt) in enumerate(col_cells):
            y   = TOP_PAD + row * cell_step
            col = level_to_color(lvl)
            tip = f"{cnt} contribution{'s' if cnt != 1 else ''} on {ds}"
            parts.append(
                f'  <rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="{RADIUS}" fill="{col}">'
                f'<title>{escape(tip)}</title>'
                f'</rect>'
            )
        parts.append('</g>')

    # ── Legend ────────────────────────────────────────────────────────────────
    legend_y = TOP_PAD + 7 * cell_step + GAP + 10
    legend_x = total_w - 6 - 6 * (CELL + GAP) - 30

    parts.append(
        f'<text x="{legend_x}" y="{legend_y + CELL}" '
        f'font-family="{FONT}" font-size="{FONT_S - 1}" fill="{DIM}">Less</text>'
    )
    for i, col in enumerate(PALETTE):
        rx = legend_x + 28 + i * (CELL + GAP)
        parts.append(
            f'<rect x="{rx}" y="{legend_y}" width="{CELL}" height="{CELL}" '
            f'rx="{RADIUS}" fill="{col}"/>'
        )
    more_x = legend_x + 28 + len(PALETTE) * (CELL + GAP) + 2
    parts.append(
        f'<text x="{more_x}" y="{legend_y + CELL}" '
        f'font-family="{FONT}" font-size="{FONT_S - 1}" fill="{DIM}">More</text>'
    )

    # ── Stats footer ──────────────────────────────────────────────────────────
    stats_y = legend_y + CELL + 16
    footer  = (
        f"{total:,} contributions in the last year"
        f"  ·  streak: {cur_streak}d"
        f"  ·  longest: {long_streak}d"
        f"  ·  best day: {best_count}"
    )
    parts.append(
        f'<text x="{LABEL_W}" y="{stats_y}" '
        f'font-family="{FONT}" font-size="{FONT_S}" fill="{DIM}">'
        f'{escape(footer)}</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    data = load_data()
    svg  = make_svg(data)
    OUT_SVG.write_text(svg, encoding="utf-8")
    total = data.get("total", 0)
    print(f"Written -> {OUT_SVG}  ({total} contributions, {len(data.get('days',[]))} days)")


if __name__ == "__main__":
    main()
