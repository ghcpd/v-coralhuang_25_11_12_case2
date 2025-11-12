import os
import sys
import json
import time
from pathlib import Path
from bs4 import BeautifulSoup

REPORT = {
    'layout_non_overlap': False,
    'media_aspect_ratio_ok': False,
    'no_forced_rotation': False,
    'time_header_stability': False,
    'accessibility_smoke': False,
    'logs': []
}

ARTIFACT_DIR = Path('artifacts')
ARTIFACT_DIR.mkdir(exist_ok=True)

ROOT = Path('.').resolve()
UI = ROOT / 'ui_fixed.html'

# Static checks using BeautifulSoup
soup = BeautifulSoup(UI.read_text(encoding='utf-8'), 'html5lib')

# Accessibility: no duplicate IDs
ids = [el.get('id') for el in soup.find_all(attrs={'id': True})]
dups = [i for i in ids if ids.count(i) > 1]
if dups:
    REPORT['logs'].append('duplicate-ids: ' + ','.join(set(dups)))
else:
    REPORT['logs'].append('no-duplicate-ids')

# images have alt attributes
imgs = soup.find_all('img')
missing_alt = [str(i) for i in imgs if not i.get('alt')]
if missing_alt:
    REPORT['logs'].append('missing-alt: ' + ','.join(missing_alt))
else:
    REPORT['logs'].append('all-images-have-alt')

# time headers have role separator
time_headers = soup.select('.time-header')
missing_role = [th for th in time_headers if th.get('role') != 'separator']
if missing_role:
    REPORT['logs'].append('time-headers-missing-role')
else:
    REPORT['logs'].append('time-headers-role-ok')

# check styles for rotate usage
css_text = ''
for cssf in (ROOT / 'styles.css',):
    if cssf.exists():
        css_text += cssf.read_text(encoding='utf-8')
if 'rotate(' in css_text:
    REPORT['logs'].append('css-rotate-found')
else:
    REPORT['logs'].append('no-css-rotate')

# If static fails certain checks, set accessibility flag accordingly
REPORT['accessibility_smoke'] = (len(dups) == 0) and (len(missing_alt) == 0) and (len(missing_role) == 0)

# --- Rendered checks with Playwright ---
try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    REPORT['logs'].append('playwright-import-failed: ' + str(e))
    Path('artifacts/test-report.json').write_text(json.dumps(REPORT, indent=2))
    print('Playwright import failed; install playwright and run playwright install to fetch browsers')
    sys.exit(1)

