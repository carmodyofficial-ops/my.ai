package ai.my.glasses.wearables

import android.util.Log
import androidx.activity.ComponentActivity
import com.meta.wearable.dat.core.Wearables
import com.meta.wearable.dat.core.types.Permission
import com.meta.wearable.dat.core.types.PermissionStatus
import kotlin.coroutines.resume
import kotlinx.coroutines.CancellableContinuation
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withTimeoutOrNull

/**
 * Real-SDK host. Constructed from a MainActivity field initializer so the
 * DAT permission launcher is registered before the Activity starts (the SDK
 * requires this, exactly as in Meta's CameraAccess sample).
 *
 * The host is per-Activity because the launcher must be; the adapter it exposes
 * is the process-wide singleton (see [GlassesAdapters]) so a config change
 * cannot spawn a rival DeviceSession.
 *
 * The Mutex serializes permission requests — the SDK delivers results to a
 * single launcher, so concurrent requests would race for the continuation.
 */
class MetaGlassesHost(activity: ComponentActivity) : GlassesHost {

    private companion object {
        const val TAG = "MetaGlassesHost"
        // The prompt lives in the Meta AI app; a user who never answers it must
        // not strand us. Matches register()'s ceiling in MetaDatAdapter.
        const val PERMISSION_TIMEOUT_MS = 120_000L
    }

    override val adapter: WearablesAdapter = GlassesAdapters.shared

    private var continuation: CancellableContinuation<PermissionStatus>? = null
    private val mutex = Mutex()

    private val permissionLauncher =
        activity.registerForActivityResult(Wearables.RequestPermissionContract()) { result ->
            val status = result.getOrDefault(PermissionStatus.Denied)
            val cont = continuation
            continuation = null
            // Only resume a continuation that is still waiting: if the Activity
            // was recreated while the prompt was up, the result is redelivered to
            // the NEW host, whose continuation is null.
            if (cont != null && cont.isActive) cont.resume(status)
        }

    /**
     * Ask the Meta AI app for the glasses-side CAMERA permission.
     *
     * Bounded, because this is awaited by the ViewModel's one-shot bootstrap: an
     * Activity recreated while the prompt is showing sends the result to the new
     * host's launcher, leaving THIS continuation with nobody to resume it. That
     * hung the bootstrap forever, and since the bootstrap guard skips while it is
     * still active, connect() would then never be called again for the life of
     * the process — the glasses would simply never connect.
     */
    override suspend fun requestGlassesCameraPermission(): Boolean = mutex.withLock {
        val status = withTimeoutOrNull(PERMISSION_TIMEOUT_MS) {
            suspendCancellableCoroutine { cont ->
                continuation = cont
                cont.invokeOnCancellation { continuation = null }
                permissionLauncher.launch(Permission.CAMERA)
            }
        }
        if (status == null) {
            Log.w(TAG, "glasses CAMERA permission timed out with no result")
            continuation = null
        }
        status == PermissionStatus.Granted
    }
}
