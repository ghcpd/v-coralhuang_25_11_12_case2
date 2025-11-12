#!/usr/bin/env python3
"""
Test validator for chat UI fixes.
Validates layout non-overlap, media aspect ratio, rotation, header stability, and accessibility.
"""

import json
import os
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Warning: Playwright not available. Static checks only.", file=sys.stderr)

# Create artifacts directory
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

def load_html(file_path):
    """Load and parse HTML file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html5lib')

def check_accessibility_static(soup):
    """Static accessibility checks using BeautifulSoup."""
    issues = []
    
    # Check for duplicate IDs
    ids = []
    for elem in soup.find_all(True):
        elem_id = elem.get('id')
        if elem_id:
            if elem_id in ids:
                issues.append(f"Duplicate ID found: {elem_id}")
            ids.append(elem_id)
    
    # Check time headers have role="separator"
    time_headers = soup.find_all(class_='time-header')
    for header in time_headers:
        role = header.get('role')
        if role != 'separator':
            issues.append(f"Time header missing role='separator': {header.get('id', 'no-id')}")
        if not header.get('aria-label'):
            issues.append(f"Time header missing aria-label: {header.get('id', 'no-id')}")
    
    # Check images have alt attributes
    images = soup.find_all('img')
    for img in images:
        if not img.get('alt'):
            issues.append(f"Image missing alt attribute: {img.get('src', 'unknown')}")
    
    # Check interactive controls have names
    buttons = soup.find_all('button')
    for btn in buttons:
        if not btn.get('aria-label') and not btn.get_text(strip=True):
            issues.append(f"Button missing accessible name")
    
    return len(issues) == 0, issues

def check_layout_non_overlap(page):
    """Check that message elements don't overlap (rendered check)."""
    try:
        # Get all message elements
        messages = page.query_selector_all('.message')
        if len(messages) < 2:
            return True, []
        
        overlaps = []
        for i, msg1 in enumerate(messages):
            box1 = msg1.bounding_box()
            if not box1:
                continue
            
            for j, msg2 in enumerate(messages[i+1:], start=i+1):
                box2 = msg2.bounding_box()
                if not box2:
                    continue
                
                # Check for intersection (allowing 1px tolerance)
                if not (box1['x'] + box1['width'] < box2['x'] - 1 or
                        box2['x'] + box2['width'] < box1['x'] - 1 or
                        box1['y'] + box1['height'] < box2['y'] - 1 or
                        box2['y'] + box2['height'] < box1['y'] - 1):
                    overlaps.append(f"Messages {i} and {j} overlap")
        
        return len(overlaps) == 0, overlaps
    except Exception as e:
        return False, [f"Error checking overlap: {str(e)}"]

def check_media_aspect_ratio(page):
    """Check that images maintain aspect ratio and aren't rotated."""
    try:
        media_images = page.query_selector_all('.message img.media')
        if len(media_images) == 0:
            return True, []
        
        issues = []
        for img in media_images:
            # Check for rotation transform
            transform = page.evaluate('(el) => window.getComputedStyle(el).transform', img)
            if transform and transform != 'none' and 'rotate' in transform.lower():
                issues.append(f"Image has rotation transform: {img.get_attribute('src')}")
            
            # Check aspect ratio (clientWidth/clientHeight vs naturalWidth/naturalHeight)
            result = page.evaluate('''(el) => {
                if (!el.complete || !el.naturalWidth || !el.naturalHeight) {
                    return { error: 'Image not loaded or no natural dimensions' };
                }
                const clientWidth = el.clientWidth;
                const clientHeight = el.clientHeight;
                const naturalWidth = el.naturalWidth;
                const naturalHeight = el.naturalHeight;
                
                if (clientWidth === 0 || clientHeight === 0) {
                    return { error: 'Zero client dimensions' };
                }
                
                const clientRatio = clientWidth / clientHeight;
                const naturalRatio = naturalWidth / naturalHeight;
                const ratioDiff = Math.abs(clientRatio - naturalRatio) / naturalRatio;
                
                return {
                    clientWidth,
                    clientHeight,
                    naturalWidth,
                    naturalHeight,
                    clientRatio,
                    naturalRatio,
                    ratioDiff
                };
            }''', img)
            
            if 'error' in result:
                continue  # Skip if image not loaded
            
            if result['ratioDiff'] > 0.02:  # 2% tolerance
                issues.append(
                    f"Image aspect ratio mismatch: "
                    f"client={result['clientRatio']:.3f}, "
                    f"natural={result['naturalRatio']:.3f}, "
                    f"diff={result['ratioDiff']*100:.1f}%"
                )
        
        return len(issues) == 0, issues
    except Exception as e:
        return False, [f"Error checking media: {str(e)}"]

