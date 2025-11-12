from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Find installed chromium binary and use it to avoid PrintDeps issues
    import os
    chrome_root = os.path.join(os.environ.get('USERPROFILE',''), 'AppData', 'Local', 'ms-playwright', 'chromium_headless_shell-1194')
    chrome_exe = os.path.join(chrome_root, 'chrome.exe')
    if os.path.exists(chrome_exe):
        b = p.chromium.launch(headless=True, executable_path=chrome_exe)
    else:
        # try to use a local browser channel (eg. msedge or chrome) if available
        try:
            b = p.chromium.launch(headless=True, channel='msedge')
        except Exception:
            b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={'width':1280,'height':900})
    page.goto('http://localhost:8080/ui_fixed.html')
    page.wait_for_selector('.message')
    rects = page.evaluate("Array.from(document.querySelectorAll('.message')).map(e=>({id:e.id, top:e.getBoundingClientRect().top, left:e.getBoundingClientRect().left, right:e.getBoundingClientRect().right, bottom:e.getBoundingClientRect().bottom, w:e.getBoundingClientRect().width, h: e.getBoundingClientRect().height}))")
    print('RECTS:', rects)
    transforms = page.evaluate("Array.from(document.querySelectorAll('img.media')).map(i=>getComputedStyle(i).transform)")
    print('TRANSFORMS:', transforms)
    page.screenshot(path='artifacts/debug-screenshot.png', full_page=True)
    b.close()
print('done')