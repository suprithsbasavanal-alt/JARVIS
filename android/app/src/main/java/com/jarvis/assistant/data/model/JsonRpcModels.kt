package com.jarvis.assistant.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject

/**
 * Standard JSON-RPC 2.0 Request Envelope.
 */
@Serializable
data class JsonRpcRequest(
    val jsonrpc: String = "2.0",
    val id: String,
    val method: String,
    val params: JsonObject = JsonObject(emptyMap())
)

/**
 * Standard JSON-RPC 2.0 Response Envelope.
 */
@Serializable
data class JsonRpcResponse(
    val jsonrpc: String = "2.0",
    val id: String? = null,
    val result: JsonElement? = null,
    val error: JsonRpcError? = null
)

@Serializable
data class JsonRpcError(
    val code: Int,
    val message: String,
    val data: JsonElement? = null
)

/**
 * Typed Exception thrown when the server returns a JSON-RPC error.
 */
class JsonRpcException(
    val code: Int,
    override val message: String,
    val data: JsonElement? = null
) : Exception("JSON-RPC Error $code: $message")

// ==========================================
// DTOs for Phase 8.2 & 8.3 Device Pairing, Auth & Session
// ==========================================

@Serializable
data class PairBeginParams(
    @SerialName("device_id") val deviceId: String,
    @SerialName("device_name") val deviceName: String,
    @SerialName("public_key_hex") val publicKeyHex: String
)

@Serializable
data class PairBeginResult(
    @SerialName("device_id") val deviceId: String,
    val status: String,
    @SerialName("pairing_code") val pairingCode: String,
    val message: String
)

@Serializable
data class PairConfirmParams(
    @SerialName("device_id") val deviceId: String,
    @SerialName("pairing_code") val pairingCode: String
)

@Serializable
data class PairConfirmResult(
    @SerialName("device_id") val deviceId: String,
    val status: String,
    @SerialName("confirmed_at") val confirmedAt: String? = null
)

@Serializable
data class AuthChallengeParams(
    @SerialName("device_id") val deviceId: String
)

@Serializable
data class AuthChallengeResult(
    @SerialName("challenge_id") val challengeId: String,
    @SerialName("device_id") val deviceId: String,
    val nonce: String,
    @SerialName("expires_at") val expiresAt: String
)

@Serializable
data class AuthVerifyParams(
    @SerialName("challenge_id") val challengeId: String,
    @SerialName("signature_hex") val signatureHex: String
)

@Serializable
data class AuthVerifyResult(
    val authenticated: Boolean,
    @SerialName("session_token") val sessionToken: String,
    @SerialName("device_id") val deviceId: String,
    @SerialName("expires_at") val expiresAt: String
)

@Serializable
data class DeviceRevokeParams(
    @SerialName("device_id") val deviceId: String
)

@Serializable
data class HeartbeatResult(
    val status: String,
    val timestamp: String,
    @SerialName("paired_devices") val pairedDevices: Int = 1,
    @SerialName("active_sessions") val activeSessions: Int = 1
)

// ==========================================
// DTOs for Core Subsystems
// ==========================================

@Serializable
data class HandshakeParams(
    @SerialName("auth_token") val authToken: String
)

@Serializable
data class HandshakeResult(
    val authenticated: Boolean,
    val version: String? = null,
    val daemon: String? = null
)

@Serializable
data class StatusResult(
    val status: String,
    val version: String,
    @SerialName("agent_state") val agentState: String,
    @SerialName("active_sessions") val activeSessions: Int,
    @SerialName("pending_approvals") val pendingApprovals: Int,
    @SerialName("paired_devices") val pairedDevices: Int = 1,
    @SerialName("active_plans") val activePlans: Int = 1
)

@Serializable
data class SessionCreateParams(
    @SerialName("user_display_name") val userDisplayName: String = "Suprith"
)

