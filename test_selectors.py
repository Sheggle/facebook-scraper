#!/usr/bin/env python3
"""
Test script to find and click Dutch comment buttons using role='button' approach.
Run with: uv run test_selectors.py
"""

import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

# Pattern to match Dutch comment text
COMMENT_TEXT_PATTERN = re.compile(r"\d+\s+opmerkingen?", re.IGNORECASE)


async def test_and_click_comment_button():
    """Find and click Dutch comment buttons using div[role='button'] approach."""

    # Check if state files exist
    state_file = Path("browser_state/facebook_state.json")
    if not state_file.exists():
        print("❌ No saved state found. Please run: uv run create_state.py first.")
        return

    print("🔍 Looking for Dutch comment buttons...")

    async with async_playwright() as p:
        # Launch browser in headful mode
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )

        # Create context with saved state
        context = await browser.new_context(
            storage_state=str(state_file),
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        )

        page = await context.new_page()

        print("📱 Navigating to Facebook...")
        await page.goto('https://www.facebook.com/')

        # Wait for page to load
        print("⏳ Waiting for page to load...")
        await asyncio.sleep(3)

        print("🔍 Searching for buttons with role='button'...")

        try:
            # Get all buttons using the specified approach
            buttons = await page.locator("div[role='button']").element_handles()
            print(f"   Found {len(buttons)} total buttons")

            button_found = False

            # Check each button for Dutch comment text
            for i, button in enumerate(buttons):
                try:
                    # Get the inner text of the button
                    label = (await button.inner_text() or "").strip()

                    # Check if it matches our Dutch comment pattern
                    if COMMENT_TEXT_PATTERN.search(label):
                        print(f"   ✅ Found Dutch comment button: '{label}'")

                        # Try to click it
                        print("   🖱️  Clicking the button...")
                        await button.click()

                        print(f"   🎉 Successfully clicked: '{label}'")
                        print("   ⏳ Waiting 5 seconds to see what happens...")
                        await asyncio.sleep(5)

                        button_found = True
                        break

                except Exception as e:
                    # Skip buttons that can't be accessed
                    continue

                # Show progress every 50 buttons
                if i > 0 and i % 50 == 0:
                    print(f"   ... checked {i} buttons so far")

            if not button_found:
                print("❌ No Dutch comment buttons found")
                print("💡 Try scrolling down to see more posts")

        except Exception as e:
            print(f"❌ Error searching for buttons: {e}")

        print("\n📸 Taking screenshot of current state...")
        await page.screenshot(path="clicked_state.png", full_page=True)
        print("Screenshot saved as: clicked_state.png")

        print("\n⏸️  Browser will stay open. Press Enter to close...")
        input()

        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(test_and_click_comment_button())
    except KeyboardInterrupt:
        print("\n❌ Test cancelled by user")
    except Exception as e:
        print(f"❌ Error during test: {e}")