package ai.my.glasses.net

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.security.MessageDigest
import java.security.cert.X509Certificate
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLContext
import javax.net.ssl.X509TrustManager

/** A my.ai host found on the LAN via its /discover beacon. */
data class DiscoveredHost(
    val name: String,
    val host: String,
    val port: Int,
    val tls: Boolean,
    /** Leaf cert fingerprint captured from the discovery handshake — the pin
     *  used for the (pinned) enroll calls, and stored on success. */
    val certSha256: String?,
    /** A stable host to PERSIST instead of the scanned one (e.g. the host's
     *  Tailscale IP), so the paired app works from any network. Null → use the
     *  discovered address. */
    val persistHost: String? = null,
    val persistPort: Int? = null,
) {
    private val scheme get() = if (tls) "https" else "http"
    /** Address used for the enroll handshake — the one we actually found. */
    val baseUrl: String get() = "$scheme://$host:$port"
    /** Address to store for ongoing use — the tailnet host if advertised. */
    val persistBaseUrl: String get() =
        if (persistHost != null) "$scheme://$persistHost:${persistPort ?: port}" else baseUrl
}

sealed interface EnrollRequestResult {
    data class Success(val requestId: String, val verifyCode: String, val expiresIn: Int) : EnrollRequestResult
    data class Failure(val code: String) : EnrollRequestResult
}

sealed interface EnrollStatusResult {
    data object Pending : EnrollStatusResult
    data object DeniedOrExpired : EnrollStatusResult
    data class Approved(val token: String, val tokenId: String, val owner: String) : EnrollStatusResult
    data class Failure(val code: String) : EnrollStatusResult
}

/**
 * LAN discovery + approval enrollment — the "find the host, approve on the host"
 * flow, so pairing needs no QR/JSON copied from a desktop.
 *
 * TRUST MODEL: the /discover probe uses a trust-all TLS client because the app
 * has no pin yet — it reads the host's ACTUAL leaf-cert fingerprint off the
 * completed handshake and pins to that for the enroll calls. That is safe here
 * because issuing a credential requires an explicit admin approval on the real
 * host with a matching verify code: a rogue LAN beacon can be discovered but can
 * never get approved, so it yields no token. Pure JVM/OkHttp — no Android types.
 */
class HostDiscovery {

    private val jsonType = "application/json".toMediaType()

