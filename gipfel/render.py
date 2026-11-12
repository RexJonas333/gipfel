"""Render a contribution year as an animated mountain panorama (pure SVG).

1 contribution = 1 metre of elevation. The ridge follows contributions per week;
the highest week becomes the summit.
"""
from __future__ import annotations

import json
import math
import random
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

W, H = 1000, 300
BASE_Y = 252            # foot of the main ridge
MIN_H, MAX_H = 22, 168  # pixel height of valley / highest summit
THEME_DIR = Path(__file__).parent / "themes"

LABELS = {
    "en": dict(gain="m elevation gain", active="active days", streak="day streak",
               summit="Summit", unit="m", per="1 contribution = 1 m", date="%b %d", sep=","),
    "de": dict(gain="Hm aufgestiegen", active="aktive Tage", streak="Tage Serie",
               summit="Gipfel", unit="Hm", per="1 Contribution = 1 Hm", date="%d.%m.", sep="."),
}


def available_themes() -> list[str]:
    return sorted(p.stem for p in THEME_DIR.glob("*.json"))


def load_theme(name_or_path: str) -> dict:
    p = Path(name_or_path)
    if not p.suffix:
        p = THEME_DIR / f"{name_or_path}.json"
    if not p.exists():
        raise ValueError(f"Unknown theme '{name_or_path}'. Available: {', '.join(available_themes())}")
    return json.loads(p.read_text(encoding="utf-8"))


def weekly(days):
    return [sum(n for _, n in days[i:i + 7]) for i in range(0, len(days), 7)]


def stats(days):
    total = sum(n for _, n in days)
    active = sum(1 for _, n in days if n)
    best = cur = 0
    for _, n in days:
        cur = cur + 1 if n else 0
        best = max(best, cur)
    return total, active, best


def _jagged(values, base, hmin, hmax, rnd, sub=6, rough=0.07, sharp=0.85):
    """Weekly values as anchor points, cosine-interpolated in between plus rock noise.
    Returns (path, anchors); anchors stay exact so the summit flag sits on the peak."""
    if len(values) < 2:
        values = list(values) + [0] * (2 - len(values))
    vmax = max(values) or 1
    n = len(values)
    step = (W + 40) / (n - 1)
    hs = [hmin + (v / vmax) ** sharp * (hmax - hmin) for v in values]
    nodes = [(-20 + i * step, base - h) for i, h in enumerate(hs)]
    pts = [nodes[0]]
    for i in range(n - 1):
        for k in range(1, sub):
            f = k / sub
            c = (1 - math.cos(f * math.pi)) / 2
            h = hs[i] * (1 - c) + hs[i + 1] * c
            x = nodes[i][0] + f * step + rnd.uniform(-step / sub * .3, step / sub * .3)
            pts.append((x, base - h + rnd.uniform(-1, 1) * (2 + rough * h)))
        pts.append(nodes[i + 1])
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts), nodes


def _smooth(pts):
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def _closed(path_d):
    return f"{path_d} L{W + 20},{H} L-20,{H} Z"


def _num(n, sep):
    return f"{n:,}".replace(",", sep)


