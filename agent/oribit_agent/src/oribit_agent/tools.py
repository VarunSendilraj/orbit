"""
Tool registry with OrbitHelper integration.
Provides the actual implementation of tools that can be called by the planner.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from .browser import get_browser
from .file_ops import (
    read_file,
    write_file,
    list_directory,
    make_directory,
    move_file,
    delete_file,
    reveal_in_finder,
)
from .calendar_ops import create_calendar_event, list_calendar_events, delete_calendar_event
from .spotify_ops import (
    spotify_play,
    spotify_pause,
    spotify_next_track,
    spotify_previous_track,
    spotify_get_current_track,
    spotify_search_and_play,
    spotify_set_volume,
)

# Optional LLM clients for summarization
try:
    import openai  # type: ignore
except Exception:
    openai = None  # type: ignore
try:
    import anthropic  # type: ignore
except Exception:
    anthropic = None  # type: ignore


# Path to OrbitHelper CLI binary from environment
HELPER_PATH = os.environ.get("ORBIT_HELPER_PATH")


def create_files(dir: str, count: int, prefix: str, ext: str) -> List[str]:
    """
    Create multiple files with specified parameters.

    Args:
        dir: Directory path (supports ~ expansion)
        count: Number of files to create
        prefix: Filename prefix
        ext: File extension

    Returns:
        List of created file paths

    Raises:
        OSError: If directory creation or file writing fails
    """
    target_path = Path(os.path.expanduser(dir))
    target_path.mkdir(parents=True, exist_ok=True)

    created_files = []
    for i in range(1, count + 1):
        file_path = target_path / f"{prefix}_{i}.{ext}"
        file_path.write_text("")  # Create empty file
        created_files.append(str(file_path))

    return created_files


def open_app(name: str) -> None:
    """
    Open a macOS application by name.
    Uses the native 'open -a' command which doesn't require Accessibility permissions.

    Args:
        name: Application name (e.g., "Notion", "Calculator")

    Raises:
        subprocess.CalledProcessError: If the app cannot be opened
    """
    try:
        subprocess.run(["open", "-a", name], check=True)
    except subprocess.CalledProcessError:
        # Fallback to bundle identifier for known apps (e.g., Spotify)
        bundle_ids = {
            "spotify": "com.spotify.client",
        }
        bundle_id = bundle_ids.get(name.lower())
        if bundle_id:
            subprocess.run(["open", "-b", bundle_id], check=True)
            return
        raise


def helper(*args: str) -> str:
    """
    Call the OrbitHelper CLI with the given arguments.
    This will be used for more advanced automation that requires Accessibility permissions.

    Args:
        *args: Command line arguments to pass to OrbitHelper

    Returns:
        Command output as string

    Raises:
        RuntimeError: If ORBIT_HELPER_PATH is not configured
        subprocess.CalledProcessError: If the helper command fails
    """
    if not HELPER_PATH:
        raise RuntimeError(
            "ORBIT_HELPER_PATH environment variable not set. "
            "Please set it to the path of your OrbitHelper binary."
        )

    if not os.path.exists(HELPER_PATH):
        raise RuntimeError(f"OrbitHelper binary not found at {HELPER_PATH}")

    result = subprocess.run([HELPER_PATH, *args], capture_output=True, text=True, check=True)

    return result.stdout.strip()


# Browser automation tools
async def browser_navigate(url: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Navigate to a URL using the persistent browser context.

    Args:
        url: Target URL to navigate to
        timeout: Timeout in milliseconds (default: 30000)

    Returns:
        Dict with success status, current URL, page title, and response status
    """
    browser = await get_browser()
    return await browser.navigate(url, timeout)


