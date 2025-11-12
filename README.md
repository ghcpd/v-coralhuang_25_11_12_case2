# WeatherBot UI Repair

This project repairs the single-page UI from `input.html` and adds tests that validate layout, media, and header stability.

## What I changed (brief)
- Replaced absolute-positioned chat UI with a flexible, non-overlapping `flex` layout for `.message` elements. Avatars are anchored to each bubble (left or right).
- Removed any forced `transform: rotate()` from images and enforced aspect-ratio-preserving rules: `max-width` and `height:auto`; `object-fit:contain` is used for consistent rendering.
- Time headers receive stable IDs (`time-<timestamp>`), role `separator`, and are inserted with minimal DOM updates—no full innerHTML rewrites. Insertions preserve scroll anchor via computed bounding rect deltas.
- Added accessibility attributes: role, aria-labels for interactive items, alt attributes for images.

## How to run tests locally

Linux/macOS:
1. Install Python packages and Playwright: `python3 -m pip install -r requirements.txt`
2. Install Playwright browser binaries: `playwright install` (only required once).
3. Run the test script: `./run_test.sh`.

Windows:
1. Install Python packages and Playwright: `py -m pip install -r requirements.txt`
2. Install Playwright: `py -m playwright install`.
3. Run the test script: `run_test.bat`.

The scripts will start a local HTTP server on port 8080 and run `test_validator.py`. Results will be written to `artifacts/test-report.json` and screenshots to `artifacts/screenshots`.

## Known limitations
- Playwright browser binary installation may require network access for the first-time install. The tests themselves do not rely on external networks.
- The orientation correction uses CSS safeguards and `img.style.transform = 'none'`; more advanced EXIF handling would require a JS EXIF library.

## Files of interest
- `ui_fixed.html` — repaired HTML page.
- `styles.css` — layout and accessibility styles.
- `app.js` — minimal DOM updates and `window.simulateInsertOnce` for header stability tests.
- `test_validator.py` — validates layout, media, header stability, and accessibility smoke checks.
- `run_test.sh` / `run_test.bat` — one-click test runners.

