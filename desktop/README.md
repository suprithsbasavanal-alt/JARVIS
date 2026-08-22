# JARVIS Desktop Client (macOS)

> **Phase 0 — Safe Development Specification**

This directory houses the architectural design, IPC bridge interfaces, and UI scaffolding for the **macOS Desktop Client**.

---

## 1. Architecture Overview

The desktop client is designed using **Tauri v2**:
- **Core Process (Rust)**: Manages local Unix Domain Socket connections to the JARVIS Core Daemon, global system hotkeys (`Cmd + Space` HUD, `Cmd + Shift + Esc` Emergency Stop), system tray lifecycle, and native macOS Accessibility/AppleScript bridges.
- **Renderer Process (Webview / Vanilla TypeScript / Stitch UI)**: High-performance, low-memory floating HUD and Control Center interface for conversation, memory inspection, and permission approval modals.

---

## 2. Directory Scaffolding (Planned for Phase 7)

```
desktop/
├── README.md
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── capabilities/        # Tauri v2 ACL capabilities
│   └── src/
│       ├── main.rs          # App entrypoint & tray setup
│       ├── ipc.rs           # Unix Domain Socket client
│       ├── hotkeys.rs       # Global shortcut listener
│       └── bridge_macos.rs  # Native Swift / AppKit bridge
└── ui/
    ├── package.json
    ├── index.html
    └── src/
        ├── App.tsx
        ├── components/
        └── styles/
```
