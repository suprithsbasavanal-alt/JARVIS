/**
 * Study & Task Plan Persistent Checklist Widget Component.
 */

import { ActivePlanPayload } from "../ipcClient";

export class PlanChecklistView {
  private container: HTMLElement;
  private onToggleStep: (planId: string, stepNumber: number, completed: boolean) => void;

  constructor(container: HTMLElement, onToggleStep: (planId: string, stepNumber: number, completed: boolean) => void) {
    this.container = container;
    this.onToggleStep = onToggleStep;
    this.renderEmpty();
  }

  private renderEmpty(): void {
    this.container.innerHTML = `
      <div class="sidebar-card">
        <div class="card-title">
          <span>Active Plan</span>
          <span style="font-size: 10px; color: var(--color-text-muted);">NONE</span>
        </div>
        <div style="font-size: 11px; color: var(--color-text-muted);">
          No active study or task execution plan.
        </div>
      </div>
    `;
  }

  public update(plan: ActivePlanPayload): void {
    if (!plan.has_plan || !plan.steps || plan.steps.length === 0) {
      this.renderEmpty();
      return;
    }

    const planId = plan.plan_id || "default_plan";
    const completedCount = plan.steps.filter((s) => s.completed).length;
    const progressPercent = Math.round((completedCount / plan.steps.length) * 100);

    const stepsHtml = plan.steps
      .map(
        (s) => `
        <label class="checklist-item">
          <input 
            type="checkbox" 
            class="checklist-checkbox" 
            data-step="${s.step_number}" 
            ${s.completed ? "checked" : ""}
          />
          <span style="${s.completed ? "text-decoration: line-through; color: var(--color-text-muted);" : ""}">
            ${s.title}
          </span>
        </label>
      `
      )
      .join("");

    this.container.innerHTML = `
      <div class="sidebar-card">
        <div class="card-title">
          <span>${plan.title || "Execution Plan"}</span>
          <span style="font-size: 11px; color: var(--primary-cyan);">${progressPercent}%</span>
        </div>
        <div style="display: flex; flex-direction: column; gap: 4px;">
          ${stepsHtml}
        </div>
      </div>
    `;

    const checkboxes = this.container.querySelectorAll<HTMLInputElement>(".checklist-checkbox");
    checkboxes.forEach((cb) => {
      cb.addEventListener("change", () => {
        const stepNum = parseInt(cb.dataset.step || "0", 10);
        this.onToggleStep(planId, stepNum, cb.checked);
      });
    });
  }
}
