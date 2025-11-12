#!/usr/bin/env python3
"""
Script to create and save a Facebook login state.
Opens a browser, waits for manual login, then saves the session state.
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def create_facebook_state():
    """
    Open a browser, wait for user to log into Facebook manually,
    then save the browser state for later use.
    """
    print("🚀 Starting Facebook state creation...")

    async with async_playwright() as p:
        # Launch browser with a persistent context directory
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security'
            ]
        )

        # Create a new context
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        )

        # Open Facebook login page
        page = await context.new_page()
        print("📱 Opening Facebook login page...")
        await page.goto('https://www.facebook.com/login')

        print("\n" + "="*60)
        print("🔑 MANUAL LOGIN REQUIRED")
        print("="*60)
        print("1. Please log into Facebook in the opened browser window")
        print("2. Complete any 2FA or security checks")
        print("3. Make sure you're fully logged in")
        print("4. Press ENTER in this terminal when done")
        print("="*60)

        # Wait for user input
        input("Press ENTER when you've successfully logged in: ")

        print("\n💾 Saving browser state...")

        # Create state directory if it doesn't exist
        state_dir = Path("browser_state")
        state_dir.mkdir(exist_ok=True)

        # Save the context state
        await context.storage_state(path="browser_state/facebook_state.json")

        # Also save cookies separately for backup
        cookies = await context.cookies()
        with open("browser_state/cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        print("✅ State saved successfully!")
        print(f"📂 Files created:")
        print(f"   - browser_state/facebook_state.json")
        print(f"   - browser_state/cookies.json")

        await browser.close()
        print("🎉 Setup complete! You can now use the main scraper.")


if __name__ == "__main__":
    try:
        asyncio.run(create_facebook_state())
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
    except Exception as e:
        print(f"❌ Error during setup: {e}")