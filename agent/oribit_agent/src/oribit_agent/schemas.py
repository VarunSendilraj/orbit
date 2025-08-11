"""
Pydantic models and JSON schemas for all Orbit Agent tools.
Used for LLM function calling and API validation.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# Browser automation schemas
class BrowserNavigateArgs(BaseModel):
    """Arguments for browser navigation."""

    url: str = Field(description="Target URL to navigate to")
    timeout: int = Field(default=30000, description="Timeout in milliseconds")


class BrowserClickArgs(BaseModel):
    """Arguments for browser element clicking."""

    selector: str = Field(description="CSS selector for the element to click")
    timeout: int = Field(default=30000, description="Timeout in milliseconds")


class BrowserTypeArgs(BaseModel):
    """Arguments for typing text into browser elements."""

    selector: str = Field(description="CSS selector for the input element")
    text: str = Field(description="Text to type into the element")
    timeout: int = Field(default=30000, description="Timeout in milliseconds")


class BrowserGetTextArgs(BaseModel):
    """Arguments for getting text from browser elements."""

    selector: str = Field(description="CSS selector for the element")
    timeout: int = Field(default=30000, description="Timeout in milliseconds")


class BrowserScreenshotArgs(BaseModel):
    """Arguments for taking browser screenshots."""

    path: Optional[str] = Field(
        default=None, description="Optional custom path for screenshot file"
    )


# File system operation schemas
class ReadFileArgs(BaseModel):
    """Arguments for reading files."""

    path: str = Field(description="File path to read (supports ~ expansion)")


class WriteFileArgs(BaseModel):
    """Arguments for writing files."""

    path: str = Field(description="File path to write to (supports ~ expansion)")
    content: str = Field(description="Text content to write")
    append: bool = Field(default=False, description="If True, append to file; if False, overwrite")


class ListDirectoryArgs(BaseModel):
    """Arguments for listing directories."""

    path: str = Field(default=".", description="Directory path to list (supports ~ expansion)")
    pattern: Optional[str] = Field(
        default=None, description="Optional glob pattern to filter results"
    )


class MakeDirectoryArgs(BaseModel):
    """Arguments for creating directories."""

    path: str = Field(description="Directory path to create (supports ~ expansion)")
    parents: bool = Field(default=True, description="Create parent directories as needed")


class MoveFileArgs(BaseModel):
    """Arguments for moving/renaming files."""

    source: str = Field(description="Source path (supports ~ expansion)")
    destination: str = Field(description="Destination path (supports ~ expansion)")


class DeleteFileArgs(BaseModel):
    """Arguments for deleting files."""

    path: str = Field(description="Path to delete (supports ~ expansion)")
    recursive: bool = Field(default=False, description="Delete directories recursively")


class RevealInFinderArgs(BaseModel):
    """Arguments for revealing files in macOS Finder."""

    path: str = Field(description="Path to reveal (supports ~ expansion)")


# Calendar integration schemas
class CreateCalendarEventArgs(BaseModel):
    """Arguments for creating calendar events."""

    title: str = Field(description="Event title")
    start_date: str = Field(description="Start date/time (ISO format or natural language)")
    end_date: Optional[str] = Field(
        default=None, description="End date/time (defaults to 1 hour after start)"
    )
    description: Optional[str] = Field(default=None, description="Event description")
    location: Optional[str] = Field(default=None, description="Event location")


class ListCalendarEventsArgs(BaseModel):
    """Arguments for listing calendar events."""

    days_ahead: int = Field(default=7, description="Number of days to look ahead")
    calendar_name: Optional[str] = Field(default=None, description="Specific calendar name")


class DeleteCalendarEventArgs(BaseModel):
    """Arguments for deleting calendar events."""

    event_id: str = Field(description="Calendar event ID to delete")


# Spotify integration schemas
class SpotifyPlayArgs(BaseModel):
    """Arguments for playing Spotify."""

    pass  # No arguments needed


class SpotifyPauseArgs(BaseModel):
    """Arguments for pausing Spotify."""

    pass  # No arguments needed


class SpotifyNextTrackArgs(BaseModel):
    """Arguments for skipping to next track."""

    pass  # No arguments needed


class SpotifyPreviousTrackArgs(BaseModel):
    """Arguments for going to previous track."""

    pass  # No arguments needed


class SpotifyGetCurrentTrackArgs(BaseModel):
    """Arguments for getting current track info."""

    pass  # No arguments needed


class SpotifySearchAndPlayArgs(BaseModel):
    """Arguments for searching and playing on Spotify."""

    query: str = Field(description="Search query (song, artist, album, etc.)")


class SpotifySetVolumeArgs(BaseModel):
    """Arguments for setting Spotify volume."""

    volume: int = Field(description="Volume level (0-100)", ge=0, le=100)


# Legacy tool schemas
class CreateFilesArgs(BaseModel):
    """Arguments for creating multiple files."""

    dir: str = Field(default="~/Documents", description="Directory path (supports ~ expansion)")
    count: int = Field(default=1, description="Number of files to create")
    prefix: str = Field(default="note", description="Filename prefix")
    ext: str = Field(default="md", description="File extension")


class OpenAppArgs(BaseModel):
    """Arguments for opening macOS applications."""

    name: str = Field(description="Application name")


class HelperArgs(BaseModel):
    """Arguments for calling OrbitHelper CLI."""

    args: List[str] = Field(description="Command line arguments for OrbitHelper")


# Tool schema registry
TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "browser_navigate": {
        "name": "browser_navigate",
        "description": "Navigate to a URL using the persistent browser context",
        "parameters": BrowserNavigateArgs.model_json_schema(),
    },
    "browser_click": {
        "name": "browser_click",
        "description": "Click an element on the current page by CSS selector",
        "parameters": BrowserClickArgs.model_json_schema(),
    },
    "browser_type": {
        "name": "browser_type",
        "description": "Type text into an input element by CSS selector",
        "parameters": BrowserTypeArgs.model_json_schema(),
    },
    "browser_get_text": {
        "name": "browser_get_text",
        "description": "Get text content from an element by CSS selector",
        "parameters": BrowserGetTextArgs.model_json_schema(),
    },
    "browser_screenshot": {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current page",
        "parameters": BrowserScreenshotArgs.model_json_schema(),
    },
    "read_file": {
        "name": "read_file",
        "description": "Read text content from a file",
        "parameters": ReadFileArgs.model_json_schema(),
    },
    "write_file": {
        "name": "write_file",
        "description": "Write text content to a file",
        "parameters": WriteFileArgs.model_json_schema(),
    },
    "list_directory": {
        "name": "list_directory",
        "description": "List files and directories in a given path",
        "parameters": ListDirectoryArgs.model_json_schema(),
    },
    "make_directory": {
        "name": "make_directory",
        "description": "Create a directory",
        "parameters": MakeDirectoryArgs.model_json_schema(),
    },
    "move_file": {
        "name": "move_file",
        "description": "Move or rename a file/directory",
        "parameters": MoveFileArgs.model_json_schema(),
    },
    "delete_file": {
        "name": "delete_file",
        "description": "Delete a file or directory",
        "parameters": DeleteFileArgs.model_json_schema(),
    },
    "reveal_in_finder": {
        "name": "reveal_in_finder",
        "description": "Reveal a file or directory in macOS Finder",
        "parameters": RevealInFinderArgs.model_json_schema(),
    },
    "create_calendar_event": {
        "name": "create_calendar_event",
        "description": "Create a new calendar event using AppleScript",
        "parameters": CreateCalendarEventArgs.model_json_schema(),
    },
    "list_calendar_events": {
        "name": "list_calendar_events",
        "description": "List upcoming calendar events",
        "parameters": ListCalendarEventsArgs.model_json_schema(),
    },
    "delete_calendar_event": {
        "name": "delete_calendar_event",
        "description": "Delete a calendar event by ID",
        "parameters": DeleteCalendarEventArgs.model_json_schema(),
    },
    "spotify_play": {
        "name": "spotify_play",
        "description": "Play/resume Spotify playback",
        "parameters": SpotifyPlayArgs.model_json_schema(),
    },
    "spotify_pause": {
        "name": "spotify_pause",
        "description": "Pause Spotify playback",
        "parameters": SpotifyPauseArgs.model_json_schema(),
    },
    "spotify_next_track": {
        "name": "spotify_next_track",
        "description": "Skip to the next track on Spotify",
        "parameters": SpotifyNextTrackArgs.model_json_schema(),
    },
    "spotify_previous_track": {
        "name": "spotify_previous_track",
        "description": "Go to the previous track on Spotify",
        "parameters": SpotifyPreviousTrackArgs.model_json_schema(),
    },
    "spotify_get_current_track": {
        "name": "spotify_get_current_track",
        "description": "Get information about the currently playing track",
        "parameters": SpotifyGetCurrentTrackArgs.model_json_schema(),
    },
    "spotify_search_and_play": {
        "name": "spotify_search_and_play",
        "description": "Search for and play a track on Spotify",
        "parameters": SpotifySearchAndPlayArgs.model_json_schema(),
    },
    "spotify_set_volume": {
        "name": "spotify_set_volume",
        "description": "Set Spotify volume (0-100)",
        "parameters": SpotifySetVolumeArgs.model_json_schema(),
    },
    "create_files": {
        "name": "create_files",
        "description": "Create multiple files with specified parameters",
        "parameters": CreateFilesArgs.model_json_schema(),
    },
    "open_app": {
        "name": "open_app",
        "description": "Open a macOS application by name",
        "parameters": OpenAppArgs.model_json_schema(),
    },
    "helper": {
        "name": "helper",
        "description": "Call the OrbitHelper CLI with given arguments",
        "parameters": HelperArgs.model_json_schema(),
    },
}


def get_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """Get the JSON schema for a specific tool."""
    return TOOL_SCHEMAS.get(tool_name)


def get_all_tool_schemas() -> Dict[str, Dict[str, Any]]:
    """Get all tool schemas for LLM function calling."""
    return TOOL_SCHEMAS


def export_schemas_to_json(output_path: str) -> None:
    """Export all tool schemas to a JSON file."""
    with open(output_path, "w") as f:
        json.dump(TOOL_SCHEMAS, f, indent=2)


def get_openai_function_definitions() -> List[Dict[str, Any]]:
    """Get tool schemas formatted for OpenAI function calling."""
    functions = []
    for tool_name, schema in TOOL_SCHEMAS.items():
        functions.append(
            {
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["parameters"],
                },
            }
        )
    return functions


def get_anthropic_tool_definitions() -> List[Dict[str, Any]]:
    """Get tool schemas formatted for Anthropic Claude function calling."""
    tools = []
    for tool_name, schema in TOOL_SCHEMAS.items():
        tools.append(
            {
                "name": schema["name"],
                "description": schema["description"],
                "input_schema": schema["parameters"],
            }
        )
    return tools


# Validation functions
def validate_tool_args(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate tool arguments against their schema."""
    schema = get_tool_schema(tool_name)
    if not schema:
        raise ValueError(f"Unknown tool: {tool_name}")

    # Get the appropriate Pydantic model class
    model_classes = {
        "browser_navigate": BrowserNavigateArgs,
        "browser_click": BrowserClickArgs,
        "browser_type": BrowserTypeArgs,
        "browser_get_text": BrowserGetTextArgs,
        "browser_screenshot": BrowserScreenshotArgs,
        "read_file": ReadFileArgs,
        "write_file": WriteFileArgs,
        "list_directory": ListDirectoryArgs,
        "make_directory": MakeDirectoryArgs,
        "move_file": MoveFileArgs,
        "delete_file": DeleteFileArgs,
        "reveal_in_finder": RevealInFinderArgs,
        "create_calendar_event": CreateCalendarEventArgs,
        "list_calendar_events": ListCalendarEventsArgs,
        "delete_calendar_event": DeleteCalendarEventArgs,
        "spotify_play": SpotifyPlayArgs,
        "spotify_pause": SpotifyPauseArgs,
        "spotify_next_track": SpotifyNextTrackArgs,
        "spotify_previous_track": SpotifyPreviousTrackArgs,
        "spotify_get_current_track": SpotifyGetCurrentTrackArgs,
        "spotify_search_and_play": SpotifySearchAndPlayArgs,
        "spotify_set_volume": SpotifySetVolumeArgs,
        "create_files": CreateFilesArgs,
        "open_app": OpenAppArgs,
        "helper": HelperArgs,
    }

    model_class = model_classes.get(tool_name)
    if not model_class:
        raise ValueError(f"No validation model for tool: {tool_name}")

    # Validate and return cleaned args
    validated = model_class(**args)
    return validated.model_dump()
