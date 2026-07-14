package ai.my.glasses.audio

import android.service.notification.NotificationListenerService

/**
 * Exists only to unlock MediaSessionManager.getActiveSessions — Android gates
 * that behind an *enabled* NotificationListenerService. We read no
 * notifications; [MediaControl] uses the granted access to find and control the
 * user's music session so a single glasses tap can play/pause it.
 *
 * The user grants this once in Settings → Notification access → my.ai Glasses.
 */
class MyAiMediaListener : NotificationListenerService()
