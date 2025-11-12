#!/usr/bin/env python3
"""
Test validator for fixed chat UI.
Validates layout non-overlap, media aspect ratios, rotation, header stability, and accessibility.
"""

import json
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Create artifacts directory
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)

def rectangles_intersect(rect1, rect2, epsilon=1):
    """Check if two rectangles intersect beyond epsilon tolerance."""
    return not (
        rect1['right'] <= rect2['left'] + epsilon or
        rect2['right'] <= rect1['left'] + epsilon or
        rect1['bottom'] <= rect2['top'] + epsilon or
        rect2['bottom'] <= rect1['top'] + epsilon
    )

def check_layout_non_overlap(page):
    """Check that no .message elements overlap."""
    print("  Checking layout non-overlap...")
    
    # Sample multiple times during rapid scroll
    overlaps_found = []
    for i in range(5):
        # Scroll to different positions
        if i % 2 == 0:
            page.evaluate("document.getElementById('chat').scrollTop = 0")
        else:
            page.evaluate("document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight")
        
        page.wait_for_timeout(100)  # Wait for layout to settle
        
        # Get all visible message elements
        messages = page.query_selector_all('.message')
        message_rects = []
        
        for msg in messages:
            box = msg.bounding_box()
            if box and box['width'] > 0 and box['height'] > 0:
                message_rects.append({
                    'left': box['x'],
                    'right': box['x'] + box['width'],
                    'top': box['y'],
                    'bottom': box['y'] + box['height'],
                    'id': msg.get_attribute('id') or 'unknown'
                })
        
        # Check for overlaps
        for i, rect1 in enumerate(message_rects):
            for j, rect2 in enumerate(message_rects[i+1:], start=i+1):
                if rectangles_intersect(rect1, rect2):
                    overlaps_found.append({
                        'message1': rect1['id'],
                        'message2': rect2['id'],
                        'iteration': i
                    })
    
    if overlaps_found:
        print(f"    FAIL: Found {len(overlaps_found)} overlapping message pairs")
        return False, f"Found {len(overlaps_found)} overlapping message pairs"
    
    print("    PASS: No overlapping messages found")
    return True, None

def check_media_aspect_ratio(page):
    """Check that media images preserve aspect ratio and have no forced rotation."""
    print("  Checking media aspect ratio...")
    
    issues = []
    
    # Check for CSS transform: rotate
    media_images = page.query_selector_all('.message img.media')
    for img in media_images:
        transform = page.evaluate("(el) => window.getComputedStyle(el).transform", img)
        if transform and transform != 'none' and 'rotate' in transform.lower():
            issues.append(f"Image has rotation transform: {transform}")
        
        # Check aspect ratio
        natural_width = img.evaluate("el => el.naturalWidth")
        natural_height = img.evaluate("el => el.naturalHeight")
        client_width = img.evaluate("el => el.clientWidth")
        client_height = img.evaluate("el => el.clientHeight")
        
        if natural_width > 0 and natural_height > 0:
            natural_ratio = natural_width / natural_height
            if client_height > 0:
                display_ratio = client_width / client_height
                ratio_diff = abs(natural_ratio - display_ratio) / natural_ratio
                
                if ratio_diff > 0.02:  # More than 2% difference
                    issues.append(
                        f"Image aspect ratio mismatch: natural={natural_ratio:.3f}, "
                        f"display={display_ratio:.3f}, diff={ratio_diff*100:.1f}%"
                    )
    
    if issues:
        print(f"    FAIL: Found {len(issues)} media issues")
        for issue in issues[:3]:  # Show first 3
            print(f"      - {issue}")
        return False, "; ".join(issues[:3])
    
    print("    PASS: All media preserve aspect ratio and have no forced rotation")
    return True, None

def check_no_forced_rotation(page):
    """Check that no images have CSS transform: rotate."""
    print("  Checking for forced rotation...")
    
    all_images = page.query_selector_all('img')
    rotated = []
    
    for img in all_images:
        transform = page.evaluate("(el) => window.getComputedStyle(el).transform", img)
        if transform and transform != 'none':
            transform_lower = transform.lower()
            if 'rotate' in transform_lower and 'rotate(0deg)' not in transform_lower:
                rotated.append({
                    'src': img.get_attribute('src') or 'unknown',
                    'transform': transform
                })
    
    if rotated:
        print(f"    FAIL: Found {len(rotated)} rotated images")
        for r in rotated[:3]:
            print(f"      - {r['src']}: {r['transform']}")
        return False, f"Found {len(rotated)} rotated images"
    
    print("    PASS: No forced rotation found")
    return True, None

