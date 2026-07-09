# Game Audio
## SFX Design
- Layer SFX: transient (attack click), body (tonal core), tail (reverb/noise). Mix in DAW, export one-shot; keep attack punchy (<5ms) for responsive game feel.
- Randomize pitch (±2-4 semitones) and volume (±2dB) per play to fight "machine-gun" repetition. Pool 3-5 variants per common sound (footstep, impact, UI click).
- Sample rate 44.1/48kHz; SFX mono (cheaper, spatializes correctly), music/ambience stereo. Export 16-bit PCM WAV as source; compress at import.
- Sidechain-duck music/ambience under key SFX (gunfire, dialogue) so important sounds cut through.
## Buses & Mixing
- Route to a bus tree: Master -> {SFX, Music, Ambience, UI, Dialogue, Voice}. Expose these as player volume sliders. Never let gameplay sounds sum past 0 dBFS -> clipping.
- Bus-level compression/limiting on Master (brickwall limiter at -1 dBFS) prevents clip. Target ~ -16 to -14 LUFS integrated for games.
- HDR audio / dynamic mixing: loud sounds temporarily push quiet ones below audibility threshold, mimicking ear dynamics (Wwise HDR, Unreal).
## Adaptive / Dynamic Music
- Horizontal re-sequencing: swap between segments/sections on beat/bar boundaries (explore -> combat). Use sync points to avoid jarring cuts; crossfade or musical transition ("stinger") on switch.
- Vertical layering (re-orchestration): stems (drums, bass, strings, tension) fade in/out with intensity parameter (0..1). Same loop, different density -> seamless because all stems share tempo/key.
- Drive with a game parameter (RTPC in Wwise, Parameter in FMOD) e.g. `combat_intensity`, `player_health`. Quantize transitions to musical grid.
- Stingers: short non-looping cues fired on events (level-up, death) over the bed.
## 3D Spatial Audio
- Attenuation curve maps distance -> volume; use logarithmic/inverse rolloff (not linear) for realism. Set min distance (full volume) and max distance (silence).
- Doppler for fast movers; spread controls stereo width as source nears. Pan by listener-relative position.
- Occlusion (wall blocks path) = low-pass filter + volume cut; obstruction (partial) = filter only. Raycast listener->source to detect. Reverb zones/aux sends per room for spatial sense.
- HRTF/binaural for headphone spatialization (Steam Audio, Oculus, Resonance). Reverb via convolution or algorithmic aux buses.
## Middleware vs Engine-Native
- FMOD/Wwise: author events, parameters, mixing in an external tool; runtime plays "events" not raw files. Sound designers iterate without code. Better for adaptive music, profiling, memory banks.
- Wwise concepts: Events, RTPCs, States, Switches, Soundbanks. FMOD: Events, Parameters, Snapshots, Banks.
- Engine-native (Unity AudioSource/AudioMixer, Godot AudioStreamPlayer + buses) fine for simpler projects; less tooling for adaptive/interactive scoring.
- Godot: AudioStreamPlayer (2D/3D), buses in the Audio panel, `AudioStreamPlayer3D` handles attenuation. Unity: AudioSource + AudioMixer groups, spatial blend slider (2D<->3D).
## Web Audio (browser games)
- Web Audio API graph: `AudioContext` -> nodes (`GainNode`, `PannerNode`, `BiquadFilterNode`) -> destination. Decode with `decodeAudioData`; play via `AudioBufferSourceNode` (one-shot, non-reusable).
- Autoplay policy: context starts `suspended`; must `resume()` inside a user gesture (click/tap) or nothing plays.
- Sample-accurate scheduling: schedule ahead with `source.start(when)` using `context.currentTime`; don't rely on setTimeout for rhythm. Use a lookahead scheduler for music.
- PannerNode `HRTF` for 3D; short SFX via decoded buffers, long music via `<audio>` MediaElementSource (streams, saves memory).
## Ambience & Reverb
- Layer ambience: a looping bed (room tone, wind) plus randomized one-shots (bird, creak, distant sound) fired on timers to break the loop and hide the seam.
- Reverb zones per space (cave, hall, outdoor); crossfade reverb send levels as the listener moves between zones. Wet/dry balance sells room size.
- Use aux/send buses for reverb and delay so many sources share one effect instance (cheaper than per-source effects).
- Loop points must be sample-accurate and zero-crossing to avoid clicks; author seamless loops in the DAW, verify no DC offset.
## Dialogue & VO
- Duck music/ambience under dialogue (sidechain or snapshot) so lines stay intelligible; restore after.
- Barks (short reactive VO) need cooldowns and priority so NPCs don't talk over each other or spam; pick one speaker, mute others.
- Localize: keep VO on separate banks per language; subtitles synced to audio events, not fixed timers.
## Performance
- Voice limit / polyphony: cap concurrent voices; use priority + virtualization (stop/steal lowest-priority, quietest, or furthest). Same sound spamming -> collapse to one instance.
- Streaming vs loaded: stream long files (music, ambience) from disk; load short SFX fully into memory. Streaming too many -> disk/decode stalls.
- Compression: Vorbis/MP3/ADPCM for size; PCM for tiny latency-critical SFX. Decompress-on-load for frequent SFX (CPU cost) vs compressed-in-memory (RAM cost) vs streamed.
- Bank/pool management: preload per-level banks, unload on level exit. Object-pool AudioSources to avoid alloc spikes.
## Gotchas -> Fix
- **Machine-gun / robotic repetition**: same sample replayed identically. Fix: pitch+volume randomization and variant pools; add a minimum retrigger interval.
- **Sound not playing at all**: AudioContext suspended (web), muted bus, source out of attenuation range, or voice-limited/stolen. Fix: check context state/resume on gesture, verify bus volumes, log active voice count.
- **Clipping / distortion on busy scenes**: too many sounds summing past 0dBFS. Fix: master limiter, lower per-instance gain, HDR/ducking, cap voices.
- **One-shot sound never fires again (Web Audio)**: `AudioBufferSourceNode` is single-use. Fix: create a new source node each play (buffers are reusable, sources are not).
- **Music transition sounds jarring**: switched mid-beat. Fix: quantize transitions to bar/beat, use crossfades or stingers, sync stems to same tempo/key.
- **Footsteps/impacts feel laggy**: high attack time or streamed/decoded on demand. Fix: preload into memory, trim silence at head, keep attack <5ms.
- **3D sound audible everywhere or cuts too fast**: linear rolloff or bad min/max distance. Fix: logarithmic attenuation, tune min (full) and max (silent) distances.
- **Doppler pitch-warble artifacts**: extreme velocity or teleport. Fix: clamp doppler factor, disable on teleport/cutscene-warp.
- **Memory bloat**: everything loaded as uncompressed PCM. Fix: compress ambience/music (Vorbis), stream long clips, per-level bank load/unload.
- **Occlusion pops**: instant filter switch. Fix: interpolate low-pass cutoff over ~100-200ms instead of snapping.
- **Looping sound clicks at seam**: non-zero-crossing loop point or DC offset. Fix: trim loop to zero crossings, remove DC offset, use middleware loop regions.
- **Dialogue drowned out**: no ducking. Fix: snapshot/sidechain lower music+ambience while VO plays, restore on end.
- **Reverb sounds wrong when moving between rooms**: no zone crossfade. Fix: interpolate reverb send between zone volumes over transition.
- **Audio latency (sound lags input)**: large buffer size or decode-on-demand. Fix: lower DSP buffer, preload SFX, use platform low-latency audio path.
- **NPCs talk over each other**: no bark arbitration. Fix: priority + per-line cooldowns, single active speaker.