def render(days, user: str, theme: dict | str = "day", lang: str = "en", animate: bool = True) -> str:
    t = load_theme(theme) if isinstance(theme, str) else theme
    L = LABELS.get(lang, LABELS["en"])
    rnd = random.Random(zlib.crc32(user.lower().encode()))  # stable per user
    wk = weekly(days)
    total, active, streak = stats(days)
    year = days[-1][0].year
    user_x = escape(user)

    main_d, main = _jagged(wk, BASE_Y, MIN_H, MAX_H, rnd)
    far_vals = [sum(wk[max(0, i - 3):i + 4]) / len(wk[max(0, i - 3):i + 4]) for i in range(len(wk))]
    far_vals = far_vals[6:] + far_vals[:6]
    far_d, _ = _jagged([v + 0.3 * (max(wk) or 1) * (1 + math.sin(i / 2.3)) for i, v in enumerate(far_vals)],
                       BASE_Y - 40, 30, 112, rnd, sub=4, rough=0.05, sharp=1.0)
    near = [(-20 + i * 52.6, 272 + 9 * math.sin(i * 0.9) + 5 * math.sin(i * 2.1)) for i in range(21)]
    near_d = _smooth(near)

    peak_i = max(range(len(wk)), key=lambda i: wk[i])
    px, py = main[peak_i]
    snowline = BASE_Y - MIN_H - 0.45 * (MAX_H - MIN_H)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
         f'aria-label="{user_x}: {total} contributions in the last year, drawn as a mountain panorama">',
         f"<title>{user_x} · {total} contributions · gipfel</title>"]
    css = ("text{font-family:'Segoe UI',system-ui,-apple-system,Helvetica,Arial,sans-serif}")
    if animate:
        css += (".tw{animation:tw 3.2s ease-in-out infinite}@keyframes tw{0%,100%{opacity:.25}50%{opacity:1}}"
                ".cl{animation:cl 60s linear infinite}"
                "@keyframes cl{from{transform:translateX(-160px)}to{transform:translateX(1160px)}}"
                ".glow{animation:gl 5s ease-in-out infinite}@keyframes gl{0%,100%{opacity:.55}50%{opacity:.9}}"
                ".flag{transform-box:fill-box;transform-origin:left center;animation:fl 1.6s ease-in-out infinite}"
                "@keyframes fl{0%,100%{transform:skewY(0)}50%{transform:skewY(-8deg)}}"
                "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    o.append(f"<style>{css}</style>")

    sky = t["sky"]
    o.append("<defs>")
    o.append(f'<linearGradient id="g-sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[0]}"/>'
             f'<stop offset=".6" stop-color="{sky[1]}"/><stop offset="1" stop-color="{sky[2]}"/></linearGradient>')
    o.append(f'<linearGradient id="g-mid" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["mid"][0]}"/>'
             f'<stop offset="1" stop-color="{t["mid"][1]}"/></linearGradient>')
    o.append(f'<linearGradient id="g-mist" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[2]}" '
             f'stop-opacity="0"/><stop offset="1" stop-color="{sky[2]}" stop-opacity=".75"/></linearGradient>')
    o.append('<radialGradient id="g-halo"><stop offset="0" stop-color="#fff" stop-opacity=".9"/>'
             '<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    o.append(f'<clipPath id="c-ridge"><path d="{_closed(main_d)}"/></clipPath>')
    zig = " ".join(f"L{x},{snowline + (7 if (x // 18) % 2 else -3) + rnd.uniform(-3, 3):.1f}"
                   for x in range(W + 20, -40, -18))
    o.append(f'<clipPath id="c-snow"><path d="M-20,0 L{W + 20},0 {zig} Z"/></clipPath>')
    o.append(f'<mask id="m-cap"><rect width="{W}" height="{H}" fill="#fff"/>'
             f'<path d="{_closed(main_d)}" fill="#000" transform="translate(0 11)"/></mask>')
    o.append('<mask id="m-crescent"><rect width="1000" height="300" fill="#fff"/>'
             '<circle cx="851" cy="61" r="21" fill="#000"/></mask>')
    if animate:
        o.append(f'<clipPath id="c-reveal"><rect x="-20" y="0" width="{W + 40}" height="{H}">'
                 f'<animate attributeName="width" from="0" to="{W + 40}" dur="4s" fill="freeze" '
                 f'calcMode="spline" keySplines=".2 .7 .3 1" keyTimes="0;1"/></rect></clipPath>')
    o.append("</defs>")

    # sky
    o.append(f'<rect width="{W}" height="{H}" fill="url(#g-sky)"/>')
    if t.get("weather") == "stars":
        for _ in range(90):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, 170), rnd.choice([0.6, 0.8, 1.0, 1.4])
            o.append(f'<circle class="tw" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{t["weather_color"]}" '
                     f'style="animation-delay:{rnd.uniform(-3.2, 0):.1f}s;animation-duration:{rnd.uniform(2, 5):.1f}s"/>')
    if t.get("sky_body") == "sun":
        o.append(f'<circle class="glow" cx="840" cy="70" r="70" fill="url(#g-halo)"/>'
                 f'<circle cx="840" cy="70" r="26" fill="{t["sky_body_color"]}"/>')
    elif t.get("sky_body") == "moon":
        o.append(f'<circle class="glow" cx="840" cy="68" r="60" fill="url(#g-halo)" opacity=".35"/>'
                 f'<circle cx="840" cy="68" r="22" fill="{t["sky_body_color"]}" mask="url(#m-crescent)"/>')
    if t.get("weather") == "clouds":
        c = t["weather_color"]
        for k in range(3):
            y, s = 70 + k * 30, 0.8 + k * 0.25
            o.append(f'<g class="cl" style="animation-delay:{-k * 21}s;animation-duration:{55 + k * 15}s" opacity=".85">'
                     f'<g transform="translate({120 + k * 330} {y}) scale({s})">'
                     f'<ellipse cx="40" cy="12" rx="40" ry="11" fill="{c}"/>'
                     f'<ellipse cx="62" cy="4" rx="24" ry="13" fill="{c}"/>'
                     f'<ellipse cx="22" cy="6" rx="18" ry="10" fill="{c}"/></g></g>')

    # mountains
    o.append(f'<path d="{_closed(far_d)}" fill="{t["far"]}" opacity=".9"/>')
    o.append(f'<rect y="120" width="{W}" height="{BASE_Y - 100}" fill="url(#g-mist)"/>')
    o.append(f'<path d="{_closed(main_d)}" fill="url(#g-mid)"/>')
    o.append(f'<g clip-path="url(#c-ridge)"><g clip-path="url(#c-snow)"><rect width="{W}" height="{H}" '
             f'fill="{t["snow"]}" opacity="{t["snow_opacity"]}" mask="url(#m-cap)"/></g></g>')
    o.append(f'<path d="{main_d}" fill="none" stroke="{t["ridge"]}" stroke-opacity="{t["ridge_opacity"]}" stroke-width="1"/>')
    reveal = ' clip-path="url(#c-reveal)"' if animate else ""
    o.append(f'<path id="trail" d="{main_d}" fill="none" stroke="{t["trail"]}" stroke-width="1.3" '
             f'stroke-dasharray="1 4" stroke-linecap="round" opacity=".95"{reveal}/>')
    if animate:
        for r, op in ((7, ".35"), (3.2, "1")):
            o.append(f'<circle r="{r}" fill="{t["trail"]}" opacity="{op}"><animateMotion dur="16s" '
                     f'repeatCount="indefinite"><mpath href="#trail"/></animateMotion></circle>')

    # summit flag
    o.append(f'<line x1="{px:.1f}" y1="{py:.1f}" x2="{px:.1f}" y2="{py - 26:.1f}" stroke="{t["text"]}" stroke-width="1.6"/>')
    o.append(f'<path class="flag" d="M{px:.1f},{py - 26:.1f} l16,5 l-16,5 Z" fill="{t["accent"]}"/>')
    peak_date = days[min(peak_i * 7, len(days) - 1)][0]
    label = f'{L["summit"]} · {peak_date.strftime(L["date"])} · {_num(wk[peak_i], L["sep"])} {L["unit"]}'
    anchor = "end" if px > W - 200 else "start"
    lx = px - 6 if anchor == "end" else px + 20
    o.append(f'<text x="{lx:.1f}" y="{py - 16:.1f}" font-size="12" font-weight="600" fill="{t["text"]}" '
             f'text-anchor="{anchor}">{escape(label)}</text>')

    # foreground with pines
    o.append(f'<path d="{_closed(near_d)}" fill="{t["near"]}"/>')
    for _ in range(46):
        x = rnd.uniform(0, W)
        seg = min(int((x + 20) / 52.6), 19)
        y = near[seg][1] + (near[seg + 1][1] - near[seg][1]) * (((x + 20) / 52.6) - seg) + 6
        h = rnd.uniform(14, 30)
        o.append(f'<path d="M{x:.1f},{y - h:.1f} L{x + h * .38:.1f},{y:.1f} L{x - h * .38:.1f},{y:.1f} Z" fill="{t["tree"]}"/>')

    # text
    o.append(f'<text x="24" y="36" font-size="20" font-weight="700" fill="{t["text"]}">{user_x}</text>')
    o.append(f'<text x="24" y="56" font-size="12" fill="{t["subtext"]}" letter-spacing=".5">{year} · {L["per"]}</text>')
    o.append(f'<text x="24" y="288" font-size="13" fill="{t["stats"]}">'
             f'<tspan font-weight="700">{_num(total, L["sep"])}</tspan> {L["gain"]}  ·  '
             f'<tspan font-weight="700">{active}</tspan> {L["active"]}  ·  '
             f'<tspan font-weight="700">{streak}</tspan> {L["streak"]}</text>')
    o.append("</svg>")
    return "\n".join(o)
