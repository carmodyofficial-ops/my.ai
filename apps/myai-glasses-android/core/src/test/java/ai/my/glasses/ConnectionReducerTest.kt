package ai.my.glasses

import ai.my.glasses.core.AppState
import ai.my.glasses.core.ConnectionReducer.failureFromCode
import ai.my.glasses.core.ConnectionReducer.reduce
import ai.my.glasses.core.Event
import ai.my.glasses.core.Failure
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class ConnectionReducerTest {

    private val healthy = AppState(
        glassesConnected = true, hostPaired = true,
        hostReachable = true, credentialValid = true)

    @Test fun `canTalk only when the host path is up`() {
        assertTrue(healthy.canTalk)
        assertFalse(healthy.copy(hostReachable = false).canTalk)
        assertFalse(healthy.copy(hostPaired = false).canTalk)
        assertFalse(healthy.copy(credentialValid = false).canTalk)
    }

    @Test fun `a transient reply-side failure must NOT latch the action buttons off`() {
        // Regression: canTalk used to gate on `failure`, so pressing Stop
        // (SESSION_CANCELLED) or hitting one rate-limit/LLM hiccup disabled
        // Ask/Talk/Look forever with no way to start a new turn to recover.
        assertTrue(reduce(healthy, Event.GatewayError("SESSION_CANCELLED")).canTalk)
        assertTrue(reduce(healthy, Event.GatewayError("LLM_UNAVAILABLE")).canTalk)
        assertTrue(reduce(healthy, Event.GatewayError("RATE_LIMITED")).canTalk)
        assertTrue(reduce(healthy, Event.GatewayError("TTS_FAILED")).canTalk)
    }

    @Test fun `a persistent host or credential failure still gates canTalk`() {
        // These flip the durable flags (hostReachable / credentialValid) so the
        // buttons stay disabled until the user recovers the host or re-pairs.
        assertFalse(reduce(healthy, Event.GatewayError("MYAI_HOST_UNREACHABLE")).canTalk)
        assertFalse(reduce(healthy, Event.GatewayError("DEVICE_CREDENTIAL_REVOKED")).canTalk)
        assertFalse(reduce(healthy, Event.GatewayError("AUTHENTICATION_REQUIRED")).canTalk)
        assertFalse(reduce(healthy, Event.GatewayError("TLS_UNTRUSTED")).canTalk)
    }

    @Test fun `glasses absence must not block the phone-only loop`() {
        // Live regression 2026-07-12: a glasses session drop set
        // GLASSES_NOT_CONNECTED and disabled Ask/Talk entirely, even though
        // the phone's own mic/speaker carry the loop without glasses.
        assertTrue(healthy.copy(failure = Failure.GLASSES_NOT_CONNECTED).canTalk)
        assertTrue(reduce(healthy, Event.GlassesDisconnected).canTalk)
    }

    @Test fun `glasses (camera) disconnect must NOT abort an in-progress capture`() {
        // The DAT camera session is separate from the audio path — acquiring the
        // glasses HFP mic can itself drop the camera session, and that must not
        // kill the utterance. listening stays; only the banner updates.
        val s = reduce(healthy.copy(listening = true), Event.GlassesDisconnected)
        assertTrue(s.listening)
        assertEquals(Failure.GLASSES_NOT_CONNECTED, s.failure)
    }

    @Test fun `credential rejection ends session and flags revocation`() {
        val s = reduce(healthy.copy(listening = true, activeSessionId = "abc"),
            Event.CredentialRejected)
        assertFalse(s.listening)
        assertNull(s.activeSessionId)
        assertEquals(Failure.DEVICE_CREDENTIAL_REVOKED, s.failure)
        assertFalse(s.canTalk)
    }

    @Test fun `host recovery clears only host failure`() {
        val down = reduce(healthy, Event.HostUnreachable)
        assertEquals(Failure.MYAI_HOST_UNREACHABLE, down.failure)
        val up = reduce(down, Event.HostHealthy)
        assertNull(up.failure)
        // But an unrelated failure is not silently cleared by host recovery.
        val sttDown = reduce(healthy, Event.GatewayError("STT_UNAVAILABLE"))
        assertEquals(Failure.STT_UNAVAILABLE, reduce(sttDown, Event.HostHealthy).failure)
    }

    @Test fun `every gateway error code maps to a UI failure`() {
        val codes = listOf("AUTHENTICATION_REQUIRED", "DEVICE_CREDENTIAL_REVOKED",
            "FORBIDDEN_SCOPE", "STT_UNAVAILABLE", "STT_FAILED", "LLM_UNAVAILABLE",
            "VISION_MODEL_NOT_CONFIGURED", "VISION_FAILED", "TTS_UNAVAILABLE",
            "TTS_FAILED", "REQUEST_TIMEOUT", "SESSION_CANCELLED",
            "UNSAFE_ACTION_BLOCKED", "APPROVAL_REQUIRED", "SOMETHING_NEW")
        codes.forEach { failureFromCode(it) } // must not throw; unknown degrades
        assertEquals(Failure.MYAI_HOST_UNREACHABLE, failureFromCode("SOMETHING_NEW"))
    }

    @Test fun `glasses-side codes map to glasses failures, not host-unreachable`() {
        // These had no case at all and fell through to MYAI_HOST_UNREACHABLE —
        // which canTalk does NOT excuse. So a failed Look-and-Ask killed Ask and
        // Talk outright and told the user to check their Wi-Fi.
        assertEquals(Failure.GLASSES_NOT_CONNECTED, failureFromCode("GLASSES_NOT_CONNECTED"))
        assertEquals(Failure.GLASSES_NOT_CONNECTED, failureFromCode("CAPTURE_FAILED"))
        assertEquals(Failure.GLASSES_PERMISSION_DENIED,
            failureFromCode("GLASSES_PERMISSION_DENIED"))
        assertEquals(Failure.META_DEVELOPER_MODE_REQUIRED,
            failureFromCode("META_DEVELOPER_MODE_REQUIRED"))
        assertEquals(Failure.BLUETOOTH_AUDIO_UNAVAILABLE,
            failureFromCode("BLUETOOTH_AUDIO_UNAVAILABLE"))
    }

    @Test fun `a failed look-and-ask leaves the phone-only loop usable`() {
        val s = reduce(healthy, Event.GatewayError("GLASSES_NOT_CONNECTED"))
        assertTrue(s.canTalk)
    }

    @Test fun `a reply-side failure must not kill an utterance in progress`() {
        // The user is already speaking their NEXT question when TTS for the
        // PREVIOUS reply fails. Clearing `listening` for every gateway error threw
        // that recording away.
        val talking = healthy.copy(listening = true)
        assertTrue(reduce(talking, Event.GatewayError("TTS_FAILED")).listening)
        assertTrue(reduce(talking, Event.GatewayError("LLM_UNAVAILABLE")).listening)
        assertTrue(reduce(talking, Event.GatewayError("SESSION_CANCELLED")).listening)
    }

    @Test fun `a capture-invalidating failure does stop the mic`() {
        val talking = healthy.copy(listening = true)
        assertFalse(reduce(talking, Event.GatewayError("BLUETOOTH_AUDIO_UNAVAILABLE")).listening)
        assertFalse(reduce(talking, Event.GatewayError("STT_UNAVAILABLE")).listening)
        assertFalse(reduce(talking, Event.GatewayError("AUTHENTICATION_REQUIRED")).listening)
    }

    @Test fun `unpairing stops the mic`() {
        // The one invalidating event that used to leave `listening` set — so the
        // mic kept recording into a host we had just thrown away.
        val s = reduce(healthy.copy(listening = true, speaking = true), Event.HostUnpaired)
        assertFalse(s.listening)
        assertFalse(s.speaking)
        assertFalse(s.hostPaired)
    }

    @Test fun `transient request failures do not read as host-unreachable`() {
        // These had no reducer case and degraded to MYAI_HOST_UNREACHABLE, which
        // both mislabels the error and (being in stopsCapture) killed the mic.
        assertEquals(Failure.RATE_LIMITED, failureFromCode("RATE_LIMITED"))
        assertEquals(Failure.PAYLOAD_TOO_LARGE, failureFromCode("PAYLOAD_TOO_LARGE"))
        assertEquals(Failure.BAD_REQUEST, failureFromCode("BAD_REQUEST"))
        assertEquals(Failure.SESSION_NOT_FOUND, failureFromCode("SESSION_NOT_FOUND"))
    }

    @Test fun `a rate-limit does not kill an utterance in progress`() {
        val talking = healthy.copy(listening = true)
        assertTrue(reduce(talking, Event.GatewayError("RATE_LIMITED")).listening)
        assertTrue(reduce(talking, Event.GatewayError("PAYLOAD_TOO_LARGE")).listening)
    }
}
