package ai.my.glasses.core

/**
 * Pure connection/failure state machine — the app's single source of truth
 * for "what should the user see / what can they do". No Android types, so it
 * is JVM-unit-testable (ConnectionReducerTest).
 */
data class AppState(
    val glassesConnected: Boolean = false,
    val hostPaired: Boolean = false,
    val hostReachable: Boolean = false,
    val credentialValid: Boolean = true,
    val listening: Boolean = false,
    val speaking: Boolean = false,
    val activeSessionId: String? = null,
    val failure: Failure? = null,
) {
    /** Talk/Ask needs the HOST path up. Glasses being absent must NOT block
     *  it — the phone's own mic/speaker carry the loop until glasses join
     *  (live finding: a glasses session drop disabled Ask entirely).
     *
     *  Deliberately does NOT look at `failure`: a transient reply-side error
     *  (a cancelled turn / Stop, rate-limit, TTS/LLM hiccup) must not latch the
     *  three action buttons off forever — that left the user with no way to even
     *  start a new turn to recover (bug: "need to close the app to interact").
     *  Persistent host/credential failures already flip hostReachable /
     *  credentialValid (see the GatewayError case), which is what gates here. */
    val canTalk: Boolean
        get() = hostPaired && hostReachable && credentialValid
}

enum class Failure {
    GLASSES_NOT_CONNECTED,
    GLASSES_PERMISSION_DENIED,
    META_DEVELOPER_MODE_REQUIRED,
    BLUETOOTH_AUDIO_UNAVAILABLE,
    MYAI_HOST_UNREACHABLE,
    TLS_UNTRUSTED,
    AUTHENTICATION_REQUIRED,
    DEVICE_CREDENTIAL_REVOKED,
    STT_UNAVAILABLE,
    LLM_UNAVAILABLE,
    VISION_MODEL_NOT_CONFIGURED,
    TTS_UNAVAILABLE,
    REQUEST_TIMEOUT,
    SESSION_CANCELLED,
    UNSAFE_ACTION_BLOCKED,
    APPROVAL_REQUIRED,
    RATE_LIMITED,
    PAYLOAD_TOO_LARGE,
    BAD_REQUEST,
    SESSION_NOT_FOUND,
}

sealed interface Event {
    data object GlassesConnected : Event
    data object GlassesDisconnected : Event
    data object HostPaired : Event
    data object HostUnpaired : Event
    data object HostHealthy : Event
    data object HostUnreachable : Event
    data object CredentialRejected : Event
    data class ListeningChanged(val listening: Boolean) : Event
    data class SpeakingChanged(val speaking: Boolean) : Event
    data class SessionStarted(val id: String) : Event
    data object SessionEnded : Event
    data class GatewayError(val code: String) : Event
    data object FailureCleared : Event
}

object ConnectionReducer {

    fun reduce(s: AppState, e: Event): AppState = when (e) {
        Event.GlassesConnected -> s.copy(glassesConnected = true,
            failure = s.failure.takeUnless { it == Failure.GLASSES_NOT_CONNECTED })
        Event.GlassesDisconnected -> s.copy(glassesConnected = false,
            // Do NOT stop the mic here. This event tracks the DAT *camera* session,
            // which is separate from the audio path: acquiring the glasses HFP mic
            // can itself drop the camera session, and a camera drop must never abort
            // an in-progress utterance. `listening` is owned by start/stopListening,
            // and by host/credential failures below.
            failure = when {
                // Mid-capture, a camera-session drop is EXPECTED (acquiring the
                // glasses mic causes it) — don't pop a "glasses not connected"
                // banner over an active Talk.
                s.listening -> s.failure
                // Don't clobber a higher-priority banner (credential revoked / host
                // unreachable) with GLASSES_NOT_CONNECTED.
                s.failure == null || s.failure == Failure.GLASSES_NOT_CONNECTED ->
                    Failure.GLASSES_NOT_CONNECTED
                else -> s.failure
            })
        Event.HostPaired -> s.copy(hostPaired = true, credentialValid = true)
        // Unpairing mid-utterance must close the mic too. It was the one
        // invalidating event that left `listening` set, so the mic kept
        // recording into a session that no longer had anywhere to go.
        Event.HostUnpaired -> s.copy(hostPaired = false, activeSessionId = null,
            listening = false, speaking = false)
        Event.HostHealthy -> s.copy(hostReachable = true,
            failure = s.failure.takeUnless { it == Failure.MYAI_HOST_UNREACHABLE })
        Event.HostUnreachable -> s.copy(hostReachable = false, listening = false,
            failure = Failure.MYAI_HOST_UNREACHABLE)
        Event.CredentialRejected -> s.copy(credentialValid = false, listening = false,
            activeSessionId = null, failure = Failure.DEVICE_CREDENTIAL_REVOKED)
        is Event.ListeningChanged -> s.copy(listening = e.listening)
        is Event.SpeakingChanged -> s.copy(speaking = e.speaking)
        is Event.SessionStarted -> s.copy(activeSessionId = e.id)
        Event.SessionEnded -> s.copy(activeSessionId = null,
            listening = false, speaking = false)
        // A gateway error must only stop the mic when it invalidates the CAPTURE.
        // Clearing `listening` for every error killed an utterance the user had
        // already started speaking whenever a *reply-side* failure (TTS, LLM,
        // vision, a cancelled previous turn) arrived for the turn before it.
        is Event.GatewayError -> failureFromCode(e.code).let { f ->
            s.copy(
                // A GLASSES_NOT_CONNECTED arriving mid-capture is the benign camera
                // drop from acquiring the glasses mic — keep the existing banner
                // rather than popping "glasses not connected" over an active Talk.
                failure = if (f == Failure.GLASSES_NOT_CONNECTED && s.listening) s.failure else f,
                listening = if (stopsCapture(f)) false else s.listening,
                // Persistent host/credential failures keep Talk/Ask gated by
                // flipping the durable flags canTalk reads — since canTalk no
                // longer excuses/blocks on `failure` itself. Transient reply-side
                // errors touch neither flag, so the user can retry immediately.
                credentialValid = if (invalidatesCredential(f)) false else s.credentialValid,
                hostReachable = if (f == Failure.MYAI_HOST_UNREACHABLE) false else s.hostReachable,
            )
        }
        Event.FailureCleared -> s.copy(failure = null)
    }

