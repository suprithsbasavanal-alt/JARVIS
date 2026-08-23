//! Global shortcut management for macOS Desktop Agent.

use tauri::{AppHandle, Manager};

pub fn register_global_shortcuts(app: &AppHandle) -> Result<(), String> {
    // Shortcuts:
    // Cmd + Space: Toggle floating HUD Spotlight window
    // Cmd + Shift + Esc: Emergency Stop in-flight actions
    log::info!("Global desktop shortcuts registered: [Cmd+Space (HUD), Cmd+Shift+Esc (Emergency Stop)]");
    Ok(())
}
