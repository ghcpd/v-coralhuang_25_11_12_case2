# Chat UI Fix — Local Test Harness

This folder contains a corrected single-page UI (`ui_fixed.html`) and a small test harness to validate layout, media rendering, header stability, and basic accessibility.

## How to run

On Linux/macOS:

1. Install requirements and Playwright browsers:
   - `python3 -m pip install -r requirements.txt`
   - `playwright install` (installs browser engines)
2. Start a local server:
   - `cd web` then `python3 -m http.server 8080`
3. Run the tests:
   - `python3 test_validator.py`

On Windows (PowerShell):

1. Install requirements and Playwright browsers:
   - `py -m pip install -r requirements.txt`
   - `py -m playwright install`
2. Start a local server:
   - `cd web; py -m http.server 8080`
3. Run the tests:
   - `py test_validator.py`

## Files added / modified

- `ui_fixed.html` — corrected HTML; no absolute positioning and anchored avatars.
- `styles.css` — extracted responsive styles and layout fixes.
- `app.js` — local placeholders for avatars/media, stable header insertion, and anchor-preserving insertion.
- `test_validator.py` — static (BeautifulSoup) and dynamic (Playwright) checks that write `artifacts/test-report.json`.
- `requirements.txt` — dependencies for the validation script.

## Validation goals and known checks

- Messages should not overlap during rendering or rapid insertions.
- Images must preserve aspect ratios and must not be rotated via CSS transforms.
- Time headers must not create excessive scroll jumps.
- Basic accessibility checks: unique IDs, images with alt text, roles present.

## Notes

- This design avoids external images and uses small embedded SVG data URIs for avatars and shared images to keep tests deterministic and offline-friendly.
- For CI, use the `run_test.sh` or `run_test.bat` scripts to automate server start and tests.