def check_time_header_stability(page):
    """Check that time headers maintain stable order and don't cause jumps."""
    print("  Checking time header stability...")
    
    # Get initial header positions and IDs
    initial_headers = page.query_selector_all('.time-header')
    initial_positions = {}
    initial_ids = []
    
    for header in initial_headers:
        header_id = header.get_attribute('id')
        if header_id:
            initial_ids.append(header_id)
            box = header.bounding_box()
            if box:
                initial_positions[header_id] = box['y']
    
    # Insert new content multiple times
    for i in range(3):
        page.evaluate("window.simulateInsertOnce()")
        page.wait_for_timeout(200)  # Wait for DOM update
    
    # Check header positions and IDs
    final_headers = page.query_selector_all('.time-header')
    final_ids = []
    final_positions = {}
    
    for header in final_headers:
        header_id = header.get_attribute('id')
        if header_id:
            final_ids.append(header_id)
            box = header.bounding_box()
            if box:
                final_positions[header_id] = box['y']
    
    # Check that existing headers didn't change position dramatically
    jumps = []
    for header_id in initial_ids:
        if header_id in initial_positions and header_id in final_positions:
            pos_diff = abs(final_positions[header_id] - initial_positions[header_id])
            if pos_diff > 50:  # More than 50px jump
                jumps.append({
                    'id': header_id,
                    'initial': initial_positions[header_id],
                    'final': final_positions[header_id],
                    'diff': pos_diff
                })
    
    # Check that IDs are unique
    if len(final_ids) != len(set(final_ids)):
        print("    FAIL: Duplicate header IDs found")
        return False, "Duplicate header IDs found"
    
    if jumps:
        print(f"    FAIL: Found {len(jumps)} header position jumps")
        for jump in jumps[:3]:
            print(f"      - {jump['id']}: {jump['diff']:.1f}px jump")
        return False, f"Found {len(jumps)} header position jumps"
    
    print("    PASS: Headers maintain stable positions and unique IDs")
    return True, None

def check_accessibility_static(html_content):
    """Static accessibility checks using BeautifulSoup."""
    print("  Checking accessibility (static)...")
    
    soup = BeautifulSoup(html_content, 'html5lib')
    issues = []
    
    # Check for duplicate IDs
    all_ids = []
    for elem in soup.find_all(attrs={'id': True}):
        elem_id = elem.get('id')
        if elem_id:
            if elem_id in all_ids:
                issues.append(f"Duplicate ID: {elem_id}")
            all_ids.append(elem_id)
    
    # Check time headers have role="separator"
    time_headers = soup.find_all(class_='time-header')
    for header in time_headers:
        role = header.get('role')
        if role != 'separator':
            issues.append(f"Time header missing role='separator': {header.get('id', 'no-id')}")
    
    # Check images have alt attributes
    images = soup.find_all('img')
    for img in images:
        if not img.get('alt') and img.get('aria-hidden') != 'true':
            issues.append(f"Image missing alt attribute: {img.get('src', 'unknown')}")
    
    # Check interactive controls have accessible names
    buttons = soup.find_all('button')
    for btn in buttons:
        aria_label = btn.get('aria-label')
        text_content = btn.get_text(strip=True)
        if not aria_label and not text_content:
            issues.append("Button missing accessible name")
    
    if issues:
        print(f"    FAIL: Found {len(issues)} accessibility issues")
        for issue in issues[:5]:
            print(f"      - {issue}")
        return False, "; ".join(issues[:5])
    
    print("    PASS: All accessibility checks passed")
    return True, None

def main():
    """Run all validation checks."""
    start_time = time.time()
    print("Starting UI validation tests...")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'checks': {},
        'overall': 'PASS'
    }
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Load the fixed page
            print("\nLoading ui_fixed.html...")
            page.goto('http://localhost:8080/ui_fixed.html', wait_until='networkidle', timeout=10000)
            page.wait_for_timeout(1000)  # Wait for initial render
            
            # Take screenshot
            page.screenshot(path=str(SCREENSHOTS_DIR / 'initial_state.png'))
            
            # Get HTML content for static checks
            html_content = page.content()
            
            # Run checks
            print("\nRunning validation checks...")
            
            # Layout non-overlap
            passed, error = check_layout_non_overlap(page)
            results['checks']['layout_non_overlap'] = {
                'passed': passed,
                'error': error
            }
            if not passed:
                results['overall'] = 'FAIL'
            
            # Media aspect ratio
            passed, error = check_media_aspect_ratio(page)
            results['checks']['media_aspect_ratio_ok'] = {
                'passed': passed,
                'error': error
            }
            if not passed:
                results['overall'] = 'FAIL'
            
            # No forced rotation
            passed, error = check_no_forced_rotation(page)
            results['checks']['no_forced_rotation'] = {
                'passed': passed,
                'error': error
            }
            if not passed:
                results['overall'] = 'FAIL'
            
            # Time header stability
            passed, error = check_time_header_stability(page)
            results['checks']['time_header_stability'] = {
                'passed': passed,
                'error': error
            }
            if not passed:
                results['overall'] = 'FAIL'
            
            # Accessibility (static)
            passed, error = check_accessibility_static(html_content)
            results['checks']['accessibility_smoke'] = {
                'passed': passed,
                'error': error
            }
            if not passed:
                results['overall'] = 'FAIL'
            
            browser.close()
    
    except PlaywrightTimeout:
        print("ERROR: Timeout loading page. Is the server running?")
        results['overall'] = 'FAIL'
        results['error'] = 'Timeout loading page'
    except Exception as e:
        print(f"ERROR: {e}")
        results['overall'] = 'FAIL'
        results['error'] = str(e)
    
    # Write results
    end_time = time.time()
    results['duration_seconds'] = round(end_time - start_time, 2)
    
    report_path = ARTIFACTS_DIR / 'test-report.json'
    with open(report_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for check_name, check_result in results['checks'].items():
        status = "PASS" if check_result['passed'] else "FAIL"
        print(f"  {check_name}: {status}")
        if check_result['error']:
            print(f"    Error: {check_result['error']}")
    print(f"\nOverall: {results['overall']}")
    print(f"Duration: {results['duration_seconds']}s")
    print("="*60)
    
    # Exit with appropriate code
    sys.exit(0 if results['overall'] == 'PASS' else 1)

if __name__ == '__main__':
    main()

