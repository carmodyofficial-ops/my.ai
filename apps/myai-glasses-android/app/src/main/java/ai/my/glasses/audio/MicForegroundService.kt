package ai.my.glasses.audio

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import ai.my.glasses.MainActivity

/**
 * Holds a microphone foreground service for the duration of an utterance.
 *
 * Why: on Android 12+ an app that is not foreground has its mic muted and its
 * Bluetooth SCO route torn down. The manifest already declared
 * FOREGROUND_SERVICE + FOREGROUND_SERVICE_MICROPHONE, but no service ever
 * existed to use them — so anything that backgrounded the app mid-capture (most
 * notably the DAT registration bounce into the Meta AI app, but also a screen
 * blank) silently killed the mic and dropped SCO, which the glasses report as a
 * disconnect tone.
 *
 * Deliberately minimal: it exists only to keep the process foreground while
 * recording. [VoiceSession] owns the actual audio.
 */
class MicForegroundService : android.app.Service() {

    companion object {
        private const val TAG = "MicForegroundService"
        private const val CHANNEL_ID = "myai_mic"
        private const val NOTIFICATION_ID = 42

        /** Best-effort: a failure here must never take down the voice loop —
         *  the mic still works while the app is in the foreground. */
        fun start(context: Context) {
            runCatching {
                context.startForegroundService(Intent(context, MicForegroundService::class.java))
            }.onFailure { Log.w(TAG, "could not start mic foreground service", it) }
        }

        fun stop(context: Context) {
            runCatching {
                context.stopService(Intent(context, MicForegroundService::class.java))
            }.onFailure { Log.w(TAG, "could not stop mic foreground service", it) }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // This is the call that can actually kill the app, not startForegroundService():
        // promoting to foreground throws SecurityException on API 34+ if RECORD_AUDIO
        // was revoked, and ForegroundServiceStartNotAllowedException if the process
        // left the while-in-use window before this ran. The voice loop still works
        // in the foreground without us, so degrade instead of crashing.
        runCatching {
            ServiceCompat.startForeground(
                this, NOTIFICATION_ID, buildNotification(),
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q)
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE else 0,
            )
        }.onFailure {
            Log.w(TAG, "could not promote to foreground; mic holds only while visible", it)
            stopSelf()
        }
        // Not sticky: if the process dies mid-utterance the recording is gone
        // anyway, and silently re-acquiring the mic later would be a privacy bug.
        return START_NOT_STICKY
    }

    private fun buildNotification(): Notification {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Listening",
                NotificationManager.IMPORTANCE_LOW).apply {
                description = "Shown while my.ai is capturing an utterance."
                setShowBadge(false)
            }
        )
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("my.ai is listening")
            .setContentText("Microphone is open for your question.")
            .setSmallIcon(android.R.drawable.presence_audio_online)
            .setContentIntent(open)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .build()
    }
}
