package ai.my.glasses.audio

import ai.my.glasses.core.Vad
import android.annotation.SuppressLint
import android.content.Context
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaPlayer
import android.media.MediaRecorder
import android.os.SystemClock
import android.util.Log
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread
import kotlin.coroutines.resume
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Push-to-talk audio lifecycle for the glasses path.
 *
 * SDK reality (META_SDK_CAPABILITY_MATRIX.md): the glasses mic is a standard
 * Bluetooth HFP source and the speakers a standard A2DP sink — there is no
 * Meta audio API. While HFP is open ALL glasses audio drops to 8 kHz mono, so
 * we toggle: open HFP → record → close HFP → play the reply over A2DP.
 *
 * Falls back to the phone's own mic/speaker when no Bluetooth headset is
 * present, so the whole voice loop is testable without glasses.
 *
 * HARDWARE-VALIDATION PENDING: written against documented AudioManager
 * behavior (API 31+ setCommunicationDevice); the HFP round-trip has not been
 * exercised on physical glasses (TEST_PLAN.md §hardware items 2-4).
 */
class VoiceSession(private val context: Context) {

    private val audioManager =
        context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    // @Volatile: onCleared() tears these down off micLock (Main) while a
    // startRecording() may still be assigning them on the IO thread — publish
    // writes so neither side reads a torn/stale reference.
    @Volatile private var record: AudioRecord? = null
    @Volatile private var recordThread: Thread? = null
    private val recording = AtomicBoolean(false)
    private val pcm = ByteArrayOutputStream()
    private var player: MediaPlayer? = null
    /** Temp file backing the current [player]. Tracked so stopPlayback() can delete
     *  it even when the player is released before prepareAsync fires (a released
     *  MediaPlayer calls none of its listeners, so finish() never runs). */
    private var playerTmp: File? = null
    /** Playback generation, bumped by stopPlayback() and captured by playAudio().
     *  A mismatch means an in-flight playAudio() was superseded (barge-in / next
     *  chunk) during its async setup and must not start. Main-thread-confined. */
    private var playGen = 0

    init {
        // Sweep TTS temp files orphaned by a process death mid-playback (the
        // onCompletion/onError delete never fired). They hold assistant-speech
        // audio, so don't leave them lying in cacheDir across restarts.
        runCatching {
            context.cacheDir.listFiles { f -> f.name.startsWith("myai_tts") }
                ?.forEach { it.delete() }
        }
    }

    companion object {
        private const val TAG = "VoiceSession"
        const val SAMPLE_RATE = 16_000        // whisper-native; the stack resamples HFP
        private const val MAX_UTTERANCE_SECONDS = 120  // hard stop; raised for long, detailed questions
        private const val MIN_UTTERANCE_BYTES = SAMPLE_RATE / 4 * 2  // 1/4 s of 16-bit @16k → ~250 ms
        // HFP/SCO link-up is typically 0.3–2 s; 3 s is a generous ceiling before
        // we give up and fall back to the phone mic.
        private const val SCO_ROUTE_TIMEOUT_MS = 3_000L
        private const val VAD_SILENCE_MS = 1_200L   // trailing silence that ends an utterance
        private const val VAD_SPEECH_RMS = 700.0    // 16-bit RMS above which we count "speech"
    }

    /** True when the mic is routed to the glasses (vs. the phone's own mic). */
    var usingBluetoothMic: Boolean = false
        private set

    /** Voice-activity endpointing (hands-free): when true, capture auto-ends after a
     *  trailing silence once speech has been heard, so the user needn't tap to send.
     *  [onAutoEndpoint] is invoked (from the mic thread) when that happens. */
    @Volatile var vadEnabled: Boolean = false
    @Volatile var onAutoEndpoint: (() -> Unit)? = null

    /** Set as soon as we ASK for the SCO route, whether or not it lands — so the
     *  release path always clears a route we requested. */
    private var routeRequested = false

