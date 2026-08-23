// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod bridge_macos;
mod hotkeys;
mod ipc;

use ipc::IpcClient;
use serde_json::{json, Value};
use std::sync::Mutex;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager, State,
};

struct AppState {
    ipc_client: Mutex<IpcClient>,
}

#[tauri::command]
async fn send_ipc_command(
    method: String,
    params: Value,
    state: State<'_, AppState>,
) -> Result<Value, String> {
    let client = state.ipc_client.lock().map_err(|e| e.to_string())?;
    client.call(&method, params).await
}

#[tauri::command]
fn toggle_hud_window(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_visible().unwrap_or(false) {
            window.hide().map_err(|e| e.to_string())?;
        } else {
            window.show().map_err(|e| e.to_string())?;
            window.set_focus().map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

#[tauri::command]
async fn trigger_emergency_stop(state: State<'_, AppState>) -> Result<Value, String> {
    let client = state.ipc_client.lock().map_err(|e| e.to_string())?;
    client.call("jarvis.system.emergency_stop", json!({})).await
}

fn main() {
    let auth_token = std::env::var("JARVIS_IPC_TOKEN").unwrap_or_else(|_| "jarvis-desktop-local-token".into());
    let initial_ipc = IpcClient::new(None, auth_token);

    tauri::Builder::default()
        .manage(AppState {
            ipc_client: Mutex::new(initial_ipc),
        })
        .setup(|app| {
            // Setup macOS vibrancy and styling
            if let Some(window) = app.get_webview_window("main") {
                bridge_macos::apply_macos_vibrancy(&window);
            }

            // Register global shortcuts
            let _ = hotkeys::register_global_shortcuts(app.handle());

            // Build system tray
            let show_item = MenuItem::with_id(app, "show_hud", "Toggle HUD (Cmd+Space)", true, None::<&str>)?;
            let stop_item = MenuItem::with_id(app, "emergency_stop", "Emergency Stop (Cmd+Shift+Esc)", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "Quit JARVIS", true, None::<&str>)?;

            let tray_menu = Menu::with_items(app, &[&show_item, &stop_item, &quit_item])?;

            let _tray = TrayIconBuilder::new()
                .menu(&tray_menu)
                .tooltip("JARVIS AI Assistant")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show_hud" => {
                        let _ = toggle_hud_window(app.clone());
                    }
                    "emergency_stop" => {
                        if let Some(state) = app.try_state::<AppState>() {
                            tauri::async_runtime::spawn(async move {
                                let _ = trigger_emergency_stop(state).await;
                            });
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        let app = tray.app_handle();
                        let _ = toggle_hud_window(app.clone());
                    }
                })
                .build(app)?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            send_ipc_command,
            toggle_hud_window,
            trigger_emergency_stop
        ])
        .run(tauri::generate_context!())
        .expect("error while running JARVIS desktop client");
}
