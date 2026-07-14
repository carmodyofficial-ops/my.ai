package ai.my.glasses

import android.content.Context
import androidx.activity.ComponentActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import ai.my.glasses.audio.GlassesControlService
import ai.my.glasses.audio.GlassesGestures
import ai.my.glasses.audio.MicForegroundService
import ai.my.glasses.audio.VoiceSession
import ai.my.glasses.core.AppState
import ai.my.glasses.core.ConnectionReducer
import ai.my.glasses.core.CredentialStore
import ai.my.glasses.core.Event
import ai.my.glasses.core.Failure
import ai.my.glasses.core.PairingPayload
import ai.my.glasses.net.ChatItem
import ai.my.glasses.net.DiscoveredHost
import ai.my.glasses.net.EnrollRequestResult
import ai.my.glasses.net.EnrollStatusResult
import ai.my.glasses.net.GatewayClient
import ai.my.glasses.net.GatewayEvent
import ai.my.glasses.net.HostDiscovery
import ai.my.glasses.net.NoteItem
import ai.my.glasses.net.PairResult
import ai.my.glasses.net.TaskItem
import ai.my.glasses.net.TranscribeResult
import ai.my.glasses.net.VisionItem
import ai.my.glasses.net.VisionResult
import ai.my.glasses.wearables.GlassesAdapters
import ai.my.glasses.wearables.GlassesConnection
import ai.my.glasses.wearables.GlassesError
import ai.my.glasses.wearables.GlassesHost
import ai.my.glasses.wearables.WearablesAdapter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext

data class UiState(
    val paired: Boolean = false,
    val canTalk: Boolean = false,
    val busy: Boolean = false,
    val refreshing: Boolean = false,
    val listening: Boolean = false,
    val glassesLabel: String = "not connected",
    val glassesDetail: String? = null,
    val hostLabel: String = "not paired",
    val modelLabel: String = "—",
    val voiceLabel: String = "—",
    val sttAvailable: Boolean = false,
    val ttsAvailable: Boolean = false,
    val visionAvailable: Boolean = false,
    /** The host's chat model is loaded and serving. When false (Ollama down / no
     *  model), the Ask/Talk inputs are disabled and a retry is offered rather than
     *  letting a tap fail silently. */
    val llmReady: Boolean = false,
    val storeTranscript: Boolean = true,
    val lastQuestion: String = "",
    val lastResponse: String = "",
    val failure: Failure? = null,
    /** A deep-link/QR pairing awaiting explicit user confirmation. Non-null →
     *  the UI shows a confirm dialog. Pairing NEVER proceeds without it. */
    val pairingPrompt: PairingPrompt? = null,
    // LAN discover + approve enrollment:
    val scanning: Boolean = false,
    val discoveredHosts: List<DiscoveredHost> = emptyList(),
    /** Non-null while waiting for the host admin to approve this device. */
    val enroll: EnrollState? = null,
    // Home productivity checklists + nav-drawer history:
    val notes: List<NoteItem> = emptyList(),
    val tasks: List<TaskItem> = emptyList(),
    val chatHistory: List<ChatItem> = emptyList(),
    val visionHistory: List<VisionItem> = emptyList(),
)

/** Shown while an enrollment is awaiting approval on the host. */
data class EnrollState(
    val hostName: String,
    val verifyCode: String,
    val status: String,   // human-readable progress line
)

/** Ports the discovery scan probes per host: the TLS lan_proxy first, then the
 *  plain-HTTP dev proxy. Matches the documented my.ai LAN endpoints. */
private val HOST_SCAN_PORTS = listOf(7443, 7000)

/** A pairing the user must confirm before it replaces their credentials. */
data class PairingPrompt(
    val host: String,
    val tls: Boolean,
    val replacesExisting: Boolean,
    val rawJson: String,
)

