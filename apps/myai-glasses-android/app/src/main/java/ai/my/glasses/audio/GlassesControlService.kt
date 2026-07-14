package ai.my.glasses.audio

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.session.MediaSession
import android.media.session.PlaybackState
import android.os.Build
import android.os.IBinder
import android.util.Log
import android.view.KeyEvent
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import ai.my.glasses.MainActivity

/**
 * Hands-free glasses control, hands-off the app:
 *   - SINGLE TAP  → play/pause the user's music
 *   - LONG HOLD (≥3s) → pause music + talk to my.ai
 *
 * HARD SDK CONSTRAINT (META_SDK_CAPABILITY_MATRIX.md): the camera-only Ray-Bans
 * expose NO touchpad/gesture API to third parties — the only thing that crosses
 * to the phone is the standard Bluetooth media button. So this service owns a
 * MediaSession to capture those key events and measures the press duration:
 * ACTION_DOWN starts a 3 s timer; if it fires, it's a hold; a release before it
 * is a tap. The user's MUSIC is driven separately via [MediaControl] (a
 * MediaController on the active session) so a tap toggles it and a hold pauses it.
 *
 * HARDWARE-VALIDATION PENDING and two real unknowns: (1) whether the glasses
 * emit a HOLD as a distinct media key with measurable down/up (vs. reserving
 * press-and-hold for "Hey Meta"), and (2) whether a background session reliably
 * wins the media button. The Log lines here exist to answer both on-device.
 */
class GlassesControlService : android.app.Service() {

    private var session: MediaSession? = null
    private val handler = android.os.Handler(android.os.Looper.getMainLooper())

    companion object {
        private const val TAG = "GlassesControl"
        private const val CHANNEL_ID = "myai_glasses_control"
        private const val NOTIFICATION_ID = 43
        private const val LONG_PRESS_MS = 3000L          // hold this long → talk to my.ai

        fun start(context: Context) {
            runCatching {
                context.startForegroundService(Intent(context, GlassesControlService::class.java))
            }.onFailure { Log.w(TAG, "could not start glasses control service", it) }
        }

        fun stop(context: Context) {
            runCatching {
                context.stopService(Intent(context, GlassesControlService::class.java))
            }.onFailure { Log.w(TAG, "could not stop glasses control service", it) }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        runCatching {
            ServiceCompat.startForeground(
                this, NOTIFICATION_ID, buildNotification(),
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK else 0,
            )
        }.onFailure {
            Log.w(TAG, "foreground promotion failed; media-button capture may be limited", it)
        }
        setupMediaSession()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    private fun setupMediaSession() {
        val s = MediaSession(this, "myai-glasses-control")
        // A media button only routes to a session that advertises it handles the
        // button AND is active with a matching action. We keep a PLAYING state so
        // this session stays the button target while paired.
        s.setPlaybackState(
            PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY_PAUSE or
                    PlaybackState.ACTION_PLAY or PlaybackState.ACTION_PAUSE)
                .setState(PlaybackState.STATE_PLAYING, 0, 1.0f)
                .build())
        s.setCallback(object : MediaSession.Callback() {
            override fun onMediaButtonEvent(mediaButtonIntent: Intent): Boolean {
                val ke = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU)
                    mediaButtonIntent.getParcelableExtra(Intent.EXTRA_KEY_EVENT, KeyEvent::class.java)
                else @Suppress("DEPRECATION") mediaButtonIntent.getParcelableExtra(Intent.EXTRA_KEY_EVENT)
                if (ke == null) return super.onMediaButtonEvent(mediaButtonIntent)
                // Surface EVERY media key to Diagnostics (even non-tap ones) so the
                // hardware's actual button behavior is visible on-device.
                val act = when (ke.action) {
                    KeyEvent.ACTION_DOWN -> "DOWN"; KeyEvent.ACTION_UP -> "UP"; else -> ke.action.toString()
                }
                // Log the initial press and the release only — a held button fires a
                // stream of auto-repeat DOWNs (repeatCount 1,2,3…) that would flood the
                // diagnostics gesture log and hide the events that matter.
                if (!(ke.action == KeyEvent.ACTION_DOWN && ke.repeatCount > 0)) {
                    GlassesGestures.emitKey(
                        "key=${ke.keyCode} $act long=${ke.isLongPress} rpt=${ke.repeatCount}")
                }
                if (!isTapKey(ke.keyCode)) return super.onMediaButtonEvent(mediaButtonIntent)
                Log.i(TAG, "media key ${ke.keyCode} action=${ke.action} long=${ke.isLongPress}")
                when (ke.action) {
                    KeyEvent.ACTION_DOWN -> onKeyDown(ke)
                    KeyEvent.ACTION_UP -> onKeyUp()
                }
                return true   // we own the button; music is driven via MediaControl
            }
            // If a route delivers a discrete transport command instead of raw
            // key up/down, we can't measure hold time — treat it as a short tap.
            override fun onPlay() { shortTap() }
            override fun onPause() { shortTap() }
        })
        runCatching { s.isActive = true }
        session = s
    }

