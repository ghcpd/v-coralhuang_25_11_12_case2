#!/usr/bin/env python3
"""
Validator script (fixed): uses Playwright and BeautifulSoup to validate UI
"""
import os
import json
import sys
import time
from pathlib import Path
from bs4 import BeautifulSoup

REPORT_PATH = Path('artifacts')
REPORT_PATH.mkdir(exist_ok=True)
REPORT_FILE = REPORT_PATH / 'test-report.json'

URL = 'http://localhost:8080/ui_fixed.html'

results = {
    'layout_non_overlap': False,
    'media_aspect_ratio_ok': False,
    'no_forced_rotation': False,
    'time_header_stability': False,
    'accessibility_smoke': False,
    'errors': []
}

# STATIC CHECKS
html_path = Path('ui_fixed.html')
if not html_path.exists():
    html_path2 = Path('web') / 'ui_fixed.html'
    if html_path2.exists():
        html_path = html_path2

if not html_path.exists():
    results['errors'].append('ui_fixed.html not found')
    with REPORT_FILE.open('w') as fh:
        json.dump(results, fh, indent=2)
    print('ui_fixed.html not found')
    sys.exit(1)

content = html_path.read_text(encoding='utf-8')
soup = BeautifulSoup(content, 'html5lib')

ids = [tag['id'] for tag in soup.find_all(attrs={'id':True})]
duplicate_ids = set([x for x in ids if ids.count(x)>1])
if duplicate_ids:
    results['errors'].append('Duplicate IDs: ' + ','.join(duplicate_ids))
else:
    results['accessibility_smoke'] = True

imgs = soup.find_all('img')
missing_alt = [str(i) for i in imgs if not (i.has_attr('alt') or i.has_attr('aria-label'))]
if missing_alt:
    results['errors'].append('Missing alt for images: ' + ','.join(missing_alt))
    results['accessibility_smoke'] = False

