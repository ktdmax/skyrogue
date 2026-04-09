from playwright.sync_api import sync_playwright

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

    p1 = page.locator('input[placeholder="Player 1"]')
    p1.clear()
    p1.fill('Claude')

    page.locator('button:text("Start Game")').click()
    page.wait_for_timeout(2000)

    # Reveal 2 cards
    my_buttons = page.locator('button:has-text("?"):not([disabled])').all()
    if my_buttons:
        my_buttons[0].click()
        page.wait_for_timeout(800)
    my_buttons = page.locator('button:has-text("?"):not([disabled])').all()
    if my_buttons:
        my_buttons[3].click()
        page.wait_for_timeout(800)

    page.wait_for_timeout(3000)

    import re

    # Main game loop - smarter strategy
    for turn in range(40):
        page.wait_for_timeout(1500)
        text = page.locator('body').inner_text()

        # Game over check
        if 'cards revealed' in text.lower() or 'see scores' in text.lower() or 'game over' in text.lower():
            print(f"Round over at turn {turn}!")
            page.screenshot(path='/tmp/skyjo_g2_revealed.png', full_page=True)
            # Click See Scores
            try:
                page.locator('button:text("See Scores")').click(timeout=3000)
                page.wait_for_timeout(2000)
                page.screenshot(path='/tmp/skyjo_g2_scores.png', full_page=True)
                score_text = page.locator('body').inner_text()
                print(f"Scores:\n{score_text}")

                # Click Next Round or Continue
                next_btn = page.locator('button:text("Next Round"), button:text("Continue"), button:text("New Round")').first
                next_btn.click(timeout=3000)
                page.wait_for_timeout(2000)
                continue
            except Exception as e:
                print(f"Score error: {e}")
                break

        if "Claude's turn" not in text:
            continue

        print(f"\n--- Turn {turn} ---")

        # Get discard value
        m = re.search(r'(-?\d+)\s*\n\s*Discard', text)
        discard_val = int(m.group(1)) if m else None
        print(f"  Discard: {discard_val}")

        # Get my visible cards
        my_cards = []
        lines = text.split('\n')
        in_claude = False
        for line in lines:
            if 'Claude' in line:
                in_claude = True
                continue
            if 'Hard Bot' in line or 'Draw' in line:
                in_claude = False
                continue
            if in_claude:
                l = line.strip()
                if l == '?':
                    my_cards.append(('?', None))
                elif re.match(r'^-?\d+$', l):
                    my_cards.append(('num', int(l)))

        face_down_count = sum(1 for c in my_cards if c[0] == '?')
        known_cards = [c[1] for c in my_cards if c[0] == 'num']
        max_known = max(known_cards) if known_cards else 0
        print(f"  My cards: {my_cards}, face_down: {face_down_count}, max: {max_known}")

        # Strategy:
        # - Take discard if <= 0 (always good)
        # - Take discard if <= 2 and we have face-down or high cards
        # - Otherwise draw from deck

        took_discard = False
        if discard_val is not None and discard_val <= 2:
            print(f"  Taking discard ({discard_val})")
            # Click the discard card value
            cursor_elements = page.locator('[class*="cursor-pointer"]').all()
            for ce in cursor_elements:
                txt = ce.text_content().strip()
                if 'Discard' in txt or str(discard_val) in txt:
                    try:
                        ce.click(timeout=2000)
                        took_discard = True
                        print(f"  Clicked discard area")
                        break
                    except:
                        continue

            if not took_discard:
                # Try clicking on the discard number directly
                all_btns = page.locator('button').all()
                for btn in all_btns:
                    txt = btn.text_content().strip()
                    if txt == str(discard_val) and btn.is_visible():
                        try:
                            btn.click(timeout=2000)
                            took_discard = True
                            break
                        except:
                            continue

        if not took_discard:
            # Draw from deck
            print(f"  Drawing from deck")
            cursor_elements = page.locator('[class*="cursor-pointer"]').all()
            for ce in cursor_elements:
                txt = ce.text_content().strip()
                if 'Draw' in txt:
                    try:
                        ce.click(timeout=3000)
                        print(f"  Clicked draw pile")
                        break
                    except:
                        continue

        page.wait_for_timeout(1500)
        text2 = page.locator('body').inner_text()
        print(f"  State after action: {text2[:200]}")

        # Check if we have a card in hand
        if 'In hand' in text2 or 'Click a card to swap' in text2:
            # Parse drawn value
            m2 = re.search(r'(\d+)\s*\n\s*In hand', text2)
            drawn_val = int(m2.group(1)) if m2 else None
            print(f"  Card in hand: {drawn_val}")

            # Decide: swap or discard
            should_swap = False
            swap_target = None

            if drawn_val is not None and drawn_val <= 3:
                should_swap = True
            elif drawn_val is not None and max_known > 0 and drawn_val < max_known:
                should_swap = True

            if should_swap:
                # Swap with highest card or face-down
                if max_known > (drawn_val or 99):
                    # Swap with highest known card
                    target_btns = page.locator(f'button:has-text("{max_known}"):not([disabled])').all()
                    for tb in target_btns:
                        try:
                            tb.click(timeout=2000)
                            print(f"  Swapped with {max_known}")
                            break
                        except:
                            continue
                else:
                    # Swap with face-down
                    fd = page.locator('button:has-text("?"):not([disabled])').all()
                    if fd:
                        fd[0].click()
                        page.wait_for_timeout(500)
                        print(f"  Swapped with face-down")
            else:
                # Discard and flip
                print(f"  Discarding drawn card")
                try:
                    discard_btn = page.locator('button:has-text("Discard & flip")').first
                    discard_btn.click(timeout=2000)
                except:
                    try:
                        discard_btn = page.locator('text="Discard & flip instead"').first
                        discard_btn.click(timeout=2000)
                    except:
                        pass
                page.wait_for_timeout(1000)

                # Flip a card
                fd = page.locator('button:has-text("?"):not([disabled])').all()
                if fd:
                    fd[0].click()
                    page.wait_for_timeout(500)
                    print(f"  Flipped a card")

        page.wait_for_timeout(1000)

    # Final
    page.wait_for_timeout(2000)
    page.screenshot(path='/tmp/skyjo_g2_final.png', full_page=True)
    print(f"\nFinal state:\n{page.locator('body').inner_text()[:500]}")
    browser.close()
