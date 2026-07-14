package ai.my.glasses.core

import org.json.JSONObject

/**
 * The QR payload minted by POST /api/wearables/v1/pairings:
 *   {"v":1,"kind":"wearables","host":"192.168.1.20","port":7001,"code":"wpair_…"}
 * Pure parser (JVM-testable). Rejects anything that isn't exactly this shape —
 * a scanned QR is untrusted input.
 */
data class PairingPayload(
    val host: String,
    val port: Int,
    val code: String,
    val tls: Boolean = false,
    /** SHA-256 (hex) of the host's DER cert — pins the self-signed LAN cert;
     *  the QR itself is the trust bootstrap. Null for plain-HTTP or CA certs. */
    val certSha256: String? = null,
) {
    val baseUrl: String get() = "${if (tls) "https" else "http"}://$host:$port"

    companion object {
        private val HEX64 = Regex("^[0-9a-fA-F]{64}$")
        // Hostname or IP literal only. Rejects URL-structural metacharacters
        // (`?`, `#`, `@`, `:`, `\`, `/`, whitespace) that would otherwise be
        // string-concatenated into baseUrl and could redirect the effective
        // host/port/query when OkHttp parses it. Not RFC1918-restricted on
        // purpose: the Tailscale remote-access path uses CGNAT (100.x) hosts.
        private val HOST = Regex("^[A-Za-z0-9._-]{1,255}$")

        fun parse(raw: String): PairingPayload? {
            val obj = try { JSONObject(raw) } catch (_: Exception) { return null }
            if (obj.optInt("v") != 1) return null
            if (obj.optString("kind") != "wearables") return null
            val host = obj.optString("host")
            val port = obj.optInt("port", -1)
            val code = obj.optString("code")
            if (!HOST.matches(host)) return null
            if (port !in 1..65535) return null
            if (!code.startsWith("wpair_") || code.length > 128) return null
            val fp = obj.optString("cert_sha256").takeIf { it.isNotBlank() }
            if (fp != null && !HEX64.matches(fp)) return null
            return PairingPayload(host, port, code, obj.optBoolean("tls", false),
                fp?.lowercase())
        }
    }
}
