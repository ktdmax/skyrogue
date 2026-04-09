from playwright.sync_api import sync_playwright
import re, time

def get_text(page):
    return page.locator('body').inner_text()

def ss(page, name):
    page.screenshot(path=f'/tmp/skyjo_online_{name}.png', full_page=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    page.goto('https://skyjo-gamma.vercel.app/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(500)

    # Login
    page.locator('input[type="password"]').fill('josky2026')
    page.locator('button:text("Enter")').click()
    page.wait_for_timeout(1000)

    # Click Play Online
    page.locator('button:text("Play Online")').click()
    page.wait_for_timeout(1000)
    ss(page, '01_online_menu')
    text = get_text(page)
    print(f"Online menu:\n{text[:500]}")

    # Look for Join game option
    # Try to find "Join" button or input for game code
    join_btn = page.locator('button:text("Join"), button:text("Join Game"), button:text("Join Room")').first
    try:
        join_btn.click(timeout=2000)
        page.wait_for_timeout(500)
    except:
        print("No direct Join button, looking for alternatives...")

    ss(page, '02_after_join_click')
    text = get_text(page)
    print(f"\nAfter join:\n{text[:500]}")

    # Find all inputs
    inputs = page.locator('input').all()
    print(f"\nInputs found: {len(inputs)}")
    for i, inp in enumerate(inputs):
        placeholder = inp.get_attribute('placeholder') or ''
        val = inp.get_attribute('value') or ''
        typ = inp.get_attribute('type') or ''
        print(f"  [{i}] type={typ} placeholder='{placeholder}' value='{val}'")

    # Find all buttons
    buttons = page.locator('button').all()
    for i, btn in enumerate(buttons):
        if btn.is_visible():
            print(f"  Button [{i}]: '{btn.text_content().strip()[:40]}'")

    browser.close()
