# UI Fixes for Chat Sample

This repository contains a repaired single-page chat UI (`ui_fixed.html`) and tests that verify layout stability, media aspect ratio, rotation, header stability, and basic accessibility.

Files:
- `ui_fixed.html` - main page fixed for layout and media
- `styles.css` - extracted and responsive styles
- `app.js` - improved JS with stable DOM updates and scroll preservation
- `requirements.txt` - Python packages needed for testing
- `test_validator.py` - automated test that uses BeautifulSoup and Playwright
- `run_test.sh` - Linux / macOS helper to start server and run tests
- `run_test.bat` - Windows variant of the same
- `artifacts/` - generated test artifacts: logs, screenshots, and `test-report.json`

What I changed (summary):
- Replaced absolute `.message` positioning with flex layout and `align-self` for left/right messages; avatars are anchored to bubbles.
- Removed forced image rotation; images load from local inline SVG data URIs and preserve natural aspect ratio.
- Improved message and header injection logic (no innerHTML hacks), preserved scroll position during updates, and added unique IDs for headers.
- Added accessibility attributes: `role="separator"` on timestamp headers, `alt` on images, and `aria-label` on interactive button.

How to run tests (Linux/macOS):
1. Install packages: `python3 -m pip install -r requirements.txt`
2. Install Playwright browsers (required): `python3 -m playwright install`
3. Start tests: `bash run_test.sh` (this starts a local server on port 8080 and runs tests)
4. Results and artifacts are under `artifacts/`.

How to run tests (Windows):
1. Install packages: `py -m pip install -r requirements.txt`
2. Install Playwright browsers: `py -m playwright install`
3. Run: `run_test.bat` (starts server and runs tests)

Notes & Known Issues:
- The tests require Playwright and its browser binaries (chromium). Install with `playwright install`.
- All images are embedded via data URIs to avoid external network dependencies.

Contact: If you need adjustments to sizing, animation, or header semantics (e.g., sticky vs pinned behavior), I can tune those next.
