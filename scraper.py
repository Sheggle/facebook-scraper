#!/usr/bin/env python3
"""
Simple Facebook scraper - minimalist approach.
"""

import asyncio
import argparse
import re
from pathlib import Path
from playwright.async_api import async_playwright
import os
from pathlib import Path
import uuid

# Pattern to match Dutch comment text
COMMENT_TEXT_PATTERN = re.compile(r"\d+\s+opmerkingen?", re.IGNORECASE)
MAX_POST_SCROLL = 10
MAX_FEED_SCROLL = ...
dir = Path('screenshots')
if not os.path.exists(dir):
    os.makedirs(dir)


async def parse_post(page):
    _id = str(uuid.uuid4())
    post_dir = dir / _id
    os.makedirs(post_dir)
    await page.mouse.move(640, 360)
    for i in range(MAX_POST_SCROLL):
        # take screenshot, save to post_dir / f'{i}.png'
        await page.screenshot(path=str(post_dir / f'{i}.png'))
        print(f"        📸 Screenshot {i+1}/{MAX_POST_SCROLL} saved")

        # scroll down (but need to finetune at what (x,y) we scroll down)
        await page.mouse.wheel(0, 300)  # TODO: finetune scroll coordinates and amount
        await asyncio.sleep(0.5)
    await page.mouse.move(0, 0)


async def handle_saving(button, page):
    """Click the button, scroll while taking screenshots, parse, close by clicking on (0,0)"""
    try:
        # Click the comment button
        await button.click()
        print("      🖱️  Clicked button, waiting 3s...")

        # Wait 3 seconds
        await asyncio.sleep(3)

        await parse_post(page)

        # Click at (0,0) to close
        await page.mouse.click(0, 0)
        print("      ❌ Closed by clicking (0,0)")

    except Exception as e:
        print(f"      ⚠️  Error in handle_saving: {e}")


async def main():
    parser = argparse.ArgumentParser(description='Simple Facebook Scraper')
    parser.add_argument('--state-dir', default='browser_state/', help='Directory containing browser state')
    parser.add_argument('--keyword', required=True, help='Keyword to search for on Facebook')
    parser.add_argument('--headful', action='store_true', help='Run browser in headful mode (default: headless)')
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    state_file = state_dir / "facebook_state.json"

    if not state_file.exists():
        print(f"❌ No saved state found at {state_file}")
        print("Please run create_state.py first")
        return

    print(f"🔍 Loading browser state from {state_file}")

    async with async_playwright() as p:
        # Launch browser (headless by default, headful if requested)
        browser = await p.chromium.launch(headless=not args.headful)

        # Create context with saved state
        context = await browser.new_context(storage_state=str(state_file))

        # Create page
        page = await context.new_page()

        print("✅ Browser loaded with saved state")
        print(f"🔍 Searching for keyword: {args.keyword}")

        search_url = f"https://www.facebook.com/search/posts/?q={args.keyword.replace(' ', '%20')}"
        await page.goto(search_url)

        # Wait for page to load
        await asyncio.sleep(3)

        print("🔍 Starting to look for comment buttons...")

        seen_texts = set()  # Track text we've seen for uniqueness check
        scroll_since_update = 0

        while len(seen_texts) < 10:
            # Get all buttons
            buttons = await page.locator("div[role='button']").element_handles()

            # Check each button for Dutch comment text
            current_found = 0
            for button in buttons:
                try:
                    text = (await button.inner_text()).strip()
                    if COMMENT_TEXT_PATTERN.search(text):
                        # TODO: improve uniqueness check - text alone isn't sufficient since multiple posts can have same comment count

                        # Check if unique by text
                        if text not in seen_texts:
                            seen_texts.add(text)
                            current_found += 1
                            print(f"   ✅ Found #{len(seen_texts)}: '{text}'")
                            await handle_saving(button, page)

                except:
                    continue

            if current_found > 0:
                scroll_since_update = 0
                print(f"   📊 Total unique buttons found: {len(seen_texts)}")

            scroll_since_update += 1
            if scroll_since_update > 10:
                print(f"✅ No new buttons found for 10 iterations. Stopping.")
                break

            # Scroll down
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(0.5)

        print(f"\n🎉 Final count: {len(seen_texts)} unique comment buttons found")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())