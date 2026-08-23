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

export class IpcConnectionError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "IpcConnectionError";
  }
}

export class IpcRpcError extends Error {
  public code: number;
  constructor(message: string, code: number = -32603) {
    super(message);
    this.name = "IpcRpcError";
    this.code = code;
  }
}

export class JarvisIpcClient {
  private sessionId: string | null = null;
  private authToken: string;
  private devBridgeUrl: string;

  constructor(
    authToken: string = "jarvis-desktop-local-token",
    devBridgeUrl: string = "http://127.0.0.1:8765/rpc"
  ) {
    this.authToken = authToken;
    this.devBridgeUrl = devBridgeUrl;
  }

  private isTauriRuntime(): boolean {
    return !!((window as any).__TAURI__ && (window as any).__TAURI__.core);
  }

  private async invokeCommand<T>(method: string, params: Record<string, any> = {}): Promise<T> {
    // 1. Native Tauri Runtime Execution
    if (this.isTauriRuntime()) {
      try {
        const result = await (window as any).__TAURI__.core.invoke("send_ipc_command", {
          method,
          params,
        });
        if (result === undefined || result === null) {
          throw new IpcRpcError(`Empty result returned for IPC command '${method}'.`);
        }
        return result as T;
      } catch (err: any) {
        throw new IpcRpcError(
          typeof err === "string" ? err : err.message || `IPC error on '${method}'`,
          err.code || -32603
        );
      }
    }

    // 2. Browser Development Diagnostic Bridge
    const reqId = "req-" + Math.random().toString(36).substring(2, 9);
    const bodyPayload = {
      jsonrpc: "2.0",
      id: reqId,
      method,
      params,
    };

    let res: Response;
    try {
      res = await fetch(this.devBridgeUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Jarvis-Auth-Token": this.authToken,
        },
        body: JSON.stringify(bodyPayload),
      });
    } catch (networkErr: any) {
      throw new IpcConnectionError(
        `Cannot connect to JARVIS Core Daemon at ${this.devBridgeUrl}. Please verify 'python -m desktop.daemon' is running.`
      );
    }

    if (!res.ok) {
      throw new IpcConnectionError(
        `JARVIS Daemon HTTP Dev Bridge returned HTTP ${res.status}: ${res.statusText}`
      );
    }

    let jsonResp: any;
    try {
      jsonResp = await res.json();
    } catch (parseErr: any) {
      throw new IpcRpcError(`Invalid JSON response received from JARVIS Daemon: ${parseErr.message}`);
    }

    if (jsonResp.error) {
      throw new IpcRpcError(
        jsonResp.error.message || `RPC Error on '${method}'`,
        jsonResp.error.code || -32603
      );
    }

    if (jsonResp.result === undefined) {
      throw new IpcRpcError(`No result field in response for method '${method}'.`);
    }

    return jsonResp.result as T;
  }

  async getStatus(): Promise<SystemStatus> {
    return await this.invokeCommand<SystemStatus>("jarvis.status");
  }

  async createSession(userName: string = "Suprith"): Promise<string> {
    const res = await this.invokeCommand<{ session_id: string }>("jarvis.session.create", {
      user_name: userName,
      permission_level: "NORMAL",
    });
    if (!res || !res.session_id) {
      throw new IpcRpcError("Failed to initialize conversational session context with JARVIS daemon.");
    }
    this.sessionId = res.session_id;
    return this.sessionId;
  }

  async ensureSession(): Promise<string> {
    if (!this.sessionId) {
      return await this.createSession();
    }
    return this.sessionId;
  }

  async processTurn(query: string): Promise<TurnResponse> {
    const activeSessionId = await this.ensureSession();
    const res = await this.invokeCommand<TurnResponse>("jarvis.turn.process", {
      session_id: activeSessionId,
      query,
    });

    if (!res || typeof res !== "object" || !res.status) {
      throw new IpcRpcError("Malformed turn response received from JARVIS daemon.");
    }
    return res;
  }

  async respondToApproval(cardId: string, decision: "APPROVE" | "DENY"): Promise<TurnResponse> {
    const activeSessionId = await this.ensureSession();
    const res = await this.invokeCommand<TurnResponse>("jarvis.approval.respond", {
      session_id: activeSessionId,
      card_id: cardId,
      decision,
    });
    if (!res || typeof res !== "object") {
      throw new IpcRpcError("Malformed approval response received from JARVIS daemon.");
    }
    return res;
  }

  async getLatestProactiveAdvisory(): Promise<ProactiveAdvisoryPayload> {
    const activeSessionId = this.sessionId || "default";
    return await this.invokeCommand<ProactiveAdvisoryPayload>("jarvis.proactive.get_latest", {
      session_id: activeSessionId,
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
    if (this.isTauriRuntime()) {
      await (window as any).__TAURI__.core.invoke("trigger_emergency_stop");
    } else {
      await this.invokeCommand("jarvis.system.emergency_stop");
    }
  }
}

