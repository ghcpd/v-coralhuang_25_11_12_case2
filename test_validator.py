#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
UI = 'http://localhost:8080/ui_fixed.html'
TIMEOUT = 15000

artifacts = ROOT / 'artifacts'
artifacts.mkdir(exist_ok=True)

report = {
    'layout_non_overlap': {'ok': False, 'details': ''},
    'media_aspect_ratio_ok': {'ok': False, 'details': ''},
    'no_forced_rotation': {'ok': False, 'details': ''},
    'time_header_stability': {'ok': False, 'details': ''},
    'accessibility_smoke': {'ok': False, 'details': ''}
}

start_ts = time.time()

# Static checks
try:
    with open(ROOT / 'ui_fixed.html', 'r', encoding='utf-8') as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html5lib')

    # Duplicate id check
    ids = [tag.get('id') for tag in soup.find_all(True) if tag.get('id')]
    duplicates = set([x for x in ids if ids.count(x) > 1])
    if duplicates:
        report['accessibility_smoke']['ok'] = False
        report['accessibility_smoke']['details'] = 'Duplicate IDs: ' + ','.join(sorted(duplicates))
    else:
        report['accessibility_smoke']['ok'] = True

    # time header role check
    headers = soup.select('.time-header')
    if not headers or not all(h.get('role') == 'separator' for h in headers):
        report['accessibility_smoke']['ok'] = False
        report['accessibility_smoke']['details'] = report['accessibility_smoke'].get('details','') + ' Missing role=separator on time headers.'

    # images have alt attributes
    imgs = soup.find_all('img')
    missing_alt = [str(i) for i in imgs if not i.get('alt')]
    if missing_alt:
        report['accessibility_smoke']['ok'] = False
        report['accessibility_smoke']['details'] += ' Missing alt on some images.'

except Exception as e:
    report['accessibility_smoke']['ok'] = False
    report['accessibility_smoke']['details'] = 'Static parse failed: ' + str(e)

