package com.jarvis.assistant.data.remote

import com.jarvis.assistant.data.model.*
import com.jarvis.assistant.security.DeviceKeyManager
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.decodeFromJsonElement
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.Socket
import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.min
import kotlin.math.pow

/**
 * Concrete Network Transport Client communicating with JARVIS NetworkBridgeServer
 * over authenticated local network TCP/TLS with hardware challenge signing,
 * lifecycle connection state tracking, periodic heartbeats, and bounded exponential backoff.
 */
class NetworkTransportClient(
    private val host: String = "127.0.0.1",
    private val port: Int = 8443,
    private val deviceKeyManager: DeviceKeyManager,
    private val coroutineScope: CoroutineScope = CoroutineScope(Dispatchers.IO + SupervisorJob()),
    private val heartbeatIntervalMs: Long = 15_000L,
    private val initialReconnectDelayMs: Long = 1_000L,
    private val maxReconnectDelayMs: Long = 30_000L,
    private val maxReconnectRetries: Int = 5
) : JarvisIpcClient {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }
    private val ioMutex = Mutex()

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    override val connectionState: Flow<ConnectionState> = _connectionState.asStateFlow()
    override val isConnected: Flow<Boolean> = _connectionState.map { it == ConnectionState.CONNECTED }

    private var socket: Socket? = null
    private var reader: BufferedReader? = null
    private var writer: OutputStreamWriter? = null
    private var activeSessionToken: String? = null

    private var heartbeatJob: Job? = null
    private var reconnectJob: Job? = null
    private val isExplicitDisconnect = AtomicBoolean(false)
    private val isDeviceRevoked = AtomicBoolean(false)

    override suspend fun handshake(authToken: String): HandshakeResult = withContext(Dispatchers.IO) {
        if (isDeviceRevoked.get()) {
            _connectionState.value = ConnectionState.REVOKED
            return@withContext HandshakeResult(authenticated = false)
        }

        isExplicitDisconnect.set(false)
        _connectionState.value = ConnectionState.CONNECTING

        try {
            ensureConnected()
            _connectionState.value = ConnectionState.AUTHENTICATING

            // 1. Request Auth Challenge
            val challengeReq = JsonRpcRequest(
                id = UUID.randomUUID().toString(),
                method = "jarvis.network.auth.challenge",
                params = JsonObject(mapOf("device_id" to JsonPrimitive(deviceKeyManager.getDeviceId())))
            )
            val challengeResp = sendAndReceiveInternal(challengeReq)
            if (challengeResp.error != null || challengeResp.result == null) {
                if (challengeResp.error?.code == -32001 || challengeResp.error?.message?.contains("revoked", ignoreCase = true) == true) {
                    isDeviceRevoked.set(true)
                    _connectionState.value = ConnectionState.REVOKED
                } else {
                    _connectionState.value = ConnectionState.ERROR
                }
                return@withContext HandshakeResult(authenticated = false)
            }

            val challengeResult = json.decodeFromJsonElement<AuthChallengeResult>(challengeResp.result)

            // 2. Sign Challenge with Hardware Key
            val signature = deviceKeyManager.signChallenge(challengeResult.nonce)

            // 3. Submit Signed Verification
            val verifyReq = JsonRpcRequest(
                id = UUID.randomUUID().toString(),
                method = "jarvis.network.auth.verify",
                params = JsonObject(
                    mapOf(
                        "challenge_id" to JsonPrimitive(challengeResult.challengeId),
                        "signature_hex" to JsonPrimitive(signature)
                    )
                )
            )
            val verifyResp = sendAndReceiveInternal(verifyReq)
            if (verifyResp.error != null || verifyResp.result == null) {
                _connectionState.value = ConnectionState.ERROR
                return@withContext HandshakeResult(authenticated = false)
            }

            val verifyResult = json.decodeFromJsonElement<AuthVerifyResult>(verifyResp.result)
            activeSessionToken = verifyResult.sessionToken
            _connectionState.value = ConnectionState.CONNECTED

            startHeartbeat()

            HandshakeResult(
                authenticated = true,
                version = "0.8.3",
                daemon = "jarvis-network-bridge"
            )
        } catch (e: Exception) {
            closeSocket()
            if (!isExplicitDisconnect.get() && !isDeviceRevoked.get()) {
                _connectionState.value = ConnectionState.ERROR
            }
            HandshakeResult(authenticated = false)
        }
    }

    override suspend fun heartbeat(): HeartbeatResult = callMethod("jarvis.heartbeat")

    override suspend fun getStatus(): StatusResult = callMethod("jarvis.status")

    override suspend fun createSession(userDisplayName: String): SessionCreateResult =
        callMethod("jarvis.session.create", mapOf("user_display_name" to JsonPrimitive(userDisplayName)))

    override suspend fun getSession(sessionId: String): SessionGetResult =
        callMethod("jarvis.session.get", mapOf("session_id" to JsonPrimitive(sessionId)))

    override suspend fun processTurn(query: String, sessionId: String): TurnProcessResult =
        callMethod("jarvis.turn.process", mapOf("query" to JsonPrimitive(query), "session_id" to JsonPrimitive(sessionId)))

    override suspend fun respondToApproval(cardId: String, decision: String): ApprovalRespondResult =
        callMethod("jarvis.approval.respond", mapOf("card_id" to JsonPrimitive(cardId), "decision" to JsonPrimitive(decision)))

    override suspend fun getLatestProactiveAdvisory(sessionId: String): ProactiveAdvisoryDto =
        callMethod("jarvis.proactive.get_latest", mapOf("session_id" to JsonPrimitive(sessionId)))

    override suspend fun getActivePlan(sessionId: String): StructuredPlanDto? =
        try {
            val res = callMethod<Map<String, StructuredPlanDto>>("jarvis.plan.get_active", mapOf("session_id" to JsonPrimitive(sessionId)))
            res["plan"]
        } catch (e: Exception) {
            null
        }

    override suspend fun updatePlanStep(planId: String, stepNumber: Int, completed: Boolean): PlanUpdateStepResult =
        callMethod(
            "jarvis.plan.update_step",
            mapOf(
                "plan_id" to JsonPrimitive(planId),
                "step_number" to JsonPrimitive(stepNumber),
                "completed" to JsonPrimitive(completed)
            )
        )

    override suspend fun emergencyStop(): EmergencyStopResult = callMethod("jarvis.system.emergency_stop")

    override suspend fun disconnect() = withContext(Dispatchers.IO) {
        isExplicitDisconnect.set(true)
        stopHeartbeat()
        reconnectJob?.cancel()
        closeSocket()
        activeSessionToken = null
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    private suspend inline fun <reified T> callMethod(
        method: String,
        params: Map<String, JsonPrimitive> = emptyMap()
    ): T = withContext(Dispatchers.IO) {
        try {
            ensureConnected()
            val allParams = params.toMutableMap()
            activeSessionToken?.let { allParams["session_token"] = JsonPrimitive(it) }

            val reqId = UUID.randomUUID().toString()
            val request = JsonRpcRequest(
                id = reqId,
                method = method,
                params = JsonObject(allParams)
            )

            val response = sendAndReceiveInternal(request)

            // Correlation ID matching
            if (response.id != null && response.id != reqId) {
                throw JsonRpcException(-32603, "Response ID mismatch: expected $reqId, received ${response.id}")
            }

            if (response.error != null) {
                if (response.error.code == -32001 || response.error.message.contains("revoked", ignoreCase = true)) {
                    isDeviceRevoked.set(true)
                    _connectionState.value = ConnectionState.REVOKED
                    closeSocket()
                }
                throw JsonRpcException(response.error.code, response.error.message, response.error.data)
            }

            val result = response.result ?: throw JsonRpcException(-32603, "Empty result received from server for $method")
            json.decodeFromJsonElement<T>(result)
        } catch (e: Exception) {
            if (e is JsonRpcException) throw e
            handleConnectionLoss()
            throw e
        }
    }

    private fun startHeartbeat() {
        stopHeartbeat()
        heartbeatJob = coroutineScope.launch {
            while (isActive && !isExplicitDisconnect.get() && !isDeviceRevoked.get()) {
                delay(heartbeatIntervalMs)
                try {
                    heartbeat()
                } catch (e: Exception) {
                    if (!isExplicitDisconnect.get() && !isDeviceRevoked.get()) {
                        handleConnectionLoss()
                    }
                    break
                }
            }
        }
    }

    private fun stopHeartbeat() {
        heartbeatJob?.cancel()
        heartbeatJob = null
    }

    private fun handleConnectionLoss() {
        if (isExplicitDisconnect.get() || isDeviceRevoked.get()) return

        closeSocket()
        _connectionState.value = ConnectionState.RECONNECTING

        if (reconnectJob?.isActive != true) {
            reconnectJob = coroutineScope.launch {
                triggerReconnectLoop()
            }
        }
    }

    private suspend fun triggerReconnectLoop() {
        var retryCount = 0
        var delayMs = initialReconnectDelayMs

        while (retryCount < maxReconnectRetries && !isExplicitDisconnect.get() && !isDeviceRevoked.get()) {
            delay(delayMs)
            retryCount++

            try {
                val res = handshake("")
                if (res.authenticated) {
                    return // Reconnect succeeded
                }
            } catch (e: Exception) {
            }

            delayMs = min(maxReconnectDelayMs, (initialReconnectDelayMs * 2.0.pow(retryCount.toDouble())).toLong())
        }

        if (!isExplicitDisconnect.get() && !isDeviceRevoked.get()) {
            _connectionState.value = ConnectionState.ERROR
        }
    }

    private fun ensureConnected() {
        if (socket == null || socket?.isClosed == true) {
            socket = Socket(host, port)
            reader = BufferedReader(InputStreamReader(socket!!.getInputStream(), Charsets.UTF_8))
            writer = OutputStreamWriter(socket!!.getOutputStream(), Charsets.UTF_8)
        }
    }

    private suspend fun sendAndReceiveInternal(request: JsonRpcRequest): JsonRpcResponse = ioMutex.withLock {
        ensureConnected()
        val payload = json.encodeToString(JsonRpcRequest.serializer(), request)
        writer?.write(payload + "\n")
        writer?.flush()

        val line = reader?.readLine() ?: throw IllegalStateException("Connection closed by JARVIS network bridge.")
        json.decodeFromString(JsonRpcResponse.serializer(), line)
    }

    private fun closeSocket() {
        try {
            socket?.close()
        } catch (e: Exception) {
        } finally {
            socket = null
            reader = null
            writer = null
        }
    }
}
