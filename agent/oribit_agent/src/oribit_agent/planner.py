"""
Deterministic natural language planner for Phase 1 + Phase 2.
Uses regex patterns to parse commands into executable tool calls.
No LLM involved - pure deterministic parsing for reliable testing.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List


def plan(command: str) -> List[Dict[str, Any]]:
    """
    Parse a natural language command into a sequence of tool calls.

    Supported patterns:
    - "create N files in DIRECTORY" -> create_files tool
    - "open APP" or "open app NAME" -> open_app tool
    - "navigate to URL" or "go to URL" -> browser_navigate tool
    - "click SELECTOR" -> browser_click tool
    - "type TEXT into SELECTOR" -> browser_type tool
    - "get text from SELECTOR" -> browser_get_text tool
    - "screenshot" or "take screenshot" -> browser_screenshot tool
    - "read file PATH" -> read_file tool
    - "write TEXT to PATH" -> write_file tool
    - "list files in PATH" -> list_directory tool
    - "create directory PATH" -> make_directory tool
    - "move SOURCE to DEST" -> move_file tool
    - "delete PATH" -> delete_file tool
    - "reveal PATH" -> reveal_in_finder tool
    - "create event TITLE at TIME" -> create_calendar_event tool
    - "list events" or "show calendar" -> list_calendar_events tool
    - "delete event ID" -> delete_calendar_event tool
    - "play spotify" or "play music" -> spotify_play tool
    - "pause spotify" -> spotify_pause tool
    - "next song" -> spotify_next_track tool
    - "previous song" -> spotify_previous_track tool
    - "current song" -> spotify_get_current_track tool
    - "search spotify QUERY" -> spotify_search_and_play tool
    - Combinations with "then" or "and"

    Args:
        command: Natural language command string

    Returns:
        List of tool call dictionaries with 'tool' and 'args' keys
    """
    steps: List[Dict[str, Any]] = []
    cmd_lower = command.lower().strip()

    # Split on common conjunctions to handle multiple commands
    parts = re.split(r"\s+(?:then|and)\s+", cmd_lower)

    for part in parts:
        part = part.strip()

        # Pattern 1: "create N files in DIRECTORY [prefix PREFIX] [ext EXTENSION]"
        if "create" in part and "file" in part and "event" not in part:
            step = _parse_create_files(part)
            if step:
                steps.append(step)

        # Pattern 2: "open APP" or "open app NAME" (but not browser navigation)
        elif "open" in part and not ("navigate" in part or "go to" in part):
            step = _parse_open_app(part)
            if step:
                steps.append(step)

        # Pattern 3: "navigate to URL" or "go to URL"
        elif "navigate" in part or "go to" in part:
            step = _parse_browser_navigate(part)
            if step:
                steps.append(step)
                # If command contains summarization intent, queue summarize step after navigation
                if any(
                    x in cmd_lower
                    for x in [
                        "summarize",
                        "summary",
                        "give me a summary",
                        "what's new",
                        "most recent news",
                    ]
                ):
                    steps.append({"tool": "browser_summarize_page", "args": {}})

        # Pattern 4: "click SELECTOR"
        elif "click" in part:
            step = _parse_browser_click(part)
            if step:
                steps.append(step)

        # Pattern 5: "type TEXT into SELECTOR"
        elif "type" in part:
            step = _parse_browser_type(part)
            if step:
                steps.append(step)

        # Pattern 6: "get text from SELECTOR"
        elif "get text" in part:
            step = _parse_browser_get_text(part)
            if step:
                steps.append(step)

        # Pattern 7: "screenshot" or "take screenshot"
        elif "screenshot" in part:
            step = _parse_browser_screenshot(part)
            if step:
                steps.append(step)
                # If screenshot was requested along with summary, add summarize too
                if any(x in cmd_lower for x in ["summarize", "summary"]):
                    steps.append({"tool": "browser_summarize_page", "args": {}})

        # Pattern 8: "read file PATH"
        elif "read" in part and "file" in part:
            step = _parse_read_file(part)
            if step:
                steps.append(step)

        # Pattern 9: "write TEXT to PATH"
        elif "write" in part:
            step = _parse_write_file(part)
            if step:
                steps.append(step)

        # Pattern 10: "list files" or "list directory"
        elif "list" in part and ("file" in part or "director" in part) and "event" not in part:
            step = _parse_list_directory(part)
            if step:
                steps.append(step)

        # Pattern 11: "create directory" or "make directory"
        elif ("create" in part or "make" in part) and "director" in part:
            step = _parse_make_directory(part)
            if step:
                steps.append(step)

        # Pattern 12: "move SOURCE to DEST"
        elif "move" in part:
            step = _parse_move_file(part)
            if step:
                steps.append(step)

        # Pattern 13: "delete PATH"
        elif "delete" in part or "remove" in part:
            if "event" in part:
                step = _parse_delete_calendar_event(part)
            else:
                step = _parse_delete_file(part)
            if step:
                steps.append(step)

        # Pattern 14: "reveal PATH" or "show in finder"
        elif "reveal" in part or ("show" in part and "finder" in part):
            step = _parse_reveal_in_finder(part)
            if step:
                steps.append(step)

        # Pattern 15: "create event" or "schedule"
        elif ("create" in part or "schedule" in part) and "event" in part:
            step = _parse_create_calendar_event(part)
            if step:
                steps.append(step)

        # Pattern 16: "list events" or "show calendar"
        elif ("list" in part and "event" in part) or ("show" in part and "calendar" in part):
            step = _parse_list_calendar_events(part)
            if step:
                steps.append(step)

        # Pattern 17: Spotify play commands
        elif ("play" in part and ("spotify" in part or "music" in part)) or part.strip() == "play":
            # Try to parse a descriptive query to play specific genre/mood
            step = _parse_spotify_play_query(part)
            if step is None:
                step = _parse_spotify_play(part)
            if step:
                steps.append(step)

        # Pattern 18: Spotify pause commands
        elif "pause" in part and ("spotify" in part or "music" in part):
            step = _parse_spotify_pause(part)
            if step:
                steps.append(step)

        # Pattern 19: Next/previous song
        elif ("next" in part or "skip" in part) and ("song" in part or "track" in part):
            step = _parse_spotify_next(part)
            if step:
                steps.append(step)
        elif "previous" in part and ("song" in part or "track" in part):
            step = _parse_spotify_previous(part)
            if step:
                steps.append(step)

        # Pattern 20: Current song
        elif ("current" in part or "what's playing" in part) and (
            "song" in part or "track" in part or "playing" in part
        ):
            step = _parse_spotify_current(part)
            if step:
                steps.append(step)

        # Pattern 21: Spotify search
        elif "search" in part and ("spotify" in part or "music" in part):
            step = _parse_spotify_search(part)
            if step:
                steps.append(step)

    return steps


def _parse_create_files(text: str) -> Dict[str, Any] | None:
    """Parse file creation command."""
    # Default values
    count = 1
    directory = "~/Documents"
    prefix = "note"
    ext = "md"

    # Extract number of files
    count_match = re.search(r"create\s+(\d+)\s+files?", text)
    if count_match:
        count = int(count_match.group(1))
    elif "create" in text and "file" in text:
        # If no number specified but "create file" is mentioned, default to 1
        count = 1
    else:
        return None

    # Extract directory
    if "documents" in text:
        directory = "~/Documents"
    elif "desktop" in text:
        directory = "~/Desktop"
    elif "downloads" in text:
        directory = "~/Downloads"
    elif dir_match := re.search(r"in\s+(~/[^\s]+|/[^\s]+)", text):
        directory = dir_match.group(1)
    elif dir_match := re.search(r"in\s+([^\s]+)", text):
        # Handle relative paths or simple directory names
        directory = f"~/{dir_match.group(1)}"

    # Extract prefix
    if prefix_match := re.search(r"prefix\s+([a-zA-Z0-9_-]+)", text):
        prefix = prefix_match.group(1)
    elif "note" in text:
        prefix = "note"
    elif "todo" in text:
        prefix = "todo"
    elif "task" in text:
        prefix = "task"

    # Extract extension
    if ext_match := re.search(r"\b(md|txt|pdf|png|jpg|jpeg|py|js|ts|json)\b", text):
        ext = ext_match.group(1)
    elif "markdown" in text:
        ext = "md"
    elif "text" in text:
        ext = "txt"

    return {
        "tool": "create_files",
        "args": {"dir": directory, "count": count, "prefix": prefix, "ext": ext},
    }


def _parse_open_app(text: str) -> Dict[str, Any] | None:
    """Parse app opening command."""
    # Common app name mappings
    app_mappings = {
        "notion": "Notion",
        "calculator": "Calculator",
        "finder": "Finder",
        "safari": "Safari",
        "chrome": "Google Chrome",
        "firefox": "Firefox",
        "vscode": "Visual Studio Code",
        "code": "Visual Studio Code",
        "terminal": "Terminal",
        "xcode": "Xcode",
        "slack": "Slack",
        "discord": "Discord",
        "spotify": "Spotify",
        "notes": "Notes",
        "mail": "Mail",
        "calendar": "Calendar",
    }

    app_name = None

    # Direct app name matches
    for keyword, proper_name in app_mappings.items():
        if keyword in text:
            app_name = proper_name
            break

    # Pattern: "open app NAME"
    if app_match := re.search(r"open\s+app\s+([^\s]+(?:\s+[^\s]+)*)", text):
        app_candidate = app_match.group(1).strip().strip('"').strip("'")
        # Capitalize each word for proper app name format
        app_name = " ".join(word.capitalize() for word in app_candidate.split())

    # Pattern: "open NAME" (direct app name)
    elif app_match := re.search(r"open\s+([a-zA-Z][^\s]*(?:\s+[a-zA-Z][^\s]*)*)", text):
        app_candidate = app_match.group(1).strip()
        if app_candidate.lower() not in ["file", "files", "folder", "directory"]:
            app_name = " ".join(word.capitalize() for word in app_candidate.split())

    if app_name:
        return {"tool": "open_app", "args": {"name": app_name}}

    return None


def _parse_browser_navigate(text: str) -> Dict[str, Any] | None:
    """Parse browser navigation command."""
    # Pattern: "navigate to URL" or "go to URL"
    url_patterns = [
        r"navigate\s+to\s+(https?://[^\s]+)",
        r"go\s+to\s+(https?://[^\s]+)",
        r"navigate\s+to\s+([^\s]+\.[^\s]{2,})",  # domain.tld
        r"go\s+to\s+([^\s]+\.[^\s]{2,})",  # domain.tld
    ]

    for pattern in url_patterns:
        if match := re.search(pattern, text):
            url = match.group(1).strip()
            # Add https:// if no protocol specified
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            return {"tool": "browser_navigate", "args": {"url": url}}

    return None


def _parse_browser_click(text: str) -> Dict[str, Any] | None:
    """Parse browser click command."""
    # Pattern: "click SELECTOR"
    if match := re.search(r"click\s+([#.]?[^\s]+(?:\s[^\s]+)*)", text):
        selector = match.group(1).strip().strip('"').strip("'")

        return {"tool": "browser_click", "args": {"selector": selector}}

    return None


def _parse_browser_type(text: str) -> Dict[str, Any] | None:
    """Parse browser type command."""
    # Pattern: "type TEXT into SELECTOR"
    if match := re.search(r'type\s+"([^"]+)"\s+into\s+([#.]?[^\s]+(?:\s[^\s]+)*)', text):
        typed_text = match.group(1).strip()
        selector = match.group(2).strip()

        return {"tool": "browser_type", "args": {"selector": selector, "text": typed_text}}

    # Pattern: "type TEXT in SELECTOR"
    elif match := re.search(r'type\s+"([^"]+)"\s+in\s+([#.]?[^\s]+(?:\s[^\s]+)*)', text):
        typed_text = match.group(1).strip()
        selector = match.group(2).strip()

        return {"tool": "browser_type", "args": {"selector": selector, "text": typed_text}}

    return None


def _parse_browser_get_text(text: str) -> Dict[str, Any] | None:
    """Parse browser get text command."""
    # Pattern: "get text from SELECTOR"
    if match := re.search(r"get\s+text\s+from\s+([#.]?[^\s]+(?:\s[^\s]+)*)", text):
        selector = match.group(1).strip().strip('"').strip("'")

        return {"tool": "browser_get_text", "args": {"selector": selector}}

    return None


def _parse_browser_screenshot(text: str) -> Dict[str, Any] | None:
    """Parse browser screenshot command."""
    # Pattern: "screenshot" or "take screenshot"
    if "screenshot" in text:
        return {"tool": "browser_screenshot", "args": {}}

    return None


def _parse_read_file(text: str) -> Dict[str, Any] | None:
    """Parse read file command."""
    # Pattern: "read file PATH"
    if match := re.search(r"read\s+file\s+([^\s]+(?:\s[^\s]+)*)", text):
        path = match.group(1).strip().strip('"').strip("'")

        return {"tool": "read_file", "args": {"path": path}}

    return None


def _parse_write_file(text: str) -> Dict[str, Any] | None:
    """Parse write file command."""
    # Pattern: "write TEXT to PATH"
    if match := re.search(r'write\s+"([^"]+)"\s+to\s+([^\s]+(?:\s[^\s]+)*)', text):
        content = match.group(1).strip()
        path = match.group(2).strip().strip('"').strip("'")

        return {"tool": "write_file", "args": {"path": path, "content": content}}

    # Pattern: "write TEXT in PATH"
    elif match := re.search(r'write\s+"([^"]+)"\s+in\s+([^\s]+(?:\s[^\s]+)*)', text):
        content = match.group(1).strip()
        path = match.group(2).strip().strip('"').strip("'")

        return {"tool": "write_file", "args": {"path": path, "content": content}}

    return None


def _parse_list_directory(text: str) -> Dict[str, Any] | None:
    """Parse list directory command."""
    # Pattern: "list files in PATH"
    if match := re.search(r"list\s+files\s+in\s+([^\s]+(?:\s[^\s]+)*)", text):
        path = match.group(1).strip().strip('"').strip("'")

        return {"tool": "list_directory", "args": {"path": path}}

    # Pattern: "list directory PATH"
    elif match := re.search(r"list\s+director(?:y|ies)\s+([^\s]+(?:\s[^\s]+)*)", text):
        path = match.group(1).strip().strip('"').strip("'")

        return {"tool": "list_directory", "args": {"path": path}}

    # Pattern: "list files" (current directory)
    elif "list" in text and "file" in text:
        return {"tool": "list_directory", "args": {"path": "."}}

    return None


def _parse_make_directory(text: str) -> Dict[str, Any] | None:
    """Parse make directory command."""
    # Pattern: "create directory PATH" or "make directory PATH"
    patterns = [
        r"create\s+director(?:y|ies)\s+([^\s]+(?:\s[^\s]+)*)",
        r"make\s+director(?:y|ies)\s+([^\s]+(?:\s[^\s]+)*)",
    ]

    for pattern in patterns:
        if match := re.search(pattern, text):
            path = match.group(1).strip().strip('"').strip("'")

            return {"tool": "make_directory", "args": {"path": path}}

    return None


def _parse_move_file(text: str) -> Dict[str, Any] | None:
    """Parse move file command."""
    # Pattern: "move SOURCE to DEST"
    if match := re.search(r"move\s+([^\s]+(?:\s[^\s]+)*)\s+to\s+([^\s]+(?:\s[^\s]+)*)", text):
        source = match.group(1).strip().strip('"').strip("'")
        dest = match.group(2).strip().strip('"').strip("'")

        return {"tool": "move_file", "args": {"source": source, "destination": dest}}

    return None


def _parse_delete_file(text: str) -> Dict[str, Any] | None:
    """Parse delete file command."""
    # Pattern: "delete PATH" or "remove PATH"
    patterns = [r"delete\s+([^\s]+(?:\s[^\s]+)*)", r"remove\s+([^\s]+(?:\s[^\s]+)*)"]

    for pattern in patterns:
        if match := re.search(pattern, text):
            path = match.group(1).strip().strip('"').strip("'")

            return {"tool": "delete_file", "args": {"path": path}}

    return None


def _parse_reveal_in_finder(text: str) -> Dict[str, Any] | None:
    """Parse reveal in finder command."""
    # Pattern: "reveal PATH" or "show PATH in finder"
    if match := re.search(r"reveal\s+([^\s]+(?:\s[^\s]+)*)", text):
        path = match.group(1).strip().strip('"').strip("'")

        return {"tool": "reveal_in_finder", "args": {"path": path}}

    elif match := re.search(r"show\s+([^\s]+(?:\s[^\s]+)*)\s+in\s+finder", text):
        path = match.group(1).strip().strip('"').strip("'")

        return {"tool": "reveal_in_finder", "args": {"path": path}}

    return None


def _parse_create_calendar_event(text: str) -> Dict[str, Any] | None:
    """Parse create calendar event command."""
    # Pattern: "create event TITLE at TIME"
    if match := re.search(r"(?:create|schedule)\s+event\s+(.+?)\s+at\s+(.+)", text):
        title = match.group(1).strip().strip('"').strip("'")
        start_date = match.group(2).strip()

        return {"tool": "create_calendar_event", "args": {"title": title, "start_date": start_date}}

    # Pattern: "create event TITLE"
    elif match := re.search(r"(?:create|schedule)\s+event\s+(.+)", text):
        title = match.group(1).strip().strip('"').strip("'")

        return {
            "tool": "create_calendar_event",
            "args": {"title": title, "start_date": "today at 9:00"},
        }

    return None


def _parse_list_calendar_events(text: str) -> Dict[str, Any] | None:
    """Parse list calendar events command."""
    # Pattern: "list events" or "show calendar"
    return {"tool": "list_calendar_events", "args": {}}


def _parse_delete_calendar_event(text: str) -> Dict[str, Any] | None:
    """Parse delete calendar event command."""
    # Pattern: "delete event ID"
    if match := re.search(r"delete\s+event\s+([^\s]+)", text):
        event_id = match.group(1).strip()

        return {"tool": "delete_calendar_event", "args": {"event_id": event_id}}

    return None


def _parse_spotify_play(text: str) -> Dict[str, Any] | None:
    """Parse Spotify play command."""
    return {"tool": "spotify_play", "args": {}}


def _parse_spotify_play_query(text: str) -> Dict[str, Any] | None:
    """Parse descriptive Spotify play query (e.g., "play some study music calm but fast")."""
    # Capture text after "play" and remove filler words
    m = re.search(r"play\s+(.*)", text)
    if not m:
        return None
    phrase = m.group(1).strip()

    # Remove common filler and platform words
    fillers = {
        "some",
        "a",
        "the",
        "music",
        "song",
        "songs",
        "track",
        "tracks",
        "on",
        "in",
        "spotify",
        "something",
    }
    tokens = [t for t in re.split(r"\s+", phrase) if t]
    tokens = [t for t in tokens if t.lower() not in fillers]
    if not tokens:
        return None

    query = " ".join(tokens)
    # If the query looks too generic (single word like "spotify"), skip
    if query.strip().lower() in ("spotify", "music"):
        return None

    return {"tool": "spotify_search_and_play", "args": {"query": query}}


def _parse_spotify_pause(text: str) -> Dict[str, Any] | None:
    """Parse Spotify pause command."""
    return {"tool": "spotify_pause", "args": {}}


def _parse_spotify_next(text: str) -> Dict[str, Any] | None:
    """Parse Spotify next track command."""
    return {"tool": "spotify_next_track", "args": {}}


def _parse_spotify_previous(text: str) -> Dict[str, Any] | None:
    """Parse Spotify previous track command."""
    return {"tool": "spotify_previous_track", "args": {}}


def _parse_spotify_current(text: str) -> Dict[str, Any] | None:
    """Parse Spotify current track command."""
    return {"tool": "spotify_get_current_track", "args": {}}


def _parse_spotify_search(text: str) -> Dict[str, Any] | None:
    """Parse Spotify search command."""
    # Pattern: "search spotify QUERY" or "search music QUERY"
    if match := re.search(r"search\s+(?:spotify|music)\s+(.+)", text):
        query = match.group(1).strip().strip('"').strip("'")

        return {"tool": "spotify_search_and_play", "args": {"query": query}}

    return None