# Rendered checks with Playwright
try:
    with sync_playwright() as p:
        # Use local playwright binary if present or fall back to msedge channel
        import os
        chrome_root = os.path.join(os.environ.get('USERPROFILE',''), 'AppData', 'Local', 'ms-playwright', 'chromium_headless_shell-1194')
        chrome_exe = os.path.join(chrome_root, 'chrome.exe')
        try:
            if os.path.exists(chrome_exe):
                browser = p.chromium.launch(headless=True, executable_path=chrome_exe)
            else:
                browser = p.chromium.launch(headless=True, channel='msedge')
        except Exception:
            browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = context.new_page()
        res = page.goto(UI, timeout=TIMEOUT)
        if res.status != 200:
            raise RuntimeError('Server returned status ' + str(res.status))
        page.wait_for_selector('.chat-container')

        # make sure we have some messages
        page.wait_for_selector('.message', timeout=5000)

        def rects(elements):
            return page.evaluate('''(els)=>els.map(e=>{const r=e.getBoundingClientRect(); return {id: e.id, top: r.top, left: r.left, right: r.right, bottom: r.bottom, w: r.width, h: r.height}})''', elements)

        # sample positions while fast scroll
        messages = page.query_selector_all('.message')
        if not messages:
            raise RuntimeError('No .message elements found')

        # Function to check overlap
        def any_overlap(samples):
            eps = 1.0
            for a in range(len(samples)):
                A = samples[a]
                for b in range(a+1, len(samples)):
                    B = samples[b]
                    # If both visible - check intersect
                    if (A['w'] <= eps or A['h'] <= eps or B['w'] <= eps or B['h'] <= eps):
                        continue
                    horiz = min(A['right'], B['right']) - max(A['left'], B['left'])
                    vert = min(A['bottom'], B['bottom']) - max(A['top'], B['top'])
                    if horiz > eps and vert > eps:
                        return True, (A['id'], B['id'])
            return False, None

        # sample frames while quick scrolling top->bottom->top multiple times
        frames = []
        for i in range(12):
            pos = (i % 2) * 1.0
            # compute an intermediate scroll target depending bottom or top
            if pos == 1.0:
                page.evaluate('document.querySelector(\".chat-container\").scrollTop = document.querySelector(\".chat-container\").scrollHeight;')
            else:
                page.evaluate('document.querySelector(\".chat-container\").scrollTop = 0;')
            # let render settle
            page.wait_for_timeout(40)
            # collect all rects currently visible
            rects_now = page.evaluate('''()=>Array.from(document.querySelectorAll('.message')).map(e=>{const r=e.getBoundingClientRect();return {id:e.id, left:r.left, right:r.right, top:r.top, bottom:r.bottom, w:r.width,h:r.height}})''')
            frames.append(rects_now)

        # check each frame for overlap
        overlap_found = False
        o_pair = None
        for rects_now in frames:
            overlap_found, o_pair = any_overlap(rects_now)
            if overlap_found:
                break
        report['layout_non_overlap']['ok'] = not overlap_found
        report['layout_non_overlap']['details'] = '' if not overlap_found else f'Overlap detected between {o_pair}'

        # check CSS transform rotate not applied to images
        transforms = page.evaluate('''()=>Array.from(document.querySelectorAll('img.media')).map(i=>getComputedStyle(i).transform)''')
        with_rotation = [t for t in transforms if t and t != 'none']
        report['no_forced_rotation']['ok'] = (len(with_rotation) == 0)
        report['no_forced_rotation']['details'] = 'transform found: ' + ','.join(with_rotation) if with_rotation else ''

        # check media aspect ratio for visible media images
        media_checks_ok = True
        media_details = []
        media_nodes = page.query_selector_all('img.media')
        for m in media_nodes:
            # ensure loaded, then evaluate dimensions
            page.wait_for_function('(img)=>img.complete && img.naturalWidth > 0', arg=m, timeout=5000)
            dims = page.evaluate('img=>({nw:img.naturalWidth, nh:img.naturalHeight, cw: img.clientWidth, ch: img.clientHeight, src: img.src})', m)
            if not dims or dims['nh'] == 0:
                media_checks_ok = False
                media_details.append('Media failed to load: ' + (dims and dims.get('src','')))
                continue
            natural_ratio = dims['nw'] / dims['nh']
            current_ratio = dims['cw'] / dims['ch'] if dims['ch'] > 0 else None
            if current_ratio is None:
                media_checks_ok = False
                media_details.append('zero height for media ' + dims['src'])
                continue
            # within 2% tolerance
            if abs(current_ratio - natural_ratio) / natural_ratio > 0.02:
                media_checks_ok = False
                media_details.append(f"Ratio mismatch for {dims['src']}: nat={natural_ratio:.3f} cur={current_ratio:.3f}")
        report['media_aspect_ratio_ok']['ok'] = media_checks_ok
        report['media_aspect_ratio_ok']['details'] = '; '.join(media_details)

        # header stability test: record headers and positions, insert once and verify
        before_headers = page.evaluate('Array.from(document.querySelectorAll(\".time-header\")).map(h=>({id:h.id, top:h.getBoundingClientRect().top}))')
        before_scroll = page.eval_on_selector('.chat-container', 'el => el.scrollTop')
        # call simulateInsertOnce
        page.evaluate('window.simulateInsertOnce && window.simulateInsertOnce()')
        page.wait_for_timeout(200)
        after_headers = page.evaluate('Array.from(document.querySelectorAll(\".time-header\")).map(h=>({id:h.id, top:h.getBoundingClientRect().top}))')
        after_scroll = page.eval_on_selector('.chat-container', 'el => el.scrollTop')

        # check IDs unique and order not reversed for existing headers
        before_ids = [h['id'] for h in before_headers]
        after_ids = [h['id'] for h in after_headers]
        duplicates_ids = set([x for x in after_ids if after_ids.count(x) > 1])
        ok_headers = True
        if duplicates_ids:
            ok_headers = False
            report['time_header_stability']['details'] = 'Duplicate header IDs after insertion: ' + ','.join(sorted(duplicates_ids))
        else:
            # ensure all before IDs are still present and in same relative order among themselves
            brief = [h for h in after_ids if h in before_ids]
            # if the sequence of before IDs in the after list should maintain order of before_ids
            idx_map = [brief.index(x) for x in before_ids if x in brief]
            if idx_map != sorted(idx_map):
                ok_headers = False
                report['time_header_stability']['details'] = 'Header relative order changed'

        # check anchor scroll jump: small delta expected (<=120 px)
        if abs(after_scroll - before_scroll) > 120:
            ok_headers = False
            report['time_header_stability']['details'] = report['time_header_stability'].get('details','') + f' Big scroll jump ({after_scroll - before_scroll}px)'

        report['time_header_stability']['ok'] = ok_headers

        # accessibility (rendered): check no duplicate IDs in DOM
        ids_rendered = page.evaluate('Array.from(document.querySelectorAll("*[id]")).map(e=>e.id)')
        dup_ids_rendered = set([x for x in ids_rendered if ids_rendered.count(x) > 1])
        if dup_ids_rendered:
            report['accessibility_smoke']['ok'] = False
            report['accessibility_smoke']['details'] = 'Duplicate IDs in rendered DOM: ' + ','.join(sorted(dup_ids_rendered))
        else:
            # ensure message roles and header roles present in DOM
            all_headers = page.query_selector_all('.time-header')
            all_ok_roles = all([page.evaluate('(n)=>n.getAttribute("role") === "separator"', h) for h in all_headers])
            if not all_ok_roles:
                report['accessibility_smoke']['ok'] = False
                report['accessibility_smoke']['details'] = report['accessibility_smoke'].get('details','') + ' Header roles invalid.'

        # if any major check false: screenshot
        failed = [k for k,v in report.items() if not v['ok']]
        if failed:
            out = artifacts / 'screenshots'
            out.mkdir(exist_ok=True)
            ss = out / ('fail-' + str(int(time.time())) + '.png')
            page.screenshot(path=str(ss), full_page=True)
            report['screenshot'] = str(ss)

        # end Playwright
        context.close()
        browser.close()

except Exception as e:
    report['layout_non_overlap']['ok'] = report['layout_non_overlap']['ok'] or False
    # write failure reason
    report['error'] = str(e)
    print('Rendered check failed:', e)

end_ts = time.time()

report['meta'] = {'start': start_ts, 'end': end_ts, 'duration': end_ts - start_ts}

with open(artifacts / 'test-report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)

# print summary
print('TEST SUMMARY:')
for k,v in report.items():
    if k == 'meta': continue
    if isinstance(v, dict):
        print(f" - {k}: {'PASS' if v.get('ok') else 'FAIL'} {v.get('details','')}")

# exit non-zero if any failures
all_ok = True
for key, val in report.items():
    if key == 'meta':
        continue
    if isinstance(val, dict) and not val.get('ok'):
        all_ok = False
if not all_ok or report.get('error'):
    sys.exit(1)
else:
    sys.exit(0)
