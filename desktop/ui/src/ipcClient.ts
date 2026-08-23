/**
 * Type-Safe IPC Client for JARVIS macOS Desktop Frontend.
 */

export interface SystemStatus {
  status: string;
  agent_state: string;
  registered_tools_count: number;
  active_sessions_count: number;
  pending_approvals_count: number;
  timestamp: string;
}

export interface TurnResponse {
  status: "COMPLETED" | "AWAITING_CONFIRMATION" | "DENIED";
  session_id: string;
  reply?: string;
  model_name?: string;
  provider_name?: string;
  requires_confirmation: boolean;
  approval_card?: ApprovalCardPayload;
}

export interface ApprovalCardPayload {
  card_id: string;
  action_name: string;
  action_category: string;
  target_resource: string;
  risk_summary: string;
  parameters: Record<string, any>;
  created_at: string;
  expires_at: string;
}

export interface ProactiveAdvisoryPayload {
  has_advisory: boolean;
  trigger_type?: string;
  health_score?: number;
  findings_count?: number;
  suggestions?: Array<{
    title: string;
    description: string;
    priority: string;
    category: string;
  }>;
  disagreements?: Array<{
    proposition: string;
    should_disagree: boolean;
    counter_proposal?: string;
  }>;
  formatted_markdown?: string;
  is_informational_only: boolean;
}

export interface PlanStep {
  step_number: number;
  title: string;
  action_required: string;
  completed: boolean;
}

export interface ActivePlanPayload {
  has_plan: boolean;
  plan_id?: string;
  title?: string;
  goal?: string;
  steps?: PlanStep[];
  is_informational_only: boolean;
}

export class JarvisIpcClient {
  private sessionId: string | null = null;

  private async invokeCommand<T>(method: string, params: Record<string, any> = {}): Promise<T> {
    if ((window as any).__TAURI__ && (window as any).__TAURI__.core) {
      return await (window as any).__TAURI__.core.invoke("send_ipc_command", {
        method,
        params,
      });
    }

    // Fallback simulation when running in standard browser dev mode
    console.info(`[IPC Fallback] Invoking '${method}'`, params);
    if (method === "jarvis.status") {
      return {
        status: "ONLINE",
        agent_state: "IDLE",
        registered_tools_count: 5,
        active_sessions_count: 1,
        pending_approvals_count: 0,
        timestamp: new Date().toISOString(),
      } as T;
    }
    if (method === "jarvis.proactive.get_latest") {
      return {
        has_advisory: true,
        trigger_type: "SESSION_START",
        health_score: 92,
        findings_count: 1,
        suggestions: [
          {
            title: "Proactive Security Recommendation",
            description: "Review repository dependencies for outdated versions.",
            priority: "LOW",
            category: "DEPENDENCY_UPGRADE",
          },
        ],
        is_informational_only: true,
      } as T;
    }
    return {} as T;
  }

  async getStatus(): Promise<SystemStatus> {
    return await this.invokeCommand<SystemStatus>("jarvis.status");
  }

  async createSession(userName: string = "Suprith"): Promise<string> {
    const res = await this.invokeCommand<{ session_id: string }>("jarvis.session.create", {
      user_name: userName,
      permission_level: "NORMAL",
    });
    this.sessionId = res.session_id;
    return this.sessionId;
  }

  async processTurn(query: string): Promise<TurnResponse> {
    return await this.invokeCommand<TurnResponse>("jarvis.turn.process", {
      session_id: this.sessionId || "default",
      query,
    });
  }

  async respondToApproval(cardId: string, decision: "APPROVE" | "DENY"): Promise<TurnResponse> {
    return await this.invokeCommand<TurnResponse>("jarvis.approval.respond", {
      card_id: cardId,
      decision,
    });
  }

  async getLatestProactiveAdvisory(): Promise<ProactiveAdvisoryPayload> {
    return await this.invokeCommand<ProactiveAdvisoryPayload>("jarvis.proactive.get_latest", {
      session_id: this.sessionId || "default",
    });
  }

  async getActivePlan(): Promise<ActivePlanPayload> {
    return await this.invokeCommand<ActivePlanPayload>("jarvis.plan.get_active", {});
  }

  async updatePlanStep(planId: string, stepNumber: number, completed: boolean): Promise<void> {
    await this.invokeCommand("jarvis.plan.update_step", {
      plan_id: planId,
      step_number: stepNumber,
      completed,
    });
  }

  async emergencyStop(): Promise<void> {
    if ((window as any).__TAURI__ && (window as any).__TAURI__.core) {
      await (window as any).__TAURI__.core.invoke("trigger_emergency_stop");
    } else {
      await this.invokeCommand("jarvis.system.emergency_stop");
    }
  }
}
