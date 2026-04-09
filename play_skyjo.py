from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    page.goto('https://skyjo-gamma.vercel.app/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)

    # Enter password
    page.locator('input[type="password"]').fill('josky2026')
    page.locator('button:text("Enter")').click()
    page.wait_for_timeout(2000)

    # Set Player 2 to Hard Bot (cycle: Human -> Easy Bot -> Hard Bot)
    player2_btn = page.locator('button:text("Human")').nth(1)
    player2_btn.click()  # -> Easy Bot
    page.wait_for_timeout(300)
    player2_btn = page.locator('button').filter(has_text="Easy Bot")
    player2_btn.click()  # -> Hard Bot
    page.wait_for_timeout(300)

    page.screenshot(path='/tmp/skyjo_04_setup.png', full_page=True)

    # Rename Player 1 to "Claude"
    p1_input = page.locator('input[placeholder="Player 1"]')
    p1_input.clear()
    p1_input.fill('Claude')

    # Start game
    page.locator('button:text("Start Game")').click()
    page.wait_for_timeout(3000)

    page.screenshot(path='/tmp/skyjo_05_game_start.png', full_page=True)

    # Print page content to understand game state
    print("=== Game state ===")
    # Find all visible text
    body_text = page.locator('body').inner_text()
    print(body_text[:3000])

    # Find all buttons/clickable elements
    buttons = page.locator('button').all()
    print(f"\nButtons: {len(buttons)}")
    for i, btn in enumerate(buttons):
        if btn.is_visible():
            txt = btn.text_content().strip()
            print(f"  [{i}] '{txt[:50]}'")

    # Check for any card-like elements
    cards = page.locator('[class*="card"], [class*="Card"]').all()
    print(f"\nCard elements: {len(cards)}")

    browser.close()