@Serializable
data class SessionCreateResult(
    @SerialName("session_id") val sessionId: String,
    @SerialName("user_display_name") val userDisplayName: String,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class SessionGetResult(
    @SerialName("session_id") val sessionId: String,
    @SerialName("user_display_name") val userDisplayName: String,
    @SerialName("history_len") val historyLen: Int = 0
)

@Serializable
data class TurnProcessParams(
    val query: String,
    @SerialName("session_id") val sessionId: String,
    @SerialName("session_token") val sessionToken: String? = null
)

@Serializable
data class TurnProcessResult(
    @SerialName("session_id") val sessionId: String,
    val reply: String,
    @SerialName("requires_confirmation") val requiresConfirmation: Boolean = false,
    @SerialName("approval_card") val approvalCard: ApprovalCardDto? = null
)

@Serializable
data class ApprovalCardDto(
    @SerialName("card_id") val cardId: String,
    @SerialName("tool_name") val toolName: String,
    @SerialName("risk_level") val riskLevel: String,
    @SerialName("action_type") val actionType: String = "",
    @SerialName("target_resource") val targetResource: String,
    val parameters: JsonObject = JsonObject(emptyMap()),
    @SerialName("reasoning_summary") val reasoningSummary: String = "",
    @SerialName("risk_summary") val riskSummary: String = "",
    @SerialName("expires_at") val expiresAt: String = "",
    @SerialName("expires_at_epoch") val expiresAtEpoch: Double = 0.0
)

@Serializable
data class ApprovalRespondParams(
    @SerialName("card_id") val cardId: String,
    val decision: String // "APPROVE" or "DENY"
)

@Serializable
data class ApprovalRespondResult(
    @SerialName("session_id") val sessionId: String,
    val reply: String,
    @SerialName("tool_executed") val toolExecuted: Boolean
)

@Serializable
data class ProactiveAdvisoryDto(
    @SerialName("is_informational_only") val isInformationalOnly: Boolean = true,
    @SerialName("is_executable_directly") val isExecutableDirectly: Boolean = false,
    @SerialName("health_score") val healthScore: Double? = null,
    @SerialName("findings_count") val findingsCount: Int = 0,
    @SerialName("suggestions_count") val suggestionsCount: Int = 0,
    val observations: List<String> = emptyList(),
    @SerialName("raw_advisory") val rawAdvisory: String? = null
)

@Serializable
data class StructuredPlanDto(
    @SerialName("plan_id") val planId: String,
    val title: String,
    val goal: String,
    val category: String,
    val milestones: List<PlanMilestoneDto> = emptyList(),
    @SerialName("estimated_hours") val estimatedHours: Double? = null,
    @SerialName("is_informational_only") val isInformationalOnly: Boolean = true
)

@Serializable
data class PlanMilestoneDto(
    @SerialName("milestone_id") val milestoneId: String,
    val title: String,
    val steps: List<PlanStepDto> = emptyList()
)

@Serializable
data class PlanStepDto(
    @SerialName("step_number") val stepNumber: Int,
    val description: String,
    val deliverable: String,
    @SerialName("is_completed") val isCompleted: Boolean = false
)

@Serializable
data class PlanUpdateStepParams(
    @SerialName("plan_id") val planId: String,
    @SerialName("step_number") val stepNumber: Int,
    val completed: Boolean
)

@Serializable
data class PlanUpdateStepResult(
    @SerialName("plan_id") val planId: String,
    @SerialName("step_number") val stepNumber: Int,
    val completed: Boolean
)

@Serializable
data class EmergencyStopResult(
    val status: String,
    @SerialName("revoked_approvals") val revokedApprovals: Int
)

// ==========================================
// DTOs for Phase 9 External Services
// ==========================================

@Serializable
data class ServiceMetadataDto(
    @SerialName("service_id") val serviceId: String,
    val name: String,
    val description: String,
    val capabilities: List<String> = emptyList(),
    val version: String = "1.0.0",
    @SerialName("auth_type") val authType: String = "OAUTH2",
    @SerialName("is_enabled") val isEnabled: Boolean = true,
    val status: String = "CONNECTED"
)

@Serializable
data class ServiceListResult(
    val services: List<ServiceMetadataDto> = emptyList()
)

@Serializable
data class ServiceStatusResult(
    @SerialName("service_id") val serviceId: String? = null,
    val status: String? = null,
    val statuses: Map<String, String> = emptyMap()
)

