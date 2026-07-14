package ai.my.glasses

import ai.my.glasses.core.PairingPayload
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class PairingPayloadTest {

    @Test fun `accepts the gateway's exact payload shape`() {
        val p = PairingPayload.parse(
            """{"v":1,"kind":"wearables","host":"192.168.1.20","port":7001,"code":"wpair_abc123"}""")!!
        assertEquals("192.168.1.20", p.host)
        assertEquals(7001, p.port)
        assertEquals("wpair_abc123", p.code)
        assertEquals("http://192.168.1.20:7001", p.baseUrl)
    }

    @Test fun `tls flag switches to https`() {
        val p = PairingPayload.parse(
            """{"v":1,"kind":"wearables","host":"192.168.1.50","port":7443,"tls":true,"code":"wpair_abc"}""")!!
        assertEquals("https://192.168.1.50:7443", p.baseUrl)
    }

    @Test fun `cert fingerprint parsed, lowercased, validated`() {
        val fp = "DB205B9DDB12773F71C4A8D2D35899ADC889E051ED4F835140897292696C3CA5"
        val p = PairingPayload.parse(
            """{"v":1,"kind":"wearables","host":"h","port":7443,"tls":true,""" +
            """"code":"wpair_x","cert_sha256":"$fp"}""")!!
        assertEquals(fp.lowercase(), p.certSha256)
        // Absent → null (plain HTTP / CA-signed hosts).
        assertNull(PairingPayload.parse(
            """{"v":1,"kind":"wearables","host":"h","port":1,"code":"wpair_x"}""")!!.certSha256)
        // Malformed fingerprints reject the whole payload — it's a trust root.
        assertNull(PairingPayload.parse(
            """{"v":1,"kind":"wearables","host":"h","port":1,"code":"wpair_x","cert_sha256":"zz"}"""))
    }

    @Test fun `rejects hostile or malformed payloads`() {
        assertNull(PairingPayload.parse("not json"))
        assertNull(PairingPayload.parse("""{"v":2,"kind":"wearables","host":"h","port":1,"code":"wpair_x"}"""))
        assertNull(PairingPayload.parse("""{"v":1,"kind":"companion","host":"h","port":1,"code":"wpair_x"}"""))
        assertNull(PairingPayload.parse("""{"v":1,"kind":"wearables","host":"a/b","port":1,"code":"wpair_x"}"""))
        assertNull(PairingPayload.parse("""{"v":1,"kind":"wearables","host":"h","port":99999,"code":"wpair_x"}"""))
        assertNull(PairingPayload.parse("""{"v":1,"kind":"wearables","host":"h","port":1,"code":"ody_notacode"}"""))
        assertNull(PairingPayload.parse("""{"v":1,"kind":"wearables","host":"","port":1,"code":"wpair_x"}"""))
    }
}
