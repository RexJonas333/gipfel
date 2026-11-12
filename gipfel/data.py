"""Contribution data sources.

Each source returns a list of (datetime.date, count) tuples, oldest first,
covering roughly the last 365 days.
"""
from __future__ import annotations

import datetime as dt
import json
import random
import re
import urllib.request

GRAPHQL_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
USER_AGENT = "gipfel (+https://github.com/RexJonas333/gipfel)"


class DataError(RuntimeError):
    pass


def parse_graphql(payload: dict) -> list[tuple[dt.date, int]]:
    if payload.get("errors"):
        raise DataError("GitHub GraphQL error: " + "; ".join(e.get("message", "?") for e in payload["errors"]))
    user = (payload.get("data") or {}).get("user")
    if not user:
        raise DataError("User not found")
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(dt.date.fromisoformat(d["date"]), int(d["contributionCount"]))
            for w in weeks for d in w["contributionDays"]]
    return sorted(days)


def fetch_graphql(user: str, token: str, timeout: int = 30) -> list[tuple[dt.date, int]]:
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(GRAPHQL_URL, data=body, method="POST", headers={
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return parse_graphql(json.load(r))


_TD = re.compile(r'<td[^>]*?data-date="(\d{4}-\d{2}-\d{2})"[^>]*?id="([^"]+)"|'
                 r'<td[^>]*?id="([^"]+)"[^>]*?data-date="(\d{4}-\d{2}-\d{2})"')
_TIP = re.compile(r'<tool-tip[^>]*?for="([^"]+)"[^>]*>\s*([^<]*?)\s*</tool-tip>')


def parse_html(html: str) -> list[tuple[dt.date, int]]:
    """Parse github.com/users/<user>/contributions (best effort, no token needed)."""
    ids = {}
    for m in _TD.finditer(html):
        date, cid = (m.group(1), m.group(2)) if m.group(1) else (m.group(4), m.group(3))
        ids[cid] = dt.date.fromisoformat(date)
    counts = {}
    for cid, text in _TIP.findall(html):
        if cid in ids:
            n = re.match(r"([\d,]+)", text)
            counts[ids[cid]] = int(n.group(1).replace(",", "")) if n else 0
    if not ids:
        raise DataError("Could not parse contribution calendar (GitHub markup changed?)")
    return sorted((d, counts.get(d, 0)) for d in ids.values())


def fetch_html(user: str, timeout: int = 30) -> list[tuple[dt.date, int]]:
    req = urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                 headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return parse_html(r.read().decode("utf-8", "replace"))


def fetch(user: str, token: str | None = None) -> list[tuple[dt.date, int]]:
    if token:
        return fetch_graphql(user, token)
    return fetch_html(user)


def demo(seed: int = 7, end: dt.date | None = None) -> list[tuple[dt.date, int]]:
    """Deterministic, realistic-looking sample year."""
    rnd = random.Random(seed)
    end = end or dt.date(2026, 11, 12)
    start = end - dt.timedelta(days=364)
    days, energy = [], 0.5
    for i in range(365):
        d = start + dt.timedelta(days=i)
        energy = min(1.4, max(0.0, energy + rnd.uniform(-0.18, 0.2)))
        if 150 < i < 175:
            energy = max(energy, 1.25)
        if 200 < i < 214:
            energy = 0.0
        p_active = 0.35 + 0.5 * min(energy, 1) - (0.25 if d.weekday() >= 5 else 0)
        n = int(rnd.expovariate(1 / (2 + 9 * energy))) + 1 if rnd.random() < p_active else 0
        days.append((d, n))
    return days
