package ai.my.glasses

import ai.my.glasses.net.GatewayEvent
import ai.my.glasses.net.SseParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SseParserTest {

    @Test fun `parses the documented frame sequence`() {
        val p = SseParser()
        val events = p.feed(
            "data: {\"type\": \"wearables_meta\", \"session_id\": \"s1\", " +
                "\"model\": \"m\", \"request_id\": \"r1\"}\n\n" +
                "data: {\"delta\": \"Hello \"}\n\n" +
                "data: {\"delta\": \"hidden\", \"thinking\": true}\n\n" +
                "data: {\"type\": \"spoken\", \"text\": \"Hello.\", \"truncated\": false}\n\n" +
                "data: {\"type\": \"done\", \"request_id\": \"r1\"}\n\n" +
                "data: [DONE]\n\n")
        assertEquals(6, events.size)
        assertTrue(events[0] is GatewayEvent.Meta)
        assertEquals("s1", (events[0] as GatewayEvent.Meta).sessionId)
        assertTrue((events[2] as GatewayEvent.Delta).thinking)
        assertEquals("Hello.", (events[3] as GatewayEvent.Spoken).text)
        assertTrue(events[5] is GatewayEvent.StreamEnd)
    }

    @Test fun `handles frames split across network chunks`() {
        val p = SseParser()
        val a = p.feed("data: {\"delta\": \"par")
        assertTrue(a.isEmpty())
        val b = p.feed("tial\"}\n\ndata: [DO")
        assertEquals("partial", (b.single() as GatewayEvent.Delta).text)
        val c = p.feed("NE]\n\n")
        assertTrue(c.single() is GatewayEvent.StreamEnd)
    }

    @Test fun `error frames carry the gateway code`() {
        val p = SseParser()
        val events = p.feed(
            "event: error\ndata: {\"code\": \"LLM_UNAVAILABLE\", \"message\": \"x\"}\n\n")
        assertEquals("LLM_UNAVAILABLE", (events.single() as GatewayEvent.Error).code)
    }

    @Test fun `garbage frames are dropped not fatal`() {
        val p = SseParser()
        val events = p.feed("data: not-json\n\ndata: {\"delta\": \"ok\"}\n\n")
        assertEquals(1, events.size)
        assertEquals("ok", (events.single() as GatewayEvent.Delta).text)
    }

    @Test fun `a separator-less flood is bounded, not an OOM`() {
        val p = SseParser()
        var err: GatewayEvent.Error? = null
        // Feed >1M chars of a single never-terminated frame. Must abort with an
        // error rather than growing the buffer without limit.
        repeat(40) { chunk ->
            val out = p.feed("x".repeat(50_000))
            out.filterIsInstance<GatewayEvent.Error>().firstOrNull()?.let { err = it }
        }
        assertEquals("MYAI_HOST_UNREACHABLE", err?.code)
        // After overflow the parser stays quiet instead of resuming.
        assertEquals(0, p.feed("data: {\"delta\": \"late\"}\n\n").size)
    }
}
