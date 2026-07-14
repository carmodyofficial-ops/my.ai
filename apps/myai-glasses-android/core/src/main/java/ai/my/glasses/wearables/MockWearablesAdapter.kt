package ai.my.glasses.wearables

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Hardware-free adapter: drives the full app flow (connect → converse →
 * Look-and-Ask) with a synthetic device. Used by default builds, unit tests,
 * and any phone without glasses. Distinct from Meta's Mock Device Kit, which
 * `MetaDatAdapter` can additionally target in -PmetaSdk=true debug builds.
 */
class MockWearablesAdapter : WearablesAdapter {
    private val _state = MutableStateFlow(GlassesState(model = "Mock Ray-Ban Meta"))
    override val state: StateFlow<GlassesState> = _state

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var pendingDisconnect: Job? = null

    override fun initialize(host: Any) { /* nothing to initialize in mock mode */ }

    override suspend fun register(host: Any): Boolean {
        _state.update { it.copy(connection = GlassesConnection.REGISTERING) }
        delay(300)
        _state.update {
            it.copy(permissionGranted = true, connection = GlassesConnection.NOT_CONNECTED)
        }
        return true
    }

    override suspend fun ensureCameraPermission(
        requestPermission: suspend () -> Boolean,
    ): Boolean {
        _state.update { it.copy(permissionGranted = true) }
        return true
    }

    override suspend fun connect(): Boolean {
        pendingDisconnect?.cancel()
        _state.update { it.copy(connection = GlassesConnection.CONNECTING) }
        delay(300)
        _state.update {
            it.copy(connection = GlassesConnection.CONNECTED, batteryPercent = 82)
        }
        return true
    }

    override suspend fun disconnect() {
        _state.update { it.copy(connection = GlassesConnection.NOT_CONNECTED) }
    }

    override fun requestDisconnect() {
        pendingDisconnect?.cancel()
        pendingDisconnect = scope.launch { disconnect() }
    }

    override suspend fun captureStillJpeg(maxDimensionPx: Int, jpegQuality: Int): ByteArray? {
        if (_state.value.connection != GlassesConnection.CONNECTED) {
            _state.update { it.copy(lastError = GlassesError.GLASSES_NOT_CONNECTED) }
            return null
        }
        _state.update { it.copy(connection = GlassesConnection.STREAMING) }
        delay(400) // stream spin-up + capture
        _state.update { it.copy(connection = GlassesConnection.CONNECTED) }
        // Tiny valid JPEG header + filler: enough for the gateway's
        // content-type/size checks in mock round-trips against a dev host.
        return byteArrayOf(0xFF.toByte(), 0xD8.toByte(), 0xFF.toByte(), 0xE0.toByte()) +
            ByteArray(128) { 0x11 } + byteArrayOf(0xFF.toByte(), 0xD9.toByte())
    }
}
