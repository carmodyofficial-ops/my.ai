package ai.my.glasses

import ai.my.glasses.core.Vad
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** Unit tests for the hands-free voice-activity endpointer (the pure decision +
 *  RMS extracted from VoiceSession so it's testable off-device). */
class VadTest {

    /** 16-bit LE PCM alternating ±[amp] → RMS == amp. */
    private fun tone(amp: Int, samples: Int = 512): ByteArray {
        val b = ByteArray(samples * 2)
        for (i in 0 until samples) {
            val s = if (i % 2 == 0) amp else -amp
            b[i * 2] = (s and 0xff).toByte()
            b[i * 2 + 1] = ((s shr 8) and 0xff).toByte()
        }
        return b
    }
    private val silent = ByteArray(1024)          // zeros
    private val loud get() = tone(5000)           // RMS 5000 (> speech threshold)

    @Test fun `rms of silence is zero`() {
        assertEquals(0.0, Vad.rms(silent, silent.size), 0.001)
    }

    @Test fun `rms recovers the amplitude, sign-independent`() {
        assertEquals(5000.0, Vad.rms(tone(5000), 1024), 1.0)
        assertEquals(300.0, Vad.rms(tone(300), 1024), 1.0)
    }

    @Test fun `silence alone never endpoints`() {
        val vad = Vad(silenceMs = 1000, minBytes = 0)
        assertFalse(vad.accept(silent, silent.size, 100_000, 0))
        assertFalse(vad.accept(silent, silent.size, 100_000, 5_000))
    }

    @Test fun `speech then trailing silence endpoints after the timeout`() {
        val vad = Vad(silenceMs = 1000, minBytes = 1000)
        assertFalse(vad.accept(loud, loud.size, 2000, 0))         // speech at t=0
        assertFalse(vad.accept(silent, silent.size, 4000, 500))   // 0.5s silence — too soon
        assertTrue(vad.accept(silent, silent.size, 6000, 1201))   // >1.2s since voice → end
    }

    @Test fun `continuing speech does not endpoint`() {
        val vad = Vad(silenceMs = 1000, minBytes = 0)
        assertFalse(vad.accept(loud, loud.size, 2000, 0))
        assertFalse(vad.accept(loud, loud.size, 4000, 2000))
        assertFalse(vad.accept(loud, loud.size, 6000, 4000))
    }

    @Test fun `min-bytes guard blocks a too-short utterance`() {
        val vad = Vad(silenceMs = 500, minBytes = 10_000)
        assertFalse(vad.accept(loud, loud.size, 500, 0))          // speech, tiny total
        assertFalse(vad.accept(silent, silent.size, 500, 1000))   // past timeout but < minBytes
    }

    @Test fun `endpoints strictly after the silence window, not at the boundary`() {
        val vad = Vad(silenceMs = 1000, minBytes = 1000)
        assertFalse(vad.accept(loud, loud.size, 2000, 0))          // speech at t=0
        assertFalse(vad.accept(silent, silent.size, 2000, 1000))   // exactly 1000ms → not yet
        assertTrue(vad.accept(silent, silent.size, 2000, 1001))    // 1ms past window → end
    }

    @Test fun `min-bytes boundary is strict`() {
        val vad = Vad(silenceMs = 500, minBytes = 2000)
        assertFalse(vad.accept(loud, loud.size, 2000, 0))          // speech, totalBytes == minBytes
        assertFalse(vad.accept(silent, silent.size, 2000, 1000))   // past timeout but not > minBytes
        assertTrue(vad.accept(silent, silent.size, 2001, 1000))    // one byte over → end
    }

    @Test fun `quiet-below-threshold audio counts as silence`() {
        val vad = Vad(speechRms = 700.0, silenceMs = 1000, minBytes = 0)
        val quiet = tone(200)   // below the 700 speech threshold
        assertFalse(vad.accept(quiet, quiet.size, 5000, 0))       // never counted as speech
        assertFalse(vad.accept(quiet, quiet.size, 5000, 5000))
    }
}
