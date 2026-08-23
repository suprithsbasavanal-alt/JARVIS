/**
 * Proactive Intelligence & Advisory Widget Component.
 */

import { ProactiveAdvisoryPayload } from "../ipcClient";

export class ProactiveAdvisoryWidget {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
    this.renderEmpty();
  }

  private renderEmpty(): void {
    this.container.innerHTML = `
      <div class="sidebar-card">
        <div class="card-title">
          <span>Proactive Intelligence</span>
          <span style="color: var(--primary-cyan); font-size: 10px;">MONITORING</span>
        </div>
        <div class="health-gauge">
          <div class="health-score-val">--</div>
          <div style="font-size: 11px; color: var(--color-text-secondary);">
            Awaiting project review trigger...
          </div>
        </div>
      </div>
    `;
  }

  public update(advisory: ProactiveAdvisoryPayload): void {
    if (!advisory.has_advisory) {
      this.renderEmpty();
      return;
    }

    const score = advisory.health_score ?? 100;
    const scoreColor = score >= 85 ? "var(--primary-cyan)" : score >= 60 ? "var(--secondary-gold)" : "var(--color-danger)";

    let findingsHtml = "";
    if (advisory.suggestions && advisory.suggestions.length > 0) {
      findingsHtml = advisory.suggestions
        .slice(0, 2)
        .map(
          (s) => `
          <div class="proactive-finding-item">
            <strong>${s.title}</strong>
            <div style="color: var(--color-text-secondary); margin-top: 2px;">${s.description}</div>
          </div>
        `
        )
        .join("");
    } else {
      findingsHtml = `<div style="font-size: 11px; color: var(--color-text-muted);">No critical anomalies detected.</div>`;
    }

    this.container.innerHTML = `
      <div class="sidebar-card">
        <div class="card-title">
          <span>Project Health</span>
          <span style="color: ${scoreColor}; font-size: 11px;">${advisory.trigger_type || "REVIEW"}</span>
        </div>
        <div class="health-gauge">
          <div class="health-score-val" style="color: ${scoreColor};">${score}</div>
          <div style="font-size: 11px; color: var(--color-text-secondary);">
            ${advisory.findings_count ?? 0} observations recorded
          </div>
        </div>
        <div style="display: flex; flex-direction: column; gap: 6px; margin-top: 4px;">
          ${findingsHtml}
        </div>
      </div>
    `;
  }
}
