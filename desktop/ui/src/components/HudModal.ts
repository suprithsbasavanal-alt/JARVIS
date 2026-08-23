/**
 * Spotlight Search & HUD Header Bar Component.
 */

export class HudModal {
  private container: HTMLElement;
  private onQuerySubmit: (query: string) => void;

  constructor(container: HTMLElement, onQuerySubmit: (query: string) => void) {
    this.container = container;
    this.onQuerySubmit = onQuerySubmit;
    this.render();
  }

  private render(): void {
    this.container.innerHTML = `
      <header class="hud-header">
        <div class="hud-brand">
          <div class="brand-icon"></div>
          <span class="brand-title">JARVIS</span>
        </div>
        <div class="hud-status-group">
          <span id="agent-state-badge" class="status-badge">L2 NORMAL</span>
          <div class="hud-actions">
            <button id="btn-emergency-stop" class="btn-icon" title="Emergency Stop (Cmd+Shift+Esc)">🛑 Stop</button>
            <button id="btn-minimize" class="btn-icon" title="Hide HUD">✕</button>
          </div>
        </div>
      </header>

      <section class="hud-search-section">
        <div class="search-input-wrapper">
          <span class="search-icon">⚡</span>
          <input 
            type="text" 
            id="hud-search-input" 
            class="search-input" 
            placeholder="Ask JARVIS anything or describe a task..." 
            autocomplete="off"
            spellcheck="false"
          />
          <span class="search-hint">⌘Space</span>
        </div>
      </section>
    `;

    const input = this.container.querySelector("#hud-search-input") as HTMLInputElement;
    input?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && input.value.trim()) {
        const query = input.value.trim();
        input.value = "";
        this.onQuerySubmit(query);
      }
    });

    const minimizeBtn = this.container.querySelector("#btn-minimize");
    minimizeBtn?.addEventListener("click", () => {
      if ((window as any).__TAURI__?.core) {
        (window as any).__TAURI__.core.invoke("toggle_hud_window");
      }
    });
  }

  public updateState(stateText: string): void {
    const badge = this.container.querySelector("#agent-state-badge");
    if (badge) {
      badge.textContent = stateText;
    }
  }
}
