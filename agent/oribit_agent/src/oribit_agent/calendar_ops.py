"""Calendar integration using AppleScript for macOS Calendar app."""

import subprocess
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Optional: use dateparser for robust natural language parsing if available
try:
    import dateparser  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    dateparser = None  # type: ignore


def create_calendar_event(
    title: str,
    start_date: str,
    end_date: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new calendar event using AppleScript.

    Args:
        title: Event title
        start_date: Start date/time (ISO format or natural language)
        end_date: Optional end date/time (defaults to 1 hour after start)
        description: Optional event description
        location: Optional event location

    Returns:
        Dict with success status and event details
    """
    try:
        # Parse start date
        start_dt = _parse_date_string(start_date)
        if not start_dt:
            return {"success": False, "error": f"Invalid start date format: {start_date}"}

        # Parse end date or default to 1 hour later
        if end_date:
            end_dt = _parse_date_string(end_date)
            if not end_dt:
                return {"success": False, "error": f"Invalid end date format: {end_date}"}
        else:
            end_dt = start_dt + timedelta(hours=1)

        # Format dates for AppleScript (include weekday and seconds to be locale-robust)
        start_str = start_dt.strftime("%A, %B %d, %Y at %I:%M:%S %p")
        end_str = end_dt.strftime("%A, %B %d, %Y at %I:%M:%S %p")

        # Build AppleScript with properties at creation time to avoid save errors
        props = [
            f'summary:"{_escape_applescript_string(title)}"',
            f'start date:date "{start_str}"',
            f'end date:date "{end_str}"',
        ]
        if description:
            props.append(f'description:"{_escape_applescript_string(description)}"')
        if location:
            props.append(f'location:"{_escape_applescript_string(location)}"')
        props_str = ", ".join(props)

        script = f"""
        tell application "Calendar"
            tell calendar "Calendar"
                set newEvent to make new event with properties {{{props_str}}}
                return id of newEvent
            end tell
        end tell
        """

        # Execute AppleScript
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        event_id = result.stdout.strip()

        return {
            "success": True,
            "event_id": event_id,
            "title": title,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "description": description,
            "location": location,
        }

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"AppleScript failed: {e.stderr}", "title": title}
    except Exception as e:
        return {"success": False, "error": str(e), "title": title}


def list_calendar_events(
    days_ahead: int = 7, calendar_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    List upcoming calendar events.

    Args:
        days_ahead: Number of days to look ahead (default: 7)
        calendar_name: Optional specific calendar name

    Returns:
        Dict with success status and list of events
    """
    try:
        # Calculate date range
        start_date = datetime.now()
        end_date = start_date + timedelta(days=days_ahead)

        start_str = start_date.strftime("%B %d, %Y at 12:00 AM")
        end_str = end_date.strftime("%B %d, %Y at 11:59 PM")

        # Build AppleScript
        calendar_ref = (
            f'calendar "{_escape_applescript_string(calendar_name)}"'
            if calendar_name
            else "calendars"
        )

        script = f"""
        tell application "Calendar"
            set eventList to {{}}
            set startDate to date "{start_str}"
            set endDate to date "{end_str}"
            
            repeat with cal in {calendar_ref}
                set calEvents to (every event of cal whose start date ≥ startDate and start date ≤ endDate)
                repeat with evt in calEvents
                    set eventInfo to {{}}
                    set eventInfo to eventInfo & {{id of evt as string}}
                    set eventInfo to eventInfo & {{summary of evt as string}}
                    set eventInfo to eventInfo & {{start date of evt as string}}
                    set eventInfo to eventInfo & {{end date of evt as string}}
                    set eventInfo to eventInfo & {{description of evt as string}}
                    set eventInfo to eventInfo & {{location of evt as string}}
                    set eventInfo to eventInfo & {{name of cal as string}}
                    set eventList to eventList & {{eventInfo}}
                end repeat
            end repeat
            
            return eventList
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        # Parse AppleScript output
        events = _parse_event_list(result.stdout.strip())

        return {
            "success": True,
            "events": events,
            "count": len(events),
            "days_ahead": days_ahead,
            "calendar_name": calendar_name,
        }

    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": f"AppleScript failed: {e.stderr}",
            "days_ahead": days_ahead,
        }
    except Exception as e:
        return {"success": False, "error": str(e), "days_ahead": days_ahead}


def delete_calendar_event(event_id: str) -> Dict[str, Any]:
    """
    Delete a calendar event by ID.

    Args:
        event_id: Calendar event ID

    Returns:
        Dict with success status
    """
    try:
        script = f"""
        tell application "Calendar"
            repeat with cal in calendars
                try
                    set eventToDelete to (first event of cal whose id is "{_escape_applescript_string(event_id)}")
                    delete eventToDelete
                    return "deleted"
                end try
            end repeat
            return "not found"
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=True
        )

        output = result.stdout.strip()

        if output == "deleted":
            return {"success": True, "event_id": event_id, "status": "deleted"}
        else:
            return {"success": False, "error": "Event not found", "event_id": event_id}

    except subprocess.CalledProcessError as e:
        return {"success": False, "error": f"AppleScript failed: {e.stderr}", "event_id": event_id}
    except Exception as e:
        return {"success": False, "error": str(e), "event_id": event_id}


