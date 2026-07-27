# Frontend Module (`src/frontend`)

## Purpose
Provides user interface client application shells for web and desktop environments. Implements modern responsive UX, live voice interaction visualizer, chat UI, tool execution timeline, and system status indicators.

## Architectural & Design Guidelines
- Designed with **Stitch MCP UI Design** specifications (Project ID: `projects/17160804318098643657`).
- Features modern dark-mode aesthetic with vibrant accent colors, high-contrast typography, and smooth responsive layouts.
- Decoupled from core agent logic, communicating strictly over WebSocket streams and REST APIs defined in `src/api_layer/`.

## Subdirectories
- `web/`: Single Page Application (SPA) web client shell.
- `desktop/`: Native desktop application wrapper specs (Electron/Tauri).
