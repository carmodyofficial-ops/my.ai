package ai.my.glasses.audio

import android.content.ComponentName
import android.content.Context
import android.media.session.MediaController
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.provider.Settings
import android.util.Log

/**
 * Controls whatever app is currently playing media on the phone — used so the
 * glasses gestures can toggle or pause the user's MUSIC, not this app.
 *
 * Reaching another app's transport controls requires MediaSessionManager, which
 * is only available to an enabled NotificationListenerService ([MyAiMediaListener]).
 * Everything here degrades to a no-op (returning false) when Notification Access
 * hasn't been granted, so the app never crashes for lack of it.
 */
object MediaControl {

    private const val TAG = "MediaControl"

    fun hasNotificationAccess(ctx: Context): Boolean {
        val enabled = Settings.Secure.getString(
            ctx.contentResolver, "enabled_notification_listeners") ?: ""
        return enabled.split(":").any { it.contains(ctx.packageName) }
    }

    /** The MediaController of a *different* app that is currently playing. */
    private fun activeMusic(ctx: Context): MediaController? {
        if (!hasNotificationAccess(ctx)) return null
        return runCatching {
            val msm = ctx.getSystemService(Context.MEDIA_SESSION_SERVICE) as MediaSessionManager
            val comp = ComponentName(ctx, MyAiMediaListener::class.java)
            val controllers = msm.getActiveSessions(comp)
            // Prefer a session that is actively playing; fall back to the first
            // real media app (never our own control session).
            controllers.firstOrNull {
                it.packageName != ctx.packageName &&
                    it.playbackState?.state == PlaybackState.STATE_PLAYING
            } ?: controllers.firstOrNull { it.packageName != ctx.packageName }
        }.getOrElse { Log.w(TAG, "getActiveSessions failed", it); null }
    }

    /** Single tap: play/pause the user's music. Returns true if handled. */
    fun toggle(ctx: Context): Boolean {
        val c = activeMusic(ctx) ?: return false
        val playing = c.playbackState?.state == PlaybackState.STATE_PLAYING
        if (playing) c.transportControls.pause() else c.transportControls.play()
        return true
    }

    /** Long hold: make sure music is paused before we start listening. */
    fun pause(ctx: Context): Boolean {
        val c = activeMusic(ctx) ?: return false
        if (c.playbackState?.state == PlaybackState.STATE_PLAYING) {
            c.transportControls.pause()
        }
        return true
    }
}
