from playwright.sync_api import sync_playwright

def ss(page, name):
    page.screenshot(path=f'/tmp/skyjo_{name}.png', full_page=True)
    text = page.locator('body').inner_text()
    print(f"\n=== {name} ===")
    # Print first few lines
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    for l in lines[:20]:
        print(f"  {l}")
    return text

def get_status(page):
    text = page.locator('body').inner_text()
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return text, lines

def wait_for_my_turn(page, timeout=15):
    """Wait until it's Claude's turn or game over."""
    for _ in range(timeout * 2):
        text, lines = get_status(page)
        if any('game over' in l.lower() or 'wins' in l.lower() or 'winner' in l.lower() or 'final score' in l.lower() or 'round over' in l.lower() for l in lines):
            return 'gameover', text
        if "Claude's turn" in text:
            return 'myturn', text
        if "Claude reveals" in text or "Flip" in text:
            return 'reveal', text
        page.wait_for_timeout(500)
    return 'timeout', text

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
    page.locator('button').filter(has_text="Easy Bot").click()
    page.wait_for_timeout(200)

    # Rename Player 1
    p1 = page.locator('input[placeholder="Player 1"]')
    p1.clear()
    p1.fill('Claude')

    # Start game
    page.locator('button:text("Start Game")').click()
    page.wait_for_timeout(2000)

    # Phase 1: Reveal 2 cards - click 2 of my face-down cards
    # My cards have yellow borders (first 12 buttons with ?)
    # Click cards at different positions for variety
    my_buttons = page.locator('button:has-text("?"):not([disabled])').all()
    print(f"Clickable ? buttons: {len(my_buttons)}")
    if my_buttons:
        my_buttons[0].click()
        page.wait_for_timeout(1000)

    my_buttons = page.locator('button:has-text("?"):not([disabled])').all()
    if my_buttons:
        my_buttons[4].click()  # Pick one in a different position
        page.wait_for_timeout(1000)

    # Wait for bot to reveal
    page.wait_for_timeout(3000)
    ss(page, "game_ready")

    # Main game loop
    for turn in range(30):
        page.wait_for_timeout(1000)
        state, text = wait_for_my_turn(page)
        print(f"\n>>> Turn {turn}, state: {state}")

        if state == 'gameover':
            print("GAME OVER!")
            ss(page, f"gameover_{turn}")
            break

        if state == 'timeout':
            print("Timed out waiting for turn")
            ss(page, f"timeout_{turn}")
            break

        if state == 'reveal':
            # Need to flip cards
            my_buttons = page.locator('button:has-text("?"):not([disabled])').all()
            if my_buttons:
                my_buttons[0].click()
                page.wait_for_timeout(500)
            continue

        # It's my turn!
        ss(page, f"turn_{turn}")

        # Strategy:
        # 1. Check the discard pile value
        # 2. If discard is low (<=3), take it and swap with a face-down or high card
        # 3. Otherwise draw from deck

        # Parse discard value from page
        discard_val = None
        if 'Discard' in text:
            # Find the number before "Discard"
            import re
            # Look for pattern like "10\nDiscard"
            m = re.search(r'(-?\d+)\s*\n\s*Discard', text)
            if m:
                discard_val = int(m.group(1))
                print(f"  Discard pile value: {discard_val}")

        # Decision: take discard if value <= 2, otherwise draw
        if discard_val is not None and discard_val <= 2:
            # Take from discard pile
            print(f"  Taking discard ({discard_val})")
            discard_btn = page.locator('text="Discard"').first
            # The discard value is a button near the "Discard" text
            # Try clicking the number above "Discard"
            discard_card = page.locator(f'button:has-text("{discard_val}")').all()
            # Find the right one (not in our grid)
            for dc in discard_card:
                try:
                    dc.click(timeout=2000)
                    print(f"  Clicked discard card {discard_val}")
                    break
                except:
                    continue

            page.wait_for_timeout(1000)
            state_text = page.locator('body').inner_text()
            print(f"  After taking discard: {state_text[:200]}")

            # Now swap with a face-down card or high value card
            # Try to find a ? card to swap with
            swap_targets = page.locator('button:has-text("?"):not([disabled])').all()
            if swap_targets:
                swap_targets[0].click()
                page.wait_for_timeout(500)
                print(f"  Swapped with face-down card")
            else:
                # Swap with highest value card
                my_card_buttons = page.locator('button:not([disabled])').all()
                highest_val = -3
                highest_btn = None
                for btn in my_card_buttons[:12]:
                    txt = btn.text_content().strip()
                    try:
                        v = int(txt)
                        if v > highest_val and v > discard_val:
                            highest_val = v
                            highest_btn = btn
                    except:
                        pass
                if highest_btn:
                    highest_btn.click()
                    page.wait_for_timeout(500)
                    print(f"  Swapped with card value {highest_val}")

        else:
            # Draw from deck
            print(f"  Drawing from deck")
            draw_btn = page.locator('text="Draw"').first
            try:
                draw_btn.click(timeout=3000)
                page.wait_for_timeout(1500)
            except Exception as e:
                print(f"  Failed to click Draw: {e}")
                # Try alternative - look for draw pile by position
                cursor_elements = page.locator('[class*="cursor-pointer"]').all()
                if cursor_elements:
                    cursor_elements[0].click()
                    page.wait_for_timeout(1500)

            # After drawing, check what we got
            state_text = page.locator('body').inner_text()
            print(f"  After draw: {state_text[:300]}")
            ss(page, f"drawn_{turn}")

            # Parse drawn card value
            drawn_val = None
            m = re.search(r'You drew.*?(-?\d+)', state_text)
            if m:
                drawn_val = int(m.group(1))
            else:
                # Try to find "Keep" or "Discard" options
                m2 = re.search(r'Swap or discard.*?(-?\d+)', state_text, re.IGNORECASE)
                if m2:
                    drawn_val = int(m2.group(1))

            print(f"  Drawn value: {drawn_val}")

            # Check for swap/discard/keep buttons
            if 'discard' in state_text.lower() or 'swap' in state_text.lower() or 'keep' in state_text.lower():
                # If drawn card is low, swap with face-down or high card
                if drawn_val is not None and drawn_val <= 3:
                    # Swap - click a ? card or high value card
                    swap_targets = page.locator('button:has-text("?"):not([disabled])').all()
                    if swap_targets:
                        swap_targets[0].click()
                        page.wait_for_timeout(500)
                        print(f"  Kept drawn card, swapped with face-down")
                    else:
                        # Find highest card to swap
                        my_card_buttons = page.locator('button:not([disabled])').all()
                        highest_val_card = -3
                        highest_btn_card = None
                        for btn in my_card_buttons[:12]:
                            txt = btn.text_content().strip()
                            try:
                                v = int(txt)
                                if v > highest_val_card and v > drawn_val:
                                    highest_val_card = v
                                    highest_btn_card = btn
                            except:
                                pass
                        if highest_btn_card:
                            highest_btn_card.click()
                            page.wait_for_timeout(500)
                            print(f"  Swapped with card {highest_val_card}")
                        else:
                            # Discard and flip
                            discard_option = page.locator('button:has-text("Discard")').first
                            try:
                                discard_option.click(timeout=2000)
                                page.wait_for_timeout(500)
                                # Flip a face-down card
                                fd = page.locator('button:has-text("?"):not([disabled])').all()
                                if fd:
                                    fd[0].click()
                                    page.wait_for_timeout(500)
                            except:
                                pass
                else:
                    # High drawn card - discard it and flip a face-down card
                    print(f"  Discarding drawn card")
                    # Try clicking discard button/area
                    try:
                        # Look for a discard action button
                        discard_action = page.locator('button:has-text("Discard")').all()
                        if discard_action:
                            for da in discard_action:
                                try:
                                    da.click(timeout=2000)
                                    print("  Clicked Discard button")
                                    break
                                except:
                                    continue
                        page.wait_for_timeout(500)

                        # Now flip a face-down card
                        fd = page.locator('button:has-text("?"):not([disabled])').all()
                        if fd:
                            fd[0].click()
                            page.wait_for_timeout(500)
                            print(f"  Flipped a face-down card")
                    except Exception as e:
                        print(f"  Error discarding: {e}")

                        # Fallback: just click on a card in my grid
                        my_card_buttons = page.locator('button:has-text("?"):not([disabled])').all()
                        if my_card_buttons:
                            my_card_buttons[0].click()
                            page.wait_for_timeout(500)

        # Wait for bot's turn
        page.wait_for_timeout(2000)

    # Final screenshot
    page.wait_for_timeout(2000)
    ss(page, "final")

    browser.close()
