/**
 * Live Conversation View with Message Rendering and Code Blocks.
 */

export interface ChatMessageItem {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export class ConversationView {
  private container: HTMLElement;
  private messages: ChatMessageItem[] = [];

  constructor(container: HTMLElement) {
    this.container = container;
    this.render();
  }

  private render(): void {
    this.container.innerHTML = `
      <div class="conversation-panel">
        <div id="messages-list" class="messages-list">
          <div class="message-item message-assistant">
            <div class="message-header">JARVIS • JUST NOW</div>
            <div class="message-bubble">
              Good day, sir. Systems are online and operating within normal parameters. How may I assist you today?
            </div>
          </div>
        </div>
      </div>
    `;
  }

  public addMessage(role: "user" | "assistant", content: string): void {
    const list = this.container.querySelector("#messages-list");
    if (!list) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const item = document.createElement("div");
    item.className = `message-item message-${role}`;
    item.innerHTML = `
      <div class="message-header">${role === "user" ? "YOU" : "JARVIS"} • ${timeStr}</div>
      <div class="message-bubble">${this.escapeHtml(content)}</div>
    `;

    list.appendChild(item);
    list.scrollTop = list.scrollHeight;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
