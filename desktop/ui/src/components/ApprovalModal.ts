/**
 * Human-in-the-Loop (HITL) Interactive Confirmation Modal Component.
 */

import { ApprovalCardPayload } from "../ipcClient";

export class ApprovalModal {
  private overlayElement: HTMLElement;
  private onDecision: (cardId: string, decision: "APPROVE" | "DENY") => void;

  constructor(overlayElement: HTMLElement, onDecision: (cardId: string, decision: "APPROVE" | "DENY") => void) {
    this.overlayElement = overlayElement;
    this.onDecision = onDecision;
  }

  public show(card: ApprovalCardPayload): void {
    this.overlayElement.innerHTML = `
      <div class="approval-card">
        <div class="approval-title">
          <span>⚠️</span>
          <span>HUMAN CONFIRMATION REQUIRED</span>
        </div>
        <div>
          <strong>Action:</strong> ${card.action_name} (${card.action_category})<br/>
          <strong>Target Resource:</strong> <code>${card.target_resource}</code>
        </div>
        <div class="approval-details">
          <strong>Risk Assessment:</strong> ${card.risk_summary}<br/>
          <strong>Parameters:</strong> <code>${JSON.stringify(card.parameters)}</code>
        </div>
        <div class="approval-actions">
          <button id="btn-deny-action" class="btn-deny">Deny</button>
          <button id="btn-approve-action" class="btn-approve">Authorize (Single-Use)</button>
        </div>
      </div>
    `;

    this.overlayElement.classList.add("active");

    const approveBtn = this.overlayElement.querySelector("#btn-approve-action");
    const denyBtn = this.overlayElement.querySelector("#btn-deny-action");

    approveBtn?.addEventListener("click", () => {
      this.hide();
      this.onDecision(card.card_id, "APPROVE");
    });

    denyBtn?.addEventListener("click", () => {
      this.hide();
      this.onDecision(card.card_id, "DENY");
    });
  }

  public hide(): void {
    this.overlayElement.classList.remove("active");
    this.overlayElement.innerHTML = "";
  }
}
