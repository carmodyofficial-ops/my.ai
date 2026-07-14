package ai.my.glasses.wearables

import androidx.activity.ComponentActivity

/**
 * Activity-side bridge to the glasses.
 *
 * Why this exists: the DAT SDK's permission launcher
 * (`Wearables.RequestPermissionContract()`) must be registered while the
 * Activity is still being constructed, and its type is SDK-only — so
 * MainActivity (in the `main` source set, which must compile WITHOUT the SDK)
 * cannot name it. The real implementation, [MetaGlassesHost], lives in the
 * `metadat` source set and is resolved reflectively by [GlassesHostFactory].
 *
 * A host is per-Activity: it owns that Activity's launcher. The *adapter* it
 * exposes is not — see [GlassesAdapters].
 */
interface GlassesHost {
    val adapter: WearablesAdapter

    /**
     * Ask for the glasses-side CAMERA permission. The prompt is shown by the
     * Meta AI app; the SDK delivers the result to a launcher this host owns.
     */
    suspend fun requestGlassesCameraPermission(): Boolean
}

/**
 * The one adapter in the process.
 *
 * The DAT SDK permits a single DeviceSession per device. The adapter used to be
 * a field of the host, hence of MainActivity — so every configuration change
 * built a *second* adapter while the retained ViewModel kept driving the first,
 * and SDK calls were made against a destroyed Activity. Two adapters racing for
 * one pair of glasses is heard as a connect tone followed immediately by a
 * disconnect tone. Hoisting the adapter to the process makes that structurally
 * impossible; the host below stays per-Activity because its launcher must be.
 */
object GlassesAdapters {
    val shared: WearablesAdapter by lazy {
        if (!ai.my.glasses.BuildConfig.META_SDK) MockWearablesAdapter()
        else runCatching {
            Class.forName("ai.my.glasses.wearables.MetaDatAdapter")
                .getDeclaredConstructor().newInstance() as WearablesAdapter
        }.getOrElse { MockWearablesAdapter() }
    }
}

/**
 * Hardware-free host: the shared adapter, permission auto-granted.
 *
 * It is also the FALLBACK when the real host can't be constructed in a META_SDK
 * build — and there the shared adapter is the *real* MetaDatAdapter. Blindly
 * returning true would then mark the glasses-camera permission granted without
 * anything ever having asked for it, so the failure would resurface much later
 * as an opaque CAPTURE_FAILED. Auto-grant only where it is actually true.
 */
class MockGlassesHost : GlassesHost {
    override val adapter: WearablesAdapter = GlassesAdapters.shared
    override suspend fun requestGlassesCameraPermission(): Boolean =
        !ai.my.glasses.BuildConfig.META_SDK
}

object GlassesHostFactory {
    /**
     * Called from a MainActivity field initializer, so the SDK launcher is
     * registered before the Activity starts. Falls back to the mock host when
     * the SDK isn't in the build (or the class is missing/stripped).
     *
     * Reflection is the price of keeping `main` SDK-free; if release
     * minification is ever enabled for a metaSdk build, add:
     *   -keep class ai.my.glasses.wearables.MetaGlassesHost { *; }
     *   -keep class ai.my.glasses.wearables.MetaDatAdapter { *; }
     */
    fun create(activity: ComponentActivity): GlassesHost {
        if (!ai.my.glasses.BuildConfig.META_SDK) return MockGlassesHost()
        return runCatching {
            Class.forName("ai.my.glasses.wearables.MetaGlassesHost")
                .getConstructor(ComponentActivity::class.java)
                .newInstance(activity) as GlassesHost
        }.getOrElse { MockGlassesHost() }
    }
}
