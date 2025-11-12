from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel='msedge')
    page = b.new_page(viewport={'width':1280,'height':900})
    page.goto('http://localhost:8080/ui_fixed.html')
    page.wait_for_selector('img.media')
    imgs = page.query_selector_all('img.media')
    for idx, i in enumerate(imgs):
        dims = page.evaluate('img=>({nw:img.naturalWidth, nh:img.naturalHeight, cw:img.clientWidth, ch:img.clientHeight })', i)
        print(idx, 'IMG dims:', dims)
    page.screenshot(path='artifacts/debug-media-dims.png', full_page=True)
    b.close()
print('done')