    /**
     * Failures that invalidate an in-progress capture: the audio path itself, or
     * the host/credential path the audio is destined for. Notably NOT
     * GLASSES_NOT_CONNECTED — [Event.GlassesDisconnected] already covers a real
     * drop, and a failed Look-and-Ask reports that code too; it must not kill an
     * utterance the user is speaking into the PHONE mic.
     */
    /** Failures that mean the host path is broken until the user re-pairs /
     *  re-approves — these must keep gating canTalk (via credentialValid), unlike
     *  transient reply-side errors which must not. */
    private fun invalidatesCredential(f: Failure): Boolean = when (f) {
        Failure.DEVICE_CREDENTIAL_REVOKED,
        Failure.AUTHENTICATION_REQUIRED,
        Failure.TLS_UNTRUSTED -> true
        else -> false
    }

    private fun stopsCapture(f: Failure): Boolean = when (f) {
        Failure.BLUETOOTH_AUDIO_UNAVAILABLE,
        Failure.MYAI_HOST_UNREACHABLE,
        Failure.TLS_UNTRUSTED,
        Failure.AUTHENTICATION_REQUIRED,
        Failure.DEVICE_CREDENTIAL_REVOKED,
        Failure.STT_UNAVAILABLE -> true
        else -> false
    }

    /** Gateway error codes map 1:1 onto UI failure states; unknown codes
     *  degrade to MYAI_HOST_UNREACHABLE rather than crashing or hiding. */
    fun failureFromCode(code: String): Failure = when (code) {
        "TLS_UNTRUSTED" -> Failure.TLS_UNTRUSTED
        "AUTHENTICATION_REQUIRED" -> Failure.AUTHENTICATION_REQUIRED
        "DEVICE_CREDENTIAL_REVOKED", "FORBIDDEN_SCOPE" -> Failure.DEVICE_CREDENTIAL_REVOKED
        "STT_UNAVAILABLE", "STT_FAILED" -> Failure.STT_UNAVAILABLE
        "LLM_UNAVAILABLE" -> Failure.LLM_UNAVAILABLE
        "VISION_MODEL_NOT_CONFIGURED", "VISION_FAILED" -> Failure.VISION_MODEL_NOT_CONFIGURED
        "TTS_UNAVAILABLE", "TTS_FAILED" -> Failure.TTS_UNAVAILABLE
        "REQUEST_TIMEOUT" -> Failure.REQUEST_TIMEOUT
        "SESSION_CANCELLED" -> Failure.SESSION_CANCELLED
        "UNSAFE_ACTION_BLOCKED" -> Failure.UNSAFE_ACTION_BLOCKED
        "APPROVAL_REQUIRED" -> Failure.APPROVAL_REQUIRED
        // The glasses-side codes had NO cases at all, so they fell through to
        // MYAI_HOST_UNREACHABLE — which canTalk does not excuse. A failed
        // Look-and-Ask therefore killed Ask/Talk entirely and told the user to
        // check their Wi-Fi. These Failure states (and their recovery hints) were
        // unreachable code until now.
        "GLASSES_NOT_CONNECTED", "CAPTURE_FAILED" -> Failure.GLASSES_NOT_CONNECTED
        "GLASSES_PERMISSION_DENIED" -> Failure.GLASSES_PERMISSION_DENIED
        "META_DEVELOPER_MODE_REQUIRED" -> Failure.META_DEVELOPER_MODE_REQUIRED
        "BLUETOOTH_AUDIO_UNAVAILABLE" -> Failure.BLUETOOTH_AUDIO_UNAVAILABLE
        // These had no case and degraded to MYAI_HOST_UNREACHABLE — which is in
        // stopsCapture, so a rate-limit or a rejected image size wrongly told the
        // user the host was down AND killed the utterance in progress.
        "RATE_LIMITED" -> Failure.RATE_LIMITED
        "PAYLOAD_TOO_LARGE" -> Failure.PAYLOAD_TOO_LARGE
        "BAD_REQUEST" -> Failure.BAD_REQUEST
        "SESSION_NOT_FOUND" -> Failure.SESSION_NOT_FOUND
        else -> Failure.MYAI_HOST_UNREACHABLE
    }
}