class MainViewModel(
    private val appContext: Context,
    private val credentials: CredentialStore,
    private val adapter: WearablesAdapter,
) : ViewModel() {

    private val client = GatewayClient(
        baseUrl = { credentials.hostBaseUrl ?: "" },
        token = { credentials.deviceToken },
        certSha256 = { credentials.certSha256 },
    )

    private var app = AppState()
    private val _ui = MutableStateFlow(UiState())
    val ui: StateFlow<UiState> = _ui
    private var streamJob: Job? = null
    private var bootstrapJob: Job? = null
    /** Set once registration+connect has run to success. onAndroidPermissionsGranted
     *  re-fires on every Activity recreation (rotation, dark-mode, return from
     *  Settings); without this, each one re-ran register()/connect(), which on the
     *  mock adapter flapped CONNECTING→CONNECTED and spuriously dispatched
     *  GlassesDisconnected — killing an in-flight recording on rotation. */
    @Volatile private var bootstrapped = false

    /**
     * Owned here, NOT by the Activity. It used to be a `by lazy` Activity field
     * handed over via attachAudio(), so a rotation mid-utterance abandoned a
     * VoiceSession with a hot AudioRecord and an SCO route nobody would ever
     * clear — the new Activity's VoiceSession had no idea either existed. The
     * mic must outlive the Activity for exactly as long as the ViewModel does.
     */
    private val voice = VoiceSession(appContext)

    /** Serializes the mic lifecycle. Acquiring the SCO route now genuinely
     *  suspends (up to 3 s), so without this a second tap during that window
     *  would open a second recording. */
    private val micLock = Mutex()

    /** The CURRENT Activity's host — it owns the DAT permission launcher, which
     *  dies with its Activity, so this is re-attached on every recreation. The
     *  adapter is process-wide (GlassesAdapters.shared) and is NOT re-attached. */
    private var host: GlassesHost? = null

    init {
        if (credentials.isPaired) {
            dispatch(Event.HostPaired)
            refreshHealth()
            GlassesControlService.start(appContext)  // arm the touchpad trigger
        }
        // Hands-free trigger: a long hold on the glasses touchpad (a held media
        // button captured by GlassesControlService) toggles the voice loop —
        // hold once to start listening, hold again to send. Works with the app
        // backgrounded, which is the point. A single tap plays/pauses music and
        // never reaches here.
        viewModelScope.launch {
            GlassesGestures.talk.collect {
                if (!app.hostPaired) return@collect
                if (_ui.value.listening) stopListening() else startListening()
            }
        }
        viewModelScope.launch {
            // Only transitions matter. The old code re-dispatched on every
            // emission (battery, model name, error text), and treated CONNECTING
            // and REGISTERING as "connected" because they merely aren't
            // NOT_CONNECTED — so the app announced a connection it did not have
            // and then immediately retracted it.
            var wasConnected: Boolean? = null
            var lastGlassesError: GlassesError? = null
            adapter.state.collect { gs ->
                _ui.value = _ui.value.copy(
                    glassesLabel = when (gs.connection) {
                        GlassesConnection.CONNECTED ->
                            (gs.model ?: "connected") +
                                (gs.batteryPercent?.let { " · $it%" } ?: "")
                        GlassesConnection.STREAMING -> "capturing…"
                        GlassesConnection.CONNECTING -> "connecting…"
                        GlassesConnection.REGISTERING -> "registering…"
                        GlassesConnection.NOT_CONNECTED -> "not connected"
                    },
                    glassesDetail = gs.lastErrorDetail,
                )
                val connected = gs.connection == GlassesConnection.CONNECTED ||
                    gs.connection == GlassesConnection.STREAMING
                if (connected != wasConnected) {
                    wasConnected = connected
                    dispatch(
                        if (connected) Event.GlassesConnected else Event.GlassesDisconnected)
                }
                // gs.lastError was read by nobody, so GLASSES_PERMISSION_DENIED and
                // META_DEVELOPER_MODE_REQUIRED could never reach AppState and their
                // recovery hints were dead code. Developer-Mode-off is the most
                // common first-run failure, and it showed only as "not connected".
                if (gs.lastError != lastGlassesError) {
                    lastGlassesError = gs.lastError
                    gs.lastError?.let { dispatch(Event.GatewayError(it.name)) }
                }
            }
        }
    }

    /** Re-attached by each Activity instance: only the permission launcher is
     *  Activity-scoped. */
    fun attachHost(glassesHost: GlassesHost) { host = glassesHost }

    /** Paired host base URL, for opening the full my.ai web UI in a browser. */
    fun hostUrl(): String? = credentials.hostBaseUrl

    /** Called once the Android runtime permissions are granted (SDK is live).
     *  Re-fires on every Activity recreation, so it must be idempotent: the
     *  in-flight guard keeps a rotation from bouncing through the Meta AI app a
     *  second time while the first registration is still pending. */
    fun onAndroidPermissionsGranted(activity: ComponentActivity) {
        if (bootstrapped || bootstrapJob?.isActive == true) return
        bootstrapJob = viewModelScope.launch {
            // Registration is a no-op if already registered; on real glasses it
            // bounces through the Meta AI app. Mock adapter returns immediately.
            if (adapter.register(activity)) {
                // Registration succeeded — the expensive Meta-app bounce is done.
                // Mark bootstrapped so a later Activity recreation doesn't re-run
                // this (reconnect is driven by pull-to-refresh / user actions).
                bootstrapped = true
                adapter.ensureCameraPermission {
                    host?.requestGlassesCameraPermission() ?: false
                }
                adapter.connect()
            }
        }
    }

    private fun dispatch(e: Event) {
        val wasListening = app.listening
        app = ConnectionReducer.reduce(app, e)
        _ui.value = _ui.value.copy(
            paired = app.hostPaired,
            canTalk = app.canTalk,
            failure = app.failure,
            // The reducer owns `listening`; mirroring it here keeps app.listening
            // and ui.listening from drifting into two independent booleans.
            listening = app.listening,
            hostLabel = when {
                !app.hostPaired -> "not paired"
                !app.hostReachable -> "unreachable"
                else -> credentials.hostBaseUrl ?: ""
            },
        )
        // The reducer forces listening=false on glasses loss, gateway error, host
        // loss and credential rejection — "losing glasses mid-capture must stop
        // the mic, never keep recording". Nothing was enforcing that: it only
        // relabelled the button while AudioRecord kept running and SCO stayed up.
        // ListeningChanged is excluded because start/stopListening already own
        // the mic on those paths (and hold micLock while dispatching).
        if (wasListening && !app.listening && e !is Event.ListeningChanged) {
            abortListening()
        }
    }

    /** Force the mic closed after a state change that invalidated the capture. */
    private fun abortListening() {
        viewModelScope.launch {
            micLock.withLock { closeMic(voice) }
        }
    }

    /**
     * A pairing payload arrived from an UNTRUSTED source (a `myai-glasses://pair`
     * deep link, deliverable by any web page or installed app). Do NOT act on it
     * — stage it for explicit confirmation. Silently consuming it let a hostile
     * link re-point the phone (host + token + cert pin) at an attacker's server,
     * even while already paired, redirecting all voice/vision to the attacker.
     * The QR/paste flows are user-initiated and call pairConfirmed directly.
     */
    fun proposePairing(rawJson: String) {
        val payload = PairingPayload.parse(rawJson.trim()) ?: run {
            dispatch(Event.GatewayError("PAIRING_CODE_INVALID")); return
        }
        _ui.value = _ui.value.copy(
            pairingPrompt = PairingPrompt(
                host = "${payload.host}:${payload.port}",
                tls = payload.tls,
                replacesExisting = credentials.isPaired,
                rawJson = rawJson.trim(),
            ),
        )
    }

    fun dismissPairingPrompt() {
        _ui.value = _ui.value.copy(pairingPrompt = null)
    }

    // ── LAN discover + approve enrollment ─────────────────────────────────
    private val discovery = HostDiscovery()
    private var enrollJob: Job? = null

    /** Scan every local /24 the phone is on for my.ai hosts advertising
     *  /discover. Scanning ALL site-local subnets (not just the first) matters:
     *  with cellular data on alongside Wi-Fi, the first interface is often the
     *  carrier's 10.x network, so a single-subnet scan misses the Wi-Fi host. */
    fun discoverHosts() {
        if (_ui.value.scanning) return
        val prefixes = localSubnetPrefixes()
        if (prefixes.isEmpty()) {
            dispatch(Event.GatewayError("MYAI_HOST_UNREACHABLE")); return
        }
        _ui.value = _ui.value.copy(scanning = true, discoveredHosts = emptyList())
        viewModelScope.launch {
            val found = java.util.Collections.synchronizedList(mutableListOf<DiscoveredHost>())
            val sem = Semaphore(48)  // bounded concurrency across subnets × /24 × ports
            val jobs = prefixes.flatMap { prefix ->
                (1..254).flatMap { host ->
                    HOST_SCAN_PORTS.map { port ->
                        async(Dispatchers.IO) {
                            sem.withPermit {
                                discovery.probe("$prefix.$host", port)?.let { h ->
                                    // De-dup: same host may answer on both ports.
                                    val snapshot = synchronized(found) {
                                        if (found.none { it.host == h.host && it.port == h.port }) {
                                            found.add(h); found.toList()
                                        } else null
                                    }
                                    // Marshal the UI write to main: every other _ui
                                    // write is main-confined, and a plain read-copy-set
                                    // from this IO thread could clobber a concurrent
                                    // glasses-state update (lost-update race, D4).
                                    if (snapshot != null) withContext(Dispatchers.Main) {
                                        _ui.value = _ui.value.copy(discoveredHosts = snapshot)
                                    }
                                }
                            }
                        }
                    }
                }
            }
            jobs.awaitAll()
            _ui.value = _ui.value.copy(scanning = false, discoveredHosts = found.toList())
        }
    }

    /** Request enrollment on a discovered host and wait for admin approval. */
    fun enrollWith(host: DiscoveredHost) {
        enrollJob?.cancel()
        _ui.value = _ui.value.copy(
            enroll = EnrollState(host.name, "", "Requesting…"), discoveredHosts = emptyList())
        enrollJob = viewModelScope.launch {
            android.util.Log.i("Enroll", "requesting on ${host.baseUrl} tls=${host.tls} pinned=${!host.certSha256.isNullOrBlank()}")
            when (val r = discovery.enrollRequest(host, android.os.Build.MODEL)) {
                is EnrollRequestResult.Failure -> {
                    android.util.Log.w("Enroll", "enroll request FAILED: ${r.code}")
                    _ui.value = _ui.value.copy(enroll = null)
                    dispatch(Event.GatewayError(r.code))
                }
                is EnrollRequestResult.Success -> {
                    android.util.Log.i("Enroll", "pending; verify code ${r.verifyCode}")
                    _ui.value = _ui.value.copy(enroll = EnrollState(
                        host.name, r.verifyCode,
                        "Approve on your my.ai host — check the code matches."))
                    pollApproval(host, r.requestId)
                }
            }
        }
    }

    private suspend fun pollApproval(host: DiscoveredHost, requestId: String) {
        // Poll until approved/denied or the request expires (~5 min).
        repeat(150) {
            kotlinx.coroutines.delay(2000)
            when (val s = discovery.enrollStatus(host, requestId)) {
                is EnrollStatusResult.Approved -> {
                    // Persist the stable address (tailnet host when advertised),
                    // so the pairing keeps working over cellular / off the LAN.
                    credentials.hostBaseUrl = host.persistBaseUrl
                    credentials.deviceToken = s.token
                    credentials.tokenId = s.tokenId
                    credentials.certSha256 = host.certSha256
                    _ui.value = _ui.value.copy(enroll = null)
                    dispatch(Event.HostPaired)
                    refreshHealth()
                    GlassesControlService.start(appContext)
                    return
                }
                is EnrollStatusResult.DeniedOrExpired -> {
                    _ui.value = _ui.value.copy(enroll = null)
                    dispatch(Event.GatewayError("PAIRING_CODE_INVALID"))
                    return
                }
                is EnrollStatusResult.Failure -> { /* transient — keep polling */ }
                EnrollStatusResult.Pending -> { /* keep waiting */ }
            }
        }
        _ui.value = _ui.value.copy(enroll = null)   // timed out
        dispatch(Event.GatewayError("REQUEST_TIMEOUT"))
    }

    fun cancelEnroll() {
        enrollJob?.cancel()
        _ui.value = _ui.value.copy(enroll = null)
    }

    /** Every distinct private-LAN IPv4 /24 prefix the phone is on (e.g.
     *  ["192.168.4"]), Wi-Fi subnets first. NetworkInterface enumeration needs
     *  NO permission (ConnectivityManager.getLinkProperties would require
     *  ACCESS_NETWORK_STATE and silently returned null without it). */
    private fun localSubnetPrefixes(): List<String> = runCatching {
        java.net.NetworkInterface.getNetworkInterfaces().asSequence()
            .filter { it.isUp && !it.isLoopback }
            // Wi-Fi (wlan*) before cellular (rmnet*) so the likely host subnet
            // is scanned and shown first.
            .sortedBy { if (it.name.startsWith("wlan")) 0 else 1 }
            .flatMap { nif ->
                nif.inetAddresses.asSequence().filter {
                    it is java.net.Inet4Address && it.isSiteLocalAddress  // 10/8, 172.16/12, 192.168/16
                }
            }
            .mapNotNull { it.hostAddress?.substringBeforeLast('.') }
            .distinct()
            .toList()
    }.getOrElse { emptyList() }

    /** The user confirmed the staged pairing prompt. */
    fun confirmPairingPrompt() {
        val prompt = _ui.value.pairingPrompt ?: return
        _ui.value = _ui.value.copy(pairingPrompt = null)
        pairConfirmed(prompt.rawJson)
    }

    /** Perform the pairing. Reached ONLY from a user-initiated path: the QR
     *  scanner, manual paste, or a confirmed deep-link prompt. */
    fun pairConfirmed(rawJson: String) {
        val payload = PairingPayload.parse(rawJson.trim()) ?: run {
            dispatch(Event.GatewayError("PAIRING_CODE_INVALID")); return
        }
        viewModelScope.launch {
            when (val r = client.pair(payload.baseUrl, payload.code,
                    android.os.Build.MODEL, payload.certSha256)) {
                is PairResult.Success -> {
                    credentials.hostBaseUrl = payload.baseUrl
                    credentials.deviceToken = r.token
                    credentials.tokenId = r.tokenId
                    credentials.certSha256 = payload.certSha256
                    dispatch(Event.HostPaired)
                    refreshHealth()
                    GlassesControlService.start(appContext)
                }
                is PairResult.Failure -> dispatch(Event.GatewayError(r.code))
            }
        }
    }

    fun refreshHealth() {
        viewModelScope.launch { doRefreshHealth() }
    }

    /** Pull-to-refresh: re-probe host health, capabilities, and glasses state,
     *  with a visible spinner while it runs. */
    fun refresh() {
        if (_ui.value.refreshing) return
        // The spinner tracks the DATA refresh only (health + capabilities +
        // productivity), which is fast. It must NOT await adapter.connect(): a
        // connect can take up to SESSION_START_TIMEOUT_MS (~20s), which left the
        // pull-to-refresh circle spinning long after the data was up (UAT #3).
        viewModelScope.launch {
            _ui.value = _ui.value.copy(refreshing = true)
            try {
                if (credentials.isPaired) doRefreshHealth()
            } finally {
                _ui.value = _ui.value.copy(refreshing = false)
            }
        }
        // Reconnect the glasses independently — a no-op when already connected,
        // serialized against any in-flight connect. Fire-and-forget so it can't
        // hold the spinner.
        viewModelScope.launch { runCatching { adapter.connect() } }
    }

    private suspend fun doRefreshHealth() {
        val healthy = client.health()
        dispatch(if (healthy) Event.HostHealthy else Event.HostUnreachable)
        var caps = client.capabilities()
        // Resilience (UAT #2): right after a reconnect the model endpoint can
        // momentarily resolve empty and report the LLM unavailable. Retry once
        // before trusting a negative, so we don't flash "no model available" over
        // a host that is actually fine. A null (network) result already leaves the
        // prior llmReady untouched below.
        if (healthy && caps?.optJSONObject("llm")?.optBoolean("available") == false) {
            kotlinx.coroutines.delay(700)
            caps = client.capabilities() ?: caps
        }
        caps?.let { caps ->
            val stt = caps.optJSONObject("stt")?.optBoolean("available") == true
            val tts = caps.optJSONObject("tts")?.optBoolean("available") == true
            val llm = caps.optJSONObject("llm")
            _ui.value = _ui.value.copy(
                modelLabel = llm?.optString("model")?.ifBlank { "—" } ?: "—",
                llmReady = llm?.optBoolean("available") == true,
                sttAvailable = stt,
                ttsAvailable = tts,
                visionAvailable =
                    caps.optJSONObject("vision")?.optBoolean("available") == true,
                voiceLabel = when {
                    stt && tts -> "listen + speak"
                    stt -> "listen only"
                    tts -> "speak only"
                    else -> "text only"
                },
            )
        }
        refreshProductivity()
    }

    /** Home checklists: notes + tasks. Best-effort, parallel. */
    fun refreshProductivity() {
        if (!credentials.isPaired) return
        viewModelScope.launch {
            val n = async { client.notes() }
            val t = async { client.tasks() }
            _ui.value = _ui.value.copy(notes = n.await(), tasks = t.await())
        }
    }

    /** Nav-drawer history: recent chats + Look-and-Ask. Loaded when it opens. */
    fun refreshHistory() {
        if (!credentials.isPaired) return
        viewModelScope.launch {
            val c = async { client.chatHistory() }
            val v = async { client.visionHistory() }
            _ui.value = _ui.value.copy(chatHistory = c.await(), visionHistory = v.await())
        }
    }

    /** date: an ISO date "YYYY-MM-DD" (all-day) or null. Notes/tasks/events all
     *  mirror onto the calendar → the owner's Google Calendar when connected. */
    fun addNote(title: String, date: String?) {
        if (title.isBlank()) return
        viewModelScope.launch { if (client.addNote(title.trim(), "", date)) refreshProductivity() }
    }

    fun addTask(text: String, date: String?) {
        if (text.isBlank()) return
        viewModelScope.launch { if (client.addTask(text.trim(), date)) refreshProductivity() }
    }

    /** Check a note/task off (archives it on the host), then refresh. */
    fun completeItem(id: String) {
        // Only TASKS are completable (via their checklist items); notes are
        // reference text with no completion. Optimistic flip so the checkbox feels
        // instant; the task stays visible (greyed) and can be toggled back.
        _ui.value = _ui.value.copy(
            tasks = _ui.value.tasks.map {
                if (it.id == id) it.copy(completed = !it.completed) else it })
        viewModelScope.launch { client.completeItem(id); refreshProductivity() }
    }

    /** Privacy toggle. storeTranscript is already threaded into client.respond()
     *  (rolling context) AND into redact_user_text (host logging) — it just had
     *  no UI to flip it, so it was permanently stuck at its true default. */
    fun setStoreTranscript(enabled: Boolean) {
        _ui.value = _ui.value.copy(storeTranscript = enabled)
    }

    // ── Voice loop ────────────────────────────────────────────────────────

    fun startListening() {
        val v = voice
        viewModelScope.launch {
            micLock.withLock {
                if (_ui.value.listening) return@withLock
                dispatch(Event.FailureCleared)  // clear a stale banner before a new turn
                v.stopPlayback()         // barge-in: talking over the reply cancels it
                dispatch(Event.SpeakingChanged(false))  // stopPlayback skips onDone
                // Foreground BEFORE the mic opens: a backgrounded app has its mic
                // muted and its SCO route dropped by the OS.
                MicForegroundService.start(appContext)
                // Mark listening BEFORE acquiring the route. Acquisition now takes
                // up to 3 s, and an invalidating event arriving in that window
                // would otherwise see listening=false, skip the abort, and then be
                // overwritten by us setting listening=true at the end — leaving the
                // mic open on a connection the reducer had already given up on.
                dispatch(Event.ListeningChanged(true))
                // Option A (UAT): capture with the PHONE mic and DON'T grab the
                // glasses HFP/SCO route — on camera-only Ray-Bans that drops the
                // DAT camera session (the glasses "disconnect"). Phone-mic-in +
                // glasses-A2DP-out keeps the camera session alive for Look & Ask.
                if (USE_GLASSES_MIC) v.acquireBluetoothMic()
                val started = try {
                    withContext(Dispatchers.IO) { v.startRecording() }
                } catch (t: Throwable) {
                    // Cancellation (the ViewModel being cleared) resumes here only
                    // AFTER the blocking IO body has run to completion — so the
                    // recorder may already be hot with nobody left to close it.
                    closeMic(v)
                    dispatch(Event.ListeningChanged(false))  // never strand listening=true
                    throw t
                }
                // The reducer may have forced listening=false while we acquired.
                if (!started || !app.listening) {
                    closeMic(v)
                    if (!started) {
                        dispatch(Event.ListeningChanged(false))
                        dispatch(Event.GatewayError("BLUETOOTH_AUDIO_UNAVAILABLE"))
                    }
                    return@withLock
                }
            }
        }
    }

    /** Close the mic and drop the audio route. Idempotent. */
    private fun closeMic(v: VoiceSession) {
        v.cancelRecording()
        v.releaseBluetoothMic()
        MicForegroundService.stop(appContext)
    }

    fun stopListening() {
        val v = voice
        viewModelScope.launch {
            val wav = micLock.withLock {
                if (!_ui.value.listening) return@launch
                // stopRecording() joins the capture thread — off the main thread.
                val captured = withContext(Dispatchers.IO) { v.stopRecording() }
                // Close HFP before playback: while the mic is open, glasses audio
                // is 8 kHz mono (SDK constraint).
                v.releaseBluetoothMic()
                MicForegroundService.stop(appContext)
                dispatch(Event.ListeningChanged(false))
                captured
            }
            if (wav == null) return@launch   // too short / empty — nothing to send

            // Network work stays OUTSIDE the mic lock: holding it across a
            // transcribe would block the next push-to-talk.
            _ui.value = _ui.value.copy(busy = true)
            when (val r = client.transcribe(wav)) {
                is TranscribeResult.Success -> {
                    if (r.empty || r.text.isBlank()) {
                        _ui.value = _ui.value.copy(busy = false)
                    } else {
                        ask(r.text)      // ask() manages busy from here
                    }
                }
                is TranscribeResult.Failure -> {
                    dispatch(Event.GatewayError(r.code))
                    _ui.value = _ui.value.copy(busy = false)
                }
            }
        }
    }

    fun ask(text: String) {
        streamJob?.cancel()
        // Starting a new turn clears a stale transient banner (a prior Stop /
        // rate-limit / TTS hiccup) so it doesn't linger through a good turn.
        dispatch(Event.FailureCleared)
        // Echo the question so the Response panel shows the Q&A pair, not just
        // the answer floating with no context (UAT #4).
        _ui.value = _ui.value.copy(busy = true, lastQuestion = text, lastResponse = "")
        streamJob = viewModelScope.launch {
            var attempt = 0
            while (true) {
                attempt++
                val sb = StringBuilder()
                var gotContent = false          // any answer text streamed this attempt
                var handled = false             // a terminal error was already surfaced
                var retryCode: String? = null   // transient error → retry candidate
                client.respond(text, app.activeSessionId, _ui.value.storeTranscript)
                    .collect { ev ->
                        when (ev) {
                            is GatewayEvent.Meta -> {
                                // The host answered → it's reachable. Clears a stale
                                // MYAI_HOST_UNREACHABLE that a flapped retry health-
                                // probe may have latched, which otherwise left
                                // canTalk=false after an otherwise-successful retry (M1).
                                dispatch(Event.HostHealthy)
                                dispatch(Event.SessionStarted(ev.sessionId))
                            }
                            is GatewayEvent.Delta -> if (!ev.thinking) {
                                gotContent = true
                                sb.append(ev.text)
                                _ui.value = _ui.value.copy(lastResponse = sb.toString())
                            }
                            is GatewayEvent.Spoken -> speak(ev.text)
                            is GatewayEvent.Cancelled -> {
                                handled = true
                                dispatch(Event.GatewayError("SESSION_CANCELLED"))
                            }
                            is GatewayEvent.Error -> when {
                                ev.code in setOf("AUTHENTICATION_REQUIRED",
                                    "DEVICE_CREDENTIAL_REVOKED", "FORBIDDEN_SCOPE") -> {
                                    handled = true
                                    dispatch(Event.CredentialRejected)
                                }
                                // Only auto-retry a transient failure that produced
                                // NO answer yet — re-asking after a partial answer
                                // would duplicate it.
                                ev.code in RETRYABLE_STREAM_CODES && !gotContent ->
                                    retryCode = ev.code
                                else -> {
                                    handled = true
                                    dispatch(Event.GatewayError(ev.code))
                                }
                            }
                            GatewayEvent.StreamEnd -> Unit
                            else -> Unit
                        }
                    }
                // UAT #2: on a transient drop, re-probe host health and retry the
                // request automatically before surfacing an error — the inference
                // session is server-side and is not reset by this.
                if (retryCode != null && !handled && attempt < MAX_ASK_ATTEMPTS) {
                    _ui.value = _ui.value.copy(lastResponse = "Reconnecting…")
                    dispatch(if (client.health()) Event.HostHealthy else Event.HostUnreachable)
                    kotlinx.coroutines.delay(attempt * 800L)   // linear backoff
                    continue
                }
                if (retryCode != null && !handled) {   // retries exhausted
                    _ui.value = _ui.value.copy(lastResponse = "")
                    dispatch(Event.GatewayError(retryCode!!))
                }
                // Don't leave the placeholder up if a retry ended with no content
                // and no error to surface (empty stream). (L3)
                if (_ui.value.lastResponse == "Reconnecting…") {
                    _ui.value = _ui.value.copy(lastResponse = "")
                }
                _ui.value = _ui.value.copy(busy = false)
                break
            }
        }
    }

    fun lookAndAsk() {
        dispatch(Event.FailureCleared)   // clear a stale banner before a new turn
        _ui.value = _ui.value.copy(busy = true)
        viewModelScope.launch {
            // Real glasses: starts a short stream (capture LED lights), grabs a
            // still, stops. Mock: synthetic JPEG.
            val jpeg = adapter.captureStillJpeg()
            if (jpeg == null) {
                dispatch(Event.GatewayError("GLASSES_NOT_CONNECTED"))
                _ui.value = _ui.value.copy(busy = false)
                return@launch
            }
            when (val r = client.visionQuery(jpeg, "What am I looking at?")) {
                is VisionResult.Success -> {
                    _ui.value = _ui.value.copy(lastResponse = r.text, busy = false)
                    speak(r.spoken)
                }
                is VisionResult.Failure -> {
                    dispatch(Event.GatewayError(r.code))
                    _ui.value = _ui.value.copy(busy = false)
                }
            }
        }
    }

    /** Speak a reply through the host's local TTS (played over A2DP → glasses). */
    private fun speak(spokenText: String) {
        if (!_ui.value.ttsAvailable || spokenText.isBlank()) return
        viewModelScope.launch {
            val audio = client.speech(spokenText)
            if (audio == null) {
                dispatch(Event.GatewayError("TTS_FAILED"))
                return@launch
            }
            dispatch(Event.SpeakingChanged(true))
            voice.playAudio(audio) { dispatch(Event.SpeakingChanged(false)) }
        }
    }

    fun cancel() {
        // Stop the stream AND the auto-retry loop immediately — otherwise Stop is a
        // no-op during the retry backoff (no active stream to receive the cancel) and
        // the loop proceeds to the next attempt (L1).
        streamJob?.cancel()
        _ui.value = _ui.value.copy(busy = false)   // cancelled ask() won't reach its own reset
        voice.stopPlayback()
        // stopPlayback() bypasses the completion listener, so clear `speaking`
        // here — otherwise it latches true after a barge-in/cancel.
        dispatch(Event.SpeakingChanged(false))
        val sid = app.activeSessionId ?: return
        viewModelScope.launch { client.cancel(sid) }
    }

    fun deleteConversation() {
        val sid = app.activeSessionId ?: return
        viewModelScope.launch {
            client.deleteSession(sid)
            dispatch(Event.SessionEnded)
            _ui.value = _ui.value.copy(lastQuestion = "", lastResponse = "")
        }
    }

    /** Start a fresh conversation: drop the current server session (so context
     *  doesn't carry over), stop any playback, and clear the panel — ready for a
     *  new question. Works even with no active session (UAT #5). */
    fun newChat() {
        streamJob?.cancel()
        voice.stopPlayback()
        dispatch(Event.SpeakingChanged(false))
        app.activeSessionId?.let { sid ->
            viewModelScope.launch { runCatching { client.deleteSession(sid) } }
        }
        dispatch(Event.SessionEnded)     // clears activeSessionId
        dispatch(Event.FailureCleared)
        _ui.value = _ui.value.copy(lastQuestion = "", lastResponse = "", busy = false)
    }

    fun unpair() {
        streamJob?.cancel()
        voice.stopPlayback()
        GlassesControlService.stop(appContext)   // disarm the triple-tap trigger
        credentials.clear()
        dispatch(Event.HostUnpaired)
        _ui.value = UiState()
    }

    override fun onCleared() {
        super.onCleared()
        voice.cancelRecording()
        voice.stopPlayback()
        voice.releaseBluetoothMic()
        MicForegroundService.stop(appContext)
        // The DeviceSession outlives this ViewModel (the adapter is process-wide)
        // and nothing was ever stopping it — disconnect() had no callers at all.
        // requestDisconnect() runs on the adapter's own scope and is cancelled by
        // any connect() that beats it, so a back-out-and-relaunch cannot tear
        // down the session the next Activity just brought up.
        adapter.requestDisconnect()
    }

    companion object {
        /** "Both — full glasses audio" (user decision): capture voice through the
         *  glasses HFP/SCO mic and play the reply through the glasses (A2DP). On
         *  camera-only Ray-Bans this can drop the DAT *camera* session while the
         *  mic is held — that's accepted: the camera isn't needed during Talk, and
         *  a camera-session drop no longer aborts capture (the mic rides HFP, not
         *  the DAT session — see ConnectionReducer.GlassesDisconnected). Look & Ask
         *  re-establishes the camera session afterward. */
        const val USE_GLASSES_MIC = true

        /** Stream-error codes worth auto-retrying (transient): a dropped
         *  connection, a timeout, or a model that is briefly unavailable
         *  (loading/busy). NOT retried: cancel, credential, and hard request
         *  errors (bad request, payload too large, rate-limited, unsafe-blocked). */
        val RETRYABLE_STREAM_CODES =
            setOf("MYAI_HOST_UNREACHABLE", "REQUEST_TIMEOUT", "LLM_UNAVAILABLE")
        const val MAX_ASK_ATTEMPTS = 3

        fun factory(
            appContext: Context,
            adapter: WearablesAdapter = GlassesAdapters.shared,
        ) = object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T =
                MainViewModel(appContext, CredentialStore(appContext), adapter) as T
        }
    }
}
