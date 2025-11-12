import json
import os
import sys
from bs4 import BeautifulSoup

# Playwright imports - optional
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    sync_playwright = None
    PLAYWRIGHT_AVAILABLE = False

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT = {"layout_non_overlap": False, "media_aspect_ratio_ok": False, "no_forced_rotation": False, "time_header_stability": False, "accessibility_smoke": False, "errors": []}
ARTIFACTS = os.path.join(ROOT, 'artifacts')
if not os.path.exists(ARTIFACTS): os.makedirs(ARTIFACTS, exist_ok=True)

# Static HTML checks using BeautifulSoup
def static_checks(html_path):
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html5lib')
        # No absolute positioning by style attributes or inline styles
        absolute_elems = []
        for el in soup.select('[style]'):
            style = el['style']
            if 'position: absolute' in style.replace(' ','').lower():
                absolute_elems.append(str(el.name))
        if absolute_elems:
            REPORT['errors'].append('Found inline absolute positioning in: ' + ','.join(absolute_elems))
        # Also check styles.css for 'position: absolute' occurrences
        css_path = os.path.join(os.path.dirname(html_path), 'styles.css')
        if os.path.exists(css_path):
            with open(css_path, 'r', encoding='utf-8') as cssf:
                css_text = cssf.read()
            if 'position: absolute' in css_text.replace('\n',' '):
                REPORT['errors'].append('styles.css contains "position: absolute" which may cause overlaps')

        # Duplicate IDs
        ids = [e['id'] for e in soup.find_all(attrs={'id': True})]
        dupes = set([x for x in ids if ids.count(x) > 1])
        if dupes:
            REPORT['errors'].append('Duplicate IDs: ' + ','.join(dupes))

        # All images must have alt
        imgs_missing_alt = [img for img in soup.find_all('img') if not img.has_attr('alt') or not img['alt'].strip()]
        if imgs_missing_alt:
            REPORT['errors'].append('Images missing alt: ' + ','.join([str(i) for i in imgs_missing_alt[:5]]))

        # headers with role=separator
        time_headers = soup.select('.time-header')
        bad_headers = [h for h in time_headers if not h.has_attr('role') or h['role']!='separator']
        if bad_headers:
            REPORT['errors'].append('Time headers missing role=separator')

        # if any static errors, return False
        if REPORT['errors']:
            return False
        return True
    except Exception as e:
        REPORT['errors'].append('Static check exception: ' + str(e))
        return False

