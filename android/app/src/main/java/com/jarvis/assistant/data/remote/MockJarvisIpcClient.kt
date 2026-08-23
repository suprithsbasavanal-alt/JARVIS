package com.jarvis.assistant.data.remote

import com.jarvis.assistant.data.model.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.UUID

/**
 * Hermetic in-memory mock IPC client implementing the full JARVIS protocol.
 * Used for offline development, previewing, and automated unit testing in Phase 8.1.
 */
class MockJarvisIpcClient(
    private val simulatedLatencyMs: Long = 50L,
    private val initialAuthToken: String = "mock-companion-token-12345"
) : JarvisIpcClient {

    private val _isConnected = MutableStateFlow(true)
    override val isConnected: Flow<Boolean> = _isConnected.asStateFlow()

    private var isAuthenticated = false
    private var activeSessionId: String? = null
    private var pendingApprovalCard: ApprovalCardDto? = null
    private var currentPlan: StructuredPlanDto = createDefaultMockPlan()

    override suspend fun handshake(authToken: String): HandshakeResult {
        delay(simulatedLatencyMs)
        return if (authToken.isNotBlank()) {
            isAuthenticated = true
            _isConnected.value = true
            HandshakeResult(authenticated = true, version = "0.8.1", daemon = "jarvis-daemon-mock")
        } else {
            isAuthenticated = false
            HandshakeResult(authenticated = false)
        }
    }

    override suspend fun getStatus(): StatusResult {
        delay(simulatedLatencyMs)
        checkAuth()
        return StatusResult(
            status = "HEALTHY",
            version = "0.8.1",
            agentState = "IDLE",
            activeSessions = if (activeSessionId != null) 1 else 0,
            pendingApprovals = if (pendingApprovalCard != null) 1 else 0,
            proactiveEvaluations = 12,
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

    override suspend fun getSession(sessionId: String): Map<String, Any> {
        delay(simulatedLatencyMs)
        checkAuth()
        return mapOf(
            "session_id" to sessionId,
            "user_display_name" to "Suprith",
            "history_len" to 4
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
        _isConnected.value = false
        isAuthenticated = false
    }

    private fun checkAuth() {
        if (!isAuthenticated) {
            throw IllegalStateException("Client is unauthenticated. Must execute jarvis.handshake first.")
        }
    }

    private fun createDefaultMockPlan(): StructuredPlanDto {
        return StructuredPlanDto(
            planId = "plan-android-companion-bootstrap",
            title = "Phase 8: Android Companion Client Mastery",
            goal = "Develop native Kotlin Jetpack Compose client with hardware keystore security and real-time synchronization.",
            category = "ENGINEERING_ROADMAP",
            estimatedHours = 12.0,
            isInformationalOnly = true,
            milestones = listOf(
                PlanMilestoneDto(
                    milestoneId = "m1",
                    title = "Phase 8.1: Architecture & Foundation",
                    steps = listOf(
                        PlanStepDto(
                            stepNumber = 1,
                            description = "Scaffold Gradle, Kotlin 1.9, and Jetpack Compose dependencies",
                            deliverable = "android/build.gradle.kts and app module",
                            isCompleted = true
                        ),
                        PlanStepDto(
                            stepNumber = 2,
                            description = "Define JSON-RPC 2.0 DTO contracts for all 10 IPC methods",
                            deliverable = "JsonRpcModels.kt",
                            isCompleted = true
                        ),
                        PlanStepDto(
                            stepNumber = 3,
                            description = "Implement Stitch Aether mobile UI theme and preview dashboard",
                            deliverable = "Theme.kt, DashboardScreen.kt",
                            isCompleted = true
                        )
                    )
                ),
                PlanMilestoneDto(
                    milestoneId = "m2",
                    title = "Phase 8.2: Hardware Security & Local Transport",
                    steps = listOf(
                        PlanStepDto(
                            stepNumber = 4,
                            description = "Integrate Android Keystore StrongBox key generation",
                            deliverable = "KeystoreManager.kt",
                            isCompleted = false
                        ),
                        PlanStepDto(
                            stepNumber = 5,
                            description = "Implement BiometricPrompt gate for HITL sensitive approvals",
                            deliverable = "BiometricAuthManager.kt",
                            isCompleted = false
                        )
                    )
                )
            )
        )
    }
}
