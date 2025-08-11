import Foundation
import AppKit
import ApplicationServices   // for Accessibility check

enum HelperError: Error {
    case usage(String)
    case appNotFound(String)
}

func printUsage() {
    print("""
    OrbitHelper – macOS action helper

    Usage:
      OrbitHelper open-app "App Name"
      OrbitHelper focus-app "App Name"
      OrbitHelper run-applescript 'tell application "System Events" to keystroke "n" using command down'
      OrbitHelper click-menu "App Name" "Menu" "Menu Item"
      OrbitHelper check-ax
      OrbitHelper click-element "App Name" "Button Name"
      OrbitHelper get-text "App Name" "Element Name"
      OrbitHelper wait-for-element "App Name" "Element Name" [timeout]
    """)
}

// Accessibility (AX) permission check & prompt
func ensureAccessibilityPermission() {
    let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
    let trusted = AXIsProcessTrustedWithOptions(options)
    if !trusted {
        fputs("Accessibility permission not granted yet. Open System Settings > Privacy & Security > Accessibility and add OrbitHelper.\n", stderr)
    }
}

func openApp(_ name: String) throws {
    if !NSWorkspace.shared.launchApplication(name) {
        throw HelperError.appNotFound("Could not open \(name)")
    }
}

func focusApp(_ name: String) throws {
    // Try to find and activate the app
    let apps = NSRunningApplication.runningApplications(withBundleIdentifier: "")
    // Simple approach: use AppleScript to activate by name
    let script = """
    tell application "\(name)" to activate
    """
    try runAppleScript(script)
}

@discardableResult
func runAppleScript(_ source: String) throws -> String {
    var error: NSDictionary?
    if let script = NSAppleScript(source: source) {
        let output = script.executeAndReturnError(&error)
        if let e = error {
            throw NSError(domain: "applescript", code: 1, userInfo: e as? [String:Any])
        }
        return output.stringValue ?? ""
    } else {
        throw NSError(domain: "applescript", code: 2, userInfo: [NSLocalizedDescriptionKey: "Invalid AppleScript"])
    }
}

func clickMenu(app: String, menu: String, item: String) throws {
    ensureAccessibilityPermission()
    let script = """
    tell application "\(app)" to activate
    tell application "System Events"
      tell process "\(app)"
        click menu item "\(item)" of menu "\(menu)" of menu bar 1
      end tell
    end tell
    """
    _ = try runAppleScript(script)
}

func clickElement(app: String, elementName: String) throws {
    ensureAccessibilityPermission()
    let script = """
    tell application "\(app)" to activate
    delay 0.5
    tell application "System Events"
      tell process "\(app)"
        try
          click button "\(elementName)"
        on error
          try
            click UI element "\(elementName)"
          on error
            error "Could not find element: \(elementName)"
          end try
        end try
      end tell
    end tell
    """
    _ = try runAppleScript(script)
}

func getText(app: String, elementName: String) throws -> String {
    ensureAccessibilityPermission()
    let script = """
    tell application "\(app)" to activate
    delay 0.5
    tell application "System Events"
      tell process "\(app)"
        try
          set textValue to value of text field "\(elementName)"
          return textValue
        on error
          try
            set textValue to name of UI element "\(elementName)"
            return textValue
          on error
            try
              set textValue to value of UI element "\(elementName)"
              return textValue
            on error
              return "Could not get text from element: \(elementName)"
            end try
          end try
        end try
      end tell
    end tell
    """
    return try runAppleScript(script)
}

func waitForElement(app: String, elementName: String, timeout: Int = 10) throws {
    ensureAccessibilityPermission()
    let script = """
    tell application "\(app)" to activate
    delay 0.5
    tell application "System Events"
      tell process "\(app)"
        set startTime to current date
        repeat
          try
            if exists button "\(elementName)" then
              return "Found button: \(elementName)"
            end if
          on error
            try
              if exists UI element "\(elementName)" then
                return "Found element: \(elementName)"
              end if
            end try
          end try
          
          if (current date) - startTime > \(timeout) then
            error "Timeout waiting for element: \(elementName)"
          end if
          delay 0.5
        end repeat
      end tell
    end tell
    """
    let result = try runAppleScript(script)
    print(result)
}

// ---- main argument routing ----
let args = CommandLine.arguments.dropFirst()
guard let cmd = args.first else {
    printUsage(); exit(1)
}

do {
    switch cmd {
    case "open-app":
        guard let name = args.dropFirst().first else { throw HelperError.usage("open-app requires app name") }
        try openApp(name)

    case "focus-app":
        guard let name = args.dropFirst().first else { throw HelperError.usage("focus-app requires app name") }
        try focusApp(name)

    case "run-applescript":
        let src = args.dropFirst().joined(separator: " ")
        guard !src.isEmpty else { throw HelperError.usage("run-applescript requires a script string") }
        let out = try runAppleScript(src)
        if !out.isEmpty { print(out) }

    case "click-menu":
        let parts = Array(args.dropFirst())
        guard parts.count == 3 else { throw HelperError.usage("click-menu requires 3 args: app, menu, item") }
        try clickMenu(app: parts[0], menu: parts[1], item: parts[2])

    case "check-ax":
        ensureAccessibilityPermission()
        
    case "click-element":
        let parts = Array(args.dropFirst())
        guard parts.count == 2 else { throw HelperError.usage("click-element requires 2 args: app, element") }
        try clickElement(app: parts[0], elementName: parts[1])
        
    case "get-text":
        let parts = Array(args.dropFirst())
        guard parts.count == 2 else { throw HelperError.usage("get-text requires 2 args: app, element") }
        let text = try getText(app: parts[0], elementName: parts[1])
        print(text)
        
    case "wait-for-element":
        let parts = Array(args.dropFirst())
        guard parts.count >= 2 else { throw HelperError.usage("wait-for-element requires at least 2 args: app, element [timeout]") }
        let timeout = parts.count >= 3 ? Int(parts[2]) ?? 10 : 10
        try waitForElement(app: parts[0], elementName: parts[1], timeout: timeout)

    default:
        printUsage(); exit(1)
    }
} catch {
    fputs("Error: \(error)\n", stderr)
    exit(2)
}

