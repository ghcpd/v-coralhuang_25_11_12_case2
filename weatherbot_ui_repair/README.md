# WeatherBot UI Repair - Local Tests

Open `http://localhost:8080/ui_fixed.html` to view the repaired UI.

## Run tests

Install dependencies:

Linux/macOS:
1. python3 -m pip install -r requirements.txt
2. playwright install
3. ./run_test.sh

Windows:
1. py -m pip install -r requirements.txt
2. py -m playwright install
3. run_test.bat

## Fix summary
- Replaced absolute positioning with flex layout and anchored avatars.
- Removed forced rotations; images use natural aspect ratio with max sizes.
- Time headers now have stable IDs and are inserted without heavy DOM rewrites.
- Minimal DOM updates and scroll anchor preservation.
- Tested for layout overlap, media distortion, header stability and accessibility.

## Test artifacts
- `artifacts/test-report.json` will contain pass/fail for each validator check and logs.
- `artifacts/screenshots/rendered.png` captures the final page for review.
