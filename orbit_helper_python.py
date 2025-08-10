#!/usr/bin/env python3
"""
Python wrapper for OrbitHelper - macOS automation helper
Use this in your Python/FastAPI agent to call OrbitHelper commands
"""

import subprocess
import os
from typing import Optional

# Path to the built OrbitHelper binary
ORBIT_HELPER_PATH = "/Users/varunsendilraj/Documents/GitHub/orbit/helper/OrbitHelper-binary"

def helper(*args) -> Optional[str]:
    """
    Call OrbitHelper with the given arguments
    
    Args:
        *args: Command arguments to pass to OrbitHelper
        
    Returns:
        str: Output from OrbitHelper command (if any)
        
    Raises:
        subprocess.CalledProcessError: If the command fails
    """
    if not os.path.exists(ORBIT_HELPER_PATH):
        raise FileNotFoundError(f"OrbitHelper binary not found at {ORBIT_HELPER_PATH}")
    
    result = subprocess.run([ORBIT_HELPER_PATH] + list(args), 
                          capture_output=True, 
                          text=True, 
                          check=True)
    
    return result.stdout.strip() if result.stdout.strip() else None

# Example usage functions
def open_app(app_name: str) -> None:
    """Open an application by name"""
    helper("open-app", app_name)

def focus_app(app_name: str) -> None:
    """Focus/activate an application by name"""
    helper("focus-app", app_name)

def run_applescript(script: str) -> Optional[str]:
    """Execute AppleScript and return result"""
    return helper("run-applescript", script)

def click_menu(app_name: str, menu_name: str, menu_item: str) -> None:
    """Click a menu item in an application (requires Accessibility permissions)"""
    helper("click-menu", app_name, menu_name, menu_item)

def check_accessibility() -> None:
    """Check and prompt for Accessibility permissions"""
    helper("check-ax")

# Example usage:
if __name__ == "__main__":
    # Demo the functions
    print("🤖 OrbitHelper Python Wrapper Demo")
    
    try:
        # Open an app
        print("Opening Calculator...")
        open_app("Calculator")
        
        # Run some AppleScript
        print("Getting current desktop name...")
        desktop = run_applescript('tell application "System Events" to get name of current desktop')
        print(f"Current desktop: {desktop}")
        
        # Focus an app
        print("Focusing Calculator...")
        focus_app("Calculator")
        
        # Close the app
        print("Closing Calculator...")
        run_applescript('tell application "Calculator" to quit')
        
        print("✅ All operations completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    # Check accessibility permissions
    try:
        print("Checking accessibility permissions...")
        check_accessibility()
    except Exception as e:
        print(f"Accessibility check: {e}")