import os
import time
import json
from bs4 import BeautifulSoup
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
UI_PATH = ROOT / 'ui_fixed.html'
REPORTS_DIR = ROOT / 'artifacts'
REPORTS_DIR.mkdir(exist_ok=True)
REPORT_JSON = REPORTS_DIR / 'test-report.json'
LOG_FILE = REPORTS_DIR / 'validator.log'
SCREENSHOT_DIR = REPORTS_DIR / 'screenshots'
SCREENSHOT_DIR.mkdir(exist_ok=True)

report = {
    'layout_non_overlap': {'passed': False, 'message': ''},
    'media_aspect_ratio_ok': {'passed': False, 'message': ''},
    'no_forced_rotation': {'passed': False, 'message': ''},
    'time_header_stability': {'passed': False, 'message': ''},
    'accessibility_smoke': {'passed': False, 'message': ''},
}

logs = []

def log(msg):
    print(msg)
    logs.append(msg)

# Static checks with BeautifulSoup
log('Starting static checks...')
with open(UI_PATH, 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html5lib')

# duplicate IDs
ids = [tag.get('id') for tag in soup.find_all(attrs={'id': True})]
dups = set([i for i in ids if ids.count(i) > 1])
if dups:
    report['accessibility_smoke']['message'] = f'Duplicate IDs found: {dups}'
    log(report['accessibility_smoke']['message'])
else:
    report['accessibility_smoke']['passed'] = True
    report['accessibility_smoke']['message'] = 'No duplicate IDs'
    log(report['accessibility_smoke']['message'])

# time headers have role separator
time_headers = soup.find_all(class_='time-header')
th_bad = [h for h in time_headers if h.get('role') != 'separator']
if th_bad:
    report['time_header_stability']['message'] = 'Some time headers missing role=separator.'
    log(report['time_header_stability']['message'])
else:
    log('Time headers have role=separator.')

# images have alt attributes
imgs = soup.find_all('img')
missing_alt = [str(i) for i in imgs if not i.get('alt')]
if missing_alt:
    report['accessibility_smoke']['passed'] = False
    report['accessibility_smoke']['message'] += '; Images missing alt: ' + ','.join(missing_alt)
    log('Images missing alt: ' + str(len(missing_alt)))
else:
    log('All images have alt attributes.')

# Now run Playwright tests for rendered checks
log('Starting rendered checks with Playwright...')
start_time = time.time()
playwright = sync_playwright().start()
browser = playwright.chromium.launch(headless=True)
context = browser.new_context(viewport={'width': 1024, 'height': 768})
page = context.new_page()

try:
    page.goto('http://localhost:8080/ui_fixed.html')
    page.wait_for_load_state('networkidle')

    # helper: get message bounding boxes
    def get_message_bboxes():
        return page.evaluate('''() => {
            const nodes = Array.from(document.querySelectorAll('.message'));
            return nodes.map(n => {
                const r = n.getBoundingClientRect();
                return {id: n.id, left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height};
            });
        }''')

    # sample multiple times while scrolling
    has_overlap = False
    for i in range(10):
        # scroll to bottom or top
        if i % 2 == 0:
            page.evaluate('() => {const chat=document.getElementById("chat"); chat.scrollTop = chat.scrollHeight;}')
        else:
            page.evaluate('() => {const chat=document.getElementById("chat"); chat.scrollTop = 0;}')
        page.wait_for_timeout(120)
        boxes = get_message_bboxes()
        # check pairwise overlap
        for j in range(len(boxes)):
            for k in range(j+1, len(boxes)):
                a = boxes[j]
                b = boxes[k]
                # only consider visible elements within viewport
                if a['height'] <= 0 or b['height'] <= 0: continue
                # compute intersection
                ix = max(0, min(a['right'], b['right']) - max(a['left'], b['left']))
                iy = max(0, min(a['bottom'], b['bottom']) - max(a['top'], b['top']))
                if ix > 1 and iy > 1:
                    log(f'Overlap detected between {a["id"]} and {b["id"]}: {ix}x{iy}')
                    has_overlap = True
    if not has_overlap:
        report['layout_non_overlap']['passed'] = True
        report['layout_non_overlap']['message'] = 'No overlaps detected under sampling scroll.'
        log(report['layout_non_overlap']['message'])
    else:
        report['layout_non_overlap']['message'] = 'Overlaps detected during scroll; see logs.'

    # Check for transform rotate on images
    transforms = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('img.media, img.avatar')).map(i => ({id:i.id||null, transform: getComputedStyle(i).transform}));
    }''')
    has_rotate = False
    for t in transforms:
        tr = t['transform']
        if tr and tr != 'none' and 'matrix' in tr:
            # simple rotation detection: matrix with values not identity
            if tr != 'matrix(1, 0, 0, 1, 0, 0)':
                has_rotate = True
                log(f'Found non-identity transform: {tr} for id {t["id"]}')
    if not has_rotate:
        report['no_forced_rotation']['passed'] = True
        report['no_forced_rotation']['message'] = 'No forced rotation found.'
        log(report['no_forced_rotation']['message'])
    else:
        report['no_forced_rotation']['message'] = 'Forced rotations detected.'

    # Check media aspect ratios
    mismatch = False
    media_info = page.evaluate('''() => {
        return Array.from(document.querySelectorAll('img.media')).map(i => ({id:i.id||null, naturalWidth: i.naturalWidth, naturalHeight: i.naturalHeight, clientWidth: i.clientWidth, clientHeight: i.clientHeight}));
    }''')
    for m in media_info:
        if m['naturalWidth'] == 0 or m['naturalHeight'] == 0:
            continue
        natural_ratio = m['naturalWidth'] / m['naturalHeight']
        client_ratio = m['clientWidth'] / m['clientHeight'] if m['clientHeight']>0 else 0
        if abs(client_ratio - natural_ratio) / natural_ratio > 0.02 and client_ratio != 0:
            mismatch = True
            log(f'Aspect ratio mismatch for {m["id"]}: natural {natural_ratio:.2f}, client {client_ratio:.2f}')
    if not mismatch:
        report['media_aspect_ratio_ok']['passed'] = True
        report['media_aspect_ratio_ok']['message'] = 'Media aspect ratios preserved within bounds.'
        log(report['media_aspect_ratio_ok']['message'])
    else:
        report['media_aspect_ratio_ok']['message'] = 'Aspect ratio mismatches detected.'

    # Header stability test: collect header order then call simulateInsertOnce several times
    initial_headers = page.evaluate('''() => Array.from(document.querySelectorAll('.time-header')).map(h => ({id:h.id, top:h.getBoundingClientRect().top}))''')
    log('Initial headers: ' + ','.join([h['id'] for h in initial_headers]))
    header_order_ok = True
    scroll_before = page.evaluate('() => document.getElementById("chat").scrollTop')
    results = []
    for i in range(8):
        result = page.evaluate('() => window.simulateInsertOnce()')
        results.append(result)
        time.sleep(0.08)
    after_headers = page.evaluate('''() => Array.from(document.querySelectorAll('.time-header')).map(h => ({id:h.id, top:Math.round(h.getBoundingClientRect().top)}))''')
    log('After headers: ' + ','.join([h['id'] for h in after_headers]))
    # ensure no duplicate ids and that header order is non-decreasing top position
    prev_top = -99999
    for h in after_headers:
        if h['top'] < prev_top:
            header_order_ok = False
            log(f'Header order changed: {h}')
        prev_top = h['top']
    if header_order_ok:
        report['time_header_stability']['passed'] = True
        report['time_header_stability']['message'] = 'Time headers stable after insertions.'
    else:
        report['time_header_stability']['message'] = 'Header order instability detected.'

    # Accessibility rendered checks
    # check simulate button has aria-label
    sim_btn_label = page.get_attribute('#simulate', 'aria-label')
    if not sim_btn_label:
        report['accessibility_smoke']['passed'] = False
        report['accessibility_smoke']['message'] += '; Simulate button missing aria-label'
        log('Simulate button missing aria-label')
    else:
        # if earlier passed, keep as true
        if report['accessibility_smoke']['passed']:
            report['accessibility_smoke']['message'] += '; Accessibility checks ok.'

    # Save a screenshot
    page.screenshot(path=str(SCREENSHOT_DIR / 'final.png'))

finally:
    browser.close()
    playwright.stop()

# Collect logs into files and write report
with open(LOG_FILE, 'w', encoding='utf-8') as lf:
    lf.write('\n'.join(logs))

# Determine final pass
all_passed = all(v['passed'] for v in report.values())
report_summary = {'passed': all_passed, 'details': report}
with open(REPORT_JSON, 'w', encoding='utf-8') as rf:
    json.dump(report_summary, rf, indent=2)

end_time = time.time()
with open(REPORTS_DIR / 'agent_runtime.txt', 'w') as f:
    f.write(f'start: {start_time}\nend: {end_time}\n')

if not all_passed:
    log('Validation FAILED. See artifacts for details.')
    print(json.dumps(report_summary, indent=2))
    exit(1)
else:
    log('Validation PASSED.')
    print(json.dumps(report_summary, indent=2))
    exit(0)
