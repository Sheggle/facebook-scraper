#!/usr/bin/env python3
"""
Simple Facebook scraper - minimalist approach.
"""

import asyncio
import argparse
import re
import time
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

# Pattern to match Dutch comment text
COMMENT_TEXT_PATTERN = re.compile(r"\d+\s+opmerkingen?", re.IGNORECASE)


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

        search_url = f"https://www.facebook.com/search/posts/?q={args.keyword}"
        await page.goto(search_url)

        # Wait for page to load
        await asyncio.sleep(3)

        print("🔍 Starting to look for comment buttons...")

        seen_texts = set()  # Track text we've seen for uniqueness check
        all_buttons = []  # Store all button data (text, is_unique, metadata)
        total_count = 0

        scroll_since_update = 0

        while True:
            # Get all buttons
            buttons = await page.locator("div[role='button']").element_handles()

            # Check each button for Dutch comment text
            current_found = 0
            for button in buttons:
                try:
                    text = (await button.inner_text()).strip()
                    if COMMENT_TEXT_PATTERN.search(text):
                        # Check if unique by text
                        is_unique = text not in seen_texts
                        if is_unique:
                            seen_texts.add(text)
                            current_found += 1
                            print(f"   ✅ Found #{len(seen_texts)}: '{text}'")

                        # Collect metadata
                        metadata = {}
                        try:
                            bbox = await button.bounding_box()
                            if bbox:
                                metadata['position'] = {'x': bbox['x'], 'y': bbox['y'], 'width': bbox['width'], 'height': bbox['height']}
                        except:
                            pass

                        # Get parent content (3 levels up)
                        try:
                            parent1 = await button.evaluate("el => el.parentElement?.textContent?.slice(0, 200)")
                            parent2 = await button.evaluate("el => el.parentElement?.parentElement?.textContent?.slice(0, 200)")
                            parent3 = await button.evaluate("el => el.parentElement?.parentElement?.parentElement?.textContent?.slice(0, 200)")
                            metadata['parents'] = {'parent1': parent1, 'parent2': parent2, 'parent3': parent3}
                        except:
                            pass

                        metadata['timestamp'] = datetime.now().isoformat()
                        metadata['scroll_iteration'] = total_count // 10  # Rough scroll position

                        # Store tuple: (text, is_unique, metadata)
                        all_buttons.append((text, is_unique, metadata))
                        total_count += 1

                except:
                    continue

            if current_found > 0:
                scroll_since_update = 0
                print(f"   📊 Total unique buttons found: {len(seen_texts)} (total seen: {total_count})")

            scroll_since_update += 1
            if scroll_since_update > 10:
                print(f"✅ No new buttons found for 5s. Stopping.")
                break

            # Scroll down
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(0.5)

        # Save data to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"comment_buttons_{args.keyword}_{timestamp}.json"

        output_data = {
            'keyword': args.keyword,
            'session_timestamp': timestamp,
            'total_buttons': total_count,
            'unique_by_text': len(seen_texts),
            'buttons': all_buttons
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n🎉 Final count: {len(seen_texts)} unique comment buttons ({total_count} total)")
        print(f"💾 Data saved to: {output_file}")
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")