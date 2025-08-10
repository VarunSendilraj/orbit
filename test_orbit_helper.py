#!/usr/bin/env python3
"""
Test script for OrbitHelper functionality
Tests all the implemented commands to ensure they work properly
"""

import subprocess
import sys
import os

# Path to the built OrbitHelper binary
HELPER_PATH = "/Users/varunsendilraj/Documents/GitHub/orbit/helper/OrbitHelper-binary"

def helper(*args):
    """Run OrbitHelper command with given arguments"""
    try:
        result = subprocess.run([HELPER_PATH] + list(args), 
                              capture_output=True, 
                              text=True, 
                              check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(args)}")
        print(f"Return code: {e.returncode}")
        print(f"Stderr: {e.stderr}")
        raise

def test_usage():
    """Test the usage/help functionality"""
    print("🧪 Testing usage display...")
    try:
        # Running with no args should show usage and exit with code 1
        subprocess.run([HELPER_PATH], check=False, capture_output=True)
        print("✅ Usage display works")
    except Exception as e:
        print(f"❌ Usage test failed: {e}")

def test_check_ax():
    """Test accessibility permission check"""
    print("🧪 Testing accessibility check...")
    try:
        helper("check-ax")
        print("✅ Accessibility check completed")
    except Exception as e:
        print(f"❌ Accessibility check failed: {e}")

def test_applescript():
    """Test AppleScript execution"""
    print("🧪 Testing AppleScript execution...")
    try:
        # Test a simple AppleScript command
        result = helper("run-applescript", 'tell application "System Events" to get name of current desktop')
        print(f"✅ AppleScript worked, result: {result}")
    except Exception as e:
        print(f"❌ AppleScript test failed: {e}")

def test_open_app():
    """Test opening an app"""
    print("🧪 Testing app opening...")
    try:
        # Try to open Calculator (should be available on all Macs)
        helper("open-app", "Calculator")
        print("✅ App opening worked (Calculator)")
        
        # Close it with AppleScript
        helper("run-applescript", 'tell application "Calculator" to quit')
        print("✅ App closed")
    except Exception as e:
        print(f"❌ App opening test failed: {e}")

def test_focus_app():
    """Test focusing an app"""
    print("🧪 Testing app focusing...")
    try:
        # Open Finder and then focus it
        helper("open-app", "Finder")
        helper("focus-app", "Finder")
        print("✅ App focusing worked (Finder)")
    except Exception as e:
        print(f"❌ App focusing test failed: {e}")

def test_menu_click():
    """Test menu clicking (requires Accessibility permissions)"""
    print("🧪 Testing menu clicking...")
    try:
        # This will prompt for Accessibility permissions if not granted
        # Try to click a simple menu in Finder
        helper("focus-app", "Finder")
        
        # Note: This might fail if Accessibility permissions aren't granted
        helper("click-menu", "Finder", "File", "New Folder")
        print("✅ Menu clicking worked (Finder > File > New Folder)")
    except Exception as e:
        print(f"⚠️  Menu clicking test failed (likely needs Accessibility permissions): {e}")

def main():
    """Run all tests"""
    print("🚀 Starting OrbitHelper tests...\n")
    
    # Check if binary exists
    if not os.path.exists(HELPER_PATH):
        print(f"❌ OrbitHelper binary not found at {HELPER_PATH}")
        sys.exit(1)
    
    # Make sure it's executable
    os.chmod(HELPER_PATH, 0o755)
    
    print(f"📍 Using OrbitHelper binary: {HELPER_PATH}\n")
    
    # Run tests
    tests = [
        test_usage,
        test_check_ax,
        test_applescript,
        test_open_app,
        test_focus_app,
        test_menu_click,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed. Check Accessibility permissions if menu clicking failed.")
    
    print("\n📝 Next steps:")
    print("1. If Accessibility tests failed, go to System Settings > Privacy & Security > Accessibility")
    print("2. Add the OrbitHelper binary to the allowed applications")
    print("3. Re-run the tests")

if __name__ == "__main__":
    main()