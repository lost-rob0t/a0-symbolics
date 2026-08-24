package io.github.lostrobot.a0symbolics

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SetupScreenTest {
    @Test
    fun normalizesStandardLoopback() {
        assertEquals(
            "http://127.0.0.1:5080",
            normalizeUrl("http://127.0.0.1:5080/").getOrThrow(),
        )
    }

    @Test
    fun acceptsShortLoopbackUsedByLocalForwarding() {
        assertEquals(
            "http://127.0.1:5080",
            normalizeUrl("http://127.0.1:5080").getOrThrow(),
        )
    }

    @Test
    fun acceptsLocalhost() {
        assertEquals(
            "http://localhost:5080",
            normalizeUrl("http://localhost:5080").getOrThrow(),
        )
    }

    @Test
    fun preservesPathAndBuildsOrigin() {
        val url = normalizeUrl("https://Example.COM:8443/a0/").getOrThrow()
        assertEquals("https://example.com:8443/a0", url)
        assertEquals("https://example.com:8443", origin(url))
    }

    @Test
    fun rejectsUnsupportedScheme() {
        assertTrue(normalizeUrl("ftp://localhost:5080").isFailure)
    }

    @Test
    fun rejectsCredentialsInUrl() {
        assertTrue(normalizeUrl("http://user:pass@localhost:5080").isFailure)
    }
}
