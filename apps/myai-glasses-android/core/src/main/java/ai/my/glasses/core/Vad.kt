package ai.my.glasses.core

import kotlin.math.sqrt

/**
 * Pure voice-activity endpointer for hands-free capture. Feed it PCM buffers and a
 * monotonic clock; it decides when an utterance has ended — once speech has been
 * heard AND a trailing silence follows, with a minimum captured length. No Android
 * dependencies, so it's unit-tested in :core (the mic hardware path needs a device).
 */
class Vad(
    private val speechRms: Double = 700.0,
    private val silenceMs: Long = 1_200L,
    private val minBytes: Int = 8_000,   // ~250 ms @ 16 kHz / 16-bit mono
) {
    private var speechSeen = false
    private var lastVoiceMs = 0L
    private var started = false

    /**
     * Feed one PCM buffer.
     * @param buf 16-bit little-endian PCM; @param n valid bytes in [buf].
     * @param totalBytes total captured so far; @param nowMs monotonic clock.
     * @return true when the utterance should end now (auto-send).
     */
    fun accept(buf: ByteArray, n: Int, totalBytes: Int, nowMs: Long): Boolean {
        if (!started) { started = true; lastVoiceMs = nowMs }
        if (rms(buf, n) > speechRms) { speechSeen = true; lastVoiceMs = nowMs }
        return speechSeen && (nowMs - lastVoiceMs) > silenceMs && totalBytes > minBytes
    }

    companion object {
        /** RMS amplitude of 16-bit little-endian PCM (first [n] bytes). */
        fun rms(buf: ByteArray, n: Int): Double {
            var sum = 0.0
            var count = 0
            var i = 0
            while (i + 1 < n) {
                val s = (buf[i + 1].toInt() shl 8) or (buf[i].toInt() and 0xff)
                sum += s.toDouble() * s
                count++
                i += 2
            }
            return if (count > 0) sqrt(sum / count) else 0.0
        }
    }
}
