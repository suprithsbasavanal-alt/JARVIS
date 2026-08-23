package com.jarvis.assistant.data.remote

import com.jarvis.assistant.data.model.*
import kotlinx.coroutines.flow.Flow

/**
 * Interface defining the asynchronous JSON-RPC 2.0 transport contract
 * between the Android Companion Client and the JARVIS backend.
 */
interface JarvisIpcClient {
    val isConnected: Flow<Boolean>

    suspend fun handshake(authToken: String): HandshakeResult
    suspend fun getStatus(): StatusResult
    suspend fun createSession(userDisplayName: String = "Suprith"): SessionCreateResult
    suspend fun getSession(sessionId: String): Map<String, Any>
    suspend fun processTurn(query: String, sessionId: String): TurnProcessResult
    suspend fun respondToApproval(cardId: String, decision: String): ApprovalRespondResult
    suspend fun getLatestProactiveAdvisory(sessionId: String): ProactiveAdvisoryDto
    suspend fun getActivePlan(sessionId: String): StructuredPlanDto?
    suspend fun updatePlanStep(planId: String, stepNumber: Int, completed: Boolean): PlanUpdateStepResult
    suspend fun emergencyStop(): EmergencyStopResult
    suspend fun disconnect()
}
