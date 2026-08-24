package io.github.lostrobot.a0symbolics

import org.junit.Assert.assertEquals
import org.junit.Test

class DefaultServerTest {
    @Test
    fun defaultServerUsesPhoneLoopbackTunnel() {
        assertEquals("http://127.0.0.1:5080", DEFAULT_SERVER_URL)
    }
}