# Rendered checks using Playwright
def rendered_checks(url):
    try:
        if not PLAYWRIGHT_AVAILABLE:
            REPORT['errors'].append('Playwright not installed; rendered checks skipped')
            return False
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)
            page.wait_for_load_state('networkidle')

            # gather visible messages and bounding boxes
            boxes = page.eval_on_selector_all('.message', 'els => els.map(e => ({x: e.getBoundingClientRect().x, y: e.getBoundingClientRect().y, w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height}))')
            # check intersections
            def intersect(a, b):
                return not (a['x'] + a['w'] <= b['x'] or b['x'] + b['w'] <= a['x'] or a['y'] + a['h'] <= b['y'] or b['y'] + b['h'] <= a['y'])
            overlaps = 0
            for i in range(len(boxes)):
                for j in range(i+1, len(boxes)):
                    if intersect(boxes[i], boxes[j]):
                        # allow tiny overlap less than or equal to 1px
                        # compute overlap area
                        ox = min(boxes[i]['x']+boxes[i]['w'], boxes[j]['x']+boxes[j]['w']) - max(boxes[i]['x'], boxes[j]['x'])
                        oy = min(boxes[i]['y']+boxes[i]['h'], boxes[j]['y']+boxes[j]['h']) - max(boxes[i]['y'], boxes[j]['y'])
                        if ox > 1 and oy > 1:
                            overlaps += 1
            REPORT['layout_non_overlap'] = overlaps == 0
            if not REPORT['layout_non_overlap']:
                page.screenshot(path=os.path.join(ARTIFACTS,'layout_overlap.png'))

            # check for forced rotation transforms on images
            transforms = page.eval_on_selector_all('.media', 'els => els.map(e => window.getComputedStyle(e).transform)')
            forced = [t for t in transforms if t and t != 'none']
            REPORT['no_forced_rotation'] = len(forced) == 0
            if not REPORT['no_forced_rotation']:
                context.storage_state(path=os.path.join(ARTIFACTS,'rotation_state.json'))

            # media aspect ratio check: compare natural sizes to client sizes
            ratios_ok = True
            imgs = page.query_selector_all('.media')
            for i, img in enumerate(imgs):
                natural = page.evaluate('i => document.querySelectorAll(\'.media\')[i].naturalWidth', i)
                natural_h = page.evaluate('i => document.querySelectorAll(\'.media\')[i].naturalHeight', i)
                client_w = page.evaluate('i => document.querySelectorAll(\'.media\')[i].clientWidth', i)
                client_h = page.evaluate('i => document.querySelectorAll(\'.media\')[i].clientHeight', i)
                if natural and natural_h and client_w and client_h:
                    ratio_n = natural / natural_h
                    ratio_c = client_w / client_h
                    if abs(ratio_n - ratio_c) / ratio_n > 0.02:
                        ratios_ok = False
                        break
            REPORT['media_aspect_ratio_ok'] = ratios_ok
            if not ratios_ok:
                page.screenshot(path=os.path.join(ARTIFACTS,'media_ratio.png'))

            # header stability: measure scrollTop before and after simulate insertions
            def check_header_stability():
                page.evaluate('window.scrollTo(0, document.getElementById(\'chat\').scrollHeight)')
                # capture scroll position
                before = page.evaluate('() => document.getElementById(\'chat\').scrollTop')
                for _ in range(5):
                    page.evaluate('() => window.simulateInsertOnce && window.simulateInsertOnce()')
                page.wait_for_timeout(200)
                after = page.evaluate('() => document.getElementById(\'chat\').scrollTop')
                # scroll jumps large if header insert moves content significantly
                return abs(after - before) <= 30
            REPORT['time_header_stability'] = check_header_stability()

            # Accessibility smoke: unique IDs
            ids = page.eval_on_selector_all('[id]', 'els => els.map(e=>e.id)')
            dups = [x for x in set(ids) if ids.count(x) > 1]
            if dups:
                REPORT['errors'].append('Duplicate IDs in runtime: ' + ','.join(dups))
            # imgs have alt and headers role
            missing_alt = page.eval_on_selector_all('img', 'els => els.filter(e=>!e.alt || e.alt.trim()==="").map(e=>e.src)')
            headers_no_role = page.eval_on_selector_all('.time-header', 'els => els.filter(h=>!h.getAttribute("role")).map(h=>h.innerText)')
            REPORT['accessibility_smoke'] = (len(dups)==0 and len(missing_alt)==0 and len(headers_no_role)==0)

            # Save screenshot
            page.screenshot(path=os.path.join(ARTIFACTS,'page.png'), full_page=True)
            context.close()
            browser.close()
            return True
    except Exception as e:
        REPORT['errors'].append('Rendered check exception: ' + str(e))
        return False

if __name__ == '__main__':
    page_path = os.path.join(ROOT, 'ui_fixed.html')
    static_ok = static_checks(page_path)
    if not static_ok:
        print('Static checks failed:', REPORT['errors'])
    # start playwright
    url = 'http://localhost:8080/ui_fixed.html'
    # ensure pages exist
    rendered_ok = rendered_checks(url)
    # persist report
    with open(os.path.join(ARTIFACTS,'test-report.json'),'w',encoding='utf-8') as f:
        json.dump(REPORT, f, indent=2)
    # print summary
    print('Test summary:')
    print(json.dumps(REPORT, indent=2))
    # produce success if all checks true
    all_pass = REPORT['layout_non_overlap'] and REPORT['media_aspect_ratio_ok'] and REPORT['no_forced_rotation'] and REPORT['time_header_stability'] and REPORT['accessibility_smoke']
    if all_pass:
        print('All checks passed.')
        sys.exit(0)
    else:
        print('One or more checks failed.')
        sys.exit(1)
