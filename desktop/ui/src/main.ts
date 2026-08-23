/**
 * Main Application Entry Point for JARVIS Aether HUD macOS Client.
 */

import "./styles/main.css";
import { JarvisIpcClient } from "./ipcClient";
import { HudModal } from "./components/HudModal";
import { ConversationView } from "./components/ConversationView";
import { ApprovalModal } from "./components/ApprovalModal";
import { ProactiveAdvisoryWidget } from "./components/ProactiveAdvisoryWidget";
import { PlanChecklistView } from "./components/PlanChecklistView";

class JarvisApp {
  private ipc: JarvisIpcClient;
  private hudModal!: HudModal;
  private conversationView!: ConversationView;
  private approvalModal!: ApprovalModal;
  private proactiveWidget!: ProactiveAdvisoryWidget;
  private planWidget!: PlanChecklistView;

  constructor() {
    this.ipc = new JarvisIpcClient();
    this.init();
  }

  private async init(): Promise<void> {
    const appElement = document.querySelector<HTMLDivElement>("#app")!;
    appElement.innerHTML = `
      <div class="hud-window">
        <div id="hud-top-container"></div>
        <main class="hud-body">
          <div id="conversation-container"></div>
          <aside class="sidebar-panel">
            <div id="proactive-container"></div>
            <div id="plan-container"></div>
          </aside>
        </main>
        <div id="modal-overlay-container" class="modal-overlay"></div>
      </div>
    `;

    // Initialize UI Components
    const topContainer = document.querySelector<HTMLElement>("#hud-top-container")!;
    const convContainer = document.querySelector<HTMLElement>("#conversation-container")!;
    const modalContainer = document.querySelector<HTMLElement>("#modal-overlay-container")!;
    const proactiveContainer = document.querySelector<HTMLElement>("#proactive-container")!;
    const planContainer = document.querySelector<HTMLElement>("#plan-container")!;

    this.hudModal = new HudModal(topContainer, (query) => this.handleUserQuery(query));
    this.conversationView = new ConversationView(convContainer);
    this.approvalModal = new ApprovalModal(modalContainer, (cardId, decision) =>
      this.handleApprovalDecision(cardId, decision)
    );
    this.proactiveWidget = new ProactiveAdvisoryWidget(proactiveContainer);
    this.planWidget = new PlanChecklistView(planContainer, (planId, stepNum, completed) =>
      this.handlePlanStepToggle(planId, stepNum, completed)
    );

    // Wire Emergency Stop Button
    document.querySelector("#btn-emergency-stop")?.addEventListener("click", () => {
      this.ipc.emergencyStop();
      this.conversationView.addMessage("assistant", "🛑 Emergency stop initiated. All pending authorizations revoked.");
    });

    // Start Session & Initial Poll
    try {
      await this.ipc.createSession("Suprith");
      const status = await this.ipc.getStatus();
      this.hudModal.updateState(`L2 ${status.agent_state}`);

      const advisory = await this.ipc.getLatestProactiveAdvisory();
      this.proactiveWidget.update(advisory);

      const plan = await this.ipc.getActivePlan();
      this.planWidget.update(plan);
    } catch (e) {
      console.warn("Initial daemon connection:", e);
    }
  }

  private async handleUserQuery(query: string): Promise<void> {
    this.conversationView.addMessage("user", query);
    this.hudModal.updateState("THINKING");

    try {
      const response = await this.ipc.processTurn(query);
      if (response.requires_confirmation && response.approval_card) {
        this.hudModal.updateState("AWAITING CONFIRMATION");
        this.approvalModal.show(response.approval_card);
      } else if (response.reply) {
        this.hudModal.updateState("IDLE");
        this.conversationView.addMessage("assistant", response.reply);
      }

      // Refresh proactive observations & plans
      const advisory = await this.ipc.getLatestProactiveAdvisory();
      this.proactiveWidget.update(advisory);

      const plan = await this.ipc.getActivePlan();
      this.planWidget.update(plan);
    } catch (err: any) {
      this.hudModal.updateState("ERROR");
      this.conversationView.addMessage("assistant", `⚠️ Error executing turn: ${err.message || err}`);
    }
  }

  private async handleApprovalDecision(cardId: string, decision: "APPROVE" | "DENY"): Promise<void> {
    this.hudModal.updateState("EXECUTING");
    try {
      const response = await this.ipc.respondToApproval(cardId, decision);
      this.hudModal.updateState("IDLE");
      if (response.reply) {
        this.conversationView.addMessage("assistant", response.reply);
      }
    } catch (err: any) {
      this.hudModal.updateState("ERROR");
      this.conversationView.addMessage("assistant", `⚠️ Approval handling error: ${err.message || err}`);
    }
  }

  private async handlePlanStepToggle(planId: string, stepNumber: number, completed: boolean): Promise<void> {
    try {
      await this.ipc.updatePlanStep(planId, stepNumber, completed);
      const plan = await this.ipc.getActivePlan();
      this.planWidget.update(plan);
    } catch (err) {
      console.error("Failed to update plan step:", err);
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new JarvisApp();
});
