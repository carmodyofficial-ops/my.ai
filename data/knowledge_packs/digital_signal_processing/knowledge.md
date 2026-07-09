# Digital Signal Processing

## Core facts (read first)
- **Nyquist-Shannon**: to reconstruct a signal, sample at `fs > 2·f_max`. Content above `fs/2` (**Nyquist frequency**) **aliases** — folds down to a false low frequency and is unrecoverable. Always **anti-alias filter (analog LPF)** before the ADC.
- Alias frequency of `f` sampled at `fs`: `|f − round(f/fs)·fs|` (reflects around `fs/2`).
- **DFT** turns `N` time samples into `N` complex frequency bins. **FFT** computes it in **O(N log N)** (vs O(N²) naive) — usually radix-2, so favor `N` = power of 2.
- **Bin spacing** = `fs/N` Hz; bin `k` -> frequency `k·fs/N`. **Frequency resolution improves only by longer records** (more time), not more zero-padding (which only interpolates the display).
- **Convolution in time = multiplication in frequency** (and vice versa). Filtering ≡ convolving with the impulse response.

## Signals & sampling
- Continuous `x(t)` vs discrete `x[n]` (`= x(nT)`, `T = 1/fs`). Digital = discrete-time + discrete-amplitude.
- **Quantization**: rounding amplitude to `2^b` levels adds noise. SNR for full-scale sine `≈ 6.02·b + 1.76 dB` (~6 dB per bit). **Dither** (add tiny noise) decorrelates quantization distortion.
- Common signals: impulse `δ[n]`, step, sinusoid, complex exponential `e^{jωn}` (eigenfunction of LTI systems). Energy vs power signals.
- **LTI systems** characterized fully by impulse response `h[n]`; output `y = x * h`. Frequency response `H(e^{jω})` = DTFT of `h`.