async def browser_click(selector: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Click an element by CSS selector.

    Args:
        selector: CSS selector for the element to click
        timeout: Timeout in milliseconds (default: 30000)

    Returns:
        Dict with success status and selector
    """
    browser = await get_browser()
    return await browser.click(selector, timeout)


async def browser_type(selector: str, text: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Type text into an input element.

    Args:
        selector: CSS selector for the input element
        text: Text to type
        timeout: Timeout in milliseconds (default: 30000)

    Returns:
        Dict with success status, selector, and text
    """
    browser = await get_browser()
    return await browser.type_text(selector, text, timeout)


async def browser_get_text(selector: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Get text content from an element.

    Args:
        selector: CSS selector for the element
        timeout: Timeout in milliseconds (default: 30000)

    Returns:
        Dict with success status, selector, and extracted text
    """
    browser = await get_browser()
    return await browser.get_text(selector, timeout)


async def browser_screenshot(path: str = None) -> Dict[str, Any]:
    """
    Take a screenshot of the current page.

    Args:
        path: Optional custom path for screenshot file

    Returns:
        Dict with success status and screenshot path
    """
    browser = await get_browser()
    return await browser.screenshot(path)


def _summarize_with_llm(text: str, instructions: Optional[str] = None) -> Dict[str, Any]:
    """Summarize text using available LLM (OpenAI preferred, else Anthropic)."""
    provider = None
    if os.environ.get("OPENAI_API_KEY") and openai is not None:
        provider = "openai"
    elif os.environ.get("ANTHROPIC_API_KEY") and anthropic is not None:
        provider = "anthropic"

    if provider is None:
        return {
            "success": False,
            "error": "No LLM API key configured for summarization",
        }

    default_instructions = (
        "Summarize the following web page content for a user. "
        "Prioritize the most recent or top items. Provide a short, factual, bullet-point summary."
    )
    prompt = instructions.strip() if instructions else default_instructions
    # Trim text to keep token usage in check
    text = text[:12000]

    try:
        if provider == "openai":
            client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            resp = client.chat.completions.create(
                model=os.environ.get("ORBIT_SUMMARY_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a concise, neutral summarizer."},
                    {
                        "role": "user",
                        "content": f"Instructions: {prompt}\n\nContent to summarize:\n{text}",
                    },
                ],
                temperature=0.2,
            )
            summary = resp.choices[0].message.content
            return {"success": True, "provider": provider, "summary": summary}
        else:
            client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
            resp = client.messages.create(
                model=os.environ.get("ORBIT_SUMMARY_MODEL", "claude-3-5-sonnet-20241022"),
                max_tokens=500,
                system="You are a concise, neutral summarizer.",
                messages=[
                    {
                        "role": "user",
                        "content": f"Instructions: {prompt}\n\nContent to summarize:\n{text}",
                    }
                ],
            )
            # Concatenate text blocks
            parts = []
            for block in resp.content:
                if getattr(block, "type", "") == "text":
                    parts.append(getattr(block, "text", ""))
            summary = "\n".join(parts) if parts else ""
            return {"success": True, "provider": provider, "summary": summary}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def browser_summarize_page(instructions: Optional[str] = None) -> Dict[str, Any]:
    """Fetch current page text and return an LLM summary."""
    browser = await get_browser()
    try:
        page = await browser.get_page()
        # Try getting visible text
        result = await browser.get_text("body", timeout=15000)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Failed to get page text")}
        text = result.get("text", "")
        if not text.strip():
            # fallback: page content (HTML), although summarization prefers plain text
            html = await page.content()
            text = html
        # First try LLM summarization
        sum_res = _summarize_with_llm(text, instructions)
        if sum_res.get("success"):
            return {
                "success": True,
                "summary": sum_res.get("summary", ""),
                "provider": sum_res.get("provider"),
                "url": page.url,
            }

        # Fallback: heuristic summary from headings if LLM not available or failed
        title = await page.title()
        try:
            headings = await page.locator(
                "article h1, article h2, main h1, main h2, h1, h2, h3, [role='heading']"
            ).all_text_contents()
        except Exception:
            headings = []
        # Clean and deduplicate
        seen = set()
        cleaned: List[str] = []
        for h in headings:
            s = (h or "").strip()
            if len(s) < 5:
                continue
            if s in seen:
                continue
            seen.add(s)
            cleaned.append(s)
        top = cleaned[:8] if cleaned else []
        summary_lines = []
        if top:
            summary_lines.append(f"Top headlines from {title}:")
            for item in top:
                summary_lines.append(f"- {item}")
        else:
            # As last resort, truncate body text
            summary_lines.append(f"Summary of {title} (first 500 chars):")
            summary_lines.append(text[:500].replace("\n", " "))

        return {
            "success": True,
            "provider": sum_res.get("provider", "heuristic"),
            "summary": "\n".join(summary_lines),
            "url": page.url,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tool registry for easy lookup and future expansion
TOOLS = {
    "create_files": create_files,
    "open_app": open_app,
    "helper": helper,
    "browser_navigate": browser_navigate,
    "browser_click": browser_click,
    "browser_type": browser_type,
    "browser_get_text": browser_get_text,
    "browser_screenshot": browser_screenshot,
    "browser_summarize_page": browser_summarize_page,
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "make_directory": make_directory,
    "move_file": move_file,
    "delete_file": delete_file,
    "reveal_in_finder": reveal_in_finder,
    "create_calendar_event": create_calendar_event,
    "list_calendar_events": list_calendar_events,
    "delete_calendar_event": delete_calendar_event,
    "spotify_play": spotify_play,
    "spotify_pause": spotify_pause,
    "spotify_next_track": spotify_next_track,
    "spotify_previous_track": spotify_previous_track,
    "spotify_get_current_track": spotify_get_current_track,
    "spotify_search_and_play": spotify_search_and_play,
    "spotify_set_volume": spotify_set_volume,
}


def get_tool(name: str):
    """Get a tool function by name."""
    return TOOLS.get(name)