    /** The audio mode before we forced MODE_IN_COMMUNICATION, restored on release
     *  so the phone isn't left in comms mode (which would keep other audio ducked). */
    private var priorMode: Int? = null

    /**
     * Route the communication stream to the BT headset (glasses) if present,
     * and wait until the route has actually landed.
     *
     * `setCommunicationDevice()` is asynchronous: `true` means the request was
     * accepted, NOT that the link is up. Bringing up HFP/SCO takes ~0.3–2 s, and
     * that link coming up *is* the glasses' connect tone. The old code returned
     * immediately, so the caller opened an AudioRecord on a route that did not
     * exist yet; the failure path then cleared the route, tearing SCO straight
     * back down — the disconnect tone, milliseconds after the connect tone.
     */
    suspend fun acquireBluetoothMic(timeoutMs: Long = SCO_ROUTE_TIMEOUT_MS): Boolean =
      // OFF-MAIN: the AudioManager binder calls below (availableCommunicationDevices
      // / setCommunicationDevice / mode=) run synchronously; keep them off the main
      // thread so BT contention can't jank the UI (the SCO listener still delivers
      // via mainExecutor). Caller (startListening) is on viewModelScope=Main.
      withContext(Dispatchers.IO) {
        // Enter communication mode FIRST. setCommunicationDevice() routes OUTPUT
        // and is accepted in MODE_NORMAL, but the SCO *uplink* — the glasses mic —
        // only comes up in MODE_IN_COMMUNICATION, and entering it is often what
        // makes Android connect HFP and surface the SCO device at all. Without it
        // AudioRecord silently reads the built-in phone mic even though the route
        // request "succeeded" (the live symptom: transcribe works, wrong mic).
        if (priorMode == null) priorMode = audioManager.mode
        audioManager.mode = AudioManager.MODE_IN_COMMUNICATION

        // From here on the phone is in MODE_IN_COMMUNICATION; any throw (some OEMs
        // raise from availableCommunicationDevices/setCommunicationDevice when BT is
        // mid-teardown, or coroutine cancellation) must restore the mode and clear
        // any half-requested route — otherwise the phone stays stuck in comms mode
        // (ducking all other audio) and the next acquire is wedged.
        try {
            // The SCO device can take a beat to appear after entering comms mode.
            var sco = audioManager.availableCommunicationDevices
                .firstOrNull { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
            if (sco == null) {
                val deadline = SystemClock.uptimeMillis() + 1_000
                while (sco == null && SystemClock.uptimeMillis() < deadline) {
                    kotlinx.coroutines.delay(100)
                    sco = audioManager.availableCommunicationDevices
                        .firstOrNull { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO }
                }
            }
            if (sco == null) {
                // No HFP mic offered by the glasses right now → phone mic. Log it so
                // "which mic" stops being invisible, and DON'T leave the phone in
                // communication mode.
                Log.w(TAG, "no BT SCO mic in availableCommunicationDevices (" +
                    audioManager.availableCommunicationDevices.joinToString { it.type.toString() } +
                    ") — using PHONE mic")
                restoreMode()
                usingBluetoothMic = false
                return@withContext false
            }
            if (audioManager.communicationDevice?.id == sco.id) {
                routeRequested = true
                usingBluetoothMic = true
                Log.i(TAG, "glasses SCO mic already routed")
                return@withContext true   // already routed; don't cycle SCO (re-tones)
            }

            routeRequested = true
            if (!audioManager.setCommunicationDevice(sco)) {
                releaseBluetoothMic()
                return@withContext false
            }

            val routed = withTimeoutOrNull(timeoutMs) { awaitCommunicationDevice(sco.id) } ?: false
            usingBluetoothMic = routed
            Log.i(TAG, if (routed) "glasses SCO mic ROUTED" else
                "SCO route did not land within ${timeoutMs}ms; using phone mic")
            if (!routed) releaseBluetoothMic()
            return@withContext routed
        } catch (t: Throwable) {
            releaseBluetoothMic()   // restores mode + clears route; idempotent
            throw t
        }
    }

    /** Suspend until [deviceId] is the active communication device. */
    private suspend fun awaitCommunicationDevice(deviceId: Int): Boolean =
        suspendCancellableCoroutine { cont ->
            val done = AtomicBoolean(false)
            val listener = object : AudioManager.OnCommunicationDeviceChangedListener {
                override fun onCommunicationDeviceChanged(device: AudioDeviceInfo?) {
                    if (device?.id == deviceId && done.compareAndSet(false, true)) {
                        audioManager.removeOnCommunicationDeviceChangedListener(this)
                        cont.resume(true)
                    }
                }
            }
            audioManager.addOnCommunicationDeviceChangedListener(
                context.mainExecutor, listener)
            cont.invokeOnCancellation {
                if (done.compareAndSet(false, true)) {
                    audioManager.removeOnCommunicationDeviceChangedListener(listener)
                }
            }
            // The route can land between setCommunicationDevice() and the line
            // above, in which case the callback already fired and we'd wait for
            // an event that will never come again.
            if (audioManager.communicationDevice?.id == deviceId &&
                done.compareAndSet(false, true)
            ) {
                audioManager.removeOnCommunicationDeviceChangedListener(listener)
                cont.resume(true)
            }
        }

    /** ALWAYS restore the previous route, even on error paths. Keyed off
     *  [routeRequested], not [usingBluetoothMic]: a route we asked for but that
     *  never landed still has to be cleared, or it leaks and wedges the next
     *  acquire. */
    fun releaseBluetoothMic() {
        if (routeRequested) {
            runCatching { audioManager.clearCommunicationDevice() }
            routeRequested = false
        }
        restoreMode()   // never leave the phone stuck in MODE_IN_COMMUNICATION
        usingBluetoothMic = false
    }

    private fun restoreMode() {
        priorMode?.let { runCatching { audioManager.mode = it }; priorMode = null }
    }

    /**
     * Start capturing an utterance. Audio is drained continuously on a
     * background thread; [stopRecording] returns the finished WAV.
     */
    @SuppressLint("MissingPermission") // RECORD_AUDIO is requested by MainActivity
    fun startRecording(): Boolean {
        if (recording.get()) return true
        val minBuf = AudioRecord.getMinBufferSize(
            SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minBuf <= 0) return false

        val r = try {
            AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION, // HFP-friendly + AEC/NS
                SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT, minBuf * 4)
        } catch (e: Exception) {
            Log.e(TAG, "AudioRecord init failed", e)
            return false
        }
        if (r.state != AudioRecord.STATE_INITIALIZED) {
            r.release()
            return false
        }

        pcm.reset()
        record = r
        recording.set(true)
        r.startRecording()

        val maxBytes = SAMPLE_RATE * 2 * MAX_UTTERANCE_SECONDS
        // Pure endpoint decision lives in :core (Vad) so it's unit-tested.
        val vad = Vad(speechRms = VAD_SPEECH_RMS, silenceMs = VAD_SILENCE_MS,
            minBytes = MIN_UTTERANCE_BYTES)
        recordThread = thread(name = "myai-mic") {
            val buf = ByteArray(4096)
            var autoEnded = false
            while (recording.get() && pcm.size() < maxBytes) {
                val n = r.read(buf, 0, buf.size)
                if (n > 0) {
                    synchronized(pcm) { pcm.write(buf, 0, n) }
                    if (vadEnabled &&
                        vad.accept(buf, n, pcm.size(), SystemClock.uptimeMillis())) {
                        autoEnded = true
                        break
                    }
                } else if (n < 0) break
            }
            // Hitting the 60s hard cap (loop exits with recording still requested)
            // must ALSO auto-send in hands-free mode — otherwise the mic stops but
            // the turn never fires and the UI hangs on "listening".
            val hitCap = recording.get() && pcm.size() >= maxBytes
            recording.set(false)
            if (autoEnded || (vadEnabled && hitCap)) runCatching { onAutoEndpoint?.invoke() }
        }
        return true
    }

