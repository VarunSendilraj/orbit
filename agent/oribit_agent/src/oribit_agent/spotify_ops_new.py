"""Spotify integration using AppleScript for macOS Spotify app."""

import subprocess
import time
from typing import Dict, Any


def spotify_play() -> Dict[str, Any]:
    """
    Play/resume Spotify playback.

    Returns:
        Dict with success status
    """
    try:
        # Try to launch Spotify if not running
        launch_script = """
        tell application "System Events"
            set isRunning to exists (processes where name is "Spotify")
        end tell
        if isRunning is false then
            tell application "Spotify" to activate
            delay 1
        end if
        return "ok"
        """
        try:
            subprocess.run(
                ["osascript", "-e", launch_script], capture_output=True, text=True, check=True
            )
        except Exception:
            pass

        script = """
        tell application "Spotify"
            if it is running then
                play
                return "playing"
            else
                return "not running"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        if output == "not running":
            return {
                "success": False,
                "error": "Spotify is not running. Please open Spotify first.",
                "action": "play",
            }

        return {"success": True, "action": "play", "status": "playing"}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"AppleScript failed: {e.stderr}", "action": "play"}
    except Exception as e:
        return {"success": False, "error": str(e), "action": "play"}


def spotify_pause() -> Dict[str, Any]:
    """
    Pause Spotify playback.

    Returns:
        Dict with success status
    """
    try:
        script = """
        tell application "Spotify"
            if it is running then
                pause
                return "paused"
            else
                return "not running"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        if output == "not running":
            return {"success": False, "error": "Spotify is not running", "action": "pause"}

        return {"success": True, "action": "pause", "status": "paused"}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"AppleScript failed: {e.stderr}", "action": "pause"}
    except Exception as e:
        return {"success": False, "error": str(e), "action": "pause"}


def spotify_next_track() -> Dict[str, Any]:
    """
    Skip to the next track.

    Returns:
        Dict with success status and track info
    """
    try:
        script = """
        tell application "Spotify"
            if it is running then
                next track
                delay 0.5
                set trackInfo to (name of current track) & " by " & (artist of current track)
                return trackInfo
            else
                return "not running"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        if output == "not running":
            return {"success": False, "error": "Spotify is not running", "action": "next"}

        return {"success": True, "action": "next", "track_info": output}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"AppleScript failed: {e.stderr}", "action": "next"}
    except Exception as e:
        return {"success": False, "error": str(e), "action": "next"}


def spotify_previous_track() -> Dict[str, Any]:
    """
    Go to the previous track.

    Returns:
        Dict with success status and track info
    """
    try:
        script = """
        tell application "Spotify"
            if it is running then
                previous track
                delay 0.5
                set trackInfo to (name of current track) & " by " & (artist of current track)
                return trackInfo
            else
                return "not running"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        if output == "not running":
            return {"success": False, "error": "Spotify is not running", "action": "previous"}

        return {"success": True, "action": "previous", "track_info": output}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"AppleScript failed: {e.stderr}", "action": "previous"}
    except Exception as e:
        return {"success": False, "error": str(e), "action": "previous"}


