package com.jarvis.assistant.data.remote

import com.jarvis.assistant.data.model.*
import com.jarvis.assistant.security.DeviceKeyManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.decodeFromJsonElement
import kotlinx.serialization.json.encodeToJsonElement
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.Socket
import java.util.UUID

/**
 * Concrete Network Transport Client communicating with JARVIS NetworkBridgeServer
 * over authenticated local network TCP/TLS with hardware challenge signing.
 */
class NetworkTransportClient(
    private val host: String = "127.0.0.1",
    private val port: Int = 8443,
    private val deviceKeyManager: DeviceKeyManager
) : JarvisIpcClient {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }
    private val _isConnected = MutableStateFlow(false)
    override val isConnected: Flow<Boolean> = _isConnected.asStateFlow()

    private var socket: Socket? = null
    private var reader: BufferedReader? = null
    private var writer: OutputStreamWriter? = null
    private var activeSessionToken: String? = null

    override suspend fun handshake(authToken: String): HandshakeResult = withContext(Dispatchers.IO) {
        try {
            ensureConnected()

            // 1. Request Auth Challenge
            val challengeReq = JsonRpcRequest(
                id = UUID.randomUUID().toString(),
                method = "jarvis.network.auth.challenge",
                params = JsonObject(mapOf("device_id" to JsonPrimitive(deviceKeyManager.getDeviceId())))
            )
            val challengeResp = sendAndReceive(challengeReq)
            if (challengeResp.error != null || challengeResp.result == null) {
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
            val verifyResp = sendAndReceive(verifyReq)
            if (verifyResp.error != null || verifyResp.result == null) {
                return@withContext HandshakeResult(authenticated = false)
            }

            val verifyResult = json.decodeFromJsonElement<AuthVerifyResult>(verifyResp.result)
            activeSessionToken = verifyResult.sessionToken
            _isConnected.value = true

            HandshakeResult(
                authenticated = true,
                version = "0.8.2",
                daemon = "jarvis-network-bridge"
            )
        } catch (e: Exception) {
            _isConnected.value = false
            HandshakeResult(authenticated = false)
        }
    }

    override suspend fun getStatus(): StatusResult = callMethod("jarvis.status")

    override suspend fun createSession(userDisplayName: String): SessionCreateResult =
        callMethod("jarvis.session.create", mapOf("user_display_name" to JsonPrimitive(userDisplayName)))

    override suspend fun getSession(sessionId: String): Map<String, Any> =
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
        try {
            socket?.close()
        } catch (e: Exception) {
        } finally {
            socket = null
            reader = null
            writer = null
            activeSessionToken = null
            _isConnected.value = false
        }
    }

    private suspend inline fun <reified T> callMethod(
        method: String,
        params: Map<String, JsonPrimitive> = emptyMap()
    ): T = withContext(Dispatchers.IO) {
        ensureConnected()
        val allParams = params.toMutableMap()
        activeSessionToken?.let { allParams["session_token"] = JsonPrimitive(it) }

        val request = JsonRpcRequest(
            id = UUID.randomUUID().toString(),
            method = method,
            params = JsonObject(allParams)
        )
        val response = sendAndReceive(request)
        if (response.error != null) {
            throw IllegalStateException("JSON-RPC Error ${response.error.code}: ${response.error.message}")
        }
        val result = response.result ?: throw IllegalStateException("Empty result from $method")
        json.decodeFromJsonElement<T>(result)
    }

    private fun ensureConnected() {
        if (socket == null || socket?.isClosed == true) {
            socket = Socket(host, port)
            reader = BufferedReader(InputStreamReader(socket!!.getInputStream(), Charsets.UTF_8))
            writer = OutputStreamWriter(socket!!.getOutputStream(), Charsets.UTF_8)
        }
    }

    private fun sendAndReceive(request: JsonRpcRequest): JsonRpcResponse {
        val payload = json.encodeToString(JsonRpcRequest.serializer(), request)
        writer?.write(payload + "\n")
        writer?.flush()

        val line = reader?.readLine() ?: throw IllegalStateException("Connection closed by JARVIS network bridge.")
        return json.decodeFromString(JsonRpcResponse.serializer(), line)
    }
}
