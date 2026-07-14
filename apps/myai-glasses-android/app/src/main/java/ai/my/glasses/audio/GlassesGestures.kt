package ai.my.glasses.audio

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/**
 * Process-wide bus from the glasses media-button detector
 * ([GlassesControlService]) to the ViewModel.
 *
 * Why a bus: the media-button service and the ViewModel have independent
 * lifecycles (the service can run while the Activity is gone), so they can't
 * hold references to each other. A replay-less SharedFlow delivers a
 * triple-tap to whoever is currently collecting.
 */
object GlassesGestures {
    // extraBufferCapacity so tryEmit never drops an event when no collector is
    // momentarily attached (e.g. during an Activity recreation).
    private val _talk = MutableSharedFlow<Unit>(extraBufferCapacity = 4)
    val talk: SharedFlow<Unit> = _talk

    fun emitTalk() { _talk.tryEmit(Unit) }

    /** Raw media-key descriptions from GlassesControlService, for the Diagnostics
     *  screen — so you can tap/hold the glasses and see exactly what the button
     *  emits on real hardware (the load-bearing gesture unknown). */
    private val _keys = MutableSharedFlow<String>(extraBufferCapacity = 16)
    val keyEvents: SharedFlow<String> = _keys

    fun emitKey(desc: String) { _keys.tryEmit(desc) }
}
