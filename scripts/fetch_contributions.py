"""
fetch_contributions.py — Scrape the public GitHub contribution calendar.

No GitHub token required. Reads the same public HTML fragment that GitHub
renders on every profile page.

URL: https://github.com/users/<USERNAME>/contributions

Writes: data/contributions.json
  {
    "username":   "Abdellahelb",
    "fetched_at": "2026-08-11T06:17:00Z",
    "total":      42,
    "days": [
      {"date": "2025-08-10", "count": 0, "level": 0},
      ...
    ],
    "stats": {
      "current_streak": 3,
      "longest_streak": 14,
      "best_day":       {"date": "2026-02-14", "count": 7},
      "monthly_totals": {"2025-08": 0, "2025-09": 2, ...}
    }
  }
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = "Abdellahelb"
URL      = f"https://github.com/users/{USERNAME}/contributions"
HEADERS  = {
    "User-Agent": "Mozilla/5.0 (compatible; profile-art-bot/1.0)"
}


def fetch_days() -> list[dict]:
    print(f"Fetching {URL} …")
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # GitHub renders <td class="ContributionCalendar-day"
    #     data-date="YYYY-MM-DD" data-level="0-4">
    cells = soup.find_all("td", class_="ContributionCalendar-day")
    if not cells:
        raise RuntimeError("No contribution cells found — GitHub may have changed their HTML.")

    days = []
    for td in cells:
        date  = td.get("data-date", "")
        level = int(td.get("data-level", 0))

        # Extract contribution count from the tooltip text next to each cell.
        # GitHub places a <tool-tip> sibling: "N contributions on Month Dth."
        count = 0
        tip_id = td.get("id", "")
        if tip_id:
            tip = soup.find("tool-tip", attrs={"for": tip_id})
            if tip:
                m = re.search(r"(\d+)\s+contribution", tip.get_text())
                if m:
                    count = int(m.group(1))

        if date:
            days.append({"date": date, "count": count, "level": level})

    # Sort chronologically
    days.sort(key=lambda d: d["date"])
    return days


def compute_stats(days: list[dict]) -> dict:
    total   = sum(d["count"] for d in days)
    best    = max(days, key=lambda d: d["count"]) if days else {}

    # Streaks
    current_streak = longest_streak = streak = 0
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    from datetime import timedelta, date as date_cls

    active_days = {d["date"] for d in days if d["count"] > 0}

    # Walk backwards from today
    cur = date_cls.fromisoformat(today_str)
    while cur.isoformat() in active_days or cur.isoformat() not in {d["date"] for d in days}:
        if cur.isoformat() in active_days:
            current_streak += 1
        elif current_streak > 0:
            break
        cur -= timedelta(days=1)
        if cur < date_cls.fromisoformat(days[0]["date"]):
            break

    # Longest streak: scan all days in order
    run = 0
    for d in days:
        if d["count"] > 0:
            run += 1
            longest_streak = max(longest_streak, run)
        else:
            run = 0

    # Monthly totals
    monthly: dict[str, int] = {}
    for d in days:
        month_key = d["date"][:7]   # "YYYY-MM"
        monthly[month_key] = monthly.get(month_key, 0) + d["count"]

    return {
        "total":           total,
        "current_streak":  current_streak,
        "longest_streak":  longest_streak,
        "best_day":        best,
        "monthly_totals":  monthly,
    }


def main():
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)

    days  = fetch_days()
    stats = compute_stats(days)

    payload = {
        "username":   USERNAME,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total":      stats.pop("total"),
        "days":       days,
        "stats":      stats,
    }

    out_path = out_dir / "contributions.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved {len(days)} days, {payload['total']} contributions -> {out_path}")


if __name__ == "__main__":
    main()
