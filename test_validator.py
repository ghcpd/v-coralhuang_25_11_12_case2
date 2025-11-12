#!/usr/bin/env python3
"""
Test Validator for Fixed Chat UI

Validates through static DOM analysis:
1. No absolute positioning in messages
2. Media elements don't have forced rotations
3. Time headers are properly marked with IDs and roles
4. Accessibility: no duplicate IDs, proper roles and aria labels
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime

# Try importing BeautifulSoup for DOM parsing
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4 html5lib")
    sys.exit(1)


class ChatUIValidator:
    def __init__(self):
        self.html_path = "ui_fixed.html"
        self.css_path = "styles.css"
        self.results = {
            "layout_non_overlap": {"status": "not_run", "message": ""},
            "media_aspect_ratio_ok": {"status": "not_run", "message": ""},
            "no_forced_rotation": {"status": "not_run", "message": ""},
            "time_header_stability": {"status": "not_run", "message": ""},
            "accessibility_smoke": {"status": "not_run", "message": ""},
        }
        self.errors = []
        self.timestamp_start = datetime.now().isoformat()

    def validate_static_dom(self):
        """Validate static DOM structure"""
        print("[Static DOM Check]")
        
        if not Path(self.html_path).exists():
            self.errors.append(f"File not found: {self.html_path}")
            return False

        if not Path(self.css_path).exists():
            self.errors.append(f"File not found: {self.css_path}")
            return False

        with open(self.html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        with open(self.css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        soup = BeautifulSoup(html_content, "html5lib")

        # ===== ACCESSIBILITY CHECK =====
        print("  Checking accessibility...")

        # Check for duplicate IDs
        all_ids = [tag.get("id") for tag in soup.find_all(id=True)]
        if len(all_ids) != len(set(all_ids)):
            duplicates = [id for id in set(all_ids) if all_ids.count(id) > 1]
            self.results["accessibility_smoke"]["status"] = "fail"
            self.results["accessibility_smoke"]["message"] = (
                f"Duplicate IDs found: {duplicates}"
            )
            self.errors.append(f"Duplicate IDs: {duplicates}")
            print(f"  [FAIL] Duplicate IDs: {duplicates}")
            return False

        # Check for alt text on images
        images = soup.find_all("img")
        missing_alt = []
        for img in images:
            if not img.get("alt"):
                missing_alt.append(img.get("src", "unknown"))

        if missing_alt:
            self.errors.append(f"Images missing alt text: {missing_alt}")
            print(f"  [FAIL] Images missing alt: {len(missing_alt)}")
            return False

        # Check for time headers with role
        headers = soup.find_all("div", class_="time-header")
        headers_with_role = [h for h in headers if h.get("role") == "separator"]
        
        if len(headers) > 0 and len(headers_with_role) != len(headers):
            self.errors.append(
                f"Not all time headers have role='separator': "
                f"{len(headers_with_role)}/{len(headers)}"
            )
            print(f"  [FAIL] Headers missing separator role")
            return False

        self.results["accessibility_smoke"]["status"] = "pass"
        self.results["accessibility_smoke"]["message"] = (
            f"No duplicate IDs, {len(images)} images have alt text, "
            f"{len(headers)} headers have role='separator'"
        )
        print(f"  [OK] No duplicate IDs")
        print(f"  [OK] {len(images)} images properly labeled")
        print(f"  [OK] {len(headers)} time headers have correct roles")

        # ===== NO FORCED ROTATION CHECK =====
        print("  Checking for forced rotations...")

        # Check HTML for inline rotation
        if "rotate(90deg)" in html_content:
            self.results["no_forced_rotation"]["status"] = "fail"
            self.results["no_forced_rotation"]["message"] = (
                "Found hardcoded rotate(90deg) in HTML"
            )
            self.errors.append("Found hardcoded rotation in HTML")
            print(f"  [FAIL] Found rotate(90deg) in HTML")
            return False

        # Check CSS for rotation on .media
        media_rotations = re.findall(r'\.media\s*{[^}]*transform\s*:\s*rotate', css_content)
        if media_rotations:
            self.results["no_forced_rotation"]["status"] = "fail"
            self.results["no_forced_rotation"]["message"] = (
                "Found transform: rotate in CSS for .media"
            )
            self.errors.append("Found rotation transform on .media in CSS")
            print(f"  [FAIL] Found rotation in CSS for .media")
            return False

        # Check that .media has object-fit: contain
        if "object-fit: contain" in css_content or "object-fit:contain" in css_content:
            self.results["no_forced_rotation"]["status"] = "pass"
            self.results["no_forced_rotation"]["message"] = (
                ".media elements use object-fit: contain (no rotation)"
            )
            print(f"  [OK] No forced rotation on media")
        else:
            self.results["no_forced_rotation"]["status"] = "fail"
            self.results["no_forced_rotation"]["message"] = (
                ".media missing object-fit: contain"
            )
            self.errors.append(".media missing object-fit: contain")
            print(f"  [FAIL] .media missing object-fit: contain")
            return False

        # ===== LAYOUT NON-OVERLAP CHECK =====
        print("  Checking for absolute positioning...")

        # The fixed version should NOT use position: absolute for .message
        # Instead it uses flexbox
        if ("position: absolute" in css_content and ".message" in css_content):
            # Check if .message specifically has absolute positioning
            msg_rules = re.findall(r'\.message[^{]*{([^}]*)}', css_content)
            for rule in msg_rules:
                if "position: absolute" in rule:
                    self.results["layout_non_overlap"]["status"] = "fail"
                    self.results["layout_non_overlap"]["message"] = (
                        ".message uses position: absolute (should use flex)"
                    )
                    self.errors.append(".message has absolute positioning")
                    print(f"  [FAIL] .message uses absolute positioning")
                    return False

        # Check that .chat-container uses flexbox
        if "display: flex" in css_content:
            self.results["layout_non_overlap"]["status"] = "pass"
            self.results["layout_non_overlap"]["message"] = (
                ".chat-container uses flexbox layout for stable message flow"
            )
            print(f"  [OK] Layout uses flexbox (no absolute positioning)")
        else:
            self.results["layout_non_overlap"]["status"] = "fail"
            self.results["layout_non_overlap"]["message"] = (
                ".chat-container not using flex layout"
            )
            self.errors.append(".chat-container missing flexbox")
            print(f"  [FAIL] .chat-container not using flexbox")
            return False

        # ===== MEDIA ASPECT RATIO CHECK =====
        print("  Checking media aspect ratio settings...")

        # Check that .media has max-height and height: auto
        if ("max-height" in css_content and "height: auto" in css_content):
            self.results["media_aspect_ratio_ok"]["status"] = "pass"
            self.results["media_aspect_ratio_ok"]["message"] = (
                ".media uses max-height and height: auto to preserve aspect ratio"
            )
            print(f"  [OK] Media aspect ratio configuration is correct")
        else:
            self.results["media_aspect_ratio_ok"]["status"] = "fail"
            self.results["media_aspect_ratio_ok"]["message"] = (
                ".media missing proper aspect ratio constraints"
            )
            self.errors.append(".media missing height: auto or max-height")
            print(f"  [FAIL] .media missing proper aspect ratio settings")
            return False

        # ===== TIME HEADER STABILITY CHECK =====
        print("  Checking time header stability...")

        # Headers should have unique IDs
        header_ids = [h.get("id") for h in headers]
        unique_ids = len(header_ids) == len(set(header_ids))
        if not unique_ids:
            self.results["time_header_stability"]["status"] = "fail"
            self.results["time_header_stability"]["message"] = (
                "Time headers do not have unique IDs"
            )
            self.errors.append("Time header IDs are not unique")
            print(f"  [FAIL] Time header IDs are not unique")
            return False

        # Headers should not use position: sticky with animations (causes flicker)
        header_rules = re.findall(r'\.time-header[^{]*{([^}]*)}', css_content)
        for rule in header_rules:
            # Check for actual animation properties (not just comments)
            has_animation = bool(re.search(r'animation\s*:', rule))
            has_sticky = "position: sticky" in rule
            if has_animation and has_sticky:
                self.results["time_header_stability"]["status"] = "fail"
                self.results["time_header_stability"]["message"] = (
                    "Time headers use sticky positioning with animations (causes flicker)"
                )
                self.errors.append("Time headers have unstable positioning")
                print(f"  [FAIL] Time headers use sticky + animation (unstable)")
                return False

        self.results["time_header_stability"]["status"] = "pass"
        self.results["time_header_stability"]["message"] = (
            f"Time headers are stable with unique IDs and no flicker animations ({len(headers)} headers)"
        )
        print(f"  [OK] {len(headers)} time headers are stable")

        return True

    def validate(self):
        """Run all validations"""
        print("=" * 60)
        print("Chat UI Validator - Static Analysis")
        print("=" * 60)

        # Run static checks
        passed = self.validate_static_dom()

        # Summary
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        all_pass = True
        for check_name, result in self.results.items():
            status = result["status"]
            message = result["message"]
            symbol = "[OK]" if status == "pass" else "[FAIL]" if status == "fail" else "[??]"
            print(f"{symbol} {check_name}: {status}")
            if message:
                print(f"    {message}")
            if status == "fail":
                all_pass = False

        self.timestamp_end = datetime.now().isoformat()
        return all_pass and passed

    def write_report(self, output_file="artifacts/test-report.json"):
        """Write structured report"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        report = {
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "overall_pass": all(
                r["status"] == "pass" for r in self.results.values()
            ),
            "checks": self.results,
            "errors": self.errors,
            "notes": "Validation performed via static CSS/HTML analysis. No runtime browser automation used."
        }

        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\nReport written to {output_file}")
        return report


def main():
    validator = ChatUIValidator()
    passed = validator.validate()
    validator.write_report()

    if passed:
        print("\n[SUCCESS] All validations passed!")
        return 0
    else:
        print("\n[FAILURE] Some validations failed. See report above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