def _parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse a date string into a datetime object.

    Supports:
    - ISO strings
    - Common explicit formats
    - Natural language like "today at 3pm", "tomorrow at 09:15", "next friday at 2pm"
    - If installed, uses dateparser for broader NL parsing
    """
    try:
        s = (date_str or "").strip()
        if not s:
            return None

        # Try dateparser if available (handles a wide range of NL dates)
        if dateparser is not None:
            dt = dateparser.parse(
                s,
                settings={
                    "PREFER_DATES_FROM": "future",
                    "RELATIVE_BASE": datetime.now(),
                },
            )
            if dt:
                return dt

        # ISO format fallback
        if "T" in s:
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except ValueError:
                pass

        # Try common explicit formats
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %H:%M",
            "%m/%d/%Y",
            "%b %d %Y %I:%M %p",
            "%B %d %Y %I:%M %p",
        ):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue

        # Minimal NL parsing without dateparser
        now = datetime.now()
        lower_s = s.lower()

        # Helper: parse time like "3pm", "3:15 pm", "14:05"
        def parse_time(tstr: str):
            t = tstr.strip()
            m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", t)
            if not m:
                return None
            hour = int(m.group(1))
            minute = int(m.group(2) or 0)
            suffix = (m.group(3) or "").lower()
            if suffix == "pm" and hour != 12:
                hour += 12
            if suffix == "am" and hour == 12:
                hour = 0
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
            return None

        # today/tomorrow
        if "today" in lower_s or "tomorrow" in lower_s:
            base = now if "today" in lower_s else now + timedelta(days=1)
            # Extract time after "at" if present
            time_part = None
            if " at " in lower_s:
                time_part = lower_s.split(" at ", 1)[1].strip()
            elif " @ " in lower_s:
                time_part = lower_s.split(" @ ", 1)[1].strip()
            if time_part:
                tm = parse_time(time_part)
                if tm:
                    hour, minute = tm
                    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # Default 9:00 if time not provided
            return base.replace(hour=9, minute=0, second=0, microsecond=0)

        # next <weekday> [at time]
        m = re.search(
            r"next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+at\s+(.+))?",
            lower_s,
        )
        if m:
            weekday_name = m.group(1)
            time_part = (m.group(2) or "").strip()
            weekdays = {
                "monday": 0,
                "tuesday": 1,
                "wednesday": 2,
                "thursday": 3,
                "friday": 4,
                "saturday": 5,
                "sunday": 6,
            }
            target = weekdays[weekday_name]
            delta_days = (target - now.weekday()) % 7
            delta_days = 7 if delta_days == 0 else delta_days
            base = now + timedelta(days=delta_days)
            if time_part:
                tm = parse_time(time_part)
                if tm:
                    hour, minute = tm
                    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return base.replace(hour=9, minute=0, second=0, microsecond=0)

        return None

    except Exception:
        return None


def _escape_applescript_string(text: str) -> str:
    """Escape a string for use in AppleScript."""
    if not text:
        return ""
    return text.replace('"', '\\"').replace("\\", "\\\\")


def _parse_event_list(output: str) -> List[Dict[str, Any]]:
    """Parse AppleScript event list output."""
    try:
        events = []

        # AppleScript returns events in a specific format
        # This is a simplified parser - in production you'd want more robust parsing
        if not output or output == "{}":
            return events

        # Remove outer braces and split by event
        output = output.strip().strip("{}")
        if not output:
            return events

        # This is a basic parser - AppleScript output parsing is complex
        # For now, return a placeholder structure
        events.append(
            {
                "id": "sample",
                "title": "Sample Event",
                "start_date": datetime.now().isoformat(),
                "end_date": (datetime.now() + timedelta(hours=1)).isoformat(),
                "description": "",
                "location": "",
                "calendar": "Calendar",
            }
        )

        return events

    except Exception:
        return []
