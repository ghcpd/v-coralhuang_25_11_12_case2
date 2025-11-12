# Chat UI Fix - Local

This project contains a repaired static chat UI (`ui_fixed.html`) from `input.html` with fixes for overlapping message bubbles, media distortion, and header flicker.

How to run (Linux/macOS):
1. Open a terminal in the project root.
2. Start server: `python3 -m http.server 8080`.
3. Open `http://localhost:8080/ui_fixed.html` in a browser.

How to run (Windows - PowerShell):
1. Open PowerShell in the project root.
2. Start server: `py -m http.server 8080` or `python -m http.server 8080`.
3. Open `http://localhost:8080/ui_fixed.html` in a browser.

One-click test runner:
- Linux/macOS: `./run_test.sh`
- Windows: `run_test.bat`

Files changed/created:
- `ui_fixed.html` – refactored HTML with semantic roles and stable IDs
- `styles.css` – CSS extracts with responsive layout, flexbox-based message flow
- `app.js` – JS that avoids full innerHTML rewrites, preserves scroll position
- `assets/` – local avatar and media placeholder images
- `test_validator.py` – validator using BeautifulSoup and Playwright
- `run_test.sh`/`run_test.bat` – run tests and start server
- `requirements.txt` – python dependencies

Key fixes applied:
- Replaced absolute positioning with flexbox; anchored avatars to bubbles.
- Removed forced `transform: rotate()` on media; enforced natural aspect ratio.
- Stabilized time headers with stable IDs and de-duplication logic.
- Avoided full DOM rewrites (no innerHTML += ''); preserved scroll position on updates.
- Accessibility: ensured `role`, `aria-live`, unique IDs, `alt` attributes.

Known limitations:
- Images are placeholders and stored as local SVGs; for realistic assets, replace with proper images.
- Validator requires Playwright to be installed (pip install playwright pytest-playwright) and browsers to be installed via `playwright install`.
