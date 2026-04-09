from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    page.goto('https://skyjo-gamma.vercel.app/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(2000)

    page.screenshot(path='/tmp/skyjo_01_initial.png', full_page=True)

    # Check for password field
    password_inputs = page.locator('input[type="password"], input[type="text"]').all()
    print(f"Found {len(password_inputs)} input fields")

    # Try to find and fill password
    for inp in password_inputs:
        print(f"Input: placeholder={inp.get_attribute('placeholder')}, type={inp.get_attribute('type')}")

    if password_inputs:
        password_inputs[0].fill('josky2026')
        page.screenshot(path='/tmp/skyjo_02_password_filled.png', full_page=True)

        # Look for submit button
        buttons = page.locator('button').all()
        for btn in buttons:
            print(f"Button: {btn.text_content()}")
        if buttons:
            buttons[0].click()
            page.wait_for_timeout(3000)
            page.wait_for_load_state('networkidle')

    page.screenshot(path='/tmp/skyjo_03_after_login.png', full_page=True)

    # Explore the page content
    print("\n--- Page content ---")
    print(page.content()[:5000])

    # Find all buttons and interactive elements
    buttons = page.locator('button').all()
    print(f"\nButtons found: {len(buttons)}")
    for btn in buttons:
        txt = btn.text_content().strip()
        if txt:
            print(f"  Button: '{txt}'")

    # Find links
    links = page.locator('a').all()
    print(f"\nLinks found: {len(links)}")
    for link in links:
        txt = link.text_content().strip()
        href = link.get_attribute('href')
        if txt:
            print(f"  Link: '{txt}' -> {href}")

    browser.close()
