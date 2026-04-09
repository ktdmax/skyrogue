from playwright.sync_api import sync_playwright
import time

def screenshot_and_state(page, name):
    page.screenshot(path=f'/tmp/skyjo_{name}.png', full_page=True)
    text = page.locator('body').inner_text()
    print(f"\n=== {name} ===")
    print(text[:1500])
    return text

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})

    page.goto('https://skyjo-gamma.vercel.app/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)

    # Login
    page.locator('input[type="password"]').fill('josky2026')
    page.locator('button:text("Enter")').click()
    page.wait_for_timeout(1500)

    # Set Player 2 to Hard Bot
    p2_btn = page.locator('button:text("Human")').nth(1)
    p2_btn.click()
    page.wait_for_timeout(200)
    p2_btn = page.locator('button').filter(has_text="Easy Bot")
    p2_btn.click()
    page.wait_for_timeout(200)

    # Rename Player 1
    p1 = page.locator('input[placeholder="Player 1"]')
    p1.clear()
    p1.fill('Claude')

    # Start game
    page.locator('button:text("Start Game")').click()
    page.wait_for_timeout(2000)

    # Phase 1: Flip 2 cards to reveal them
    # My cards are buttons 1-12 (indices in grid)
    # Click card at position 0,0 (first card) and 1,1 (fifth card)
    my_cards = page.locator('button:has-text("?")').all()
    print(f"Total ? buttons: {len(my_cards)}")

    # Click first card of my grid
    my_cards[0].click()
    page.wait_for_timeout(1000)

    screenshot_and_state(page, "10_flip1")

    # Click second card
    my_cards_after = page.locator('button:has-text("?")').all()
    # Click a different card
    my_cards_after[5].click()
    page.wait_for_timeout(2000)

    screenshot_and_state(page, "11_flip2")

    # Wait for bot to also reveal cards
    page.wait_for_timeout(3000)
    screenshot_and_state(page, "12_after_bot_reveal")

    # Now the actual game begins - let's play multiple turns
    for turn in range(15):
        page.wait_for_timeout(1500)
        text = page.locator('body').inner_text()
        print(f"\n--- Turn {turn} ---")
        print(text[:800])

        # Check if game is over
        if 'winner' in text.lower() or 'game over' in text.lower() or 'final' in text.lower() or 'wins' in text.lower():
            print("GAME OVER detected!")
            page.screenshot(path=f'/tmp/skyjo_final.png', full_page=True)
            break

        # Check if it's our turn (look for action prompts)
        if 'Claude' in text and ('turn' in text.lower() or 'draw' in text.lower() or 'pick' in text.lower() or 'choose' in text.lower() or 'flip' in text.lower()):

            # Look for deck/discard pile to draw from
            # Try clicking the draw pile (usually first non-grid button or specific element)

            # Check what actions are available
            all_buttons = page.locator('button').all()
            visible_buttons = []
            for i, btn in enumerate(all_buttons):
                if btn.is_visible():
                    txt = btn.text_content().strip()
                    visible_buttons.append((i, txt))

            print(f"Visible buttons: {visible_buttons[:20]}")

            # Strategy: Try to find draw pile or discard pile
            # The draw/discard are usually specific elements
            draw_pile = page.locator('[class*="draw"], [class*="deck"], [class*="pile"]').all()
            print(f"Draw/deck elements: {len(draw_pile)}")

            # Try clicking the first non-card button (likely draw pile)
            # Or look for specific game action elements
            clickable = page.locator('button:not(:has-text("?"))').all()
            for i, c in enumerate(clickable):
                if c.is_visible():
                    txt = c.text_content().strip()
                    print(f"  Clickable [{i}]: '{txt[:30]}'")

            # Try to draw from deck - it might be a div, not a button
            deck = page.locator('[class*="cursor-pointer"]').all()
            print(f"Cursor-pointer elements: {len(deck)}")

            # Let's try clicking the draw pile area
            # Usually positioned between the two player grids
            try:
                # Try to find and click draw pile
                draw = page.locator('text="Draw"').first
                if draw.is_visible():
                    draw.click()
                    page.wait_for_timeout(1000)
                    print("Clicked Draw")
            except:
                pass

            # If there are face-down cards to flip, click one
            face_down = page.locator('button:has-text("?")').all()
            my_face_down = face_down[:12]  # First 12 are mine
            has_mine = [c for c in my_face_down if c.is_visible()]

            if has_mine:
                # Click a face-down card
                has_mine[0].click()
                page.wait_for_timeout(1000)
                print(f"Clicked a face-down card")

        page.wait_for_timeout(1500)
        page.screenshot(path=f'/tmp/skyjo_turn_{turn}.png', full_page=True)

    # Final state
    page.wait_for_timeout(2000)
    screenshot_and_state(page, "final")
    page.screenshot(path='/tmp/skyjo_final.png', full_page=True)

    browser.close()
