package com.jarvis.assistant.data.repository

import com.jarvis.assistant.data.model.*
import com.jarvis.assistant.data.remote.JarvisIpcClient
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Repository layer managing local session state, connection lifecycle, and DTO caching.
 */
class JarvisRepository(
    private val ipcClient: JarvisIpcClient
) {
    val isConnected: Flow<Boolean> = ipcClient.isConnected

    private val _currentSession = MutableStateFlow<SessionCreateResult?>(null)
    val currentSession: Flow<SessionCreateResult?> = _currentSession.asStateFlow()

    private val _activePlan = MutableStateFlow<StructuredPlanDto?>(null)
    val activePlan: Flow<StructuredPlanDto?> = _activePlan.asStateFlow()

    suspend fun initializeConnection(authToken: String): Boolean {
        val result = ipcClient.handshake(authToken)
        if (result.authenticated) {
            val session = ipcClient.createSession("Suprith")
            _currentSession.value = session
            refreshActivePlan(session.sessionId)
            return true
        }
        return false
    }

    suspend fun getStatus(): StatusResult {
        return ipcClient.getStatus()
    }

    suspend fun sendQuery(query: String): TurnProcessResult {
        val session = _currentSession.value ?: throw IllegalStateException("No active session")
        return ipcClient.processTurn(query, session.sessionId)
    }

    suspend fun submitApproval(cardId: String, approved: Boolean): ApprovalRespondResult {
        val decision = if (approved) "APPROVE" else "DENY"
        return ipcClient.respondToApproval(cardId, decision)
    }

    suspend fun getLatestAdvisory(): ProactiveAdvisoryDto {
        val session = _currentSession.value ?: throw IllegalStateException("No active session")
        return ipcClient.getLatestProactiveAdvisory(session.sessionId)
    }

    suspend fun refreshActivePlan(sessionId: String): StructuredPlanDto? {
        val plan = ipcClient.getActivePlan(sessionId)
        _activePlan.value = plan
        return plan
    }

    suspend fun togglePlanStep(planId: String, stepNumber: Int, completed: Boolean): PlanUpdateStepResult {
        val res = ipcClient.updatePlanStep(planId, stepNumber, completed)
        _currentSession.value?.let { refreshActivePlan(it.sessionId) }
        return res
    }

    suspend fun triggerEmergencyStop(): EmergencyStopResult {
        return ipcClient.emergencyStop()
    }
}
