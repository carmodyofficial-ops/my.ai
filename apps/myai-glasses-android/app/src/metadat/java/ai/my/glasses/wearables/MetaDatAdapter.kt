package ai.my.glasses.wearables

import android.app.Activity
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import com.meta.wearable.dat.camera.Stream
import com.meta.wearable.dat.camera.addStream
import com.meta.wearable.dat.camera.types.PhotoData
import com.meta.wearable.dat.camera.types.StreamConfiguration
import com.meta.wearable.dat.camera.types.StreamState
import com.meta.wearable.dat.camera.types.VideoQuality
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.selectors.AutoDeviceSelector
import com.meta.wearable.dat.core.selectors.DeviceSelector
import com.meta.wearable.dat.core.session.DeviceSession
import com.meta.wearable.dat.core.session.DeviceSessionState
import com.meta.wearable.dat.core.types.Permission
import com.meta.wearable.dat.core.types.PermissionStatus
import com.meta.wearable.dat.core.types.RegistrationState
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.onStart
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Real-glasses adapter over the Meta Wearables Device Access Toolkit v0.8,
 * written against the official CameraAccess sample's API usage.
 * Compiled only with `-PmetaSdk=true`.
 *
 * Look-and-Ask maps onto the SDK's constraint that photo capture requires an
 * ACTIVE stream: start session → addStream(LOW/7fps) → await STREAMING →
 * capturePhoto() → stop stream. LOW quality keeps stream spin-up quick; the
 * still we get back is full capture resolution regardless.
 *
 * PROCESS-SCOPED: exactly one instance exists (see [GlassesAdapters]). The SDK
 * permits one DeviceSession per device, so a per-Activity adapter races itself
 * across configuration changes — two sessions contending for one pair of
 * glasses, one evicting the other (connect tone → immediate disconnect tone).
 *
 * HARDWARE-VALIDATION PENDING: compiles against the real SDK, but has not been
 * exercised on physical glasses from this environment.
 */
class MetaDatAdapter : WearablesAdapter {

    private companion object {
        const val TAG = "MetaDatAdapter"
        const val STREAM_READY_TIMEOUT_MS = 15_000L
        const val CAPTURE_TIMEOUT_MS = 20_000L
        const val SESSION_START_TIMEOUT_MS = 20_000L
        const val ERROR_SUBSCRIBE_TIMEOUT_MS = 2_000L
    }

    private val _state = MutableStateFlow(GlassesState())
    override val state: StateFlow<GlassesState> = _state

    // Process-lived by design: this adapter is a singleton, so the scope's
    // lifetime is the app's rather than any Activity's.
    private val scope = CoroutineScope(SupervisorJob())
    private val deviceSelector: DeviceSelector by lazy { AutoDeviceSelector() }

    /** Serializes connect/disconnect. The SDK allows one session per device,
     *  and an unguarded second createSession() displaces the first. */
    private val sessionLock = Mutex()

    /** Written under [sessionLock] but read from the monitoring collectors and
     *  from captureStillJpeg, so publication has to be visible across threads. */
    @Volatile private var session: DeviceSession? = null

    private var sessionErrorJob: Job? = null
    private var sessionStateJob: Job? = null
    private var deviceMetaJob: Job? = null
    @Volatile private var pendingDisconnect: Job? = null
    private var initialized = false
    private var monitoring = false

    override fun initialize(host: Any) {
        val activity = host as Activity
        // REQUIRED before any other Wearables call, and only after the Android
        // runtime permissions have been granted (the Activity does that first).
        // Guarded: MainActivity's permission callback re-fires on every
        // recreation, and a second initialize() would rebind the SDK to an
        // Activity that is about to be destroyed.
        if (initialized) return
        initialized = true
        Wearables.initialize(activity)
        startMonitoring()
    }

