package ai.my.glasses.net

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.security.MessageDigest
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLException
import javax.net.ssl.X509TrustManager

/**
 * HTTP client for /api/wearables/v1 (contract: docs/wearables/openapi.yaml).
 * Holds no UI state; credential comes from CredentialStore per call so
 * revocation/re-pairing needs no client rebuild.
 *
 * TLS: the my.ai LAN proxy uses a self-signed cert, which Android rejects
 * ("Trust anchor not found" — crashed pairing live, 2026-07-12). The pairing
 * payload carries the cert's SHA-256; when present we pin exactly that cert
 * (leaf fingerprint match, hostname redundant) instead of the system roots.
 */
class GatewayClient(
    private val baseUrl: () -> String,          // e.g. https://192.168.1.20:7001
    private val token: () -> String?,           // ody_… or null before pairing
    private val certSha256: () -> String? = { null }, // pinned cert or null
) {
    private val plainHttp = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.MILLISECONDS)  // SSE streams stay open
        .build()

    private var pinnedFp: String? = null
    private var pinnedHttp: OkHttpClient? = null

    private fun clientFor(fp: String?): OkHttpClient {
        if (fp.isNullOrBlank()) return plainHttp
        synchronized(this) {
            pinnedHttp?.let { if (pinnedFp == fp) return it }
            val tm = object : X509TrustManager {
                override fun checkClientTrusted(
                    chain: Array<X509Certificate>?, authType: String?,
                ) = throw CertificateException("client certificates unsupported")

                override fun checkServerTrusted(
                    chain: Array<X509Certificate>?, authType: String?,
                ) {
                    val leaf = chain?.firstOrNull()
                        ?: throw CertificateException("empty certificate chain")
                    val hex = MessageDigest.getInstance("SHA-256")
                        .digest(leaf.encoded)
                        .joinToString("") { "%02x".format(it) }
                    if (!hex.equals(fp, ignoreCase = true)) {
                        throw CertificateException("certificate fingerprint mismatch")
                    }
                }

                override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
            }
            val ctx = SSLContext.getInstance("TLS")
            ctx.init(null, arrayOf(tm), null)
            val client = plainHttp.newBuilder()
                .sslSocketFactory(ctx.socketFactory, tm)
                // Identity is the pinned key itself, stronger than a hostname
                // match — and the LAN IP may change while the cert does not.
                .hostnameVerifier { _, _ -> true }
                .build()
            pinnedFp = fp
            pinnedHttp = client
            return client
        }
    }

    private fun http(): OkHttpClient = clientFor(certSha256())

    private fun req(path: String): Request.Builder {
        val b = Request.Builder().url(baseUrl().trimEnd('/') + "/api/wearables/v1" + path)
        token()?.let { b.header("Authorization", "Bearer $it") }
        return b
    }

    private val jsonType = "application/json".toMediaType()

    /** Enrollment: exchange a scanned pairing code. No token yet — the pin
     *  comes from the payload, not the credential store. Never throws: a
     *  network/TLS failure is a UI state, not a crash (learned live). */
    suspend fun pair(
        host: String, code: String, deviceName: String,
        pinSha256: String? = null,
    ): PairResult = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("code", code).put("device_name", deviceName)
            .toString().toRequestBody(jsonType)
        val request = Request.Builder()
            .url(host.trimEnd('/') + "/api/wearables/v1/pair")
            .post(body).build()
        runCatching {
            clientFor(pinSha256).newCall(request).execute().use { resp ->
                val obj = JSONObject(resp.body?.string() ?: "{}")
                if (resp.isSuccessful) {
                    PairResult.Success(obj.getString("token"), obj.getString("token_id"),
                        obj.optString("owner"))
                } else {
                    PairResult.Failure(obj.optJSONObject("detail")
                        ?.optString("code") ?: "PAIRING_CODE_INVALID")
                }
            }
        }.getOrElse { e ->
            PairResult.Failure(
                if (e is SSLException || e.cause is SSLException) "TLS_UNTRUSTED"
                else "MYAI_HOST_UNREACHABLE"
            )
        }
    }

    suspend fun health(): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            http().newCall(req("/health").get().build()).execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }

    suspend fun capabilities(): JSONObject? = withContext(Dispatchers.IO) {
        runCatching {
            http().newCall(req("/capabilities").get().build()).execute().use {
                if (it.isSuccessful) JSONObject(it.body?.string() ?: "{}") else null
            }
        }.getOrNull()
    }

    // ── Productivity + history (owner-scoped previews / quick-add) ─────────
    private suspend fun getArray(path: String, key: String): List<JSONObject> =
        withContext(Dispatchers.IO) {
            runCatching {
                http().newCall(req(path).get().build()).execute().use { resp ->
                    if (!resp.isSuccessful) return@use emptyList<JSONObject>()
                    val arr = JSONObject(resp.body?.string() ?: "{}").optJSONArray(key)
                        ?: return@use emptyList<JSONObject>()
                    (0 until arr.length()).map { arr.getJSONObject(it) }
                }
            }.getOrDefault(emptyList())
        }

    private suspend fun post(path: String, body: JSONObject): Boolean =
        withContext(Dispatchers.IO) {
            runCatching {
                http().newCall(req(path).post(body.toString().toRequestBody(jsonType)).build())
                    .execute().use { it.isSuccessful }
            }.getOrDefault(false)
        }

    suspend fun notes(): List<NoteItem> = getArray("/notes", "notes").map {
        NoteItem(it.optString("id"), it.optString("title"), it.optString("snippet"))
    }

    suspend fun addNote(title: String, content: String): Boolean =
        post("/notes", JSONObject().put("title", title).put("content", content))

    suspend fun tasks(): List<TaskItem> = getArray("/tasks", "tasks").map {
        TaskItem(it.optString("id"), it.optString("title"),
            it.optString("due_date").takeIf { d -> d.isNotBlank() && d != "null" },
            it.optInt("done"), it.optInt("total"), it.optBoolean("completed"))
    }

    suspend fun addTask(text: String): Boolean =
        post("/tasks", JSONObject().put("text", text))

    /** Toggle a note/task between completed and active — the host flips its done
     *  state and keeps it in the list (greyed while completed). */
    suspend fun completeItem(id: String): Boolean = post("/items/$id/done", JSONObject())

    /** Remove a note/task entirely (owner-scoped hard delete on the host). */
    suspend fun deleteItem(id: String): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            http().newCall(req("/items/$id").delete().build())
                .execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }

    suspend fun chatHistory(): List<ChatItem> = getArray("/history/chats", "chats").map {
        ChatItem(it.optString("id"), it.optString("name"), it.optInt("messages"))
    }

    suspend fun visionHistory(): List<VisionItem> = getArray("/history/vision", "vision").map {
        VisionItem(it.optString("id"), it.optString("question"), it.optString("answer"))
    }

    /** Streamed conversation turn. Emits GatewayEvents until StreamEnd. */
    fun respond(text: String, sessionId: String?, storeTranscript: Boolean): Flow<GatewayEvent> =
        callbackFlow {
            val payload = JSONObject().put("text", text)
                .put("store_transcript", storeTranscript)
            sessionId?.let { payload.put("session_id", it) }
            val call = http().newCall(
                req("/respond").post(payload.toString().toRequestBody(jsonType)).build())
            val parser = SseParser()
            try {
                call.execute().use { resp ->
                    if (!resp.isSuccessful) {
                        val code = runCatching {
                            JSONObject(resp.body?.string() ?: "{}")
                                .optJSONObject("detail")?.optString("code")
                        }.getOrNull()
                        trySend(GatewayEvent.Error(code ?: httpFallback(resp.code), ""))
                        trySend(GatewayEvent.StreamEnd)
                        return@use
                    }
                    // Read UTF-8 line by line via OkHttp's BufferedSource, which
                    // decodes whole codepoints. The old `String(buf, 0, n)` with
                    // the default charset corrupted any multibyte character
                    // (emoji, non-Latin script) that straddled the 8 KB read
                    // boundary. readUtf8Line strips the newline, so re-add "\n"
                    // to keep the SSE frame separator ("\n\n") intact for the parser.
                    val source = resp.body!!.source()
                    while (true) {
                        val line = source.readUtf8Line() ?: break
                        parser.feed(line + "\n").forEach { trySend(it) }
                    }
                }
            } catch (e: Exception) {
                trySend(GatewayEvent.Error("MYAI_HOST_UNREACHABLE", e.message ?: ""))
            } finally {
                trySend(GatewayEvent.StreamEnd)
                close()
            }
            awaitClose { call.cancel() } // dropping the collector cancels server-side
        }.flowOn(Dispatchers.IO)

    suspend fun cancel(sessionId: String): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            http().newCall(req("/session/$sessionId/cancel")
                .post(ByteArray(0).toRequestBody(null)).build())
                .execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }

    suspend fun deleteSession(sessionId: String): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            http().newCall(req("/session/$sessionId").delete().build())
                .execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }

    suspend fun transcribe(wavBytes: ByteArray): TranscribeResult = withContext(Dispatchers.IO) {
        val body = MultipartBody.Builder().setType(MultipartBody.FORM)
            .addFormDataPart("file", "utterance.wav",
                wavBytes.toRequestBody("audio/wav".toMediaType()))
            .build()
        runCatching {
            http().newCall(req("/transcribe").post(body).build()).execute().use { resp ->
                val obj = JSONObject(resp.body?.string() ?: "{}")
                if (resp.isSuccessful) {
                    TranscribeResult.Success(obj.optString("text"), obj.optBoolean("empty"))
                } else TranscribeResult.Failure(obj.optJSONObject("detail")
                    ?.optString("code") ?: httpFallback(resp.code))
            }
        }.getOrElse { TranscribeResult.Failure("MYAI_HOST_UNREACHABLE") }
    }

    /** Returns audio bytes (mp3/wav) or null with errorCode set via callback. */
    suspend fun speech(text: String): ByteArray? = withContext(Dispatchers.IO) {
        runCatching {
            val payload = JSONObject().put("text", text).put("transform", true)
            http().newCall(req("/speech").post(payload.toString().toRequestBody(jsonType)).build())
                .execute().use { if (it.isSuccessful) it.body?.bytes() else null }
        }.getOrNull()
    }

    suspend fun visionQuery(jpeg: ByteArray, question: String): VisionResult =
        withContext(Dispatchers.IO) {
            val body = MultipartBody.Builder().setType(MultipartBody.FORM)
                .addFormDataPart("image", "look.jpg",
                    jpeg.toRequestBody("image/jpeg".toMediaType()))
                .addFormDataPart("question", question)
                .build()
            runCatching {
                http().newCall(req("/vision/query").post(body).build()).execute().use { resp ->
                    val obj = JSONObject(resp.body?.string() ?: "{}")
                    if (resp.isSuccessful) {
                        VisionResult.Success(obj.optString("text"), obj.optString("spoken"),
                            obj.optString("model"))
                    } else VisionResult.Failure(obj.optJSONObject("detail")
                        ?.optString("code") ?: httpFallback(resp.code))
                }
            }.getOrElse { VisionResult.Failure("MYAI_HOST_UNREACHABLE") }
        }

    /** Preload the vision model so the first Look-and-Ask doesn't cold-load.
     *  Best-effort + fire-and-forget: returns true if the host reports it warmed. */
    suspend fun warmVision(): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            http().newCall(req("/vision/warm")
                .post(ByteArray(0).toRequestBody(null)).build())
                .execute().use { resp ->
                    resp.isSuccessful &&
                        JSONObject(resp.body?.string() ?: "{}").optBoolean("warmed")
                }
        }.getOrDefault(false)
    }

    /** Streaming Look-and-Ask: image (+ optional spoken question) → the SAME
     *  GatewayEvent stream as [respond], so TTS can start on the first spoken
     *  sentence instead of waiting for the whole answer. */
    fun visionStream(jpeg: ByteArray, question: String): Flow<GatewayEvent> =
        callbackFlow {
            val body = MultipartBody.Builder().setType(MultipartBody.FORM)
                .addFormDataPart("image", "look.jpg",
                    jpeg.toRequestBody("image/jpeg".toMediaType()))
                .addFormDataPart("question", question)
                .build()
            val call = http().newCall(req("/vision/stream").post(body).build())
            val parser = SseParser()
            try {
                call.execute().use { resp ->
                    if (!resp.isSuccessful) {
                        val code = runCatching {
                            JSONObject(resp.body?.string() ?: "{}")
                                .optJSONObject("detail")?.optString("code")
                        }.getOrNull()
                        trySend(GatewayEvent.Error(code ?: httpFallback(resp.code), ""))
                        trySend(GatewayEvent.StreamEnd)
                        return@use
                    }
                    val source = resp.body!!.source()
                    while (true) {
                        val line = source.readUtf8Line() ?: break
                        parser.feed(line + "\n").forEach { trySend(it) }
                    }
                }
            } catch (e: Exception) {
                trySend(GatewayEvent.Error("MYAI_HOST_UNREACHABLE", e.message ?: ""))
            } finally {
                trySend(GatewayEvent.StreamEnd)
                close()
            }
            awaitClose { call.cancel() } // dropping the collector cancels server-side
        }.flowOn(Dispatchers.IO)

    private fun httpFallback(code: Int) = when (code) {
        400 -> "BAD_REQUEST"
        401 -> "AUTHENTICATION_REQUIRED"
        403 -> "DEVICE_CREDENTIAL_REVOKED"
        404 -> "SESSION_NOT_FOUND"
        408, 504 -> "REQUEST_TIMEOUT"
        413 -> "PAYLOAD_TOO_LARGE"
        429 -> "RATE_LIMITED"
        else -> "MYAI_HOST_UNREACHABLE"
    }
}

sealed interface PairResult {
    data class Success(val token: String, val tokenId: String, val owner: String) : PairResult
    data class Failure(val code: String) : PairResult
}

sealed interface TranscribeResult {
    data class Success(val text: String, val empty: Boolean) : TranscribeResult
    data class Failure(val code: String) : TranscribeResult
}

sealed interface VisionResult {
    data class Success(val text: String, val spoken: String, val model: String) : VisionResult
    data class Failure(val code: String) : VisionResult
}

// ── Productivity + history preview models ──────────────────────────────────
data class NoteItem(val id: String, val title: String, val snippet: String)
data class TaskItem(
    val id: String, val title: String, val dueDate: String?,
    val done: Int, val total: Int, val completed: Boolean = false,
)
data class ChatItem(val id: String, val name: String, val messages: Int)
data class VisionItem(val id: String, val question: String, val answer: String)
