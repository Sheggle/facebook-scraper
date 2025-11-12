"""
Facebook-specific scraping logic and selectors.
"""

import asyncio
import re
from typing import Optional, List
from .browser import FacebookBrowser

# Pattern to match Dutch comment text
COMMENT_TEXT_PATTERN = re.compile(r"\d+\s+opmerkingen?", re.IGNORECASE)


class FacebookScraper:
    """Handles Facebook-specific scraping operations."""

    # TODO: increase max_scroll_attempts once we've improved the detection of being at the end of the file
    def __init__(self, browser: FacebookBrowser, max_scroll_attempts: int = 5):
        self.browser = browser
        self.max_scroll_attempts = max_scroll_attempts

    async def find_comment_section_button(self) -> bool:
        """
        Find and click the comment section button to expand comments using role='button' approach.
        Returns True if button found and clicked, False otherwise.
        """
        print("🔍 Looking for Dutch comment section button...")

        try:
            # Get all buttons using the proven approach from test script
            buttons = await self.browser.page.locator("div[role='button']").element_handles()
            print(f"   Found {len(buttons)} total buttons")

            # Check each button for Dutch comment text
            for i, button in enumerate(buttons):
                try:
                    # Get the inner text of the button
                    label = (await button.inner_text() or "").strip()

                    # Check if it matches our Dutch comment pattern
                    if COMMENT_TEXT_PATTERN.search(label):
                        print(f"✅ Found Dutch comment button: '{label}'")

                        # Try to click it
                        print("🖱️  Clicking the comment button...")
                        await button.click()

                        print(f"✅ Successfully clicked: '{label}'")
                        # Wait for comments to expand
                        await asyncio.sleep(3)
                        return True

                except Exception:
                    # Skip buttons that can't be accessed
                    continue

                # Show progress every 50 buttons
                if i > 0 and i % 50 == 0:
                    print(f"   ... checked {i} buttons so far")

            print("❌ No Dutch comment section button found")
            return False

        except Exception as e:
            print(f"❌ Error searching for comment button: {e}")
            return False

    async def wait_for_comments_to_load(self) -> bool:
        """
        Wait for comments section to fully load after clicking.
        Returns True if comments loaded, False otherwise.
        """
        # TODO: Add selectors for detecting when comments are loaded
        comment_indicators = [
            # TODO: Replace with actual Facebook comment section selectors
            '[role="article"]',  # Comment articles
            '.comment-content',  # Comment content divs
            '[data-testid="comment-list"]',  # Comment list container
            '.comment-text',  # Individual comment text
        ]

        print("⏳ Waiting for comments to load...")

        for indicator in comment_indicators:
            print(f"   Checking for: {indicator}")

            # TODO: Implement actual waiting logic
            if await self.browser.wait_for_element(indicator, timeout=5000):
                print(f"✅ Comments loaded (detected: {indicator})")
                return True
            else:
                print(f"   ❌ Not found: {indicator}")

        print("❌ Comments did not load or were not detected")
        return False

    async def find_and_click_expansion_buttons(self) -> int:
        """
        Find and click all expansion buttons like 'Load more comments', 'View replies', etc.
        Returns the number of buttons clicked.
        """
        expansion_patterns = [
            # Dutch patterns
            re.compile(r"meer\s+laden", re.IGNORECASE),
            re.compile(r"meer\s+opmerkingen", re.IGNORECASE),
            re.compile(r"bekijk\s+antwoorden", re.IGNORECASE),
            re.compile(r"\d+\s+antwoorden", re.IGNORECASE),
            re.compile(r"toon\s+meer", re.IGNORECASE),

            # English patterns (fallback)
            re.compile(r"load\s+more", re.IGNORECASE),
            re.compile(r"view\s+more", re.IGNORECASE),
            re.compile(r"see\s+more", re.IGNORECASE),
            re.compile(r"view\s+\d+\s+replies", re.IGNORECASE),
            re.compile(r"show\s+more", re.IGNORECASE),
        ]

        clicked_count = 0

        try:
            # Get all buttons that might be expansion buttons
            buttons = await self.browser.page.locator("div[role='button'], a[role='button'], span[role='button']").element_handles()

            print(f"🔍 Checking {len(buttons)} buttons for expansion options...")

            for button in buttons:
                try:
                    label = (await button.inner_text() or "").strip()

                    # Check if button text matches any expansion pattern
                    for pattern in expansion_patterns:
                        if pattern.search(label):
                            print(f"   ✅ Found expansion button: '{label}'")

                            try:
                                await button.click()
                                clicked_count += 1
                                print(f"   🖱️  Clicked: '{label}'")

                                # Wait for content to load
                                await asyncio.sleep(2)
                                break  # Don't check other patterns for this button

                            except Exception as click_error:
                                print(f"   ❌ Failed to click '{label}': {click_error}")

                except Exception:
                    # Skip buttons that can't be accessed
                    continue

            print(f"✅ Clicked {clicked_count} expansion buttons")
            return clicked_count

        except Exception as e:
            print(f"❌ Error finding expansion buttons: {e}")
            return clicked_count

    async def scroll_through_comments_with_screenshots(self) -> List[str]:
        """
        Comprehensive scroll through comments with wheel scrolling and screenshots.

        Returns:
            List of screenshot filepaths
        """
        print(f"📜 Starting comprehensive scroll through comments (max {self.max_scroll_attempts} attempts)...")

        screenshots = []
        scroll_count = 0

        # Take initial screenshot
        initial_screenshot = await self.browser.take_numbered_screenshot("initial",
            metadata={"scroll_position": 0, "type": "initial"})
        screenshots.append(initial_screenshot)

        try:
            while scroll_count < self.max_scroll_attempts:
                # Look for and click expansion buttons before scrolling
                expansion_clicks = await self.find_and_click_expansion_buttons()
                if expansion_clicks > 0:
                    # Take screenshot after clicking expansion buttons
                    expansion_screenshot = await self.browser.take_numbered_screenshot("expansion",
                        metadata={"scroll_count": scroll_count, "expansion_clicks": expansion_clicks})
                    screenshots.append(expansion_screenshot)

                # Perform wheel scroll
                print(f"   Scroll {scroll_count + 1}")
                await self.browser.scroll_with_wheel()

                # Take screenshot after scroll
                scroll_screenshot = await self.browser.take_numbered_screenshot("scroll",
                    metadata={
                        "scroll_count": scroll_count + 1,
                    })
                screenshots.append(scroll_screenshot)

                scroll_count += 1

                # Show progress every 10 scrolls
                if scroll_count % 10 == 0:
                    print(f"   ... completed {scroll_count} scrolls")

            # Take final screenshot
            final_screenshot = await self.browser.take_numbered_screenshot("final",
                metadata={
                    "total_scrolls": scroll_count,
                })
            screenshots.append(final_screenshot)

            print(f"✅ Finished scrolling: {scroll_count} scrolls, {len(screenshots)} screenshots")

        except Exception as e:
            print(f"❌ Error during scrolling: {e}")

        return screenshots