    private fun startMonitoring() {
        if (monitoring) return
        monitoring = true

        scope.launch {
            Wearables.registrationState.collect { reg ->
                _state.update { s ->
                    s.copy(
                        connection = when (reg) {
                            RegistrationState.REGISTERING -> GlassesConnection.REGISTERING
                            else -> s.connection
                        },
                        // UNAVAILABLE = this app can't register at all: the Meta
                        // AI app is missing/too old, or Developer Mode is off (an
                        // unpublished app needs it). AVAILABLE just means "not
                        // registered yet" — register() drives that.
                        lastError = if (reg == RegistrationState.UNAVAILABLE)
                            GlassesError.META_DEVELOPER_MODE_REQUIRED else s.lastError,
                    )
                }
            }
        }

        scope.launch {
            deviceSelector.activeDeviceFlow().collect { device ->
                // Cancel-and-relaunch, never stack: this collector fires on every
                // selector emission, and the old code leaked a metadata collector
                // each time.
                deviceMetaJob?.cancel()
                deviceMetaJob = null
                if (device == null) {
                    // A live OR IN-FLIGHT session is the authority on connection
                    // state. The selector emits transient nulls (BT blip, device
                    // re-selection); letting those through flapped the UI and
                    // re-triggered connect() underneath a healthy session. Note
                    // the session is NOT_STARTED for up to SESSION_START_TIMEOUT_MS
                    // during a connect, so checking only for STARTED would still
                    // let a blip clobber CONNECTING.
                    val busy = session?.state?.value == DeviceSessionState.STARTED ||
                        _state.value.connection == GlassesConnection.CONNECTING
                    if (!busy) {
                        _state.update {
                            it.copy(
                                connection = GlassesConnection.NOT_CONNECTED,
                                batteryPercent = null,
                                lastError = GlassesError.GLASSES_NOT_CONNECTED,
                            )
                        }
                    }
                } else {
                    deviceMetaJob = scope.launch {
                        Wearables.devicesMetadata[device]?.collect { meta ->
                            _state.update { it.copy(model = meta.name) }
                        }
                    }
                }
            }
        }
    }

    override suspend fun register(host: Any): Boolean {
        val activity = host as Activity
        if (Wearables.registrationState.value == RegistrationState.REGISTERED) return true
        _state.update { it.copy(connection = GlassesConnection.REGISTERING) }
        // Bounces into the Meta AI app; returns via the myai-glasses:// callback.
        Wearables.startRegistration(activity)
        val registered = withTimeoutOrNull(120_000L) {
            Wearables.registrationState.first { it == RegistrationState.REGISTERED }
            true
        } ?: false
        if (!registered) {
            _state.update {
                it.copy(
                    connection = GlassesConnection.NOT_CONNECTED,
                    lastError = GlassesError.META_DEVELOPER_MODE_REQUIRED)
            }
        }
        return registered
    }

    override suspend fun ensureCameraPermission(
        requestPermission: suspend () -> Boolean,
    ): Boolean {
        val current = Wearables.checkPermissionStatus(Permission.CAMERA).getOrNull()
        if (current == PermissionStatus.Granted) {
            _state.update { it.copy(permissionGranted = true, lastError = null) }
            return true
        }
        // The prompt is shown by the Meta AI app; the Activity owns the launcher.
        val granted = requestPermission()
        _state.update {
            it.copy(
                permissionGranted = granted,
                lastError = if (granted) null else GlassesError.GLASSES_PERMISSION_DENIED,
            )
        }
        return granted
    }

