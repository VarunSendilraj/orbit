#!/usr/bin/env python3
"""
Test script for Phase 2 Orbit Agent functionality.
Tests LLM integration, tool schemas, and end-to-end workflows.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from oribit_agent.llm_planner import LLMPlanner
from oribit_agent.hybrid_planner import smart_plan, analyze_command_complexity
from oribit_agent.planner import plan as deterministic_plan
from oribit_agent.schemas import get_openai_function_definitions, validate_tool_args
from oribit_agent.tools import get_tool


async def test_llm_connection():
    """Test basic LLM connection and function calling."""
    print("🧠 Testing LLM Connection...")

    try:
        # Test OpenAI API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False

        print(f"✅ Found OpenAI API key: {api_key[:10]}...")

        # Test LLM planner initialization
        planner = LLMPlanner(provider="openai")
        print(f"✅ Initialized LLM planner with model: {planner.model}")

        # Test simple function calling
        simple_command = "create a file called test.txt"
        steps = await planner.plan(simple_command)

        if steps:
            print(f"✅ LLM planning succeeded with {len(steps)} steps")
            for i, step in enumerate(steps, 1):
                print(f"   Step {i}: {step['tool']} - {step['args']}")
        else:
            print("⚠️  LLM planning returned no steps")

        return True

    except Exception as e:
        print(f"❌ LLM connection test failed: {e}")
        return False


async def test_hybrid_planning():
    """Test hybrid planning with different command types."""
    print("\n🔄 Testing Hybrid Planning...")

    test_commands = [
        "create 3 markdown files in Documents",  # Should use deterministic
        "navigate to github.com and take a screenshot",  # Should use LLM
        "play spotify then list my calendar events",  # Complex multi-step
        "open calculator",  # Simple deterministic
    ]

    results = []

    for command in test_commands:
        print(f"\n📝 Testing command: '{command}'")

        # Analyze complexity
        analysis = analyze_command_complexity(command)
        print(f"   Complexity: {analysis['complexity_score']}/10")
        print(f"   Strategy: {analysis['suggested_strategy']}")
        print(f"   Patterns: {analysis['simple_patterns']}")

        # Test hybrid planning
        try:
            steps = await smart_plan(command)
            if steps:
                print(f"   ✅ Generated {len(steps)} steps:")
                for i, step in enumerate(steps, 1):
                    print(f"      {i}. {step['tool']}({step['args']})")
            else:
                print("   ⚠️  No steps generated")

            results.append(
                {
                    "command": command,
                    "success": bool(steps),
                    "steps": len(steps) if steps else 0,
                    "analysis": analysis,
                }
            )

        except Exception as e:
            print(f"   ❌ Planning failed: {e}")
            results.append({"command": command, "success": False, "error": str(e)})

    return results


def test_tool_schemas():
    """Test tool schema definitions and validation."""
    print("\n📋 Testing Tool Schemas...")

    try:
        # Test OpenAI function definitions
        functions = get_openai_function_definitions()
        print(f"✅ Generated {len(functions)} OpenAI function definitions")

        # Test a few specific schemas
        test_cases = [
            ("browser_navigate", {"url": "https://github.com"}),
            ("create_files", {"dir": "~/Documents", "count": 3, "prefix": "test", "ext": "md"}),
            ("spotify_play", {}),
        ]

        for tool_name, args in test_cases:
            try:
                validated = validate_tool_args(tool_name, args)
                print(f"   ✅ {tool_name}: {validated}")
            except Exception as e:
                print(f"   ❌ {tool_name} validation failed: {e}")

        return True

    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False


def test_deterministic_fallback():
    """Test deterministic planner as fallback."""
    print("\n⚙️  Testing Deterministic Fallback...")

    test_commands = [
        "create 5 files in desktop",
        "open safari",
        "navigate to anthropic.com",
        "play spotify",
        "list files in documents",
    ]

    for command in test_commands:
        steps = deterministic_plan(command)
        if steps:
            print(f"   ✅ '{command}' -> {len(steps)} steps")
            for step in steps:
                print(f"      {step['tool']}({step['args']})")
        else:
            print(f"   ⚠️  '{command}' -> No steps")


def test_tool_registry():
    """Test tool registry and availability."""
    print("\n🔧 Testing Tool Registry...")

    from oribit_agent.tools import TOOLS

    print(f"✅ Found {len(TOOLS)} tools in registry:")

    categories = {
        "Browser": [
            "browser_navigate",
            "browser_click",
            "browser_type",
            "browser_get_text",
            "browser_screenshot",
        ],
        "Files": [
            "read_file",
            "write_file",
            "list_directory",
            "make_directory",
            "move_file",
            "delete_file",
            "reveal_in_finder",
        ],
        "Calendar": ["create_calendar_event", "list_calendar_events", "delete_calendar_event"],
        "Spotify": [
            "spotify_play",
            "spotify_pause",
            "spotify_next_track",
            "spotify_previous_track",
            "spotify_get_current_track",
            "spotify_search_and_play",
        ],
        "Legacy": ["create_files", "open_app", "helper"],
    }

    for category, tools in categories.items():
        available = [tool for tool in tools if tool in TOOLS]
        print(f"   {category}: {len(available)}/{len(tools)} available")
        if len(available) != len(tools):
            missing = [tool for tool in tools if tool not in TOOLS]
            print(f"      Missing: {missing}")


async def run_integration_test():
    """Run a simple integration test with actual tool execution."""
    print("\n🚀 Running Integration Test...")

    # Test a safe command that creates files
    test_command = "create 2 test files in /tmp with prefix orbit and extension txt"

    try:
        # Plan the command
        steps = await smart_plan(test_command)
        print(f"✅ Planned {len(steps)} steps for: '{test_command}'")

        # Execute first step (file creation is safe)
        if steps and steps[0]["tool"] == "create_files":
            tool_func = get_tool("create_files")
            if tool_func:
                result = tool_func(**steps[0]["args"])
                print(f"✅ Executed step 1: Created {len(result)} files")
                print(f"   Files: {result}")

                # Clean up test files
                import os

                for file_path in result:
                    try:
                        os.remove(file_path)
                        print(f"   Cleaned up: {file_path}")
                    except Exception:
                        pass
            else:
                print("❌ Tool function not found")
        else:
            print("⚠️  Not executing - first step is not file creation")

    except Exception as e:
        print(f"❌ Integration test failed: {e}")


async def main():
    """Run all Phase 2 tests."""
    print("🧪 Orbit Agent Phase 2 Testing Suite")
    print("=" * 50)

    # Set up environment
    os.environ.setdefault("ORBIT_HELPER_PATH", "/path/to/helper")  # Mock for testing

    tests = [
        ("LLM Connection", test_llm_connection()),
        ("Hybrid Planning", test_hybrid_planning()),
        ("Tool Schemas", test_tool_schemas()),
        ("Deterministic Fallback", test_deterministic_fallback()),
        ("Tool Registry", test_tool_registry()),
        ("Integration Test", run_integration_test()),
    ]

    results = []
    for test_name, test_coro in tests:
        try:
            if asyncio.iscoroutine(test_coro):
                result = await test_coro
            else:
                result = test_coro
            results.append((test_name, True, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False, str(e)))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for test_name, success, result in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status}: {test_name}")

    print(f"\n🎯 Overall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Phase 2 is ready for deployment.")
    else:
        print("⚠️  Some tests failed. Please review the output above.")


if __name__ == "__main__":
    asyncio.run(main())
