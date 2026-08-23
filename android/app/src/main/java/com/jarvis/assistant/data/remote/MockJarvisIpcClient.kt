package com.jarvis.assistant.data.remote

import com.jarvis.assistant.data.model.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import java.util.UUID

/**
 * Hermetic in-memory mock IPC client implementing the full JARVIS protocol.
 * Used for offline development, previewing, and automated unit testing in Phase 8.
 */
class MockJarvisIpcClient(
    private val simulatedLatencyMs: Long = 10L,
    private val initialAuthToken: String = "mock-companion-token-12345"
) : JarvisIpcClient {

    private val _connectionState = MutableStateFlow(ConnectionState.CONNECTED)
    override val connectionState: Flow<ConnectionState> = _connectionState.asStateFlow()
    override val isConnected: Flow<Boolean> = _connectionState.map { it == ConnectionState.CONNECTED }

    private var isAuthenticated = true
    private var activeSessionId: String? = null
    private var pendingApprovalCard: ApprovalCardDto? = null
    private var currentPlan: StructuredPlanDto = createDefaultMockPlan()

    var shouldSimulateRevocation = false
    var shouldSimulateError = false

    override suspend fun handshake(authToken: String): HandshakeResult {
        delay(simulatedLatencyMs)
        if (shouldSimulateRevocation) {
            _connectionState.value = ConnectionState.REVOKED
            return HandshakeResult(authenticated = false)
        }
        if (shouldSimulateError) {
            _connectionState.value = ConnectionState.ERROR
            return HandshakeResult(authenticated = false)
        }

        return if (authToken.isNotBlank() || initialAuthToken.isNotBlank()) {
            isAuthenticated = true
            _connectionState.value = ConnectionState.CONNECTED
            HandshakeResult(authenticated = true, version = "0.8.3", daemon = "jarvis-daemon-mock")
        } else {
            isAuthenticated = false
            _connectionState.value = ConnectionState.ERROR
            HandshakeResult(authenticated = false)
        }
    }

    override suspend fun heartbeat(): HeartbeatResult {
        delay(simulatedLatencyMs)
        checkAuth()
        return HeartbeatResult(
            status = "ALIVE",
            timestamp = "2026-08-23T09:00:00Z",
            pairedDevices = 1,
            activeSessions = if (activeSessionId != null) 1 else 0
        )
    }

    override suspend fun getStatus(): StatusResult {
        delay(simulatedLatencyMs)
        checkAuth()
        return StatusResult(
            status = "HEALTHY",
            version = "0.8.3",
            agentState = "IDLE",
            activeSessions = if (activeSessionId != null) 1 else 0,
            pendingApprovals = if (pendingApprovalCard != null) 1 else 0,
            pairedDevices = 1,
            activePlans = 1
        )
    }

    override suspend fun createSession(userDisplayName: String): SessionCreateResult {
        delay(simulatedLatencyMs)
        checkAuth()
        val sid = "sess-" + UUID.randomUUID().toString().take(8)
        activeSessionId = sid
        return SessionCreateResult(
            sessionId = sid,
            userDisplayName = userDisplayName,
            createdAt = "2026-08-23T09:00:00Z"
        )
    }

    override suspend fun getSession(sessionId: String): SessionGetResult {
        delay(simulatedLatencyMs)
        checkAuth()
        return SessionGetResult(
            sessionId = sessionId,
            userDisplayName = "Suprith",
            historyLen = 4
        )
    }

    override suspend fun processTurn(query: String, sessionId: String): TurnProcessResult {
        delay(simulatedLatencyMs)
        checkAuth()

        // Sensitive keyword triggers mock approval card
        if (query.contains("delete", ignoreCase = true) || query.contains("send email", ignoreCase = true)) {
            val card = ApprovalCardDto(
                cardId = "card-" + UUID.randomUUID().toString().take(8),
                toolName = "mock_email_sender",
                riskLevel = "HIGH",
                actionType = "EXTERNAL_COMMUNICATION",
                targetResource = "mailto:stakeholder@example.com",
                reasoningSummary = "User requested sending an outbound status email.",
                riskSummary = "Outbound email will be transmitted to external recipient.",
                expiresAt = "2026-08-23T09:10:00Z"
            )
            pendingApprovalCard = card
            return TurnProcessResult(
                sessionId = sessionId,
                reply = "Executing this action requires your explicit human authorization.",
                requiresConfirmation = true,
                approvalCard = card
            )
        }

        return TurnProcessResult(
            sessionId = sessionId,
            reply = "Very good, Sir. I have processed your request: \"$query\". All systems remain fully operational.",
            requiresConfirmation = false,
            approvalCard = null
        )
    }

    override suspend fun respondToApproval(cardId: String, decision: String): ApprovalRespondResult {
        delay(simulatedLatencyMs)
        checkAuth()
        pendingApprovalCard = null
        val executed = decision.equals("APPROVE", ignoreCase = true)
        return ApprovalRespondResult(
            sessionId = activeSessionId ?: "default",
            reply = if (executed) "Action authorized. Tool execution completed successfully in the secure sandbox." else "Action was cancelled per your instruction.",
            toolExecuted = executed
        )
    }

    override suspend fun getLatestProactiveAdvisory(sessionId: String): ProactiveAdvisoryDto {
        delay(simulatedLatencyMs)
        checkAuth()
        return ProactiveAdvisoryDto(
            isInformationalOnly = true,
            isExecutableDirectly = false,
            healthScore = 96.5,
            findingsCount = 1,
            suggestionsCount = 2,
            observations = listOf(
                "Repository test coverage is 100% across all verified phases.",
                "Advisory: No unencrypted secrets found in active memory stores."
            ),
            rawAdvisory = "<proactive_advisory><health_score>96.5</health_score></proactive_advisory>"
        )
    }

    override suspend fun getActivePlan(sessionId: String): StructuredPlanDto? {
        delay(simulatedLatencyMs)
        checkAuth()
        return currentPlan
    }

    override suspend fun updatePlanStep(planId: String, stepNumber: Int, completed: Boolean): PlanUpdateStepResult {
        delay(simulatedLatencyMs)
        checkAuth()
        val updatedMilestones = currentPlan.milestones.map { m ->
            m.copy(steps = m.steps.map { s ->
                if (s.stepNumber == stepNumber) s.copy(isCompleted = completed) else s
            })
        }
        currentPlan = currentPlan.copy(milestones = updatedMilestones)
        return PlanUpdateStepResult(planId = planId, stepNumber = stepNumber, completed = completed)
    }

    override suspend fun emergencyStop(): EmergencyStopResult {
        delay(simulatedLatencyMs)
        pendingApprovalCard = null
        return EmergencyStopResult(status = "STOPPED", revokedApprovals = 1)
    }

    override suspend fun disconnect() {
        delay(simulatedLatencyMs)
        isAuthenticated = false
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    private fun checkAuth() {
        if (!isAuthenticated) {
            throw IllegalStateException("Mock client is not authenticated. Call handshake() first.")
        }
    }

    private fun createDefaultMockPlan(): StructuredPlanDto {
        return StructuredPlanDto(
            planId = "plan-001",
            title = "Phase 8: Android Companion Client Mastery",
            goal = "Develop native Kotlin + Jetpack Compose companion HUD with biometric confirmation.",
            category = "ARCHITECTURE",
            estimatedHours = 12.0,
            isInformationalOnly = true,
            milestones = listOf(
                PlanMilestoneDto(
                    milestoneId = "m1",
                    title = "Scaffolding & Architecture",
                    steps = listOf(
                        PlanStepDto(1, "Create Gradle build scripts", "build.gradle.kts", true),
                        PlanStepDto(2, "Implement JSON-RPC DTOs", "JsonRpcModels.kt", true),
                        PlanStepDto(3, "Implement Android Keystore manager", "KeystoreManager.kt", true)
                    )
                ),
                PlanMilestoneDto(
                    milestoneId = "m2",
                    title = "Stitch Aether HUD & Security",
                    steps = listOf(
                        PlanStepDto(4, "Build Dashboard and Chat screens", "DashboardScreen.kt", true),
                        PlanStepDto(5, "Integrate BiometricPrompt approval dialog", "ApprovalDialog.kt", false)
                    )
                )
            )
        )
    }
}
