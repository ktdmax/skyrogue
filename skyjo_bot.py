from playwright.sync_api import sync_playwright
import re

GAME_CODE = "LYKEUD"
PLAYER_NAME = '<style color=red>rot'
W = 150

def ss(page, name):
    page.screenshot(path=f'/tmp/skyjo_online_{name}.png', full_page=True)

def txt(page):
    return page.locator('body').inner_text()

def parse_my_cards(text):
    cards = []
    lines = text.split('\n')
    in_my = False
    found_star = False
    skip_score = True
    for line in lines:
        l = line.strip()
        if 'rot' in l and '★' in l:
            in_my = True
            found_star = True
            continue
        if in_my:
            # Skip the score line (e.g. "68+8")
            if re.match(r'^\d+[+\-]\d+$', l):
                continue
            if l == '?':
                cards.append('?')
            elif re.match(r'^-?\d+$', l):
                cards.append(l)
            elif l and not l.startswith('Flip') and not l.startswith('Draw'):
                # Check if this is another player section
                if any(x in l for x in ['Alex', 'Mörv', 'dan', 'Bot', 'Draw', 'Discard', 'Waiting']):
                    break
    return cards

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.set_default_timeout(5000)

    # Login & Join
    page.goto('https://skyjo-gamma.vercel.app/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(W)
    page.locator('input[type="password"]').fill('josky2026')
    page.locator('button:text("Enter")').click()
    page.wait_for_timeout(300)
    page.locator('button:text("Play Online")').click()
    page.wait_for_timeout(W)
    page.locator('input[placeholder="Enter your name"]').fill(PLAYER_NAME)
    page.wait_for_timeout(W)
    page.locator('button:text("Join Room")').click()
    page.wait_for_timeout(300)
    page.locator('input[placeholder="XXXXXX"]').fill(GAME_CODE)
    page.wait_for_timeout(W)
    page.locator('button:text("Join Room")').click()
    page.wait_for_timeout(1000)
    print(f"Joined! {txt(page)[:200]}")

    # Wait for my turn
    for i in range(300):
        t = txt(page)
        if 'your turn' in t.lower() or ('flip' in t.lower() and 'rot' in t.lower()):
            print(f"My turn! ({i*0.5}s)")
            break
        if i % 20 == 0 and i > 0:
            print(f"  waiting {i*0.5}s...")
        page.wait_for_timeout(500)

    ss(page, 'start')

    # ===== MAIN LOOP =====
    stale_count = 0
    last_state = ""

    for turn in range(300):
        page.wait_for_timeout(W)
        t = txt(page)

        # Round/Game over
        if 'cards revealed' in t.lower() or 'see scores' in t.lower():
            print(f"\n*** ROUND OVER (t{turn}) ***")
            ss(page, f'round_{turn}')
            try:
                page.locator('button:text("See Scores")').click(timeout=3000)
                page.wait_for_timeout(1500)
                ss(page, f'scores_{turn}')
                print(txt(page)[:400])
                page.locator('button:text("Next Round")').click(timeout=3000)
                page.wait_for_timeout(2000)
            except:
                try:
                    page.locator('button').filter(has_text="Next").first.click(timeout=2000)
                    page.wait_for_timeout(2000)
                except:
                    pass
            stale_count = 0
            continue

        if 'game over' in t.lower() or 'final standing' in t.lower():
            print(f"\n*** GAME OVER ***")
            ss(page, 'game_over')
            print(t[:500])
            break

        # Check my turn
        is_my_turn = 'your turn' in t.lower()
        is_reveal = 'flip' in t.lower() and 'more card' in t.lower() and 'rot' in t.lower()

        if not is_my_turn and not is_reveal:
            page.wait_for_timeout(250)
            continue

        # Stale detection
        if t == last_state:
            stale_count += 1
            if stale_count > 10:
                print(f"  t{turn}: STUCK, taking screenshot")
                ss(page, f'stuck_{turn}')
                # Try to unstick by clicking around
                stale_count = 0
                page.wait_for_timeout(500)
                continue
        else:
            stale_count = 0
            last_state = t

        # Reveal phase
        if is_reveal:
            fd = page.locator('button:has-text("?"):not([disabled])').all()
            if fd:
                fd[0].click()
                page.wait_for_timeout(W)
                t2 = txt(page)
                if 'flip' in t2.lower() and 'more' in t2.lower():
                    fd2 = page.locator('button:has-text("?"):not([disabled])').all()
                    if fd2:
                        fd2[min(3, len(fd2)-1)].click()
                        page.wait_for_timeout(W)
                print(f"  t{turn}: revealed")
            continue

        # === MY TURN - parse state ===
        cards = parse_my_cards(t)
        face_down = [i for i, c in enumerate(cards) if c == '?']
        known = [(i, int(c)) for i, c in enumerate(cards) if c != '?']
        hi_i, hi_v = max(known, key=lambda x: x[1]) if known else (-1, -3)

        m = re.search(r'(-?\d+)\s*\n\s*Discard', t)
        dv = int(m.group(1)) if m else None

        print(f"\n  t{turn}: cards={cards} dv={dv} hi={hi_v} fd={len(face_down)}")

        # STRATEGY
        take_d = False
        if dv is not None:
            if dv <= 0: take_d = True
            elif dv <= 2 and (face_down or hi_v >= 6): take_d = True
            elif dv <= 4 and hi_v >= 9: take_d = True
            elif hi_v >= 8 and dv <= hi_v - 4: take_d = True

        # The Draw pile and Discard pile are at the bottom of the page
        # Draw pile: a card with "?" text, labeled "Draw (N)" below
        # Discard pile: a card with the number, labeled "Discard" below
        # Both are inside a dark container at the bottom

        if take_d:
            print(f"    TAKE discard {dv}")
            # Click the discard pile card - it has the number and "Discard" text nearby
            try:
                # Find the discard section - look for element containing both the value and "Discard"
                # The discard card is a clickable element near "Discard" text
                discard_container = page.locator('text="Discard"').first
                # Click the card above the "Discard" label
                discard_container.click(timeout=2000)
                page.wait_for_timeout(W*3)
            except:
                # Try clicking by coordinates - discard is on the right side of bottom area
                try:
                    # Get the "Discard" text position and click above it
                    box = page.locator('text="Discard"').first.bounding_box()
                    if box:
                        page.mouse.click(box['x'] + box['width']/2, box['y'] - 40)
                        page.wait_for_timeout(W*3)
                except:
                    pass

            t2 = txt(page)
            if 'In hand' in t2 or 'swap' in t2.lower():
                # Swap with highest or facedown
                if hi_v > dv and hi_v >= 5:
                    # Click the highest card in my grid
                    try:
                        # Find my grid buttons - they're in the section with ★
                        my_section = page.locator('text="rot ★"').first.locator('..')
                        # Click highest value card
                        btns = page.locator('button:not([disabled])').all()
                        for btn in btns:
                            bt = btn.text_content().strip()
                            if bt == str(hi_v):
                                try:
                                    btn.click(timeout=1000)
                                    print(f"    swapped {hi_v}")
                                    break
                                except:
                                    continue
                    except:
                        pass
                elif face_down:
                    fd = page.locator('button:has-text("?"):not([disabled])').all()
                    if fd:
                        fd[0].click()
                        print(f"    swapped facedown")
            else:
                print(f"    discard click may have failed, state: {t2[:150]}")
        else:
            print(f"    DRAW")
            # Click the draw pile - it's the "?" card on the left side of bottom area
            try:
                # Try clicking by finding Draw text and clicking above it
                draw_label = page.locator('text=/Draw \\(\\d+\\)/').first
                box = draw_label.bounding_box()
                if box:
                    page.mouse.click(box['x'] + box['width']/2, box['y'] - 40)
                    page.wait_for_timeout(W*3)
                else:
                    raise Exception("no bbox")
            except:
                try:
                    # Alternative: find all cursor-pointer elements
                    ces = page.locator('[class*="cursor-pointer"]').all()
                    for ce in ces:
                        ct = ce.text_content().strip()
                        if 'Draw' in ct or ct == '?':
                            ce.click(timeout=2000)
                            page.wait_for_timeout(W*3)
                            break
                except:
                    pass

            t2 = txt(page)
            m2 = re.search(r'(-?\d+)\s*\n\s*In hand', t2)
            drawn = int(m2.group(1)) if m2 else None
            print(f"    drew: {drawn}")

            if drawn is not None:
                keep = False
                if drawn <= 0: keep = True
                elif drawn <= 2 and (face_down or hi_v >= 6): keep = True
                elif drawn < hi_v and hi_v >= 7: keep = True
                elif drawn <= 4 and hi_v >= 9: keep = True

                if keep:
                    print(f"    KEEP {drawn}")
                    if hi_v > drawn and hi_v >= 5:
                        for btn in page.locator('button:not([disabled])').all():
                            bt = btn.text_content().strip()
                            if bt == str(hi_v):
                                try:
                                    btn.click(timeout=1000)
                                    print(f"    replaced {hi_v}")
                                    break
                                except:
                                    continue
                    elif face_down:
                        fd = page.locator('button:has-text("?"):not([disabled])').all()
                        if fd:
                            fd[0].click()
                            print(f"    replaced facedown")
                else:
                    print(f"    TOSS {drawn}")
                    # Click "Discard & flip instead"
                    try:
                        page.locator('text="Discard & flip instead"').click(timeout=2000)
                    except:
                        try:
                            # Try finding it as a button
                            page.locator('button:has-text("Discard")').first.click(timeout=1500)
                        except:
                            # Click by position - "Discard & flip" text
                            try:
                                el = page.locator('text=/Discard/').first
                                el.click(timeout=1000)
                            except:
                                pass
                    page.wait_for_timeout(W*2)

                    # Now flip a facedown card
                    fd = page.locator('button:has-text("?"):not([disabled])').all()
                    if fd:
                        fd[0].click()
                        print(f"    flipped")
            else:
                # Could not parse drawn card - take screenshot for debug
                ss(page, f'nodraw_{turn}')
                print(f"    no drawn card parsed, state: {t2[:200]}")
                # Try fallback: discard & flip
                try:
                    page.locator('text="Discard & flip instead"').click(timeout=1500)
                    page.wait_for_timeout(W)
                    fd = page.locator('button:has-text("?"):not([disabled])').all()
                    if fd: fd[0].click()
                except:
                    pass

        page.wait_for_timeout(W)

    ss(page, 'final')
    print(f"\nFinal:\n{txt(page)[:500]}")
    browser.close()
