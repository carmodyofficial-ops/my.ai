package ai.my.glasses.wearables

import kotlinx.coroutines.flow.StateFlow

/**
 * The ONLY seam between this app and the Meta Wearables Device Access
 * Toolkit. Everything else (UI, gateway client, audio) depends on this
 * interface, never on SDK types — so the app builds and runs end-to-end with
 * [MockWearablesAdapter] on any device, and `MetaDatAdapter` (src/metadat,
 * compiled with -PmetaSdk=true) binds the real glasses.
 *
 * SDK reality this interface encodes (META_SDK_CAPABILITY_MATRIX.md):
 *  - mic/speaker are NOT SDK APIs — they ride OS Bluetooth HFP/A2DP, so this
 *    interface has no audio methods; [ai.my.glasses.audio.VoiceSession] owns that.
 *  - photo capture only works during an active stream, so lookAndAsk() is
 *    modeled as one explicit operation: start stream → capture → stop.
 *  - there is no glasses-side gesture/wake hook for third-party apps.
 */
interface WearablesAdapter {
    val state: StateFlow<GlassesState>

    /**
     * Initialize the SDK. The real SDK requires this AFTER the Android runtime
     * permissions (BLUETOOTH, BLUETOOTH_CONNECT, CAMERA, INTERNET) are granted
     * and BEFORE any other call. `host` is the Activity, typed as Any so this
     * module stays free of Android types.
     */
    fun initialize(host: Any)

    /** One-time registration bounce through the Meta AI app (no-op if done). */
    suspend fun register(host: Any): Boolean

    /**
     * Ensure the glasses-side CAMERA permission is granted (the prompt lives
     * inside the Meta AI app). `requestPermission` is provided by the Activity,
     * which owns the SDK's permission ActivityResult launcher.
     */
    suspend fun ensureCameraPermission(requestPermission: suspend () -> Boolean): Boolean

    /** Connect a device session to the paired glasses. */
    suspend fun connect(): Boolean

    /**
     * Everything the SDK knows about why the glasses are (not) usable, as text
     * for the Diagnostics screen: which adapter is live, whether the Meta AI app
     * is installed, registration state, what devices the SDK can see and their
     * link/compatibility. A connect failure is otherwise indistinguishable from
     * a missing companion app or an unregistered build.
     */
    fun diagnosticSnapshot(): String = "adapter: ${javaClass.simpleName} (no SDK)"

    suspend fun disconnect()

    /**
     * Fire-and-forget teardown, for lifecycle callbacks that cannot suspend.
     *
     * Ordering matters: the adapter is process-wide, so a back-out-and-relaunch
     * (ViewModel cleared, then a new one connecting) would otherwise race a
     * detached disconnect against the new connect — and a disconnect that lands
     * second tears down the session the new Activity just established. A
     * [connect] that arrives before this runs CANCELS it.
     */
    fun requestDisconnect()

    /**
     * Explicit Look-and-Ask capture: starts a short camera stream (capture
     * LED on, firmware-enforced), grabs one frame/photo, stops the stream.
     * Returns JPEG bytes, or null with [GlassesState.lastError] set.
     */
    suspend fun captureStillJpeg(maxDimensionPx: Int = 1280, jpegQuality: Int = 80): ByteArray?
}

data class GlassesState(
    val connection: GlassesConnection = GlassesConnection.NOT_CONNECTED,
    val batteryPercent: Int? = null,   // exposed by DeviceState when available
    val model: String? = null,
    val permissionGranted: Boolean = false, // DAT CAMERA permission
    val lastError: GlassesError? = null,
    /** Raw SDK error text (e.g. DeviceSessionError.description) — shown in
     *  the UI so device-side session drops aren't a blind "not connected". */
    val lastErrorDetail: String? = null,
    /** App-to-MetaAI registration, which gates EVERYTHING else: with no
     *  registration there is no device list and createSession always fails.
     *  Tracked separately from [connection] because "not registered" and
     *  "registered but the glasses are asleep" need opposite user actions. */
    val registration: GlassesRegistration = GlassesRegistration.UNKNOWN,
    /** The SDK's initialize() succeeded. False means no SDK call will ever
     *  work — usually a missing/bad MetaAppID + ClientToken in the manifest. */
    val sdkReady: Boolean = false,
)

enum class GlassesConnection { NOT_CONNECTED, REGISTERING, CONNECTING, CONNECTED, STREAMING }

/** Mirrors the SDK's RegistrationState, plus UNKNOWN for "SDK not up yet". */
enum class GlassesRegistration { UNKNOWN, UNAVAILABLE, AVAILABLE, REGISTERING, REGISTERED }

enum class GlassesError {
    GLASSES_NOT_CONNECTED,
    GLASSES_PERMISSION_DENIED,
    META_DEVELOPER_MODE_REQUIRED,
    BLUETOOTH_AUDIO_UNAVAILABLE,
    CAPTURE_FAILED,
    /** The Meta AI companion app isn't installed — the SDK talks to the glasses
     *  only through it, so nothing works until it is. */
    META_AI_NOT_INSTALLED,
    /** The SDK can see the glasses but their firmware is too old for DAT. */
    GLASSES_UPDATE_REQUIRED,
    /** Registration was attempted and refused (not merely unavailable). */
    REGISTRATION_FAILED,
    /** The app never got BLUETOOTH_CONNECT, so the SDK was never initialized. */
    BLUETOOTH_PERMISSION_DENIED,
}
