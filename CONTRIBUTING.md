# Contributing to gipfel

Thanks for climbing along! The easiest and most welcome contribution is a **new theme**.

## Add a theme (≈ 10 minutes)

1. Fork the repo and copy `gipfel/themes/day.json` to `gipfel/themes/<your-theme>.json`.
2. Set `"name"` to the file name and change the colours.
   - `sky`: three gradient stops, top → horizon
   - `far`, `mid`: back ridge and main ridge (main ridge is a top → bottom gradient)
   - `sky_body`: `"sun"`, `"moon"` or `"none"`; `weather`: `"clouds"`, `"stars"` or `"none"`
3. Preview it:
   ```bash
   python -m gipfel --user demo --demo --themes <your-theme> --out preview
   ```
   Open `preview/gipfel-<your-theme>.svg` in a browser.
4. Run the tests: `python -m unittest discover -s tests`
5. Open a pull request with a screenshot.

Theme ideas: alpenglow sunset, autumn, winter blizzard, desert, mars, synthwave, high contrast.

## Other contributions

- New label languages: add an entry to `LABELS` in `gipfel/render.py`
- Bug reports and rendering issues: please include the SVG and your browser
- Keep the project dependency-free (Python standard library only)