    override suspend fun connect(): Boolean = withContext(Dispatchers.IO) {
        // OFF-MAIN, always: the DAT SDK's session primitives below
        // (createSession/start, and stop() in teardown) are synchronous binder
        // IPC to the Meta AI app plus Bluetooth GATT work, and the SDK delivers
        // some callbacks on the main thread. Run on the caller's dispatcher —
        // every caller is on viewModelScope (Main.immediate) — they block and can
        // self-deadlock the looper (ANR → force-close). This is exactly the
        // "app freezes after refreshing more than once" bug: the first connect
        // hits the STARTED fast-path and does no SDK call, a later refresh that
        // must createSession runs the blocking path on main.
        // Beat any teardown that a departing ViewModel scheduled: the adapter
        // outlives the ViewModel, so a back-out-and-relaunch would otherwise let
        // that disconnect land on the session we are about to establish.
        pendingDisconnect?.cancel()
        sessionLock.withLock {
            // Everything runs under the lock, so a connect already in flight is
            // awaited rather than duplicated. The previous guard ran unlocked and
            // only caught an ALREADY-STARTED session: a second caller arriving
            // mid-start sailed past it, created a rival session, and orphaned the
            // first — one of the two ways the glasses got a connect tone followed
            // immediately by a disconnect tone.
            session?.let { existing ->
                if (existing.state.value == DeviceSessionState.STARTED) {
                    return@withLock true
                }
                // Half-open session from a previous attempt: tear it down so this
                // attempt starts clean rather than stacking on top of it.
                teardownSessionLocked()
            }

            _state.update {
                it.copy(connection = GlassesConnection.CONNECTING, lastErrorDetail = null)
            }

            val created = Wearables.createSession(deviceSelector).getOrNull()
            if (created == null) {
                _state.update {
                    it.copy(
                        connection = GlassesConnection.NOT_CONNECTED,
                        lastError = GlassesError.GLASSES_NOT_CONNECTED)
                }
                return@withLock false
            }
            session = created

            // Subscribe to the session's error stream and WAIT until the collector
            // is actually attached before calling start(). scope.launch does not
            // subscribe synchronously, so errors emitted during startup — the ones
            // that say *why* the device refused (firmware update required, session
            // ended by device, Meta AI takeover) — landed before any collector
            // existed and were dropped. That is why a failed connect surfaced as a
            // blind "not connected" with nothing in lastErrorDetail.
            val subscribed = CompletableDeferred<Unit>()
            sessionErrorJob = scope.launch {
                created.errors
                    .onStart { subscribed.complete(Unit) }
                    .collect { err ->
                        Log.e(TAG, "session error: ${err.description}")
                        _state.update { it.copy(lastErrorDetail = err.description) }
                    }
            }
            // Bounded: a wait that never completes must not wedge connect() —
            // worst case we start unsubscribed, exactly as before.
            withTimeoutOrNull(ERROR_SUBSCRIBE_TIMEOUT_MS) { subscribed.await() }

            created.start()

            val started = withTimeoutOrNull(SESSION_START_TIMEOUT_MS) {
                created.state.first { it == DeviceSessionState.STARTED }
                true
            } ?: false

            if (!started) {
                // Don't keep a zombie session — retries must begin clean, and a
                // stacked half-open session re-triggers the glasses' connect tone.
                teardownSessionLocked()
            } else {
                // Track the session for its whole life: a later device-side stop
                // (fold, sleep, Meta AI takeover) must flip the UI back.
                sessionStateJob?.cancel()
                sessionStateJob = scope.launch {
                    created.state.collect { st ->
                        _state.update {
                            it.copy(
                                connection = when (st) {
                                    DeviceSessionState.STARTED,
                                    DeviceSessionState.PAUSED -> GlassesConnection.CONNECTED
                                    else -> GlassesConnection.NOT_CONNECTED
                                },
                            )
                        }
                    }
                }
            }
            _state.update {
                it.copy(
                    connection = if (started) GlassesConnection.CONNECTED
                                 else GlassesConnection.NOT_CONNECTED,
                    lastError = if (started) null else GlassesError.GLASSES_NOT_CONNECTED,
                )
            }
            started
        }
    }

    override suspend fun disconnect() = sessionLock.withLock {
        teardownSessionLocked()
        _state.update { it.copy(connection = GlassesConnection.NOT_CONNECTED) }
    }

    override fun requestDisconnect() {
        pendingDisconnect?.cancel()
        // On the adapter's own scope, so a departing ViewModel doesn't have to
        // leak a detached one. connect() cancels this if it gets there first.
        pendingDisconnect = scope.launch { disconnect() }
    }

