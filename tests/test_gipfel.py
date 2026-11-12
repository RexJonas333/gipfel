import datetime as dt
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from gipfel import data, render
from gipfel.__main__ import main

FIX = Path(__file__).parent / "fixtures"


class DataTests(unittest.TestCase):
    def test_graphql(self):
        days = data.parse_graphql(json.loads((FIX / "graphql.json").read_text()))
        self.assertEqual(len(days), 21)
        self.assertEqual(days[0], (dt.date(2026, 1, 4), 0))
        self.assertEqual(days[3][1], 3)

    def test_graphql_error(self):
        with self.assertRaises(data.DataError):
            data.parse_graphql({"errors": [{"message": "nope"}]})
        with self.assertRaises(data.DataError):
            data.parse_graphql({"data": {"user": None}})

    def test_html(self):
        days = data.parse_html((FIX / "contributions.html").read_text())
        self.assertEqual(days, [(dt.date(2026, 1, 4), 0), (dt.date(2026, 1, 5), 7), (dt.date(2026, 1, 6), 1204)])

    def test_html_garbage(self):
        with self.assertRaises(data.DataError):
            data.parse_html("<html></html>")


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.days = data.demo()

    def test_valid_xml_all_themes_and_langs(self):
        for theme in render.available_themes():
            for lang in render.LABELS:
                for animate in (True, False):
                    ET.fromstring(render.render(self.days, "octo<cat>", theme, lang, animate))

    def test_stats(self):
        self.assertEqual(render.stats([(None, 0), (None, 2), (None, 3), (None, 0), (None, 1)]), (6, 3, 2))

    def test_empty_year(self):
        start = dt.date(2026, 1, 1)
        days = [(start + dt.timedelta(days=i), 0) for i in range(365)]
        ET.fromstring(render.render(days, "new-user"))

    def test_static_has_no_animation(self):
        svg = render.render(self.days, "x", "day", animate=False)
        self.assertNotIn("animateMotion", svg)
        self.assertNotIn("@keyframes", svg)

    def test_deterministic(self):
        self.assertEqual(render.render(self.days, "same"), render.render(self.days, "same"))

    def test_unknown_theme(self):
        with self.assertRaises(ValueError):
            render.load_theme("does-not-exist")

    def test_theme_schema(self):
        keys = set(json.loads((render.THEME_DIR / "day.json").read_text()))
        for name in render.available_themes():
            self.assertEqual(set(render.load_theme(name)), keys, name)


class CliTests(unittest.TestCase):
    def test_demo_cli(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(main(["--user", "demo", "--demo", "--out", d]), 0)
            self.assertTrue((Path(d) / "gipfel-day.svg").exists())
            self.assertTrue((Path(d) / "gipfel-night.svg").exists())


if __name__ == "__main__":
    unittest.main()
