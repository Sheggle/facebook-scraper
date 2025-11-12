"""
Browser state management and session handling.
"""

import asyncio
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class FacebookBrowser:
    """Manages browser state and Facebook session persistence."""

    def __init__(self, scroll_jump_size: int, scroll_wait_time: float, state_dir: str = "browser_state"):
        self.state_dir = Path(state_dir)
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Scroll configuration
        self.scroll_jump_size = scroll_jump_size
        self.scroll_wait_time = scroll_wait_time
        self.screenshot_counter = 0

    async def initialize(self) -> bool:
        """
        Initialize browser with saved state.
        Returns True if successfully initialized, False otherwise.
        """
        try:
            # Check if state files exist
            state_file = self.state_dir / "facebook_state.json"
            if not state_file.exists():
                print("❌ No saved state found. Please run create_state.py first.")
                return False

            self.playwright = await async_playwright().start()

            # Launch browser
            self.browser = await self.playwright.chromium.launch(
                headless=False,  # Can be changed to True for headless mode
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security'
                ]
            )

            # Create context with saved state
            self.context = await self.browser.new_context(
                storage_state=str(state_file),
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            )

            # Create a new page
            self.page = await self.context.new_page()

            print("✅ Browser initialized with saved Facebook session")
            return True

        except Exception as e:
            print(f"❌ Failed to initialize browser: {e}")
            return False

    async def scroll_with_wheel(self) -> None:
        """
        Scroll using mouse wheel for natural behavior.
        """
        if not self.page:
            print("❌ Browser not initialized")
            return

        try:
            # Use mouse wheel scrolling for natural behavior
            await self.page.mouse.wheel(0, self.scroll_jump_size)
            # Wait for content to settle and any dynamic loading
            await asyncio.sleep(self.scroll_wait_time)
        except Exception as e:
            print(f"❌ Error during wheel scroll: {e}")

    async def take_numbered_screenshot(self, prefix: str = "scroll", metadata: dict = None) -> str:
        # TODO: naming should be based on the post index
        """
        Take a screenshot with automatic numbering and metadata.

        Args:
            prefix: Filename prefix (default: "scroll")
            metadata: Additional metadata to include

        Returns:
            Filepath of saved screenshot
        """
        if not self.page:
            raise RuntimeError("Browser not initialized")

        # Increment counter
        self.screenshot_counter += 1

        # Create timestamped directory structure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = Path("screenshots") / f"session_{timestamp}"
        session_dir.mkdir(parents=True, exist_ok=True)

        # Create filename with number and timestamp
        filename = f"{prefix}_{self.screenshot_counter:03d}_{timestamp}.png"
        filepath = session_dir / filename

        try:
            await self.page.screenshot(path=str(filepath), full_page=True)

            # Save metadata if provided
            if metadata:
                metadata_file = filepath.with_suffix('.json')
                metadata_with_timestamp = {
                    'screenshot_number': self.screenshot_counter,
                    'timestamp': datetime.now().isoformat(),
                    'filename': filename,
                    **metadata
                }

                with open(metadata_file, 'w') as f:
                    json.dump(metadata_with_timestamp, f, indent=2)

            print(f"📸 Screenshot {self.screenshot_counter:03d} saved: {filepath}")
            return str(filepath)

        except Exception as e:
            print(f"❌ Error taking screenshot: {e}")
            return ""

    async def close(self) -> None:
        """Close browser and clean up resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            print("🔒 Browser closed")
        except Exception as e:
            print(f"❌ Error closing browser: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()