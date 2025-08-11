from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional

from .audit_logger import get_audit_logger
from .hybrid_planner import analyze_command_complexity, smart_plan
from .planner import plan
from .steps import new_run_id
from .tools import (
    browser_click,
    browser_get_text,
    browser_navigate,
    browser_screenshot,
    browser_type,
    create_calendar_event,
    create_files,
    delete_calendar_event,
    delete_file,
    list_calendar_events,
    list_directory,
    make_directory,
    move_file,
    open_app,
    read_file,
    reveal_in_finder,
    spotify_get_current_track,
    spotify_next_track,
    spotify_pause,
    spotify_play,
    spotify_previous_track,
    spotify_search_and_play,
    spotify_set_volume,
    write_file,
)


EmitFn = Callable[[str, int, str, str, Optional[Dict[str, Any]]], Awaitable[None]]


async def default_emit(
    run_id: str, step_id: int, status: str, message: str, data: Optional[Dict[str, Any]] = None
) -> None:
    prefix = f"[{status.upper():>7}]"
    print(prefix, message)


async def execute_command(
    command: str,
    dry_run: bool = False,
    emit: Optional[EmitFn] = None,
) -> Dict[str, Any]:
    """Plan and execute a natural language command using the same logic as the HTTP server.

    Parameters
    - command: The natural language instruction
    - dry_run: If True, only plans the steps and returns them without executing
    - emit: Async callback to stream step events (run_id, step_id, status, message, data)
    """
    if emit is None:
        emit = default_emit

    run_id = new_run_id()
    audit_logger = get_audit_logger()
    start_time = asyncio.get_event_loop().time()

    # Log command start
    audit_logger.log_command_start(
        run_id=run_id,
        user_command=command,
        metadata={"dry_run": dry_run, "client": "cli"},
    )

    # Analyze and announce planning strategy
    analysis = analyze_command_complexity(command)
    await emit(
        run_id,
        0,
        "queued",
        f"Planning strategy: {analysis['suggested_strategy']}",
        {"analysis": analysis},
    )

    # Compute steps
    try:
        steps = await smart_plan(command)
        if not steps:
            await emit(run_id, 0, "running", "Smart planning failed, trying deterministic fallback")
            steps = plan(command)
    except Exception as e:  # noqa: BLE001
        audit_logger.log_error(run_id, f"Smart planning failed: {e}")
        await emit(run_id, 0, "running", f"Planning error ({e}), using deterministic fallback")
        steps = plan(command)

    if not steps:
        error_msg = "Could not parse command into any actions"
        audit_logger.log_command_complete(
            run_id=run_id,
            status="error",
            message=error_msg,
            total_steps=0,
            duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
        )
        await emit(run_id, 1, "error", error_msg)
        return {"run_id": run_id, "error": error_msg}

    # Queue all steps first
    for i, step in enumerate(steps, start=1):
        await emit(run_id, i, "queued", f"Plan: {step['tool']} {step['args']}")

    if dry_run:
        audit_logger.log_command_complete(
            run_id=run_id,
            status="dry_run_complete",
            message=f"Dry run completed with {len(steps)} planned steps",
            total_steps=len(steps),
            duration_ms=(asyncio.get_event_loop().time() - start_time) * 1000,
        )
        return {"run_id": run_id, "planned": steps}

    # Execute steps sequentially
    successful_steps = 0
    for i, step in enumerate(steps, start=1):
        step_start_time = asyncio.get_event_loop().time()

        audit_logger.log_step_start(
            run_id=run_id, step_id=i, tool_name=step["tool"], tool_args=step["args"]
        )
        await emit(run_id, i, "running", f"Executing {step['tool']}")

        try:
            if step["tool"] == "create_files":
                created = create_files(**step["args"])
                await emit(run_id, i, "ok", f"Created {len(created)} file(s)", {"paths": created})

            elif step["tool"] == "open_app":
                open_app(**step["args"])
                await emit(run_id, i, "ok", f"Opened {step['args']['name']}")

            elif step["tool"] == "browser_navigate":
                result = await browser_navigate(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Navigated to {result['url']}"
                        if result["success"]
                        else f"Navigation failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "browser_click":
                result = await browser_click(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Clicked {result['selector']}"
                        if result["success"]
                        else f"Click failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "browser_type":
                result = await browser_type(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Typed into {result['selector']}"
                        if result["success"]
                        else f"Type failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "browser_get_text":
                result = await browser_get_text(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Got text: {result['text'][:50]}..."
                        if result["success"]
                        else f"Get text failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "browser_screenshot":
                result = await browser_screenshot(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Screenshot saved to {result['path']}"
                        if result["success"]
                        else f"Screenshot failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "read_file":
                result = read_file(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Read file: {len(result['content'])} chars"
                        if result["success"]
                        else f"Read failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "write_file":
                result = write_file(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Wrote to {result['path']}"
                        if result["success"]
                        else f"Write failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "list_directory":
                result = list_directory(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Found {result['count']} entries"
                        if result["success"]
                        else f"List failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "make_directory":
                result = make_directory(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Created directory {result['path']}"
                        if result["success"]
                        else f"Mkdir failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "move_file":
                result = move_file(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Moved to {result['destination']}"
                        if result["success"]
                        else f"Move failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "delete_file":
                result = delete_file(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Deleted {result['path']}"
                        if result["success"]
                        else f"Delete failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "reveal_in_finder":
                result = reveal_in_finder(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Revealed {result['path']}"
                        if result["success"]
                        else f"Reveal failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "create_calendar_event":
                result = create_calendar_event(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Created event: {result['title']}"
                        if result["success"]
                        else f"Event creation failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "list_calendar_events":
                result = list_calendar_events(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Found {result['count']} events"
                        if result["success"]
                        else f"List events failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "delete_calendar_event":
                result = delete_calendar_event(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Deleted event {result['event_id']}"
                        if result["success"]
                        else f"Delete event failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "spotify_play":
                result = spotify_play(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result.get("success") else "error",
                    result.get("status")
                    or (
                        "Started playing"
                        if result.get("success")
                        else f"Play failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "spotify_pause":
                result = spotify_pause(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result.get("success") else "error",
                    result.get("status")
                    or (
                        "Paused playback"
                        if result.get("success")
                        else f"Pause failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "spotify_next_track":
                result = spotify_next_track(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result.get("success") else "error",
                    (
                        f"Next: {result.get('track_info', 'Unknown')}"
                        if result.get("success")
                        else f"Next track failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "spotify_previous_track":
                result = spotify_previous_track(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result.get("success") else "error",
                    (
                        f"Previous: {result.get('track_info', 'Unknown')}"
                        if result.get("success")
                        else f"Previous track failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "spotify_get_current_track":
                result = spotify_get_current_track(**step["args"])
                if result.get("success"):
                    if result.get("playing") and result.get("track"):
                        track = result["track"]
                        await emit(
                            run_id,
                            i,
                            "ok",
                            f"Now playing: {track.get('name', 'Unknown')} by {track.get('artist', 'Unknown')}",
                            result,
                        )
                    else:
                        await emit(run_id, i, "ok", "No track playing", result)
                else:
                    await emit(
                        run_id,
                        i,
                        "error",
                        f"Get current track failed: {result.get('error')}",
                        result,
                    )

            elif step["tool"] == "spotify_search_and_play":
                result = spotify_search_and_play(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result.get("success") else "error",
                    result.get("status")
                    or (
                        f"Searched for: {result.get('query')}"
                        if result.get("success")
                        else f"Search failed: {result.get('error')}"
                    ),
                    result,
                )

            elif step["tool"] == "spotify_set_volume":
                result = spotify_set_volume(**step["args"])
                await emit(
                    run_id,
                    i,
                    "ok" if result["success"] else "error",
                    (
                        f"Set volume to {step['args'].get('volume')}"
                        if result["success"]
                        else f"Set volume failed: {result.get('error')}"
                    ),
                    result,
                )

            else:
                raise ValueError(f"Unknown tool: {step['tool']}")

            # Success logging
            step_duration = (asyncio.get_event_loop().time() - step_start_time) * 1000
            successful_steps += 1
            audit_logger.log_step_complete(
                run_id=run_id,
                step_id=i,
                tool_name=step["tool"],
                status="ok",
                message="Step completed successfully",
                duration_ms=step_duration,
            )

        except Exception as e:  # noqa: BLE001
            step_duration = (asyncio.get_event_loop().time() - step_start_time) * 1000
            error_msg = f"{step['tool']} failed: {e}"
            audit_logger.log_step_complete(
                run_id=run_id,
                step_id=i,
                tool_name=step["tool"],
                status="error",
                message=error_msg,
                duration_ms=step_duration,
            )
            audit_logger.log_error(
                run_id=run_id,
                step_id=i,
                tool_name=step["tool"],
                error_details=str(e),
            )
            await emit(run_id, i, "error", error_msg)
            break

        await asyncio.sleep(0.05)

    # Completion
    total_duration = (asyncio.get_event_loop().time() - start_time) * 1000
    command_status = "completed" if successful_steps == len(steps) else "partial_failure"
    audit_logger.log_command_complete(
        run_id=run_id,
        status=command_status,
        message=f"Command completed: {successful_steps}/{len(steps)} steps successful",
        total_steps=len(steps),
        duration_ms=total_duration,
        metadata={
            "successful_steps": successful_steps,
            "failed_steps": len(steps) - successful_steps,
        },
    )

    return {"run_id": run_id, "steps": len(steps), "status": command_status}
