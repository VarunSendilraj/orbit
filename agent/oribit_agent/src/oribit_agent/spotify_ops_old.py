"""Spotify integration using AppleScript for macOS Spotify app."""

import subprocess
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
    Search for and play a track or playlist on Spotify based on a natural-language query.
    More robustly attempts to start playback by simulating UI keystrokes if needed.
    """
    try:
        # Ensure Spotify is running and frontmost
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Spotify" to activate',
            ],
            capture_output=True,
            text=True,
        )

        # Open search
        search_url = f"spotify:search:{query.replace(' ', '%20')}"
        open_and_try_play = f"""
        tell application "Spotify"
            if it is running then
                open location "{search_url}"
                delay 2.0
                try
                    play
                    return "playing_after_search"
                on error errMsg
                    return "search_opened"
                end try
            else
                return "not running"
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", open_and_try_play],
            capture_output=True,
            text=True,
            check=True,
        )

        output = result.stdout.strip()
        if output == "not running":
            return {
                "success": False,
                "error": "Spotify is not running. Please open Spotify first.",
                "action": "search",
                "query": query,
            }

        if output == "playing_after_search":
            return {
                "success": True,
                "action": "search_and_play",
                "query": query,
                "status": "Playing top result",
            }

        # If not playing yet, try UI automation to explicitly play the first result
        # Try a different approach: double-click the first search result
        double_click_script = """
        tell application "System Events"
            tell process "Spotify"
                set frontmost to true
                delay 1.0
                try
                    -- Look for the first clickable result item
                    set theWin to window 1
                    set theRows to every row of every table of every scroll area of theWin
                    if (count of theRows) > 0 then
                        set firstRow to item 1 of theRows
                        -- Double-click to play the first result
                        click firstRow
                        delay 0.2
                        click firstRow
                        return "double_clicked_first_result"
                    end if
                end try
                
                -- Fallback: try clicking any visible play button
                try
                    set theWin to window 1
                    set allButtons to every button of theWin
                    repeat with btn in allButtons
                        if description of btn contains "Play" then
                            click btn
                            return "clicked_play_button"
                        end if
                    end repeat
                end try
                
                -- Last resort: space bar
                key code 49 -- space
                return "pressed_space"
            end tell
        end tell
        """

        ui_result = subprocess.run(
            ["osascript", "-e", double_click_script],
            capture_output=True,
            text=True,
        )

        # Wait for playback to start
        import time

        time.sleep(1.5)

        # Check what's actually playing now and log it
        state = spotify_get_current_track()
        current_track_info = "Nothing playing"
        if state.get("success") and state.get("track"):
            track = state.get("track", {})
            current_track_info = (
                f"{track.get('name', 'Unknown')} by {track.get('artist', 'Unknown')}"
            )

        # Check if what's playing matches our query
        def query_matches_track(q: str, track_name: str, artist_name: str) -> bool:
            q_lower = q.lower()
            name_lower = track_name.lower()
            artist_lower = artist_name.lower()

            # Split query into tokens and check if any are in the track/artist
            query_tokens = [
                t.strip() for t in q_lower.replace("-", " ").split() if len(t.strip()) >= 3
            ]

            for token in query_tokens:
                if token in name_lower or token in artist_lower:
                    return True
            return False

        if state.get("success") and state.get("playing"):
            track = state.get("track", {})
            track_name = track.get("name", "")
            artist_name = track.get("artist", "")

            if query_matches_track(query, track_name, artist_name):
                return {
                    "success": True,
                    "action": "search_and_play",
                    "query": query,
                    "status": f"✓ Playing searched item: {current_track_info}",
                    "ui_action": ui_result.stdout.strip() if ui_result.stdout else "unknown",
                }
            else:
                return {
                    "success": False,
                    "action": "search_and_play",
                    "query": query,
                    "status": f"✗ Playing wrong item. Searched: '{query}', Playing: {current_track_info}",
                    "ui_action": ui_result.stdout.strip() if ui_result.stdout else "unknown",
                }
        else:
            return {
                "success": False,
                "action": "search",
                "query": query,
                "status": f"Search opened but no playback started. Current: {current_track_info}",
                "ui_action": ui_result.stdout.strip() if ui_result.stdout else "unknown",
            }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"AppleScript failed: {e.stderr}",
            "action": "search",
            "query": query,
        }
    except Exception as e:  # noqa: BLE001
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
