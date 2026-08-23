package com.jarvis.assistant

import com.jarvis.assistant.data.model.*
import com.jarvis.assistant.data.remote.MockJarvisIpcClient
import com.jarvis.assistant.data.repository.JarvisRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class JarvisCompanionTest {

    private lateinit var mockClient: MockJarvisIpcClient
    private lateinit var repository: JarvisRepository

    @Before
    fun setUp() {
        mockClient = MockJarvisIpcClient(simulatedLatencyMs = 0L)
        repository = JarvisRepository(mockClient)
    }

    @Test
    fun testHandshakeSuccess() = runBlocking {
        val result = mockClient.handshake("test-token-valid")
        assertTrue(result.authenticated)
        assertEquals("0.8.1", result.version)
    }

    @Test
    fun testHandshakeEmptyTokenFails() = runBlocking {
        val result = mockClient.handshake("")
        assertFalse(result.authenticated)
    }

    @Test
    fun testRepositoryInitialization() = runBlocking {
        val connected = repository.initializeConnection("auth-valid-token")
        assertTrue(connected)
        val status = repository.getStatus()
        assertEquals("HEALTHY", status.status)
        assertEquals("IDLE", status.agentState)
    }

    @Test
    fun testNormalTurnProcessing() = runBlocking {
        repository.initializeConnection("auth-valid-token")
        val result = repository.sendQuery("What is the current system status?")
        assertNotNull(result.reply)
        assertFalse(result.requiresConfirmation)
        assertNull(result.approvalCard)
    }

    @Test
    fun testSensitiveActionTriggersApprovalCard() = runBlocking {
        repository.initializeConnection("auth-valid-token")
        val result = repository.sendQuery("Please send email to client")
        assertTrue(result.requiresConfirmation)
        assertNotNull(result.approvalCard)
        assertEquals("mock_email_sender", result.approvalCard?.toolName)
        assertEquals("HIGH", result.approvalCard?.riskLevel)
    }

    @Test
    fun testApprovalDecisionApprove() = runBlocking {
        repository.initializeConnection("auth-valid-token")
        val turnRes = repository.sendQuery("send email")
        val cardId = turnRes.approvalCard!!.cardId

        val approvalRes = repository.submitApproval(cardId, true)
        assertTrue(approvalRes.toolExecuted)
        assertTrue(approvalRes.reply.contains("authorized"))
    }

    @Test
    fun testApprovalDecisionDeny() = runBlocking {
        repository.initializeConnection("auth-valid-token")
        val turnRes = repository.sendQuery("send email")
        val cardId = turnRes.approvalCard!!.cardId

        val approvalRes = repository.submitApproval(cardId, false)
        assertFalse(approvalRes.toolExecuted)
        assertTrue(approvalRes.reply.contains("cancelled"))
    }

    @Test
    fun testProactiveAdvisoryRetrieval() = runBlocking {
        repository.initializeConnection("auth-valid-token")
        val advisory = repository.getLatestAdvisory()
        assertTrue(advisory.isInformationalOnly)
        assertFalse(advisory.isExecutableDirectly)
        assertEquals(96.5, advisory.healthScore ?: 0.0, 0.01)
        assertTrue(advisory.observations.isNotEmpty())
    }

    @Test
    fun testPlanChecklistStepToggle() = runBlocking {
        repository.initializeConnection("auth-valid-token")
        val plan = repository.refreshActivePlan("sess-test")
        assertNotNull(plan)
        assertEquals("Phase 8: Android Companion Client Mastery", plan?.title)

        // Toggle step 1 to incomplete
        val updateRes = repository.togglePlanStep(plan!!.planId, 1, false)
        assertFalse(updateRes.completed)
    }

    @Test
    fun testEmergencyStop() = runBlocking {
        repository.initializeConnection("auth-valid-token")
        val stopRes = repository.triggerEmergencyStop()
        assertEquals("STOPPED", stopRes.status)
        assertEquals(1, stopRes.revokedApprovals)
    }

    @Test
    fun testDeviceKeyManagerSigning() {
        val keyManager = com.jarvis.assistant.security.StandardDeviceKeyManager()
        val pubKey = keyManager.getPublicKeyHex()
        assertNotNull(pubKey)
        assertEquals(64, pubKey.length)

        val challenge = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        val signature = keyManager.signChallenge(challenge)
        assertNotNull(signature)
        assertEquals(64, signature.length)
    }
}