roles = [tag for tag in soup.find_all(True) if tag.has_attr('role')]
if not roles:
    results['errors'].append('No roles found; add at least a role to chat-body or headers')
    results['accessibility_smoke'] = False

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    results['errors'].append('Playwright not available: ' + str(e))
    with REPORT_FILE.open('w') as fh:
        json.dump(results, fh, indent=2)
    print('Playwright not available')
    sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width':1280,'height':960})
    page = context.new_page()
    page.goto(URL, wait_until='networkidle')
    time.sleep(0.5)

    append_test = page.evaluate("""() => { const before = document.querySelector('.chat-body').scrollTop; const el = document.createElement('div'); el.style.height = '220px'; el.style.background = '#f88'; el.className = 'debug-block'; document.querySelector('.chat-body').appendChild(el); const after = document.querySelector('.chat-body').scrollTop; el.remove(); return { before, after }; }""")
    results['append_bottom_test'] = append_test

    check = page.evaluate("""() => {
        const messages = Array.from(document.querySelectorAll('.chat-body .message'));
        const war = {overlaps:[], ratios:[], rotations:[]};
        const rects = messages.map(m => m.getBoundingClientRect());
        for (let i=0;i<rects.length;i++){
            for (let j=i+1;j<rects.length;j++){
                const a = rects[i], b = rects[j];
                if (a.top < b.bottom && b.top < a.bottom && a.left < b.right && b.left < a.right) {
                    const horiz = Math.min(a.right,b.right) - Math.max(a.left,b.left);
                    const vert = Math.min(a.bottom,b.bottom) - Math.max(a.top,b.top);
                    const interArea = (horiz>0 && vert>0) ? horiz*vert : 0;
                    if (interArea > 1) war.overlaps.push({i,j,interArea});
                }
            }
        }
        const imgs = Array.from(document.querySelectorAll('.chat-body img.media, .chat-body .media-wrap img'));
        imgs.forEach(img => {
            const natural = {w: img.naturalWidth, h: img.naturalHeight};
            const client = {w: img.clientWidth, h: img.clientHeight};
            const ratioNatural = natural.w/natural.h || 1;
            const ratioClient = client.w/client.h || 1;
            const percentError = Math.abs((ratioNatural/ratioClient)-1) * 100;
            war.ratios.push({src:img.src, natural, client, percentError});
            const transform = window.getComputedStyle(img).transform || 'none';
            war.rotations.push({src:img.src, transform});
        });
        const beforeScroll = document.querySelector('.chat-body').scrollTop;
        const beforeList = Array.from(document.querySelectorAll('.chat-body > *')).map(e => ({tag:e.tagName, cls:e.className, text:e.innerText && e.innerText.slice(0,30)}));
        window.simulateInsertOnce();
        const mid1 = document.querySelector('.chat-body').scrollTop;
        const mid1List = Array.from(document.querySelectorAll('.chat-body > *')).map(e => ({tag:e.tagName, cls:e.className, text:e.innerText && e.innerText.slice(0,30)}));
        window.simulateInsertOnce();
        const mid2 = document.querySelector('.chat-body').scrollTop;
        const mid2List = Array.from(document.querySelectorAll('.chat-body > *')).map(e => ({tag:e.tagName, cls:e.className, text:e.innerText && e.innerText.slice(0,30)}));
        window.simulateInsertOnce();
        const afterScroll = document.querySelector('.chat-body').scrollTop;
        const afterList = Array.from(document.querySelectorAll('.chat-body > *')).map(e => ({tag:e.tagName, cls:e.className, text:e.innerText && e.innerText.slice(0,30)}));
        return {war, beforeScroll, mid1, mid2, afterScroll, beforeList, mid1List, mid2List, afterList, lastInsertionLocation: window.lastInsertionLocation || null};
    }""")

    overlaps = check['war']['overlaps']
    ratios = check['war']['ratios']
    rotations = check['war']['rotations']
    before = check['beforeScroll'];
    after = check['afterScroll'];

    results['lastInsertionLocation'] = check.get('lastInsertionLocation')
    results['beforeList'] = check.get('beforeList')
    results['mid1List'] = check.get('mid1List')
    results['mid2List'] = check.get('mid2List')
    results['afterList'] = check.get('afterList')

    results['layout_non_overlap'] = len(overlaps)==0
    if not results['layout_non_overlap']:
        results['errors'].append('Overlapping messages found: ' + str(overlaps[:4]))

    bad_ratio = [r for r in ratios if r['percentError']>2]
    results['media_aspect_ratio_ok'] = len(bad_ratio)==0
    if not results['media_aspect_ratio_ok']:
        results['errors'].append('Bad aspect ratios: ' + str(bad_ratio[:4]))

    bad_rot = [r for r in rotations if r['transform']!='none' and r['transform'].includes('rotate')]
    results['no_forced_rotation'] = len(bad_rot)==0
    if not results['no_forced_rotation']:
        results['errors'].append('Found rotated images: ' + str(bad_rot[:4]))

    delta = abs(after-before)
    results['time_header_stability'] = (delta < 50)
    results['scroll_before'] = before
    results['scroll_mid1'] = check.get('mid1')
    results['scroll_mid2'] = check.get('mid2')
    results['scroll_after'] = after
    if not results['time_header_stability']:
        results['errors'].append(f'Large scroll delta after headers inserted: {delta} (before={before}, mid1={check.get("mid1")}, mid2={check.get("mid2")}, after={after})')

    ids = page.evaluate('() => Array.from(document.querySelectorAll("[id]")).map(e => e.id)')
    dup = [x for x in set(ids) if ids.count(x)>1]
    if dup:
        results['accessibility_smoke'] = False
        results['errors'].append('Duplicate IDs at runtime: ' + ','.join(dup))
    else:
        results['accessibility_smoke'] = results['accessibility_smoke'] and True

    browser.close()

with REPORT_FILE.open('w') as fh:
    json.dump(results, fh, indent=2)

if all((results['layout_non_overlap'], results['media_aspect_ratio_ok'], results['no_forced_rotation'], results['time_header_stability'], results['accessibility_smoke'])):
    print('ALL CHECKS PASSED')
    sys.exit(0)

print('SOME CHECKS FAILED: see artifacts/test-report.json')
sys.exit(1)