## Fourier analysis
- **DTFT** (continuous freq, infinite sum) vs **DFT** (sampled freq, finite N, what computers use). **FFT** = fast DFT algorithm. `X[k] = Σ x[n] e^{−j2πkn/N}`.
- Magnitude spectrum `|X[k]|`, phase `∠X[k]`. Real input -> **conjugate-symmetric** spectrum -> only `N/2+1` unique bins (use `rfft`). Power spectral density (PSD) via periodogram/**Welch** (average windowed segments -> lower variance).
- **Windowing & spectral leakage**: DFT assumes the block repeats periodically. A non-integer number of cycles -> discontinuity at edges -> energy **leaks** across bins. Apply a **window** (Hann, Hamming, Blackman, Kaiser) to taper edges: reduces leakage/sidelobes but **widens the main lobe** (worse resolution) — a tradeoff. Rectangular window = best resolution, worst leakage.
- **Zero-padding** interpolates the spectrum (smoother plot) but adds **no** real resolution. **Scalloping loss**: a tone between bins reads low.
- Fs, N, window are the three knobs: resolution `= fs/N`, span `= fs/2`.

## Convolution & correlation
- Linear convolution `y[n] = Σ x[k]h[n−k]`; length `Nx+Nh−1`. Fast via FFT: `ifft(fft(x)·fft(y))` — but that's **circular** convolution; **zero-pad both to ≥ Nx+Nh−1** to get linear (else time-domain wraparound/aliasing).
- Long streams: **overlap-add** / **overlap-save** block convolution.
- Cross-correlation for delay/similarity (matched filter, template matching); autocorrelation for periodicity.

## Filters
- **FIR** (finite impulse response): `y[n]=Σ b_k x[n−k]`, no feedback -> **always stable**, can be **exactly linear phase** (symmetric taps -> constant group delay, no phase distortion). Cost: many taps for sharp cutoff. Design: **windowed-sinc**, **Parks-McClellan/Remez** (equiripple, optimal).
- **IIR** (infinite): has feedback (poles) -> far fewer coefficients for a sharp response, but can be **unstable** and has **nonlinear phase**. Design from analog prototypes: **Butterworth** (maximally flat), **Chebyshev I/II** (ripple in pass/stop band, steeper), **Elliptic/Cauer** (steepest, ripple both), **Bessel** (best phase/group delay). Map via **bilinear transform**.
- Types: low-pass, high-pass, band-pass, band-stop/notch. Specs: passband/stopband edges, ripple (dB), stopband attenuation, transition width.
- **z-transform** `X(z)=Σ x[n]z^{−n}`: poles/zeros in the z-plane. **Stability (IIR): all poles strictly inside the unit circle `|z|<1`.** Zeros shape nulls. Unit circle `z=e^{jω}` = frequency response.
- Implement IIR as **cascaded second-order sections (biquads/SOS)**, not one high-order transfer function (avoids coefficient quantization instability).

## Time vs frequency domain & real-time
- Time domain: transients, timing, amplitude. Frequency domain: tones, harmonics, filtering. **STFT/spectrogram** = FFT over sliding windows -> time-frequency (tradeoff: window length balances time vs freq resolution; wavelets adapt).
- Real-time DSP: fixed latency, block processing, ring buffers, **fixed-point** arithmetic on DSP chips (watch overflow/saturation, Q-format scaling). Group delay = latency; linear-phase FIR delay `= (N−1)/2` samples.
- Resampling: upsample (insert zeros + LPF interpolate), downsample (**LPF first to avoid aliasing**, then decimate). Rational rate change `L/M`.
- Applications: audio (EQ, compression, MP3/AAC via MDCT), comms (modulation QAM/OFDM, pulse shaping, equalization), radar/sonar, biomedical (ECG/EEG), image/video.

## Filter design & implementation details
- **FIR design methods**: window method (ideal sinc × window — simple, suboptimal), frequency sampling, **Parks-McClellan/Remez** (equiripple, minimum taps for a spec), least-squares. `scipy.signal.firwin`, `remez`, `firwin2`.
- **IIR design**: `scipy.signal.butter/cheby1/cheby2/ellip/bessel` (specify order + cutoff normalized to Nyquist `fs/2`), or `iirdesign` from specs. Get **SOS** output (`output='sos'`) and filter with `sosfilt`/`sosfiltfilt`.
- **Zero-phase filtering** (`filtfilt`): forward+backward pass cancels phase, doubles attenuation, no delay — offline only (non-causal). Real-time must use causal `lfilter`/`sosfilt` and accept delay.
- **Order/rolloff**: higher order = steeper transition, more ringing/latency, more numerical risk. Rolloff ~`6·order` dB/octave for Butterworth.
- Multirate: polyphase filters for efficient resampling; CIC filters for cheap decimation in hardware.

## Spectral estimation & DFT details
- **Periodogram** = `|FFT|²/N` — high variance (doesn't shrink with N). **Welch**: split into overlapping windowed segments, average periodograms -> lower variance, coarser resolution. **Multitaper** (Slepian/DPSS) for better bias/variance.
- **Bartlett** = Welch with no overlap. Overlap 50% (Hann) is common.
- **Coherent gain** (window mean) scales amplitude; **ENBW** (equivalent noise bandwidth) scales noise floor — normalize accordingly for calibrated spectra.
- FFT length `N`: pad to power of 2 for speed; DC at bin 0, Nyquist at `N/2` (real signals). `fftshift` to center zero frequency for display. Negative frequencies live in the upper half.

## Applications detail
- **Audio**: parametric/graphic EQ (biquads), dynamics (compressor/limiter — envelope follower), reverb (comb+allpass, convolution), pitch (phase vocoder), lossy codecs use MDCT + psychoacoustic masking.
- **Comms**: pulse shaping (raised-cosine to limit ISI), matched filter, carrier/timing recovery (PLL), equalizers (LMS/RLS adaptive), OFDM (IFFT/FFT-based subcarriers, cyclic prefix), FEC.
- **Biomedical/sensor**: notch filter mains hum (50/60 Hz), baseline wander high-pass, adaptive noise cancellation.

## Pitfalls -> Fix
- **Aliasing** (undersampling / no anti-alias filter) -> phantom low-frequency tones -> analog LPF before ADC; sample `fs > 2·f_max`; LPF before any downsampling.
- **Spectral leakage** (non-integer cycles in the block) -> smeared/inaccurate peaks -> apply a window (Hann/Hamming); pick block length near integer cycles.
- **Zero-padding mistaken for resolution** -> peaks look sharper but aren't -> real resolution needs a longer time record (`fs/N`).
- **Circular convolution wraparound** (FFT filtering without padding) -> corrupted block edges -> zero-pad to `Nx+Nh−1`; use overlap-add/save for streams.
- **Off-by-one / bin indexing** -> wrong frequency labels -> bin `k` = `k·fs/N`; account for the `N/2+1` real-FFT layout and DC at bin 0; Nyquist at `N/2`.
- **IIR instability** (poles outside unit circle, coefficient quantization) -> output blows up / limit cycles -> check pole radius `<1`; implement as SOS/biquads; use enough coefficient bits.
- **Ignoring phase / nonlinear phase** -> waveform distortion, smeared transients -> use linear-phase FIR when phase matters (audio, comms).
- **Fixed-point overflow/saturation** -> clipping, wraparound noise -> scale (Q-format), add guard bits, saturate not wrap.
- **Windowing amplitude error** -> magnitudes read low (coherent/incoherent gain) -> normalize by the window's gain; account for scalloping.
- **Group delay / latency ignored** in real-time loops -> misaligned/late output -> account for filter delay `(N−1)/2`; budget block latency.
- **DFT amplitude scaling** confusion -> wrong dB levels -> divide by `N` (or window sum); single-sided spectrum doubles non-DC/Nyquist bins.
- **Cutoff not normalized to Nyquist** in `scipy.signal.butter` -> wrong filter band -> pass `Wn = fc/(fs/2)` (or supply `fs=`).
- **Transfer-function (`b,a`) IIR at high order** -> coefficient quantization instability -> always design/filter in **SOS** form.
- **Using `filtfilt` in real-time** -> non-causal, impossible on a stream -> `filtfilt` offline only; causal filters live.
- **Periodogram noisy, drawing conclusions** -> variance never averages out -> use Welch/multitaper averaging.
- **Forgetting decimation LPF** -> aliasing on downsample -> low-pass to new Nyquist before decimating (or use `resample_poly`).
- **Comparing spectra with different windows/lengths/scaling** -> apples to oranges -> fix window, N, and normalization; account for ENBW.
