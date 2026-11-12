"""CLI: python -m gipfel --user <login> [--out dist] [--themes day,night] [--lang en]"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__, data, render


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gipfel", description="Turn a GitHub contribution year into an animated mountain panorama SVG.")
    ap.add_argument("--user", required=True, help="GitHub login")
    ap.add_argument("--out", default="dist", help="output directory (default: dist)")
    ap.add_argument("--themes", default="day,night", help="comma-separated theme names or JSON paths")
    ap.add_argument("--lang", default="en", choices=sorted(render.LABELS), help="label language")
    ap.add_argument("--no-animation", action="store_true", help="static SVG")
    ap.add_argument("--demo", action="store_true", help="use built-in sample data instead of GitHub")
    ap.add_argument("--version", action="version", version=f"gipfel {__version__}")
    a = ap.parse_args(argv)

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    try:
        days = data.demo() if a.demo else data.fetch(a.user, token)
    except Exception as e:  # noqa: BLE001
        print(f"gipfel: could not load contributions for '{a.user}': {e}", file=sys.stderr)
        return 1

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in [s.strip() for s in a.themes.split(",") if s.strip()]:
        theme = render.load_theme(name)
        svg = render.render(days, a.user, theme, a.lang, animate=not a.no_animation)
        target = out / f"gipfel-{theme.get('name', Path(name).stem)}.svg"
        target.write_text(svg, encoding="utf-8")
        print(f"wrote {target}")
    total, active, streak = render.stats(days)
    print(f"{a.user}: {total} contributions, {active} active days, longest streak {streak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
