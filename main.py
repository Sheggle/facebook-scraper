#!/usr/bin/env python3
"""
Facebook Scraper - Main CLI interface
"""

import asyncio
import argparse
import sys
import json
from pathlib import Path
from scraper.browser import FacebookBrowser
from scraper.facebook import FacebookScraper


async def scrape_facebook_post(url: str, scroll_jump_size: int = 3, scroll_wait_time: float = 1.5, max_scrolls: int = 100) -> None:
    """
    Scrape a single Facebook post with comments.

    Args:
        url: Facebook post URL to scrape
        scroll_jump_size: Number of wheel notches per scroll (default: 3)
        scroll_wait_time: Wait time after each scroll in seconds (default: 1.5)
        max_scrolls: Maximum number of scroll attempts (default: 100)
    """
    print("🚀 Facebook Scraper Starting...")
    print(f"🎯 Target URL: {url}")
    print(f"⚙️  Scroll settings: {scroll_jump_size} notches, {scroll_wait_time}s wait, max {max_scrolls} scrolls")
    print("-" * 60)

    async with FacebookBrowser(scroll_jump_size=scroll_jump_size, scroll_wait_time=scroll_wait_time) as browser:
        if not browser.page:
            print("❌ Failed to initialize browser. Please run create_state.py first.")
            return

        scraper = FacebookScraper(browser, max_scroll_attempts=max_scrolls)

        result = await scraper.scrape_post_with_comments(url)

        # Save results to JSON file
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"scrape_results_{timestamp}.json"

        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2)

        print("\n" + "=" * 60)
        print("📊 SCRAPING RESULTS")
        print("=" * 60)
        print(f"Success: {'✅ Yes' if result['success'] else '❌ No'}")
        print(f"Screenshots taken: {len(result['screenshots'])}")
        print(f"Errors: {len(result['errors'])}")

        if result['screenshots']:
            print("\n📸 Screenshots:")
            for screenshot in result['screenshots']:
                print(f"   - {screenshot}")

        if result['errors']:
            print("\n❌ Errors:")
            for error in result['errors']:
                print(f"   - {error}")

        print(f"\n💾 Results saved to: {results_file}")
        print("=" * 60)


def validate_facebook_url(url: str) -> bool:
    """
    Validate that the provided URL is a Facebook URL.

    Args:
        url: URL to validate

    Returns:
        True if valid Facebook URL, False otherwise
    """
    facebook_domains = [
        'facebook.com',
        'www.facebook.com',
        'm.facebook.com',
        'mobile.facebook.com'
    ]

    return any(domain in url.lower() for domain in facebook_domains)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Facebook Post Scraper - Extract posts and comments using browser automation'
    )
    parser.add_argument(
        'url',
        help='Facebook post URL to scrape'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    # Scroll configuration options
    parser.add_argument(
        '--scroll-jump-size', '-s',
        type=int,
        default=3,
        help='Number of wheel notches per scroll (default: 3)'
    )
    parser.add_argument(
        '--scroll-wait-time', '-w',
        type=float,
        default=1.5,
        help='Wait time after each scroll in seconds (default: 1.5)'
    )
    parser.add_argument(
        '--max-scrolls', '-m',
        type=int,
        default=100,
        help='Maximum number of scroll attempts (default: 100)'
    )

    args = parser.parse_args()

    # Validate URL
    if not validate_facebook_url(args.url):
        print("❌ Error: Please provide a valid Facebook URL")
        print("   Example: https://www.facebook.com/page/posts/123456789")
        sys.exit(1)

    # Check if browser state exists
    state_file = Path("browser_state/facebook_state.json")
    if not state_file.exists():
        print("❌ No Facebook session found!")
        print("Please run the following command first to log in:")
        print("   python create_state.py")
        sys.exit(1)

    try:
        # Run the scraper with configuration options
        asyncio.run(scrape_facebook_post(
            args.url,
            scroll_jump_size=args.scroll_jump_size,
            scroll_wait_time=args.scroll_wait_time,
            max_scrolls=args.max_scrolls
        ))
    except KeyboardInterrupt:
        print("\n❌ Scraping cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
