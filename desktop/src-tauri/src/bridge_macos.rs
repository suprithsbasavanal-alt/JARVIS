//! Native macOS AppKit Window Vibrancy and Styling Bridge.

use tauri::WebviewWindow;

pub fn apply_macos_vibrancy(window: &WebviewWindow) {
    // Configures macOS translucent window vibrancy, rounded corners, and shadow
    #[cfg(target_os = "macos")]
    {
        use cocoa::appkit::{NSColor, NSWindow};
        use cocoa::base::{id, nil};

        if let Ok(ns_window) = window.ns_window() {
            let ns_win = ns_window as id;
            unsafe {
                ns_win.setBackgroundColor_(NSColor::clearColor(nil));
                ns_win.setOpaque_(cocoa::base::NO);
            }
        }
    }
}
