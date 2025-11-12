import json
import os
import time
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(__file__)
REPORT = os.path.join(ROOT, 'artifacts', 'test-report.json')
LOG = os.path.join(ROOT, 'artifacts', 'test.log')
SCREEN = os.path.join(ROOT, 'artifacts', 'screenshot.png')

os.makedirs(os.path.join(ROOT, 'artifacts'), exist_ok=True)

results = {
    'layout_non_overlap': False,
    'media_aspect_ratio_ok': False,
    'no_forced_rotation': False,
    'time_header_stability': False,
    'accessibility_smoke': False,
    'details': {}
}

# Static checks with BeautifulSoup
html_path = os.path.join(ROOT, 'ui_fixed.html')
with open(html_path, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html5lib')

# accessibility: duplicate ids
ids = [el.get('id') for el in soup.find_all(attrs={'id': True})]
dup_ids = [x for x in set(ids) if ids.count(x) > 1]
results['details']['dup_ids'] = dup_ids

# buttons have aria-label (or text)
buttons = soup.find_all('button')
missing_labels = [b for b in buttons if not (b.get('aria-label') or b.text.strip())]
results['details']['missing_button_labels'] = len(missing_labels)

# images have alt
imgs = soup.find_all('img')
missing_alts = [str(i) for i in imgs if not i.get('alt')]
results['details']['missing_alts'] = missing_alts

# header role check
headers_with_role = [h for h in soup.find_all(class_='time-header') if h.get('role')]
results['details']['time_header_role_count'] = len(headers_with_role)

# determine pass/fail for static logistic
results['accessibility_smoke'] = (len(dup_ids) == 0 and len(missing_labels) == 0 and len(missing_alts) == 0 and len(headers_with_role) > 0)

# Run Playwright tests for rendering checks
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    url = 'http://localhost:8080/ui_fixed.html'
    page.goto(url)
    time.sleep(1)

    # ensure messages present
    msgs = page.query_selector_all('.message')
    if not msgs:
        results['details']['error'] = 'No .message nodes found in page'
    # check overlap while different scroll positions
    def check_overlap():
        rects = []
        nodes = page.query_selector_all('.message')
        for n in nodes:
            box = n.bounding_box()
            if not box:
                continue
            rects.append(box)
        # check pairwise overlaps
        overlaps = []
        def intersect(a,b):
            x_overlap = max(0, min(a['x']+a['width'], b['x']+b['width']) - max(a['x'], b['x']))
            y_overlap = max(0, min(a['y']+a['height'], b['y']+b['height']) - max(a['y'], b['y']))
            return x_overlap * y_overlap
        for i in range(len(rects)):
            for j in range(i+1, len(rects)):
                area = intersect(rects[i], rects[j])
                if area > 1: # allow 1px tolerance
                    overlaps.append((i,j,area))
        return overlaps

    overlap_found = False
    for top in [0, page.evaluate('document.getElementById("chat").scrollHeight/2'), page.evaluate('document.getElementById("chat").scrollHeight')]:
        page.evaluate('document.getElementById("chat").scrollTop = %s' % top)
        time.sleep(0.25)
        ov = check_overlap()
        if ov:
            results['details'].setdefault('overlaps', []).append({'top': top, 'overlaps': ov})
            overlap_found = True
    results['layout_non_overlap'] = not overlap_found

    # media aspect ratio & rotation
    medias = page.query_selector_all('.media')
    ratio_ok = True
    rotation_ok = True
    media_details = []
    for m in medias:
        natural = page.evaluate('(e) => ({w: e.naturalWidth, h: e.naturalHeight})', m)
        client = page.evaluate('(e) => ({w: e.clientWidth, h: e.clientHeight})', m)
        if natural['w'] == 0 or natural['h'] == 0:
            ratio_ok = False
            media_details.append({'reason':'zero natural dimensions', 'natural': natural, 'client': client})
            continue
        ratio_n = natural['w'] / natural['h']
        ratio_c = client['w'] / client['h'] if client['h'] else 0
        # percent diff
        diff = abs(ratio_n - ratio_c) / ratio_n
        media_details.append({'natural': natural, 'client': client, 'ratio_diff': diff})
        if diff > 0.02:
            ratio_ok = False
        # check rotation apply
        cs = page.evaluate('(e) => window.getComputedStyle(e).transform', m)
        if cs and cs != 'none' and 'rotate' in cs:
            rotation_ok = False
    results['media_aspect_ratio_ok'] = ratio_ok
    results['no_forced_rotation'] = rotation_ok
    results['details']['media'] = media_details

    # header stability and scroll preserving
    stabilities = []
    stable_ok = True
    for i in range(5):
        before = page.evaluate('() => document.getElementById("chat").scrollTop')
        page.evaluate('() => window.simulateInsertOnce && window.simulateInsertOnce()')
        time.sleep(0.1)
        after = page.evaluate('() => document.getElementById("chat").scrollTop')
        stabilities.append(after - before)
        if abs(after - before) > 50: # more than 50 px indicates a jump
            stable_ok = False
    results['time_header_stability'] = stable_ok
    results['details']['header_scroll_deltas'] = stabilities

    # re-check duplicate ids in live DOM
    ids = page.evaluate("() => Array.from(document.querySelectorAll('[id]')).map(e=>e.id)")
    dup_ids = [x for x in set(ids) if ids.count(x) > 1]
    results['details']['live_dup_ids'] = dup_ids

    # accessibility checks
    alts_missing = page.evaluate("() => Array.from(document.querySelectorAll('img')).filter(i=>!i.hasAttribute('alt')).map(i=>i.outerHTML)")
    results['details']['missing_alts_live'] = alts_missing

    # screenshot
    page.screenshot(path=SCREEN, full_page=True)

    # write log
    with open(LOG, 'w', encoding='utf-8') as lf:
        lf.write(json.dumps(results, indent=2))

    # mark final
    browser.close()

# Final summary decision
all_ok = results['layout_non_overlap'] and results['media_aspect_ratio_ok'] and results['no_forced_rotation'] and results['time_header_stability'] and results['accessibility_smoke']
if not all_ok:
    results['summary'] = 'FAIL'
    with open(REPORT, 'w', encoding='utf-8') as r:
        json.dump(results, r, indent=2)
    print('FAILURES: see artifacts/test-report.json')
    raise SystemExit(1)
else:
    results['summary'] = 'PASS'
    with open(REPORT, 'w', encoding='utf-8') as r:
        json.dump(results, r, indent=2)
    print('All checks passed')
    raise SystemExit(0)