    /** Short timeouts: this runs across a whole subnet, so a dead IP must fail fast. */
    private fun trustAllClient(): OkHttpClient {
        val tm = object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<X509Certificate>?, authType: String?) {}
            override fun checkServerTrusted(chain: Array<X509Certificate>?, authType: String?) {}
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        }
        val ctx = SSLContext.getInstance("TLS")
        ctx.init(null, arrayOf(tm), null)
        return OkHttpClient.Builder()
            .connectTimeout(1200, TimeUnit.MILLISECONDS)
            .readTimeout(1500, TimeUnit.MILLISECONDS)
            .sslSocketFactory(ctx.socketFactory, tm)
            .hostnameVerifier { _, _ -> true }
            .build()
    }

    private fun pinnedClient(fp: String): OkHttpClient {
        val tm = object : X509TrustManager {
            override fun checkClientTrusted(chain: Array<X509Certificate>?, authType: String?) {}
            override fun checkServerTrusted(chain: Array<X509Certificate>?, authType: String?) {
                val leaf = chain?.firstOrNull() ?: throw javax.net.ssl.SSLException("no cert")
                if (fpOf(leaf) != fp.lowercase()) throw javax.net.ssl.SSLException("pin mismatch")
            }
            override fun getAcceptedIssuers(): Array<X509Certificate> = arrayOf()
        }
        val ctx = SSLContext.getInstance("TLS")
        ctx.init(null, arrayOf(tm), null)
        return OkHttpClient.Builder()
            .connectTimeout(4, TimeUnit.SECONDS)
            .readTimeout(6, TimeUnit.SECONDS)
            .sslSocketFactory(ctx.socketFactory, tm)
            .hostnameVerifier { _, _ -> true }
            .build()
    }

    private fun clientForHost(h: DiscoveredHost): OkHttpClient =
        if (h.tls && !h.certSha256.isNullOrBlank()) pinnedClient(h.certSha256) else plainClient()

    private fun plainClient(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(4, TimeUnit.SECONDS).readTimeout(6, TimeUnit.SECONDS).build()

    private fun fpOf(cert: java.security.cert.Certificate): String =
        MessageDigest.getInstance("SHA-256").digest(cert.encoded)
            .joinToString("") { "%02x".format(it) }

    /**
     * Probe one address for the my.ai discovery beacon. Tries https first
     * (the usual LAN-proxy TLS port), then plain http. Returns null for
     * anything that isn't a my.ai host. Never throws.
     */
    suspend fun probe(ip: String, port: Int): DiscoveredHost? = withContext(Dispatchers.IO) {
        // https (capture the real leaf fingerprint from the handshake)
        runCatching {
            val c = trustAllClient()
            c.newCall(Request.Builder().url("https://$ip:$port/api/wearables/v1/discover").build())
                .execute().use { resp ->
                    if (!resp.isSuccessful) return@runCatching null
                    val obj = JSONObject(resp.body?.string() ?: "{}")
                    if (obj.optString("service") != "myai-wearables") return@runCatching null
                    // Pin to the cert we actually saw on the wire; fall back to
                    // the fingerprint the beacon reports if the handshake didn't
                    // expose it (else enroll would drop the pin and fail the
                    // self-signed TLS). Both are the same public leaf cert.
                    val leafFp = resp.handshake?.peerCertificates?.firstOrNull()?.let { fpOf(it) }
                        ?: obj.optString("cert_sha256").takeIf { it.isNotBlank() }
                    return@withContext DiscoveredHost(
                        name = obj.optString("name", "my.ai host"),
                        host = ip, port = port, tls = true, certSha256 = leafFp,
                        persistHost = obj.optString("persist_host").takeIf { it.isNotBlank() },
                        persistPort = obj.optInt("persist_port").takeIf { it > 0 })
                }
        }.getOrNull()?.let { return@withContext it }
        // plain http fallback
        runCatching {
            plainClient().newCall(
                Request.Builder().url("http://$ip:$port/api/wearables/v1/discover").build())
                .execute().use { resp ->
                    if (!resp.isSuccessful) return@runCatching null
                    val obj = JSONObject(resp.body?.string() ?: "{}")
                    if (obj.optString("service") != "myai-wearables") return@runCatching null
                    return@withContext DiscoveredHost(
                        name = obj.optString("name", "my.ai host"),
                        host = ip, port = port, tls = false, certSha256 = null,
                        persistHost = obj.optString("persist_host").takeIf { it.isNotBlank() },
                        persistPort = obj.optInt("persist_port").takeIf { it > 0 })
                }
        }
        null
    }

    /** Ask a discovered host to enroll this device. */
    suspend fun enrollRequest(host: DiscoveredHost, deviceName: String): EnrollRequestResult =
        withContext(Dispatchers.IO) {
            val body = JSONObject().put("device_name", deviceName).toString().toRequestBody(jsonType)
            runCatching {
                clientForHost(host).newCall(
                    Request.Builder().url(host.baseUrl + "/api/wearables/v1/enroll/request").post(body).build())
                    .execute().use { resp ->
                        val obj = JSONObject(resp.body?.string() ?: "{}")
                        if (resp.isSuccessful) EnrollRequestResult.Success(
                            obj.getString("request_id"), obj.getString("verify_code"),
                            obj.optInt("expires_in", 300))
                        else EnrollRequestResult.Failure(
                            obj.optJSONObject("detail")?.optString("code") ?: "ENROLL_FAILED")
                    }
            }.getOrElse { EnrollRequestResult.Failure("MYAI_HOST_UNREACHABLE") }
        }

    /** Poll a discovered host for approval + the minted token. */
    suspend fun enrollStatus(host: DiscoveredHost, requestId: String): EnrollStatusResult =
        withContext(Dispatchers.IO) {
            runCatching {
                clientForHost(host).newCall(
                    Request.Builder().url(
                        host.baseUrl + "/api/wearables/v1/enroll/status/" + requestId).build())
                    .execute().use { resp ->
                        val obj = JSONObject(resp.body?.string() ?: "{}")
                        if (!resp.isSuccessful)
                            return@use EnrollStatusResult.Failure(
                                obj.optJSONObject("detail")?.optString("code") ?: "MYAI_HOST_UNREACHABLE")
                        when (obj.optString("status")) {
                            "approved" -> EnrollStatusResult.Approved(
                                obj.getString("token"), obj.optString("token_id"), obj.optString("owner"))
                            "denied_or_expired" -> EnrollStatusResult.DeniedOrExpired
                            else -> EnrollStatusResult.Pending
                        }
                    }
            }.getOrElse { EnrollStatusResult.Failure("MYAI_HOST_UNREACHABLE") }
        }
}
