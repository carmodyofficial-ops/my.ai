package ai.my.glasses.wearables

import android.app.Activity
import android.content.Context
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
import com.meta.wearable.dat.core.types.Device
import com.meta.wearable.dat.core.types.DeviceCompatibility
import com.meta.wearable.dat.core.types.DeviceIdentifier
import com.meta.wearable.dat.core.types.Permission
import com.meta.wearable.dat.core.types.PermissionStatus
import com.meta.wearable.dat.core.types.RegistrationError
import com.meta.wearable.dat.core.types.RegistrationState
import com.meta.wearable.dat.core.types.WearablesError
import java.io.ByteArrayOutputStream
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
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
        /** Ceiling on the round trip through the Meta AI app. */
        const val REGISTRATION_TIMEOUT_MS = 120_000L
        /** How long to let registrationState leave its initial UNAVAILABLE
         *  before concluding registration really is unavailable. */
        const val REGISTRATION_SETTLE_TIMEOUT_MS = 8_000L
        /** The companion app the DAT SDK talks through (release, then debug). */
        val META_AI_PACKAGES = listOf("com.facebook.stella", "com.facebook.stella_debug")
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

    /** For the PackageManager lookups in [diagnosticSnapshot] — the adapter is
     *  process-scoped, so it holds the APPLICATION context, never the Activity. */
    @Volatile private var appContext: Context? = null

    /** Last device the selector reported on, as text. Kept apart from
     *  [GlassesState.lastErrorDetail] so a device note can't overwrite a real
     *  session error (and vice versa). */
    @Volatile private var deviceSummary: String? = null

    /**
     * The most recent registration failure — the single most useful fact when
     * the glasses "just don't connect" (see [register]).
     *
     * A StateFlow rather than a plain field because [register] waits on it: the
     * SDK reports failures on a stream SEPARATE from registrationState, and a
     * refusal does not always move that state. Waiting on the state alone would
     * sit out the full two-minute timeout with the reason already in hand.
     */
    private val registrationErrors = MutableStateFlow<RegistrationError?>(null)

    /** Per-device metadata collectors, keyed so a device leaving the set takes
     *  its collector with it rather than leaking one per emission. */
    private val seenDeviceJobs = mutableMapOf<DeviceIdentifier, Job>()
    @Volatile private var knownDevices = 0

    override fun initialize(host: Any) {
        val activity = host as Activity
        // REQUIRED before any other Wearables call, and only after the Android
        // runtime permissions have been granted (the Activity does that first).
        // Guarded: MainActivity's permission callback re-fires on every
        // recreation, and a second initialize() would rebind the SDK to an
        // Activity that is about to be destroyed.
        if (initialized) return
        initialized = true
        appContext = activity.applicationContext
        // initialize() returns a DatResult, and its failure was being discarded.
        // A failed init (bad/missing MetaAppID + ClientToken in the manifest)
        // makes every later SDK call a no-op, which the user only ever saw as a
        // permanent "not connected" — so record it and stop claiming SDK-ready.
        val result = runCatching { Wearables.initialize(activity) }
        val initError = result.getOrNull()?.errorOrNull()
        val threw = result.exceptionOrNull()
        // ALREADY_INITIALIZED is benign: the SDK is up, which is all we need.
        val ok = threw == null &&
            (initError == null || initError == WearablesError.ALREADY_INITIALIZED)
        if (!ok) {
            val detail = threw?.message ?: initError?.description ?: "unknown"
            Log.e(TAG, "Wearables.initialize failed: $detail")
            _state.update {
                it.copy(sdkReady = false, lastErrorDetail = "SDK init failed: $detail")
            }
            return   // nothing to monitor; every SDK call would fail anyway
        }
        _state.update { it.copy(sdkReady = true) }
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
                        registration = reg.toGlassesRegistration(),
                        // UNAVAILABLE = this app can't register at all: the Meta
                        // AI app is missing/too old, or Developer Mode is off (an
                        // unpublished app needs it). AVAILABLE just means "not
                        // registered yet" — register() drives that.
                        lastError = when {
                            reg != RegistrationState.UNAVAILABLE -> s.lastError
                            // Distinguish the two ways to be UNAVAILABLE. Telling
                            // someone with no Meta AI app to enable Developer Mode
                            // sends them looking for a setting that isn't there.
                            !metaAiInstalled() -> GlassesError.META_AI_NOT_INSTALLED
                            else -> GlassesError.META_DEVELOPER_MODE_REQUIRED
                        },
                    )
                }
            }
        }

        // The SDK's own account of why registration failed. Nothing collected
        // this stream, so META_AI_NOT_INSTALLED / INCOMPATIBLE_SDK_LEVEL /
        // FAILED_TO_REGISTER were all emitted into the void and the app showed
        // a blank "not connected" instead — the registration-side twin of the
        // session-error bug fixed in connect().
        scope.launch {
            Wearables.registrationErrorStream.collect { err ->
                Log.e(TAG, "registration error: ${err.name}")
                registrationErrors.value = err
                _state.update {
                    it.copy(
                        lastErrorDetail = "registration: ${err.description}",
                        lastError = err.toGlassesError() ?: it.lastError,
                    )
                }
            }
        }

        // Every device the SDK can see, not just the selector's ACTIVE one.
        // Glasses whose firmware is too old for DAT never become active, so
        // watching only the active device meant DEVICE_UPDATE_REQUIRED — a
        // named, fixable cause — could never be observed. (This is the shape
        // Meta's own samples use.)
        scope.launch {
            Wearables.devices.collect { ids ->
                knownDevices = ids.size
                seenDeviceJobs.values.forEach { it.cancel() }
                seenDeviceJobs.clear()
                ids.forEach { id ->
                    seenDeviceJobs[id] = scope.launch {
                        Wearables.devicesMetadata[id]?.collect { meta ->
                            if (meta.compatibility == DeviceCompatibility.DEVICE_UPDATE_REQUIRED) {
                                _state.update {
                                    it.copy(
                                        lastError = GlassesError.GLASSES_UPDATE_REQUIRED,
                                        lastErrorDetail =
                                            "${meta.name.ifEmpty { "glasses" }} needs a firmware update",
                                    )
                                }
                            }
                        }
                    }
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
                    deviceSummary = null
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
                            deviceSummary = meta.summary()
                            _state.update {
                                it.copy(
                                    model = meta.name,
                                    // Stale firmware is a distinct, fixable cause
                                    // of "createSession returns null" — surface it
                                    // instead of letting it read as "not connected".
                                    lastError = if (meta.compatibility ==
                                            DeviceCompatibility.DEVICE_UPDATE_REQUIRED)
                                        GlassesError.GLASSES_UPDATE_REQUIRED
                                    else it.lastError,
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    override suspend fun register(host: Any): Boolean {
        val activity = host as Activity
        if (!_state.value.sdkReady) return false
        if (Wearables.registrationState.value == RegistrationState.REGISTERED) return true

        // Fail fast when the SDK says registration isn't even offered — the old
        // code called startRegistration() anyway and then sat on a 120-second
        // timeout, two minutes of "registering…" with no Meta AI app in sight,
        // before reporting one generic Developer-Mode hint.
        //
        // But UNAVAILABLE is ALSO what registrationState reports before the SDK
        // has finished binding to the Meta AI app (it is the flow's initial
        // value), so a tap right after launch would otherwise be told the app is
        // missing. Give it a moment to settle first, and only then give up.
        if (Wearables.registrationState.value == RegistrationState.UNAVAILABLE) {
            _state.update { it.copy(connection = GlassesConnection.REGISTERING) }
            val settled = withTimeoutOrNull(REGISTRATION_SETTLE_TIMEOUT_MS) {
                Wearables.registrationState.first { it != RegistrationState.UNAVAILABLE }
            }
            if (settled == null) {
                val why = if (!metaAiInstalled()) GlassesError.META_AI_NOT_INSTALLED
                          else GlassesError.META_DEVELOPER_MODE_REQUIRED
                _state.update {
                    it.copy(connection = GlassesConnection.NOT_CONNECTED, lastError = why)
                }
                return false
            }
            if (settled == RegistrationState.REGISTERED) return true
        }

        registrationErrors.value = null
        _state.update {
            it.copy(connection = GlassesConnection.REGISTERING, lastErrorDetail = null)
        }
        // Hands off to the Meta AI app, which registers this app over the DAT
        // service binding and flips registrationState. Fire-and-forget by design.
        Wearables.startRegistration(activity)

        // Settle on the FIRST of: registered, refused, or the user never
        // finishing in the Meta AI app. Watching only for REGISTERED meant a
        // refusal still cost the full timeout before saying anything — and the
        // refusal arrives on registrationErrors, which is why both are combined
        // here rather than waiting on the state alone.
        val outcome = withTimeoutOrNull(REGISTRATION_TIMEOUT_MS) {
            combine(Wearables.registrationState, registrationErrors) { state, err ->
                state to err
            }.first { (state, err) ->
                state == RegistrationState.REGISTERED ||
                    (err != null && state != RegistrationState.REGISTERING)
            }
        }
        val registered = outcome?.first == RegistrationState.REGISTERED

        if (registered) {
            // A retry that worked must retract the reason the last one failed,
            // or the "enable Developer Mode" banner outlives its cause.
            _state.update { it.copy(lastError = null, lastErrorDetail = null) }
        } else {
            // The error collector has usually already set a precise lastError by
            // now; only fall back to a guess when it hasn't.
            _state.update {
                it.copy(
                    connection = GlassesConnection.NOT_CONNECTED,
                    lastError = registrationErrors.value?.toGlassesError()
                        ?: it.lastError
                        ?: GlassesError.META_DEVELOPER_MODE_REQUIRED,
                )
            }
        }
        return registered
    }

    /** The SDK reaches the glasses only through the Meta AI companion app; if
     *  it isn't installed, no amount of retrying will help. The DAT AAR already
     *  declares the `<queries>` entries that make these packages visible. */
    private fun metaAiInstalled(): Boolean {
        val pm = appContext?.packageManager ?: return true   // unknown: don't accuse
        return META_AI_PACKAGES.any { pkg ->
            runCatching { pm.getPackageInfo(pkg, 0) }.isSuccess
        }
    }

    private fun RegistrationState.toGlassesRegistration(): GlassesRegistration = when (this) {
        RegistrationState.UNAVAILABLE -> GlassesRegistration.UNAVAILABLE
        RegistrationState.AVAILABLE -> GlassesRegistration.AVAILABLE
        RegistrationState.REGISTERING -> GlassesRegistration.REGISTERING
        RegistrationState.REGISTERED -> GlassesRegistration.REGISTERED
        RegistrationState.UNREGISTERING -> GlassesRegistration.AVAILABLE
    }

    /** Null where the SDK error carries no action for the user (it stays in
     *  lastErrorDetail either way). */
    private fun RegistrationError.toGlassesError(): GlassesError? = when (this) {
        RegistrationError.META_AI_NOT_INSTALLED -> GlassesError.META_AI_NOT_INSTALLED
        RegistrationError.INCOMPATIBLE_SDK_LEVEL -> GlassesError.GLASSES_UPDATE_REQUIRED
        RegistrationError.FAILED_TO_REGISTER -> GlassesError.REGISTRATION_FAILED
        RegistrationError.ALREADY_REGISTERED -> null   // benign
        else -> null
    }

    private fun Device.summary(): String =
        "$name  type=$deviceType  link=$linkState  fw=$firmwareInfo  compat=$compatibility"

    override suspend fun ensureCameraPermission(
        requestPermission: suspend () -> Boolean,
    ): Boolean {
        val check = Wearables.checkPermissionStatus(Permission.CAMERA)
        val current = check.getOrNull()
        if (current == PermissionStatus.Granted) {
            _state.update { it.copy(permissionGranted = true, lastError = null) }
            return true
        }
        // NO_DEVICE / NO_DEVICE_WITH_CONNECTION / META_AI_NOT_INSTALLED arrive
        // here and used to be dropped by getOrNull(), so a permission check that
        // failed because the glasses were asleep looked like a user denial.
        check.errorOrNull()?.let { err ->
            Log.w(TAG, "checkPermissionStatus: ${err.name}")
            _state.update { it.copy(lastErrorDetail = "permission: ${err.description}") }
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

    /**
     * Everything the SDK will tell us about why the glasses are unusable,
     * gathered in one place. This is the report to read FIRST when the answer
     * to "why won't they connect" isn't obvious: it separates "no companion
     * app" from "not registered" from "registered but no device in range".
     */
    override fun diagnosticSnapshot(): String = buildString {
        val s = _state.value
        appendLine("adapter: MetaDatAdapter (Meta DAT SDK)")
        appendLine("sdk initialized: ${s.sdkReady}")
        val pm = appContext?.packageManager
        val metaAi = META_AI_PACKAGES.firstNotNullOfOrNull { pkg ->
            runCatching { pm?.getPackageInfo(pkg, 0) }.getOrNull()?.let { "$pkg ${it.versionName}" }
        }
        appendLine("Meta AI app: ${metaAi ?: "NOT INSTALLED (or not visible)"}")
        appendLine("dev mode: ${runCatching { Wearables.isDevMode.toString() }.getOrDefault("?")}")
        appendLine("registration: ${s.registration}" +
            (registrationErrors.value?.let { "  lastError=${it.name}" } ?: ""))
        appendLine("devices seen by SDK: $knownDevices")
        deviceSummary?.let { appendLine("active device: $it") }
        appendLine("session: ${session?.state?.value ?: "none"}")
        appendLine("connection: ${s.connection}  glasses-camera-permission=${s.permissionGranted}")
        s.lastError?.let { appendLine("lastError: $it") }
        append(s.lastErrorDetail?.let { "detail: $it" } ?: "detail: —")
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
