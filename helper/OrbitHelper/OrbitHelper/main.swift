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

    default:
        printUsage(); exit(1)
    }
} catch {
    fputs("Error: \(error)\n", stderr)
    exit(2)
}

