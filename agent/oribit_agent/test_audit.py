#!/usr/bin/env python3
"""
Test audit logging functionality.
"""

import sys
import asyncio
import json
import tempfile
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oribit_agent.audit_logger import configure_audit_logger, get_audit_logger


async def test_audit_logging():
    """Test the audit logging system."""
    print("🔍 Testing Audit Logging System...")

    # Use temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configure logger with temp directory
        configure_audit_logger(
            log_dir=temp_dir, max_file_size_mb=1, max_files=3, enable_console=True
        )

        audit_logger = get_audit_logger()

        # Test 1: Command lifecycle logging
        run_id = "test_run_001"

        # Log command start
        audit_logger.log_command_start(
            run_id=run_id,
            user_command="create 3 files and open calculator",
            metadata={"test": True},
        )

        # Log steps
        audit_logger.log_step_start(
            run_id=run_id,
            step_id=1,
            tool_name="create_files",
            tool_args={"dir": "~/test", "count": 3, "prefix": "test", "ext": "txt"},
        )

        await asyncio.sleep(0.1)  # Simulate work

        audit_logger.log_step_complete(
            run_id=run_id,
            step_id=1,
            tool_name="create_files",
            status="ok",
            message="Created 3 files successfully",
            result={"paths": ["/tmp/test1.txt", "/tmp/test2.txt", "/tmp/test3.txt"]},
            duration_ms=150.5,
        )

        audit_logger.log_step_start(
            run_id=run_id, step_id=2, tool_name="open_app", tool_args={"name": "Calculator"}
        )

        audit_logger.log_step_complete(
            run_id=run_id,
            step_id=2,
            tool_name="open_app",
            status="ok",
            message="Opened Calculator",
            duration_ms=75.2,
        )

        audit_logger.log_command_complete(
            run_id=run_id,
            status="completed",
            message="All steps completed successfully",
            total_steps=2,
            duration_ms=250.8,
        )

        # Test 2: Error logging
        error_run_id = "test_run_002"

        audit_logger.log_command_start(run_id=error_run_id, user_command="navigate to invalid-url")

        audit_logger.log_step_start(
            run_id=error_run_id,
            step_id=1,
            tool_name="browser_navigate",
            tool_args={"url": "invalid-url"},
        )

        audit_logger.log_error(
            run_id=error_run_id,
            step_id=1,
            tool_name="browser_navigate",
            error_details="Invalid URL format",
        )

        audit_logger.log_step_complete(
            run_id=error_run_id,
            step_id=1,
            tool_name="browser_navigate",
            status="error",
            message="Navigation failed",
            duration_ms=10.5,
        )

        audit_logger.log_command_complete(
            run_id=error_run_id,
            status="error",
            message="Command failed due to invalid URL",
            total_steps=1,
            duration_ms=15.0,
        )

        # Test 3: Security logging
        audit_logger.log_security_event(
            run_id="security_test",
            event_description="User requested file deletion with recursive flag",
            severity="warning",
            metadata={"path": "/important/data", "recursive": True},
        )

        # Give background thread time to write
        await asyncio.sleep(0.2)

        # Test 4: Query logs
        print("   Testing log queries...")

        # Query all logs
        all_logs = audit_logger.query_logs()
        print(f"   ✅ Found {len(all_logs)} total log entries")

        # Query by run_id
        run_logs = audit_logger.query_logs(run_id=run_id)
        print(f"   ✅ Found {len(run_logs)} logs for run {run_id}")

        # Query by event type
        command_logs = audit_logger.query_logs(event_type="command_start")
        print(f"   ✅ Found {len(command_logs)} command start events")

        # Query by tool
        create_logs = audit_logger.query_logs(tool_name="create_files")
        print(f"   ✅ Found {len(create_logs)} create_files events")

        # Test 5: Command summary
        summary = audit_logger.get_command_summary(run_id)
        if summary:
            print(f"   ✅ Command summary: {summary['status']} with {summary['total_steps']} steps")
            print(f"      Tools used: {summary['tools_used']}")
        else:
            print("   ❌ Failed to get command summary")

        # Test 6: Verify log file exists
        log_file = Path(temp_dir) / "audit.jsonl"
        if log_file.exists():
            with open(log_file, "r") as f:
                lines = f.readlines()
                print(f"   ✅ Log file contains {len(lines)} JSONL entries")

                # Validate JSONL format
                try:
                    for line in lines[:3]:  # Check first 3 lines
                        json.loads(line.strip())
                    print("   ✅ JSONL format is valid")
                except json.JSONDecodeError as e:
                    print(f"   ❌ Invalid JSONL format: {e}")
        else:
            print("   ❌ Log file was not created")

        # Shutdown audit logger
        audit_logger.shutdown()

        print("🎉 Audit logging test completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_audit_logging())