    private fun isTapKey(code: Int) = code == KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE ||
        code == KeyEvent.KEYCODE_HEADSETHOOK ||
        code == KeyEvent.KEYCODE_MEDIA_PLAY ||
        code == KeyEvent.KEYCODE_MEDIA_PAUSE

    // Long-press vs single-tap. A physical press arrives as ACTION_DOWN … held …
    // ACTION_UP. Holding ≥ LONG_PRESS_MS fires the talk gesture (and pauses
    // music); a quick release toggles play/pause on the user's music.
    //
    // Threading invariant: setCallback() is called from onCreate() on the main
    // thread with no Handler, so onKeyDown/onKeyUp and the longPress Runnable all
    // run on the single main looper — longFired needs no cross-thread visibility.
    // The @Synchronized below is defensive only; if setup ever moves to a
    // background HandlerThread, longFired must become properly synchronized.
    private var longFired = false
    /** True between a DOWN and its matching UP. Guards against BT stacks that
     *  deliver a duplicate UP (or an UP with no preceding DOWN), which would
     *  otherwise fire the tap twice (net no-op toggle, but visibly wrong). */
    private var downSeen = false
    private val longPress = Runnable {
        longFired = true
        Log.i(TAG, "long-press → pause music + talk to my.ai")
        MediaControl.pause(this)
        GlassesGestures.emitTalk()
    }

    @Synchronized
    private fun onKeyDown(ke: KeyEvent) {
        // Bluetooth can auto-repeat DOWN while held; only the first starts the timer.
        if (ke.repeatCount > 0) return
        downSeen = true
        longFired = false
        handler.removeCallbacks(longPress)
        handler.postDelayed(longPress, LONG_PRESS_MS)
    }

    @Synchronized
    private fun onKeyUp() {
        handler.removeCallbacks(longPress)
        if (!downSeen) return                       // stray/duplicate UP — ignore
        downSeen = false
        if (longFired) return                       // already handled as a hold
        // Not a hold (the timer was just cancelled and never ran), so this is a
        // tap — fire it regardless of measured elapsed time. Keying off longFired
        // rather than an elapsed threshold avoids a one-tick dead-zone at exactly
        // LONG_PRESS_MS where neither hold nor tap would fire.
        shortTap()
    }

    private fun shortTap() {
        Log.i(TAG, "single tap → play/pause music")
        if (!MediaControl.toggle(this)) {
            Log.w(TAG, "no music session (Notification Access not granted?)")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        handler.removeCallbacks(longPress)
        runCatching { session?.isActive = false; session?.release() }
        session = null
    }

    private fun buildNotification(): Notification {
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Glasses control",
                NotificationManager.IMPORTANCE_LOW).apply {
                description = "Listens for the glasses touchpad: hold to talk, tap for music."
                setShowBadge(false)
            })
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("my.ai Glasses ready")
            .setContentText("Hold the glasses touchpad to talk; tap for play/pause.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(open)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
    }
}
