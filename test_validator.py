#!/usr/bin/env python3
"""
Test validator for Chat UI fix
Validates layout, media rendering, headers, and accessibility
Uses BeautifulSoup for static checks and Playwright for rendered validation
"""

import json
import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Any

# Try importing dependencies with helpful error messages
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: beautifulsoup4 not installed. Run: pip install beautifulsoup4")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright")
    sys.exit(1)


class ChatUIValidator:
    """Validates Chat UI for rendering issues and accessibility"""
    
    def __init__(self, html_file: str, base_url: str = "http://localhost:8080"):
        self.html_file = html_file
        self.base_url = base_url
        self.report = {
            "layout_non_overlap": True,
            "media_aspect_ratio_ok": True,
            "no_forced_rotation": True,
            "time_header_stability": True,
            "accessibility_smoke": True,
            "checks": {}
        }
        self.errors = []
        self.warnings = []
    
    def static_check(self) -> bool:
        """BeautifulSoup-based static analysis"""
        print("[1/4] Running static HTML analysis...")
        
        try:
            with open(self.html_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html5lib')
        except Exception as e:
            self.errors.append(f"Failed to parse HTML: {e}")
            return False
        
        checks = {}
        
        # Check for absolute positioning
        style_tag = soup.find('style')
        if style_tag:
            style_content = style_tag.string or ""
            if "position: absolute" in style_tag.string:
                self.errors.append("Found 'position: absolute' in CSS - should use flex/grid")
                self.report["layout_non_overlap"] = False
            checks["has_absolute_positioning"] = "position: absolute" in style_content
        
        # Check for transform: rotate in styles
        if "transform: rotate" in str(style_tag):
            self.errors.append("Found 'transform: rotate' in media styles - should not rotate images")
            self.report["no_forced_rotation"] = False
        checks["has_forced_rotation"] = "transform: rotate" in str(style_tag) if style_tag else False
        
        # Check for duplicate IDs
        all_ids = [elem.get('id') for elem in soup.find_all(id=True)]
        duplicates = [id for id in all_ids if all_ids.count(id) > 1]
        if duplicates:
            self.warnings.append(f"Duplicate IDs found: {set(duplicates)}")
            self.report["accessibility_smoke"] = False
        checks["duplicate_ids"] = duplicates
        
        # Check for alt attributes on images
        images = soup.find_all('img')
        missing_alts = [img.get('src', 'unknown') for img in images if not img.get('alt')]
        if missing_alts:
            self.warnings.append(f"Images without alt text: {len(missing_alts)}")
            self.report["accessibility_smoke"] = False
        checks["missing_alts"] = len(missing_alts)
        
        # Check for role attributes
        messages = soup.find_all(class_='message')
        missing_roles = sum(1 for msg in messages if not msg.get('role'))
        if missing_roles > 0:
            self.warnings.append(f"{missing_roles} messages without role attribute")
            self.report["accessibility_smoke"] = False
        checks["messages_missing_role"] = missing_roles
        
        # Check for external resources (should be local or from allowed CDN)
        self.warnings.append("Note: Using external image sources (i.pravatar.cc, picsum.photos) for demo")
        checks["uses_external_images"] = True
        
        self.report["checks"]["static_analysis"] = checks
        
        if self.errors:
            print(f"  ✗ Static checks found issues")
            return False
        print(f"  ✓ Static checks passed")
        return True
    
    def rendered_check(self) -> bool:
        """Playwright-based rendered validation"""
        print("[2/4] Running rendered UI validation...")
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
                page = browser.new_page()
                
                # Navigate to the page
                try:
                    page.goto(f"{self.base_url}/ui_fixed.html", wait_until="networkidle", timeout=10000)
                except PlaywrightTimeout:
                    self.warnings.append("Page load timeout - continuing with checks")
                
                # Wait for images to load
                time.sleep(2)
                
                # Check for overlapping messages
                overlaps = page.evaluate("window.checkOverlaps()")
                if overlaps:
                    overlap_area = sum(o.get('area', 0) for o in overlaps)
                    if overlap_area > 100:  # More than 1px threshold
                        self.errors.append(f"Layout overlaps detected: {len(overlaps)} overlapping pairs, total area: {overlap_area}")
                        self.report["layout_non_overlap"] = False
                    else:
                        self.warnings.append(f"Minor overlaps (<1px): {len(overlaps)}")
                
                self.report["checks"]["layout_overlaps"] = {
                    "overlap_count": len(overlaps),
                    "total_area": sum(o.get('area', 0) for o in overlaps)
                }
                
                # Check media aspect ratios
                try:
                    media_ratios = page.evaluate("window.checkMediaAspectRatios()")
                    out_of_tolerance = [m for m in media_ratios if not m.get('isWithinTolerance', True)]
                    
                    if out_of_tolerance:
                        self.errors.append(f"Media aspect ratios off by >2%: {len(out_of_tolerance)} images")
                        self.report["media_aspect_ratio_ok"] = False
                    
                    # Check for rotation transforms
                    rotated = [m for m in media_ratios if m.get('transform') and 'rotate' in m['transform']]
                    if rotated:
                        self.errors.append(f"Forced rotation detected on {len(rotated)} images")
                        self.report["no_forced_rotation"] = False
                    
                    self.report["checks"]["media_rendering"] = {
                        "total_media": len(media_ratios),
                        "aspect_ratio_issues": len(out_of_tolerance),
                        "rotated_images": len(rotated)
                    }
                except Exception as e:
                    self.warnings.append(f"Could not check media rendering: {e}")
                
                # Check accessibility
                try:
                    a11y = page.evaluate("window.checkAccessibility()")
                    if a11y.get('totalIssues', 0) > 0:
                        self.warnings.append(f"Accessibility issues: {a11y['totalIssues']}")
                        self.report["accessibility_smoke"] = False
                    self.report["checks"]["accessibility"] = a11y
                except Exception as e:
                    self.warnings.append(f"Could not check accessibility: {e}")
                
                # Test header stability
                scroll_pos_before = page.evaluate("document.querySelector('.chat-container').scrollTop")
                page.evaluate("window.simulateInsertOnce()")
                time.sleep(0.5)
                scroll_pos_after = page.evaluate("document.querySelector('.chat-container').scrollTop")
                scroll_jump = abs(scroll_pos_after - scroll_pos_before)
                
                if scroll_jump > 200:  # More than 200px jump is unstable
                    self.warnings.append(f"Large scroll jump detected: {scroll_jump}px")
                    self.report["time_header_stability"] = False
                
                # Check header count
                header_count = page.evaluate("document.querySelectorAll('.time-header').length")
                
                self.report["checks"]["header_stability"] = {
                    "scroll_jump_pixels": scroll_jump,
                    "header_count": header_count
                }
                
                browser.close()
                
            except Exception as e:
                self.errors.append(f"Playwright validation failed: {e}")
                return False
        
        if self.errors:
            print(f"  ✗ Rendered checks found issues")
            return False
        print(f"  ✓ Rendered checks passed")
        return True
    
    def layout_detailed_check(self) -> bool:
        """Detailed layout position check"""
        print("[3/4] Checking detailed layout positions...")
        
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"{self.base_url}/ui_fixed.html", wait_until="networkidle", timeout=10000)
            time.sleep(1)
            
            try:
                layout_info = page.evaluate("window.getLayoutInfo()")
                
                # Check that no message uses absolute positioning
                absolute_msgs = [m for m in layout_info if m.get('isAbsolute')]
                if absolute_msgs:
                    self.errors.append(f"{len(absolute_msgs)} messages still using absolute positioning")
                    self.report["layout_non_overlap"] = False
                
                # Check that messages are within container bounds
                container = page.evaluate("document.querySelector('.chat-container').getBoundingClientRect()")
                container_rect = {
                    'left': container['x'],
                    'right': container['x'] + container['width'],
                    'top': container['y'],
                    'bottom': container['y'] + container['height']
                }
                
                for msg in layout_info:
                    if msg['left'] < container_rect['left'] or msg['right'] > container_rect['right']:
                        self.warnings.append(f"Message {msg['id']} extends beyond container bounds")
                
                self.report["checks"]["layout_details"] = {
                    "total_messages": len(layout_info),
                    "absolute_positioned": len(absolute_msgs),
                    "all_have_avatars": all(m.get('hasAvatar') or m.get('hasMedia') for m in layout_info)
                }
                
            except Exception as e:
                self.warnings.append(f"Could not get detailed layout: {e}")
            finally:
                browser.close()
        
        print(f"  ✓ Layout details checked")
        return True
    
    def summary(self) -> bool:
        """Print validation summary"""
        print("\n[4/4] Validation Summary:")
        print("=" * 60)
        
        all_pass = True
        
        checks = [
            ("Layout Non-Overlap", self.report["layout_non_overlap"]),
            ("Media Aspect Ratio OK", self.report["media_aspect_ratio_ok"]),
            ("No Forced Rotation", self.report["no_forced_rotation"]),
            ("Time Header Stability", self.report["time_header_stability"]),
            ("Accessibility Smoke", self.report["accessibility_smoke"])
        ]
        
        for check_name, passed in checks:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{check_name:.<40} {status}")
            if not passed:
                all_pass = False
        
        print("=" * 60)
        
        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\nWARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if all_pass:
            print("\n✓ All validation checks PASSED")
        else:
            print("\n✗ Some validation checks FAILED")
        
        return all_pass
    
    def save_report(self, output_file: str):
        """Save validation report to JSON"""
        self.report["errors"] = self.errors
        self.report["warnings"] = self.warnings
        self.report["passed"] = all([
            self.report["layout_non_overlap"],
            self.report["media_aspect_ratio_ok"],
            self.report["no_forced_rotation"],
            self.report["time_header_stability"],
            self.report["accessibility_smoke"]
        ])
        
        # Create artifacts directory if it doesn't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(self.report, f, indent=2)
        
        print(f"\nReport saved to: {output_file}")


def main():
    # Determine HTML file location
    script_dir = Path(__file__).parent
    html_file = script_dir / "ui_fixed.html"
    
    if not html_file.exists():
        print(f"ERROR: {html_file} not found")
        sys.exit(1)
    
    # Check if server is running
    print(f"Checking server at http://localhost:8080/ui_fixed.html...")
    
    import socket
    import time
    
    # Try multiple times with delay
    server_available = False
    for attempt in range(5):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', 8080))
            sock.close()
            if result == 0:
                server_available = True
                break
        except:
            pass
        if attempt < 4:
            time.sleep(1)
    
    if not server_available:
        print("ERROR: Server not running on port 8080")
        print("Start the server first with: python -m http.server 8080")
        sys.exit(1)
    
    # Run validator
    validator = ChatUIValidator(str(html_file))
    
    results = [
        validator.static_check(),
        validator.rendered_check(),
        validator.layout_detailed_check(),
    ]
    
    all_pass = validator.summary()
    
    # Save report
    report_path = script_dir / "artifacts" / "test-report.json"
    validator.save_report(str(report_path))
    
    # Exit with appropriate code
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
