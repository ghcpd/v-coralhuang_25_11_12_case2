# Chat UI Repair — weatherbot_ui_repair

This project fixes UI layout issues from the broken chat `input.html`, ensuring messages do not overlap, avatars are anchored, media respects natural aspect ratio (no forced rotation), and time headers are stable when inserting content dynamically.

Quick start

- Install Python packages:
  - pip install -r requirements.txt
- Run the tests (Linux/macOS):
  - sh run_test.sh
- Run the tests (Windows PowerShell):
  - run_test.bat

Files created

- `ui_fixed.html` — fixed page using local paths
- `styles.css` — extracted styles that avoid absolute positioning and add responsive rules
- `app.js` — minimal chat UI code: stable headers, append-only DOM updates, preserved scroll behavior, and anchors for avatars
- `test_validator.py` — static and rendered checks using BeautifulSoup & Playwright
- `run_test.sh` / `run_test.bat` — OS-aware runner to start a local server, run tests, and capture artifacts
- `requirements.txt` — Python packages used by the validator

Fixes applied

- Replaced `position:absolute` on `.message` elements with a flexible, flow-based layout using flexbox
- Anchored avatars to the message bubble layout (no drifting)
- Removed forced CSS `transform: rotate(90deg)` on image elements
- Constrained media with `max-width` and `height:auto`, and used inline SVG placeholders to avoid external resources
- Implemented stable time headers with unique IDs and `role="separator"` for accessibility
- Avoided full innerHTML rewrites: DOM updates use append/insert and preserve scroll position
- Added basic accessibility attributes: `role` and `alt` where sensible

Known limitations

- The validator uses Playwright; environment must have Playwright installed and set up (see `requirements.txt`)
- The tests run headless; visual rendering might vary with different browsers or platform DPI settings

