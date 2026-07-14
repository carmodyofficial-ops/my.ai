package ai.my.glasses.net

import org.json.JSONObject

/**
 * Incremental parser for the gateway's SSE frames (openapi.yaml /respond).
 * Pure Kotlin + org.json (present on Android) so it is JVM-testable.
 */
sealed interface GatewayEvent {
    data class Meta(val sessionId: String, val model: String, val requestId: String) : GatewayEvent
    data class Delta(val text: String, val thinking: Boolean) : GatewayEvent
    data class Spoken(val text: String, val truncated: Boolean) : GatewayEvent
    data class Cancelled(val requestId: String) : GatewayEvent
    data class Done(val requestId: String) : GatewayEvent
    data class Error(val code: String, val message: String) : GatewayEvent
    data object StreamEnd : GatewayEvent
    /** Tool/progress frames we pass through for the diagnostics screen. */
    data class Other(val type: String?) : GatewayEvent
}

class SseParser {
    private val buffer = StringBuilder()
    private var overflowed = false

    companion object {
        // A well-behaved host frames on "\n\n" continually. A host that never
        // sends a separator (buggy or hostile) would otherwise grow this buffer
        // without bound → OOM. Cap it; a single frame this large is not real.
        const val MAX_BUFFER_CHARS = 1 shl 20   // 1M chars
    }

    /** Feed raw bytes-as-text; returns fully-parsed events. */
    fun feed(chunk: String): List<GatewayEvent> {
        if (overflowed) return emptyList()
        buffer.append(chunk)
        val events = mutableListOf<GatewayEvent>()
        while (true) {
            val sep = buffer.indexOf("\n\n")
            if (sep < 0) break
            val frame = buffer.substring(0, sep)
            buffer.delete(0, sep + 2)
            parseFrame(frame)?.let { events.add(it) }
        }
        // Still no complete frame but the buffer is already huge → give up on
        // this stream rather than letting it consume all memory.
        if (buffer.length > MAX_BUFFER_CHARS) {
            overflowed = true
            buffer.setLength(0)
            events.add(GatewayEvent.Error("MYAI_HOST_UNREACHABLE", "stream frame too large"))
        }
        return events
    }

    private fun parseFrame(frame: String): GatewayEvent? {
        var isError = false
        var data: String? = null
        for (line in frame.lines()) {
            when {
                line.startsWith("event:") -> isError = line.removePrefix("event:").trim() == "error"
                line.startsWith("data:") -> data = line.removePrefix("data:").trim()
            }
        }
        val payload = data ?: return null
        if (payload == "[DONE]") return GatewayEvent.StreamEnd
        val obj = try { JSONObject(payload) } catch (_: Exception) { return null }
        if (isError) {
            return GatewayEvent.Error(
                obj.optString("code", "MYAI_HOST_UNREACHABLE"),
                obj.optString("message", ""))
        }
        if (obj.has("delta")) {
            return GatewayEvent.Delta(obj.getString("delta"), obj.optBoolean("thinking", false))
        }
        return when (obj.optString("type")) {
            "wearables_meta" -> GatewayEvent.Meta(
                obj.getString("session_id"), obj.optString("model"), obj.optString("request_id"))
            "spoken" -> GatewayEvent.Spoken(
                obj.optString("text"), obj.optBoolean("truncated", false))
            "cancelled" -> GatewayEvent.Cancelled(obj.optString("request_id"))
            "done" -> GatewayEvent.Done(obj.optString("request_id"))
            else -> GatewayEvent.Other(obj.optString("type", null))
        }
    }
}