def check_time_header_stability(page):
    """Check that time headers remain stable during insertions."""
    try:
        # Get initial header count and IDs
        initial_headers = page.query_selector_all('.time-header')
        initial_count = len(initial_headers)
        initial_ids = [h.get_attribute('id') for h in initial_headers]
        
        # Simulate multiple insertions
        for _ in range(3):
            page.evaluate('window.simulateInsertOnce()')
            page.wait_for_timeout(100)  # Wait for DOM update
        
        # Check final state
        final_headers = page.query_selector_all('.time-header')
        final_count = len(final_headers)
        final_ids = [h.get_attribute('id') for h in final_headers]
        
        issues = []
        
        # Check that all IDs are unique
        if len(final_ids) != len(set(final_ids)):
            issues.append("Duplicate header IDs found after insertions")
        
        # Check that initial headers still exist (if they should)
        for initial_id in initial_ids:
            if initial_id and initial_id not in final_ids:
                issues.append(f"Initial header ID disappeared: {initial_id}")
        
        # Check scroll stability (should not jump dramatically)
        scroll_before = page.evaluate('document.getElementById("chat").scrollTop')
        page.evaluate('window.simulateInsertOnce()')
        page.wait_for_timeout(100)
        scroll_after = page.evaluate('document.getElementById("chat").scrollTop')
        
        scroll_jump = abs(scroll_after - scroll_before)
        if scroll_jump > 100:  # Allow some scroll change but not dramatic jumps
            issues.append(f"Large scroll jump detected: {scroll_jump}px")
        
        return len(issues) == 0, issues
    except Exception as e:
        return False, [f"Error checking header stability: {str(e)}"]

def run_tests():
    """Run all tests and generate report."""
    html_file = "ui_fixed.html"
    
    if not os.path.exists(html_file):
        print(f"Error: {html_file} not found", file=sys.stderr)
        return False
    
    report = {
        "layout_non_overlap": {"passed": False, "issues": []},
        "media_aspect_ratio_ok": {"passed": False, "issues": []},
        "no_forced_rotation": {"passed": False, "issues": []},
        "time_header_stability": {"passed": False, "issues": []},
        "accessibility_smoke": {"passed": False, "issues": []}
    }
    
    # Static accessibility check
    print("Running static accessibility checks...")
    soup = load_html(html_file)
    acc_passed, acc_issues = check_accessibility_static(soup)
    report["accessibility_smoke"]["passed"] = acc_passed
    report["accessibility_smoke"]["issues"] = acc_issues
    
    if not PLAYWRIGHT_AVAILABLE:
        print("Skipping rendered checks (Playwright not available)")
        all_passed = acc_passed
    else:
        print("Running rendered checks with Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Load the page - try HTTP server first, fallback to file://
            try:
                page.goto("http://localhost:8080/ui_fixed.html", timeout=5000)
            except Exception:
                # Fallback to file:// if server not available
                file_url = f"file://{os.path.abspath(html_file)}"
                print(f"  Server not available, using file:// URL")
                page.goto(file_url)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(500)  # Wait for any animations
            
            # Check layout non-overlap
            print("  Checking layout non-overlap...")
            overlap_passed, overlap_issues = check_layout_non_overlap(page)
            report["layout_non_overlap"]["passed"] = overlap_passed
            report["layout_non_overlap"]["issues"] = overlap_issues
            
            # Check media aspect ratio and rotation
            print("  Checking media aspect ratio and rotation...")
            media_passed, media_issues = check_media_aspect_ratio(page)
            report["media_aspect_ratio_ok"]["passed"] = media_passed
            report["media_aspect_ratio_ok"]["issues"] = media_issues
            report["no_forced_rotation"]["passed"] = media_passed  # Same check covers both
            report["no_forced_rotation"]["issues"] = media_issues
            
            # Check time header stability
            print("  Checking time header stability...")
            header_passed, header_issues = check_time_header_stability(page)
            report["time_header_stability"]["passed"] = header_passed
            report["time_header_stability"]["issues"] = header_issues
            
            # Take screenshot
            screenshot_path = ARTIFACTS_DIR / "test-screenshot.png"
            page.screenshot(path=str(screenshot_path))
            print(f"  Screenshot saved to {screenshot_path}")
            
            browser.close()
    
    # Write report
    report_path = ARTIFACTS_DIR / "test-report.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    all_passed = all(check["passed"] for check in report.values())
    
    for test_name, result in report.items():
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"{status}: {test_name}")
        if result["issues"]:
            for issue in result["issues"]:
                print(f"  - {issue}")
    
    print("="*60)
    print(f"Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print(f"Report saved to: {report_path}")
    
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)

