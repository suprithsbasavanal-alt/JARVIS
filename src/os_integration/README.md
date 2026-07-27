# Operating System Integration Module (`src/os_integration`)

## Purpose
Provides cross-platform native hooks into host operating systems (macOS, Linux, Windows), including local file system change notifications, safe process spawning, and native desktop notifications/system tray integration.

## Architectural Layer
**Infrastructure Layer (SRP)**. Enforces strict boundary isolation around native OS system calls so core AI reasoning code remains pure and cross-platform portable.

## Subdirectories
- `fs_watcher/`: Real-time local file system monitor (file created, modified, deleted).
- `process_runner/`: Subprocess launcher with memory and CPU quota enforcement.
- `native_hooks/`: Platform-specific native system tray, global hotkeys, and system toasts.