def spotify_get_current_track() -> Dict[str, Any]:
    """
    Get information about the currently playing track.

    Returns:
        Dict with success status and track details
    """
    try:
        script = """
        tell application "Spotify"
            if it is running then
                if player state is playing or player state is paused then
                    set trackName to name of current track
                    set trackArtist to artist of current track
                    set trackAlbum to album of current track
                    set trackDuration to duration of current track
                    set playerPosition to player position
                    set playerState to player state as string
                    
                    return trackName & "||" & trackArtist & "||" & trackAlbum & "||" & trackDuration & "||" & playerPosition & "||" & playerState
                else
                    return "no track"
                end if
            else
                return "not running"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        if output == "not running":
            return {"success": False, "error": "Spotify is not running", "action": "get_current"}

        if output == "no track":
            return {"success": True, "action": "get_current", "playing": False, "track": None}

        # Parse track info
        parts = output.split("||")
        if len(parts) >= 6:
            return {
                "success": True,
                "action": "get_current",
                "playing": True,
                "track": {
                    "name": parts[0],
                    "artist": parts[1],
                    "album": parts[2],
                    "duration": float(parts[3]) if parts[3].replace(".", "").isdigit() else 0,
                    "position": float(parts[4]) if parts[4].replace(".", "").isdigit() else 0,
                    "state": parts[5],
                },
            }

        return {
            "success": True,
            "action": "get_current",
            "playing": True,
            "track": {"info": output},
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"AppleScript failed: {e.stderr}",
            "action": "get_current",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "action": "get_current"}


def spotify_search_and_play(query: str) -> Dict[str, Any]:
    """
    Search for and play a track or playlist on Spotify using Cmd+K search.
    This approach is more reliable than URI navigation.
    """
    try:
        # Ensure Spotify is running and frontmost
        subprocess.run(
            ["osascript", "-e", 'tell application "Spotify" to activate'],
            capture_output=True,
            text=True,
        )

        time.sleep(0.5)

        # Use Cmd+K to open search, type query, then Enter to play first result
        search_script = f"""
        tell application "System Events"
            tell process "Spotify"
                set frontmost to true
                delay 0.8
                
                -- Open search with Cmd+K
                key code 40 using command down -- Cmd+K
                delay 0.8
                
                -- Clear any existing search and type new query
                key code 0 using command down -- Cmd+A to select all
                delay 0.1
                keystroke "{query}"
                delay 1.5
                
                -- Press Enter to play the first result
                key code 36 -- Return
                delay 0.3
                
                return "search_enter_completed"
            end tell
        end tell
        """

        ui_result = subprocess.run(
            ["osascript", "-e", search_script],
            capture_output=True,
            text=True,
        )

        # Wait for Spotify to process the search and start playback
        time.sleep(2.0)

        # Check what's actually playing now and log detailed info
        state = spotify_get_current_track()
        current_track_info = "Nothing playing"
        if state.get("success") and state.get("track"):
            track = state.get("track", {})
            current_track_info = (
                f"{track.get('name', 'Unknown')} by {track.get('artist', 'Unknown')}"
            )

        # Enhanced matching logic
        def query_matches_track(q: str, track_info: Dict[str, Any]) -> bool:
            if not track_info:
                return False

            q_lower = q.lower()
            name_lower = str(track_info.get("name", "")).lower()
            artist_lower = str(track_info.get("artist", "")).lower()

            # Direct substring match first
            if q_lower in name_lower or q_lower in artist_lower:
                return True

            # Token-based matching
            query_tokens = [
                t.strip() for t in q_lower.replace("-", " ").split() if len(t.strip()) >= 2
            ]
            if not query_tokens:
                return False

            matched_tokens = 0
            for token in query_tokens:
                if token in name_lower or token in artist_lower:
                    matched_tokens += 1

            # Consider it a match if at least half the tokens match
            return matched_tokens >= len(query_tokens) / 2

        # Always return detailed logging info
        debug_info = {
            "query": query,
            "current_track": current_track_info,
            "ui_action": ui_result.stdout.strip() if ui_result.stdout else "unknown",
            "spotify_state": state,
        }

        if state.get("success") and state.get("playing"):
            track = state.get("track", {})

            if query_matches_track(query, track):
                return {
                    "success": True,
                    "action": "search_and_play",
                    "query": query,
                    "status": f"✓ Playing searched item: {current_track_info}",
                    "debug": debug_info,
                }
            else:
                return {
                    "success": False,
                    "action": "search_and_play",
                    "query": query,
                    "status": f"✗ Playing wrong item. Searched: '{query}', Playing: {current_track_info}",
                    "debug": debug_info,
                }
        else:
            return {
                "success": False,
                "action": "search",
                "query": query,
                "status": f"Search completed but no playback started. Current: {current_track_info}",
                "debug": debug_info,
            }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"AppleScript failed: {e.stderr}",
            "action": "search",
            "query": query,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "action": "search",
            "query": query,
        }


def spotify_set_volume(volume: int) -> Dict[str, Any]:
    """
    Set Spotify volume (0-100).

    Args:
        volume: Volume level (0-100)

    Returns:
        Dict with success status
    """
    try:
        # Clamp volume to valid range
        volume = max(0, min(100, volume))

        script = f"""
        tell application "Spotify"
            if it is running then
                set sound volume to {volume}
                return "volume set"
            else
                return "not running"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        if output == "not running":
            return {
                "success": False,
                "error": "Spotify is not running",
                "action": "set_volume",
                "volume": volume,
            }

        return {"success": True, "action": "set_volume", "volume": volume}

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"AppleScript failed: {e.stderr}",
            "action": "set_volume",
            "volume": volume,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "action": "set_volume", "volume": volume}