    /** Stop capture and return the utterance as a WAV, or null if too short. */
    fun stopRecording(): ByteArray? {
        val r = record ?: return null
        recording.set(false)
        runCatching { r.stop() }          // unblocks a blocking read() so the thread exits fast
        recordThread?.join(2_000)
        val threadAlive = recordThread?.isAlive == true
        recordThread = null
        record = null
        // Releasing while the capture thread is still inside read() is a native
        // crash. If (very rarely) it didn't exit within the join, skip release —
        // a leaked recorder is recoverable; a native crash is not.
        if (!threadAlive) r.release()
        else Log.w(TAG, "record thread still alive after stop; skipping release")

        val bytes = synchronized(pcm) { pcm.toByteArray() }
        if (bytes.size < MIN_UTTERANCE_BYTES) return null
        return wavFromPcm16(bytes, SAMPLE_RATE)
    }

    fun cancelRecording() {
        recording.set(false)
        val r = record
        runCatching { r?.stop() }         // unblock read() before joining
        recordThread?.join(2_000)
        val threadAlive = recordThread?.isAlive == true
        recordThread = null
        record = null
        if (r != null && !threadAlive) r.release()   // don't release under a live read()
        synchronized(pcm) { pcm.reset() }
    }

    /**
     * Play gateway TTS bytes over the current output route (A2DP → glasses).
     *
     * The temp-file write happens on an IO dispatcher and decoding via
     * prepareAsync(): this runs once per reply from the ViewModel's main-thread
     * scope, and createTempFile + writeBytes + a synchronous prepare() there
     * blocked the UI for the length of the decode.
     */
    suspend fun playAudio(bytes: ByteArray, onDone: () -> Unit = {}) {
        stopPlayback()                     // supersede/stop any current playback
        val myGen = playGen                // this attempt's generation (post-bump)
        val tmp = withContext(Dispatchers.IO) {
            File.createTempFile("myai_tts", ".audio", context.cacheDir)
                .also { it.writeBytes(bytes) }
        }
        // A newer playAudio() OR a stopPlayback() (barge-in) ran during the temp
        // write. `player` is only assigned AFTER this suspension, so the old code's
        // stopPlayback() missed an in-setup player — with USE_GLASSES_MIC the reply
        // could then start playing INTO the open SCO mic (feedback), or two players
        // could overlap. Bail if superseded. (Everything here is main-confined, so
        // playGen needs no synchronization.)
        if (myGen != playGen) { tmp.delete(); onDone(); return }
        playerTmp = tmp
        var mp: MediaPlayer? = null
        val finish = {
            tmp.delete()
            mp?.let { runCatching { it.release() } }
            if (mp != null && player === mp) { player = null; playerTmp = null }
            onDone()
        }
        runCatching {
            val p = MediaPlayer()
            mp = p
            player = p
            p.setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_ASSISTANT)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build())
            p.setDataSource(tmp.absolutePath)
            p.setOnCompletionListener { finish() }
            p.setOnErrorListener { _, _, _ -> finish(); true }
            // Don't start if superseded between prepareAsync() and onPrepared.
            p.setOnPreparedListener { if (myGen == playGen) it.start() else finish() }
            p.prepareAsync()
        }.onFailure {
            Log.e(TAG, "TTS playback failed", it)
            finish()
        }
    }

    /** Barge-in: the user started talking → kill playback immediately. */
    fun stopPlayback() {
        playGen++   // invalidate any playAudio() still in its async setup phase
        player?.let { runCatching { it.stop() }; runCatching { it.release() } }
        player = null
        // A released player fires no completion/error listener, so delete the temp
        // file here rather than leaking it until the next process-start sweep.
        playerTmp?.let { runCatching { it.delete() } }
        playerTmp = null
    }

    // ── Diagnostics (on-device hardware validation) ───────────────────────────

    /** Human-readable snapshot of the audio routing state — which communication
     *  devices the OS offers (is a glasses BT SCO mic present?), the current route,
     *  and the audio mode. */
    fun audioRouteSnapshot(): String {
        val devs = runCatching { audioManager.availableCommunicationDevices }
            .getOrNull().orEmpty()
        val names = devs.joinToString(", ") { deviceTypeName(it.type) }.ifEmpty { "none" }
        val cur = runCatching { audioManager.communicationDevice }.getOrNull()
        return "audio mode: ${modeName(audioManager.mode)}\n" +
            "comm devices: $names\n" +
            "active route: ${cur?.let { deviceTypeName(it.type) } ?: "none"}"
    }

    /** True if the last acquire routed to the glasses HFP/SCO mic (vs the phone). */
    fun lastMicWasGlasses(): Boolean = usingBluetoothMic

    /** A short test tone played through the normal playback path (USAGE_ASSISTANT →
     *  A2DP) so the user can confirm audio reaches the GLASSES speaker. */
    suspend fun playTestTone(onDone: () -> Unit = {}) {
        val n = (SAMPLE_RATE * 0.6).toInt()
        val pcm = ByteArray(n * 2)
        for (i in 0 until n) {
            val s = (Math.sin(2 * Math.PI * 660.0 * i / SAMPLE_RATE) * 0.35 * Short.MAX_VALUE)
                .toInt().toShort().toInt()
            pcm[i * 2] = (s and 0xff).toByte()
            pcm[i * 2 + 1] = ((s shr 8) and 0xff).toByte()
        }
        playAudio(wavFromPcm16(pcm, SAMPLE_RATE), onDone)
    }

    private fun deviceTypeName(t: Int): String = when (t) {
        AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "BT_SCO(glasses mic/HFP)"
        AudioDeviceInfo.TYPE_BLUETOOTH_A2DP -> "BT_A2DP(glasses speaker)"
        AudioDeviceInfo.TYPE_BLE_HEADSET -> "BLE_HEADSET"
        AudioDeviceInfo.TYPE_BUILTIN_MIC -> "PHONE_MIC"
        AudioDeviceInfo.TYPE_BUILTIN_SPEAKER -> "PHONE_SPEAKER"
        AudioDeviceInfo.TYPE_WIRED_HEADSET -> "WIRED_HEADSET"
        else -> "type$t"
    }

    private fun modeName(m: Int): String = when (m) {
        AudioManager.MODE_NORMAL -> "NORMAL"
        AudioManager.MODE_IN_COMMUNICATION -> "IN_COMMUNICATION"
        AudioManager.MODE_IN_CALL -> "IN_CALL"
        else -> "mode$m"
    }

    /** Minimal RIFF/WAVE header around 16-bit mono PCM. */
    internal fun wavFromPcm16(pcm: ByteArray, sampleRate: Int): ByteArray {
        val byteRate = sampleRate * 2
        val out = ByteArrayOutputStream(44 + pcm.size)
        fun le32(v: Int) = out.write(byteArrayOf(
            (v and 0xff).toByte(), ((v shr 8) and 0xff).toByte(),
            ((v shr 16) and 0xff).toByte(), ((v shr 24) and 0xff).toByte()))
        fun le16(v: Int) = out.write(byteArrayOf(
            (v and 0xff).toByte(), ((v shr 8) and 0xff).toByte()))
        out.write("RIFF".toByteArray()); le32(36 + pcm.size); out.write("WAVE".toByteArray())
        out.write("fmt ".toByteArray()); le32(16); le16(1); le16(1)
        le32(sampleRate); le32(byteRate); le16(2); le16(16)
        out.write("data".toByteArray()); le32(pcm.size); out.write(pcm)
        return out.toByteArray()
    }
}
