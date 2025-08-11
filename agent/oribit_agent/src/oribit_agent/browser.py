"""Browser automation with persistent context management."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger(__name__)


class BrowserContextManager:
    """Manages persistent Playwright browser context with session storage."""

    def __init__(self, user_data_dir: Optional[str] = None):
        self.user_data_dir = user_data_dir or str(Path.home() / ".orbit" / "browser_data")
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._playwright = None

    async def start(self) -> None:
        """Initialize browser with persistent context."""
        if self.browser is not None:
            return

        try:
            self._playwright = await async_playwright().start()

            # Launch browser with persistent context
            headless_env = os.environ.get("ORBIT_HEADLESS", "").lower()
            headless = headless_env in ("1", "true", "yes")

            self.browser = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=headless,  # Toggle via ORBIT_HEADLESS env var
                viewport={"width": 1280, "height": 720},
                args=["--disable-blink-features=AutomationControlled", "--disable-dev-shm-usage"],
            )

            # Get or create the first page
            pages = self.browser.pages
            if pages:
                self.page = pages[0]
            else:
                self.page = await self.browser.new_page()

            logger.info(f"Browser started with persistent context at {self.user_data_dir}")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Clean shutdown of browser."""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.page = None

            if self._playwright:
                await self._playwright.stop()
                self._playwright = None

            logger.info("Browser stopped")

        except Exception as e:
            logger.error(f"Error stopping browser: {e}")

    async def get_page(self) -> Page:
        """Get the current page, starting browser if needed."""
        if not self.browser or not self.page:
            await self.start()

        if not self.page or self.page.is_closed():
            self.page = await self.browser.new_page()

        return self.page

    async def navigate(self, url: str, timeout: int = 30000) -> Dict[str, Any]:
        """Navigate to a URL."""
        page = await self.get_page()

        try:
            response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")

            return {
                "success": True,
                "url": page.url,
                "title": await page.title(),
                "status": response.status if response else None,
            }

        except Exception as e:
            logger.error(f"Navigation failed for {url}: {e}")
            return {"success": False, "error": str(e), "url": page.url}

    async def click(self, selector: str, timeout: int = 30000) -> Dict[str, Any]:
        """Click an element by CSS selector."""
        page = await self.get_page()

        try:
            await page.wait_for_selector(selector, timeout=timeout)
            await page.click(selector)

            return {"success": True, "selector": selector}

        except Exception as e:
            logger.error(f"Click failed for selector {selector}: {e}")
            return {"success": False, "error": str(e), "selector": selector}

    async def type_text(self, selector: str, text: str, timeout: int = 30000) -> Dict[str, Any]:
        """Type text into an input element."""
        page = await self.get_page()

        try:
            await page.wait_for_selector(selector, timeout=timeout)
            await page.fill(selector, text)

            return {"success": True, "selector": selector, "text": text}

        except Exception as e:
            logger.error(f"Type failed for selector {selector}: {e}")
            return {"success": False, "error": str(e), "selector": selector}

    async def get_text(self, selector: str, timeout: int = 30000) -> Dict[str, Any]:
        """Get text content from an element."""
        page = await self.get_page()

        try:
            await page.wait_for_selector(selector, timeout=timeout)
            text = await page.text_content(selector)

            return {"success": True, "selector": selector, "text": text or ""}

        except Exception as e:
            logger.error(f"Get text failed for selector {selector}: {e}")
            return {"success": False, "error": str(e), "selector": selector}

    async def screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot of the current page."""
        page = await self.get_page()

        try:
            if not path:
                path = str(
                    Path.home()
                    / ".orbit"
                    / "screenshots"
                    / f"screenshot_{asyncio.get_event_loop().time()}.png"
                )

            Path(path).parent.mkdir(parents=True, exist_ok=True)

            await page.screenshot(path=path, full_page=True)

            return {"success": True, "path": path, "url": page.url}

        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"success": False, "error": str(e)}


# Global browser instance
_browser_manager: Optional[BrowserContextManager] = None


async def get_browser() -> BrowserContextManager:
    """Get the global browser instance."""
    global _browser_manager

    if _browser_manager is None:
        _browser_manager = BrowserContextManager()

    return _browser_manager


async def cleanup_browser() -> None:
    """Cleanup the global browser instance."""
    global _browser_manager

    if _browser_manager:
        await _browser_manager.stop()
        _browser_manager = None
