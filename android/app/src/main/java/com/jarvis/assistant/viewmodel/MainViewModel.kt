package com.jarvis.assistant.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.jarvis.assistant.data.model.*
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

class MainViewModel(
    private val repository: JarvisRepository = JarvisRepository(MockJarvisIpcClient()),
    private val biometricAuthManager: BiometricAuthManager? = null
) : ViewModel() {

    private val _selectedTab = MutableStateFlow(CompanionTab.DASHBOARD)
    val selectedTab: StateFlow<CompanionTab> = _selectedTab.asStateFlow()

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
                repository.currentSession
                // Plan is refreshed in repository
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
                    content = "Error communicating with JARVIS core: ${e.message}"
                )
            }
        }
    }

    fun handleApprovalDecision(cardId: String, approved: Boolean) {
        if (approved && biometricAuthManager != null) {
            biometricAuthManager.authenticate(
                onSuccess = { submitApprovalInternal(cardId, true) },
                onError = { _, _ -> submitApprovalInternal(cardId, false) },
                onFailed = { submitApprovalInternal(cardId, false) }
            )
        } else {
            submitApprovalInternal(cardId, approved)
        }
    }

    private fun submitApprovalInternal(cardId: String, approved: Boolean) {
        viewModelScope.launch {
            try {
                val res = repository.submitApproval(cardId, approved)
                _pendingApproval.value = null
                _messages.value = _messages.value + MessageUiModel(
                    role = "assistant",
                    content = res.reply
                )
            } catch (e: Exception) {
                _pendingApproval.value = null
            }
        }
    }

    fun toggleStep(planId: String, stepNumber: Int, currentCompleted: Boolean) {
        viewModelScope.launch {
            try {
                repository.togglePlanStep(planId, stepNumber, !currentCompleted)
                // update local state
                _activePlan.value?.let { plan ->
                    val updated = plan.copy(
                        milestones = plan.milestones.map { m ->
                            m.copy(steps = m.steps.map { s ->
                                if (s.stepNumber == stepNumber) s.copy(isCompleted = !currentCompleted) else s
                            })
                        }
                    )
                    _activePlan.value = updated
                }
            } catch (e: Exception) {
                // Ignore or reload
            }
        }
    }

    fun triggerEmergencyStop() {
        viewModelScope.launch {
            try {
                val res = repository.triggerEmergencyStop()
                _pendingApproval.value = null
                _messages.value = _messages.value + MessageUiModel(
                    role = "assistant",
                    content = "EMERGENCY STOP TRIGGERED: Revoked ${res.revokedApprovals} pending authorizations."
                )
            } catch (e: Exception) {
                // Emergency stop failed
            }
        }
    }
}
