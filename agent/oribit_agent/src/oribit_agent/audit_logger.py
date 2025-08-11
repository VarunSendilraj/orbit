"""
JSONL audit logging system for all Orbit Agent command executions.
Provides comprehensive tracking of user commands, tool executions, and outcomes.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import threading
import queue


@dataclass
class AuditEvent:
    """Represents a single audit event."""

    timestamp: str
    event_type: str  # command_start, step_start, step_complete, command_complete, error
    run_id: str
    step_id: Optional[int] = None
    user_command: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    status: Optional[str] = None  # queued, running, ok, error
    message: Optional[str] = None
    error_details: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogger:
    """Thread-safe JSONL audit logger with automatic log rotation."""

    def __init__(
        self,
        log_dir: str = "~/.orbit/logs",
        max_file_size_mb: int = 10,
        max_files: int = 10,
        enable_console: bool = False,
    ):
        """
        Initialize audit logger.

        Args:
            log_dir: Directory to store audit logs
            max_file_size_mb: Maximum size per log file before rotation
            max_files: Maximum number of log files to keep
            enable_console: Whether to also log to console
        """
        self.log_dir = Path(os.path.expanduser(log_dir))
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.max_files = max_files
        self.enable_console = enable_console

        # Current log file
        self.current_log_file = self.log_dir / "audit.jsonl"

        # Thread-safe logging queue
        self._queue: queue.Queue = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._shutdown = threading.Event()
        self._worker_thread.start()

        # Console logger
        if self.enable_console:
            self.console_logger = logging.getLogger("orbit.audit")
            self.console_logger.setLevel(logging.INFO)
            if not self.console_logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter("%(asctime)s - AUDIT - %(message)s")
                handler.setFormatter(formatter)
                self.console_logger.addHandler(handler)
        else:
            self.console_logger = None

    def _worker(self) -> None:
        """Background worker thread that handles actual file writing."""
        while not self._shutdown.is_set():
            try:
                # Get event from queue with timeout
                event = self._queue.get(timeout=1.0)
                if event is None:  # Shutdown signal
                    break

                self._write_event(event)
                self._queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                # Log to stderr if we can't write to file
                print(f"Audit logger error: {e}", file=__import__("sys").stderr)

    def _write_event(self, event: AuditEvent) -> None:
        """Write a single event to the log file."""
        try:
            # Check if log rotation is needed
            if (
                self.current_log_file.exists()
                and self.current_log_file.stat().st_size > self.max_file_size
            ):
                self._rotate_logs()

            # Write event as JSONL
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                json.dump(asdict(event), f, separators=(",", ":"))
                f.write("\n")

            # Also log to console if enabled
            if self.console_logger:
                self.console_logger.info(self._format_console_message(event))

        except Exception as e:
            print(f"Failed to write audit event: {e}", file=__import__("sys").stderr)

    def _format_console_message(self, event: AuditEvent) -> str:
        """Format event for console display."""
        if event.event_type == "command_start":
            return f"COMMAND START [{event.run_id}]: {event.user_command}"
        elif event.event_type == "step_start":
            return (
                f"STEP START [{event.run_id}.{event.step_id}]: {event.tool_name}({event.tool_args})"
            )
        elif event.event_type == "step_complete":
            return f"STEP {event.status.upper()} [{event.run_id}.{event.step_id}]: {event.message}"
        elif event.event_type == "command_complete":
            return f"COMMAND COMPLETE [{event.run_id}]: {event.message}"
        elif event.event_type == "error":
            return f"ERROR [{event.run_id}]: {event.error_details}"
        else:
            return f"{event.event_type.upper()} [{event.run_id}]: {event.message}"

    def _rotate_logs(self) -> None:
        """Rotate log files when they get too large."""
        try:
            # Move current log to timestamped version
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archived_file = self.log_dir / f"audit_{timestamp}.jsonl"

            if self.current_log_file.exists():
                self.current_log_file.rename(archived_file)

            # Clean up old log files
            self._cleanup_old_logs()

        except Exception as e:
            print(f"Log rotation failed: {e}", file=__import__("sys").stderr)

    def _cleanup_old_logs(self) -> None:
        """Remove old log files beyond the maximum count."""
        try:
            # Get all audit log files sorted by modification time
            log_files = []
            for file_path in self.log_dir.glob("audit_*.jsonl"):
                log_files.append((file_path.stat().st_mtime, file_path))

            log_files.sort(reverse=True)  # Newest first

            # Remove files beyond the limit
            for _, file_path in log_files[self.max_files :]:
                file_path.unlink()

        except Exception as e:
            print(f"Log cleanup failed: {e}", file=__import__("sys").stderr)

    def log_command_start(
        self, run_id: str, user_command: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log the start of a command execution."""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="command_start",
            run_id=run_id,
            user_command=user_command,
            metadata=metadata,
        )
        self._queue.put(event)

    def log_step_start(
        self,
        run_id: str,
        step_id: int,
        tool_name: str,
        tool_args: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log the start of a tool execution step."""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="step_start",
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            tool_args=tool_args,
            status="running",
            metadata=metadata,
        )
        self._queue.put(event)

    def log_step_complete(
        self,
        run_id: str,
        step_id: int,
        tool_name: str,
        status: str,
        message: str,
        result: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log the completion of a tool execution step."""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="step_complete",
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            status=status,
            message=message,
            result=result,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        self._queue.put(event)

    def log_command_complete(
        self,
        run_id: str,
        status: str,
        message: str,
        total_steps: int,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log the completion of a command execution."""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="command_complete",
            run_id=run_id,
            status=status,
            message=message,
            duration_ms=duration_ms,
            metadata={"total_steps": total_steps, **(metadata or {})},
        )
        self._queue.put(event)

    def log_error(
        self,
        run_id: str,
        error_details: str,
        step_id: Optional[int] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an error that occurred during execution."""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="error",
            run_id=run_id,
            step_id=step_id,
            tool_name=tool_name,
            status="error",
            error_details=error_details,
            metadata=metadata,
        )
        self._queue.put(event)

    def log_security_event(
        self,
        run_id: str,
        event_description: str,
        severity: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log security-related events (permission requests, etc.)."""
        event = AuditEvent(
            timestamp=datetime.now().isoformat(),
            event_type="security",
            run_id=run_id,
            message=event_description,
            metadata={"severity": severity, **(metadata or {})},
        )
        self._queue.put(event)

    def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        run_id: Optional[str] = None,
        event_type: Optional[str] = None,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.

        Returns:
            List of matching audit events as dictionaries
        """
        results = []

        # Get all log files to search
        log_files = [self.current_log_file]
        log_files.extend(self.log_dir.glob("audit_*.jsonl"))

        for log_file in log_files:
            if not log_file.exists():
                continue

            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            event_dict = json.loads(line.strip())

                            # Apply filters
                            if (
                                start_time
                                and datetime.fromisoformat(event_dict["timestamp"]) < start_time
                            ):
                                continue
                            if (
                                end_time
                                and datetime.fromisoformat(event_dict["timestamp"]) > end_time
                            ):
                                continue
                            if run_id and event_dict.get("run_id") != run_id:
                                continue
                            if event_type and event_dict.get("event_type") != event_type:
                                continue
                            if tool_name and event_dict.get("tool_name") != tool_name:
                                continue
                            if status and event_dict.get("status") != status:
                                continue

                            results.append(event_dict)

                            # Apply limit
                            if limit and len(results) >= limit:
                                return results

                        except json.JSONDecodeError:
                            continue  # Skip malformed lines

            except Exception:
                continue  # Skip files we can't read

        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x["timestamp"], reverse=True)

        if limit:
            results = results[:limit]

        return results

    def get_command_summary(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a specific command execution."""
        events = self.query_logs(run_id=run_id)

        if not events:
            return None

        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])

        summary = {
            "run_id": run_id,
            "command": None,
            "start_time": None,
            "end_time": None,
            "status": "unknown",
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "tools_used": [],
            "errors": [],
        }

        for event in events:
            if event["event_type"] == "command_start":
                summary["command"] = event.get("user_command")
                summary["start_time"] = event["timestamp"]
            elif event["event_type"] == "command_complete":
                summary["end_time"] = event["timestamp"]
                summary["status"] = event.get("status", "completed")
            elif event["event_type"] == "step_complete":
                summary["total_steps"] += 1
                if event.get("status") == "ok":
                    summary["successful_steps"] += 1
                else:
                    summary["failed_steps"] += 1

                tool_name = event.get("tool_name")
                if tool_name and tool_name not in summary["tools_used"]:
                    summary["tools_used"].append(tool_name)
            elif event["event_type"] == "error":
                summary["errors"].append(event.get("error_details", "Unknown error"))

        return summary

    def shutdown(self) -> None:
        """Gracefully shutdown the audit logger."""
        # Signal shutdown
        self._shutdown.set()
        self._queue.put(None)  # Wake up worker thread

        # Wait for worker thread to finish
        self._worker_thread.join(timeout=5.0)


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger()

    return _audit_logger


def configure_audit_logger(
    log_dir: str = "~/.orbit/logs",
    max_file_size_mb: int = 10,
    max_files: int = 10,
    enable_console: bool = False,
) -> None:
    """Configure the global audit logger."""
    global _audit_logger
    if _audit_logger:
        _audit_logger.shutdown()

    _audit_logger = AuditLogger(
        log_dir=log_dir,
        max_file_size_mb=max_file_size_mb,
        max_files=max_files,
        enable_console=enable_console,
    )