# helper: check for overlap
def rectangles_intersect(a, b, epsilon=1.0):
    # a and b are dictionaries with x,y,w,h computed from bounding box
    # returns True if intersection area > epsilon
    ax1, ay1, ax2, ay2 = a['left'], a['top'], a['right'], a['bottom']
    bx1, by1, bx2, by2 = b['left'], b['top'], b['right'], b['bottom']
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    if ix2 <= ix1 or iy2 <= iy1:
        return False
    area = (ix2 - ix1) * (iy2 - iy1)
    return area > epsilon

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    page.goto('http://localhost:8080/ui_fixed.html')
    page.wait_for_selector('.message-list')

    # Layout non-overlap: sample while fast scrolling
    has_overlap = False
    bboxes = []
    for pos in [0, 0.25, 0.5, 0.75, 1.0]:
        # scroll message-list container
        page.evaluate("(pos)=>{const ml=document.getElementById('message-list'); ml.scrollTop=(ml.scrollHeight-ml.clientHeight)*pos;}", pos)
        time.sleep(0.2)
        boxes = page.evaluate("() => Array.from(document.querySelectorAll('.message')).map(e=>{const r=e.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom}})")
        # check overlap between visible boxes
        for i in range(len(boxes)):
            for j in range(i+1,len(boxes)):
                if rectangles_intersect(boxes[i], boxes[j], epsilon=1.0):
                    has_overlap = True
                    REPORT['logs'].append(f'overlap-detected between {i} and {j} at pos {pos}')
    REPORT['layout_non_overlap'] = not has_overlap

    # Media checks: aspect ratio & rotation
    media_ok = True
    imgs = page.query_selector_all('img')
    if not imgs:
        REPORT['logs'].append('no-images-found-on-page')
        media_ok = False
    else:
        for img in imgs:
            # check computed transform
            transform = page.evaluate('(img)=>getComputedStyle(img).transform', img)
            if transform and transform != 'none':
                media_ok = False
                REPORT['logs'].append('image-has-transform:' + transform)
            # natural and client ratio
            ratio = page.evaluate('(img)=>({nw:img.naturalWidth, nh:img.naturalHeight, cw:img.clientWidth, ch:img.clientHeight})', img)
            nw, nh, cw, ch = ratio['nw'], ratio['nh'], ratio['cw'], ratio['ch']
            if nh == 0:
                media_ok = False
                REPORT['logs'].append('image-natural-height-zero')
                continue
            natural_ratio = nw/nh
            client_ratio = cw/ch if ch else 1
            rel = abs(natural_ratio - client_ratio) / (natural_ratio if natural_ratio != 0 else 1)
            if rel > 0.02:
                media_ok = False
                REPORT['logs'].append(f'image-aspect-ratio-mismatch: natural {natural_ratio:.3f} client {client_ratio:.3f}')
    REPORT['media_aspect_ratio_ok'] = media_ok
    REPORT['no_forced_rotation'] = media_ok and ('css-rotate-found' not in REPORT['logs'])

    # header stability: record header positions & ids then insert a new message and compare
    headerInfoBefore = page.evaluate("() => Array.from(document.querySelectorAll('.time-header')).map(h=>({id:h.id, y:h.getBoundingClientRect().top}))")
    # ensure stable anchor when inserting
    page.evaluate('()=>window.simulateInsertOnce()')
    time.sleep(0.1)
    headerInfoAfter = page.evaluate("() => Array.from(document.querySelectorAll('.time-header')).map(h=>({id:h.id, y:h.getBoundingClientRect().top}))")

    stable = True
    for b, a in zip(headerInfoBefore, headerInfoAfter):
        if b['id'] != a['id']:
            stable = False
            REPORT['logs'].append('header-id-reordered: ' + b['id'] + ' -> ' + a['id'])
        if abs(b['y'] - a['y']) > 30:  # allow small shift when new message inserted
            stable = False
            REPORT['logs'].append('header-moved-too-much: ' + b['id'])
    REPORT['time_header_stability'] = stable

    # accessibility smoke checks in rendered page
    # check presence of role on time headers
    missing_role_rendered = page.evaluate("() => Array.from(document.querySelectorAll('.time-header')).some(h=>!h.getAttribute('role'))")
    has_alt_missing = page.evaluate("() => Array.from(document.querySelectorAll('img')).some(i=>!i.getAttribute('alt'))")
    has_duplicate_ids = page.evaluate("() => { const ids = Array.from(document.querySelectorAll('[id]')).map(e=>e.id); return ids.filter((v,i,a)=>a.indexOf(v)!==i) }")

    REPORT['accessibility_smoke'] = REPORT['accessibility_smoke'] and (not missing_role_rendered) and (not has_alt_missing) and (len(has_duplicate_ids)==0)

    # Save a screenshot and logs
    ss = ARTIFACT_DIR / 'screenshots'
    ss.mkdir(exist_ok=True)
    shot = ss / 'rendered.png'
    page.screenshot(path=str(shot), full_page=True)

    browser.close()

# Write final report
REPORT['timestamp_end'] = time.time()
REPORT['timestamp_start'] = REPORT.get('timestamp_start', time.time())
with open('artifacts/test-report.json','w',encoding='utf-8') as fh:
    json.dump(REPORT, fh, indent=2)

print('Checks:')
for k in ['layout_non_overlap','media_aspect_ratio_ok','no_forced_rotation','time_header_stability','accessibility_smoke']:
    print(k, REPORT[k])

if all([REPORT['layout_non_overlap'], REPORT['media_aspect_ratio_ok'], REPORT['no_forced_rotation'], REPORT['time_header_stability'], REPORT['accessibility_smoke']]):
    print('All checks passed')
    sys.exit(0)
else:
    print('Some checks failed; see artifacts/test-report.json')
    sys.exit(1)