    /**
     * Stop and forget the current session. Caller must hold [sessionLock].
     * The state collector is cancelled BEFORE stop() so the NOT_CONNECTED it
     * would observe cannot land on top of a subsequent connect()'s state.
     */
    private suspend fun teardownSessionLocked() {
        sessionStateJob?.cancel(); sessionStateJob = null
        sessionErrorJob?.cancel(); sessionErrorJob = null
        // Detach FIRST, then stop under NonCancellable. connect() cancels a pending
        // requestDisconnect(), and if that cancellation landed while stop() was
        // suspended, the old order left `session` non-null with both monitor jobs
        // already dead — connect()'s STARTED fast path would then hand back a
        // session nobody was watching, so a device-side drop could never flip the
        // UI back and its errors were dropped.
        val dying = session
        session = null
        if (dying != null) {
            withContext(NonCancellable) { runCatching { dying.stop() } }
        }
    }

    override suspend fun captureStillJpeg(maxDimensionPx: Int, jpegQuality: Int): ByteArray? =
      withContext(Dispatchers.IO) {
        // OFF-MAIN: addStream/start/capturePhoto are blocking SDK + BT calls. On
        // the caller's Main dispatcher (lookAndAsk runs on viewModelScope) they
        // freeze the UI mid-capture — same root cause as connect().
        val active = session
        if (active == null || active.state.value != DeviceSessionState.STARTED) {
            _state.update { it.copy(lastError = GlassesError.GLASSES_NOT_CONNECTED) }
            return@withContext null
        }

        // Photo capture requires an active stream (SDK constraint). LOW/7fps
        // gets us to STREAMING quickly; the still itself is full capture res.
        val stream: Stream = active.addStream(
            StreamConfiguration(videoQuality = VideoQuality.LOW, frameRate = 7)
        ).getOrNull() ?: run {
            _state.update { it.copy(lastError = GlassesError.CAPTURE_FAILED) }
            return@withContext null
        }

        try {
            _state.update { it.copy(connection = GlassesConnection.STREAMING) }
            stream.start()

            val streaming = withTimeoutOrNull(STREAM_READY_TIMEOUT_MS) {
                stream.state.first { it == StreamState.STREAMING }
                true
            } ?: false
            if (!streaming) {
                _state.update { it.copy(lastError = GlassesError.CAPTURE_FAILED) }
                return@withContext null
            }

            val photo = withTimeoutOrNull(CAPTURE_TIMEOUT_MS) {
                stream.capturePhoto().getOrNull()
            }
            if (photo == null) {
                _state.update { it.copy(lastError = GlassesError.CAPTURE_FAILED) }
                return@withContext null
            }

            val bitmap = photo.toBitmap()
            if (bitmap == null) {
                _state.update { it.copy(lastError = GlassesError.CAPTURE_FAILED) }
                return@withContext null
            }
            _state.update { it.copy(lastError = null) }
            bitmap.downscaledJpeg(maxDimensionPx, jpegQuality)
        } finally {
            // Always stop the stream — leaving it running keeps the capture LED
            // on and drains the glasses battery.
            runCatching { stream.stop() }
            // Only claim CONNECTED if the session actually still is: a capture
            // that failed *because* the session died must not paint over that.
            if (session?.state?.value == DeviceSessionState.STARTED) {
                _state.update { it.copy(connection = GlassesConnection.CONNECTED) }
            }
        }
    }

    /** PhotoData arrives as either a Bitmap or HEIC bytes, depending on device. */
    private fun PhotoData.toBitmap(): Bitmap? = when (this) {
        is PhotoData.Bitmap -> this.bitmap
        is PhotoData.HEIC -> {
            val bytes = ByteArray(data.remaining())
            data.get(bytes)
            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
        }
    }

    /** Downscale + JPEG-compress on the phone before it crosses the network. */
    private fun Bitmap.downscaledJpeg(maxDimensionPx: Int, quality: Int): ByteArray {
        val longest = maxOf(width, height)
        val scaled = if (longest > maxDimensionPx && longest > 0) {
            val ratio = maxDimensionPx.toFloat() / longest
            Bitmap.createScaledBitmap(
                this, (width * ratio).toInt().coerceAtLeast(1),
                (height * ratio).toInt().coerceAtLeast(1), true)
        } else this
        return ByteArrayOutputStream().use { out ->
            scaled.compress(Bitmap.CompressFormat.JPEG, quality, out)
            out.toByteArray()
        }
    }
}
