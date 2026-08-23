package com.jarvis.assistant.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jarvis.assistant.data.model.*
import com.jarvis.assistant.data.remote.ConnectionState
import com.jarvis.assistant.data.remote.MockJarvisIpcClient
import com.jarvis.assistant.data.repository.JarvisRepository
import com.jarvis.assistant.security.BiometricAuthManager
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class MessageUiModel(
    val role: String, // "user" or "assistant"
    val content: String,
    val timestamp: String = "Just now"
)

enum class CompanionTab {
    DASHBOARD,
    CHAT,
    PROACTIVE,
    PLANS
}

/**
 * Production-Hardened MainViewModel managing Android UI state, HITL approvals,
 * biometric verification, and lifecycle synchronization.
 */
class MainViewModel(
    private val repository: JarvisRepository = JarvisRepository(MockJarvisIpcClient()),
    private val biometricAuthManager: BiometricAuthManager? = null
) : ViewModel() {

    private val _selectedTab = MutableStateFlow(CompanionTab.DASHBOARD)
    val selectedTab: StateFlow<CompanionTab> = _selectedTab.asStateFlow()

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

    private val _status = MutableStateFlow<StatusResult?>(null)
    val status: StateFlow<StatusResult?> = _status.asStateFlow()

    private val _messages = MutableStateFlow<List<MessageUiModel>>(
        listOf(
            MessageUiModel(
                role = "assistant",
                content = "Good day, Sir. JARVIS Android Companion Client initialized and standing by."
            )
        )
    )
    val messages: StateFlow<List<MessageUiModel>> = _messages.asStateFlow()

    private val _pendingApproval = MutableStateFlow<ApprovalCardDto?>(null)
    val pendingApproval: StateFlow<ApprovalCardDto?> = _pendingApproval.asStateFlow()

    private val _proactiveAdvisory = MutableStateFlow<ProactiveAdvisoryDto?>(null)
    val proactiveAdvisory: StateFlow<ProactiveAdvisoryDto?> = _proactiveAdvisory.asStateFlow()

    private val _activePlan = MutableStateFlow<StructuredPlanDto?>(null)
    val activePlan: StateFlow<StructuredPlanDto?> = _activePlan.asStateFlow()

    init {
        viewModelScope.launch {
            repository.connectionState.collect { state ->
                _connectionState.value = state
                _isConnected.value = (state == ConnectionState.CONNECTED)
                if (state == ConnectionState.REVOKED || state == ConnectionState.DISCONNECTED) {
                    _pendingApproval.value = null
                }
            }
        }
        viewModelScope.launch {
            repository.activePlan.collect { plan ->
                _activePlan.value = plan
            }
        }
        connectToDaemon()
    }

    fun selectTab(tab: CompanionTab) {
        _selectedTab.value = tab
    }

    fun connectToDaemon() {
        viewModelScope.launch {
            val success = repository.initializeConnection("companion-auth-token-001")
            _isConnected.value = success
            if (success) {
                refreshAll()
            }
        }
    }

    fun refreshAll() {
        viewModelScope.launch {
            try {
                _status.value = repository.getStatus()
                _proactiveAdvisory.value = repository.getLatestAdvisory()
            } catch (e: Exception) {
                // Fail-closed handling
            }
        }
    }

    fun sendQuery(text: String) {
        if (text.isBlank()) return
        val userMsg = MessageUiModel(role = "user", content = text)
        _messages.value = _messages.value + userMsg

        viewModelScope.launch {
            try {
                val result = repository.sendQuery(text)
                val assistantMsg = MessageUiModel(role = "assistant", content = result.reply)
                _messages.value = _messages.value + assistantMsg

                if (result.requiresConfirmation && result.approvalCard != null) {
                    _pendingApproval.value = result.approvalCard
                }
            } catch (e: Exception) {
                _messages.value = _messages.value + MessageUiModel(
                    role = "assistant",
                    content = "Unable to process query: ${e.message ?: "Network error"}"
                )
            }
        }
    }

    fun handleApproval(cardId: String, approve: Boolean, onAuthFailed: () -> Unit = {}) {
        val currentCard = _pendingApproval.value
        // Guard against stale or mismatched approval card IDs
        if (currentCard == null || currentCard.cardId != cardId) {
            _pendingApproval.value = null
            onAuthFailed()
            return
        }

        if (approve && biometricAuthManager != null && biometricAuthManager.canAuthenticate()) {
            biometricAuthManager.authenticate(
                title = "Authorize Sensitive Tool Execution",
                subtitle = "Confirm execution of ${currentCard.toolName}",
                onSuccess = {
                    submitApprovalInternal(cardId, true)
                },
                onError = { _, _ ->
                    onAuthFailed()
                },
                onFailed = {
                    onAuthFailed()
                }
            )
        } else {
            submitApprovalInternal(cardId, approve)
        }
    }

    private fun submitApprovalInternal(cardId: String, approve: Boolean) {
        viewModelScope.launch {
            try {
                val res = repository.submitApproval(cardId, approve)
                _pendingApproval.value = null
                _messages.value = _messages.value + MessageUiModel(
                    role = "assistant",
                    content = res.reply
                )
            } catch (e: Exception) {
                _pendingApproval.value = null
                _messages.value = _messages.value + MessageUiModel(
                    role = "assistant",
                    content = "Approval submission failed: ${e.message ?: "Network error"}"
                )
            }
        }
    }

    fun togglePlanStep(stepNumber: Int, completed: Boolean) {
        val plan = _activePlan.value ?: return
        viewModelScope.launch {
            try {
                repository.togglePlanStep(plan.planId, stepNumber, completed)
            } catch (e: Exception) {
            }
        }
    }

    fun triggerEmergencyStop() {
        viewModelScope.launch {
            _pendingApproval.value = null
            try {
                val stopRes = repository.triggerEmergencyStop()
                _messages.value = _messages.value + MessageUiModel(
                    role = "assistant",
                    content = "[EMERGENCY STOP TRIGGERED] All active operations and tokens revoked."
                )
                refreshAll()
            } catch (e: Exception) {
                _messages.value = _messages.value + MessageUiModel(
                    role = "assistant",
                    content = "[EMERGENCY STOP LOCAL FAIL-CLOSED] Approvals cleared locally."
                )
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        viewModelScope.launch {
            repository.disconnect()
        }
    }
}
