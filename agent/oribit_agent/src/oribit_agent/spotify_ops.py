"""Spotify integration using AppleScript for macOS Spotify app."""

import os
import subprocess
import time
from typing import Dict, Any

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials

    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False


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
    Search for and play a track or playlist on Spotify.
    Uses Web API if available, falls back to UI automation.
    """
    try:
        # Method 1: Try Spotify Web API for precise search + URI playback
        if (
            SPOTIPY_AVAILABLE
            and os.environ.get("SPOTIFY_CLIENT_ID")
            and os.environ.get("SPOTIFY_CLIENT_SECRET")
        ):
            try:
                client_credentials_manager = SpotifyClientCredentials(
                    client_id=os.environ["SPOTIFY_CLIENT_ID"],
                    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
                )
                sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

                # Search for both tracks and playlists
                track_results = sp.search(q=query, type="track", limit=1)
                playlist_results = sp.search(q=query, type="playlist", limit=1)

                target_uri = None
                target_name = None
                target_type = None

                # Prefer exact playlist matches for playlist-like queries
                if any(word in query.lower() for word in ["playlist", "top hits", "mix", "radio"]):
                    if playlist_results["playlists"]["items"]:
                        playlist = playlist_results["playlists"]["items"][0]
                        target_uri = playlist["uri"]
                        target_name = playlist["name"]
                        target_type = "playlist"
                elif track_results["tracks"]["items"]:
                    track = track_results["tracks"]["items"][0]
                    target_uri = track["uri"]
                    target_name = f"{track['name']} by {track['artists'][0]['name']}"
                    target_type = "track"

                if target_uri:
                    # Open the specific URI in Spotify
                    subprocess.run(
                        [
                            "osascript",
                            "-e",
                            f'tell application "Spotify" to open location "{target_uri}"',
                        ],
                        capture_output=True,
                        text=True,
                    )

                    time.sleep(2.0)  # Wait longer for playlists

                    # Try to start playback
                    subprocess.run(
                        ["osascript", "-e", 'tell application "Spotify" to play'],
                        capture_output=True,
                        text=True,
                    )

                    time.sleep(1.0)

                    # Verify it's playing
                    state = spotify_get_current_track()
                    if state.get("success") and state.get("playing"):
                        current_track = state.get("track", {})
                        current_info = f"{current_track.get('name', 'Unknown')} by {current_track.get('artist', 'Unknown')}"
                        return {
                            "success": True,
                            "action": "search_and_play",
                            "query": query,
                            "status": f"✓ Playing via Web API ({target_type}): {current_info}",
                            "method": "web_api",
                            "target": target_name,
                        }
            except Exception:
                # Fall through to UI method
                pass

        # Method 2: Direct track URI approach
        # Try to find the exact track/playlist using known popular items
        known_items = {
            # Popular Tracks
            "bohemian rhapsody": "spotify:track:1AhDOtG9vPSOmsWgNW0BEY",
            "bohemian rhapsody queen": "spotify:track:1AhDOtG9vPSOmsWgNW0BEY",
            "bohemian rhapsody by queen": "spotify:track:1AhDOtG9vPSOmsWgNW0BEY",
            "imagine": "spotify:track:7pKfPomDEeI4TPT6EOYjn9",
            "imagine john lennon": "spotify:track:7pKfPomDEeI4TPT6EOYjn9",
            "imagine by john lennon": "spotify:track:7pKfPomDEeI4TPT6EOYjn9",
            "hey jude": "spotify:track:0aym2LBJBk9DAYuHHutrIl",
            "hey jude beatles": "spotify:track:0aym2LBJBk9DAYuHHutrIl",
            "hey jude by beatles": "spotify:track:0aym2LBJBk9DAYuHHutrIl",
            "let it be": "spotify:track:7iN1s7xHE4ifF5povM6A48",
            "let it be beatles": "spotify:track:7iN1s7xHE4ifF5povM6A48",
            "stairway to heaven": "spotify:track:5CQ30WqJwcep0pYcV4AMNc",
            "stairway to heaven led zeppelin": "spotify:track:5CQ30WqJwcep0pYcV4AMNc",
            "wish you were here": "spotify:track:6mFkJmJqdDVQ1REhVfGgd1",
            "wish you were here pink floyd": "spotify:track:6mFkJmJqdDVQ1REhVfGgd1",
            # Popular Playlists (these change, but some are relatively stable)
            "today's top hits": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
            "todays top hits": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
            "top hits": "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M",
            "rap caviar": "spotify:playlist:37i9dQZF1DX0XUsuxWHRQd",
            "rapcaviar": "spotify:playlist:37i9dQZF1DX0XUsuxWHRQd",
            "rock classics": "spotify:playlist:37i9dQZF1DWXRqgorJj26U",
            "chill hits": "spotify:playlist:37i9dQZF1DX4WYpdgoIcn6",
            "pop rising": "spotify:playlist:37i9dQZF1DWUa8ZRTfalHk",
        }

        query_lower = query.lower().strip()
        direct_uri = known_items.get(query_lower)

        if direct_uri:
            # Try to play the specific track/playlist directly
            item_type = "playlist" if "playlist" in direct_uri else "track"
            wait_time = 2.5 if item_type == "playlist" else 1.5

            play_direct_script = f"""
            tell application "Spotify"
                activate
                delay 0.5
                pause
                delay 0.3
                open location "{direct_uri}"
                delay {wait_time}
                play
                delay 0.5
                play  -- Sometimes need to call play twice
                return "played_direct_uri_{item_type}"
            end tell
            """

            ui_result = subprocess.run(
                ["osascript", "-e", play_direct_script],
                capture_output=True,
                text=True,
            )
        else:
            # Fallback: enhanced search with better targeting
            search_script = f"""
            tell application "Spotify"
                activate
                delay 0.8
                pause
                delay 0.3
            end tell
            
            tell application "System Events"
                tell process "Spotify"
                    set frontmost to true
                    delay 0.8
                    
                    -- Open search
                    key code 40 using command down -- Cmd+K
                    delay 1.0
                    
                    -- Clear and search
                    key code 0 using command down -- Cmd+A
                    delay 0.1
                    keystroke "{query}"
                    delay 3.5  -- Wait even longer for results
                    
                    -- Try multiple strategies to play first result
                    try
                        -- Strategy 1: Tab to results, then Enter
                        key code 48 -- Tab to move to results
                        delay 0.5
                        key code 36 -- Enter to play first
                        delay 0.8
                        return "tab_enter_strategy"
                    on error
                        try
                            -- Strategy 2: Down arrow then Enter
                            key code 125 -- Down arrow
                            delay 0.3
                            key code 36 -- Enter
                            delay 0.5
                            return "down_enter_strategy"
                        on error
                            -- Strategy 3: Double Enter
                            key code 36 -- Enter
                            delay 0.3
                            key code 36 -- Enter again
                            return "double_enter_strategy"
                        end try
                    end try
                end tell
            end tell
            """

            ui_result = subprocess.run(
                ["osascript", "-e", search_script],
                capture_output=True,
                text=True,
            )

        # Wait for Spotify to process and start playback
        time.sleep(3.0)

        # Check what's actually playing now and log detailed info
        state = spotify_get_current_track()
        current_track_info = "Nothing playing"
        if state.get("success") and state.get("track"):
            track = state.get("track", {})
            current_track_info = (
                f"{track.get('name', 'Unknown')} by {track.get('artist', 'Unknown')}"
            )

        # Enhanced matching logic for tracks and playlists
        def query_matches_result(
            q: str, track_info: Dict[str, Any], used_direct_uri: bool = False
        ) -> bool:
            if not track_info:
                return False

            q_lower = q.lower()
            name_lower = str(track_info.get("name", "")).lower()
            artist_lower = str(track_info.get("artist", "")).lower()

            # If we used a direct URI, we should trust that it worked
            # Check if this looks like a playlist query
            if used_direct_uri and any(
                word in q_lower
                for word in [
                    "playlist",
                    "top hits",
                    "mix",
                    "radio",
                    "caviar",
                    "classics",
                    "chill",
                    "rising",
                ]
            ):
                return True  # Assume playlist loaded correctly

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
            "ui_stderr": ui_result.stderr.strip() if ui_result.stderr else "no_errors",
            "spotify_state": state,
        }

        # Print debug info for immediate visibility
        print("🎵 SPOTIFY DEBUG:")
        print(f"   Query: {query}")
        print(f"   UI Action: {debug_info['ui_action']}")
        print(f"   UI Errors: {debug_info['ui_stderr']}")
        print(f"   Currently Playing: {current_track_info}")
        print(
            f"   Playback State: {state.get('track', {}).get('state', 'unknown') if state.get('track') else 'no_track'}"
        )

        # Determine if we used direct URI
        used_direct_uri = "played_direct_uri" in debug_info.get("ui_action", "")

        if state.get("success") and state.get("playing"):
            track = state.get("track", {})

            if query_matches_result(query, track, used_direct_uri):
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
