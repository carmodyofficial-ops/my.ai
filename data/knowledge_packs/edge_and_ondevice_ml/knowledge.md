# Edge & On-Device ML

## Why on-device (vs cloud inference)
- **Latency**: no network round-trip; real-time (<10-50ms) for AR, keyboard, camera.
- **Privacy**: raw data (voice, images, health) never leaves device; aids HIPAA/GDPR.
- **Offline**: works with no/intermittent connectivity.
- **Cost**: no per-inference server/GPU bill; shifts compute to user hardware.
- **Reliability**: no dependence on backend uptime.
- Tradeoffs: smaller models → lower accuracy; harder updates; device fragmentation.

## Constraints (design around these)
- **Compute**: mobile CPU/NPU TOPS ≪ datacenter GPU.
- **Memory**: RAM budget (model + activations + KV cache); mobile apps killed if they exceed ~a few hundred MB working set.
- **Storage/binary size**: app download limits; ship small weights.
- **Battery**: sustained inference drains battery; NPU far more efficient than CPU/GPU.
- **Thermal**: sustained load → **throttling** → clocks drop → latency doubles after ~30-60s. Benchmark steady-state, not first-run.

## Model optimization
### Quantization (biggest lever)
- **PTQ (post-training)**: quantize a trained FP model. Fast, no retraining. **int8** typical (weights+activations). Needs a **calibration set** (~100-1000 samples) to pick activation ranges.
- **QAT (quantization-aware training)**: simulate quant in training (fake-quant nodes) → recovers accuracy; needed for int4 / aggressive quant / sensitive models.
- **Schemes**: symmetric vs asymmetric; per-tensor vs **per-channel** (per-channel weights = much better accuracy); dynamic (activations quantized at runtime) vs static (calibrated).
- **int4 / lower**: for LLMs — GPTQ, AWQ, GGUF k-quants (Q4_K_M etc.). Mixed precision keeps sensitive layers higher.
- Rule of thumb: int8 PTQ ≈ <1% accuracy drop on many CNNs; verify per model.
### Other
- **Pruning**: remove weights (unstructured = sparse, needs sparse kernels to speed up; **structured**/channel pruning = real speedup on dense HW).
- **Knowledge distillation**: train small "student" to mimic large "teacher" logits — recover accuracy at small size.
- **Operator/layer fusion**: fold conv+BN+ReLU into one op; reduces memory traffic (runtime/compiler does this).
- **Architecture**: use mobile-first nets (MobileNet, EfficientNet-Lite, SqueezeNet) or NAS-designed models.

## Formats & runtimes
- **TFLite / LiteRT** (Android/embedded): `.tflite` flatbuffer; delegates (NNAPI, GPU, Hexagon, Core ML). NNAPI deprecated → vendor delegates.
- **Core ML** (`.mlpackage`/`.mlmodel`, Apple): converts via `coremltools`; runs on CPU/GPU/**ANE** (Apple Neural Engine). Compute-unit selection matters.
- **ONNX Runtime**: cross-platform; execution providers (CoreML, NNAPI, QNN, XNNPACK, CUDA, TensorRT). Good portability.
- **ExecuTorch** (PyTorch): export → lowered `.pte` for mobile/embedded; successor to PyTorch Mobile.
- **llama.cpp / GGUF**: on-device LLMs; CPU+Metal/CUDA; k-quant formats. **MLC-LLM**, **MediaPipe LLM Inference** also.
- **TensorRT** (NVIDIA Jetson edge), **OpenVINO** (Intel edge), **NCNN/MNN** (mobile), **Qualcomm QNN/SNPE**, **Ethos-U/TVM/microTVM** and **TFLite Micro** for MCUs.

## Hardware accelerators
- **NPU / Neural Engine**: dedicated matmul/convolution; highest perf/watt; limited op support → may fall back to CPU silently.
- **GPU**: flexible, good for parallel; more power than NPU.
- **DSP** (Hexagon): efficient for int8.
- **CPU**: universal fallback (XNNPACK); slowest.
- **MCU** (Cortex-M, ESP32): KB-MB RAM, TFLite Micro, int8 only, no dynamic allocation.

## On-device LLMs
- Small models: Phi-3-mini, Gemma 2B, Llama-3.2-1B/3B, Qwen2.5 small, quantized to 4-bit.
- Memory ≈ params × bytes/param (4-bit ≈ 0.5 B/param) + KV cache (grows with context length × layers). Context length is the RAM killer.
- Prefill (prompt) vs decode (token/s) — decode is memory-bandwidth bound.
- Use for: on-device assistants, summarization, function-calling; keep context short.

## Use-case fit (when on-device wins)
- Strong fit: wake-word / keyword spotting, on-device ASR, camera effects, AR/pose, OCR, keyboard prediction, photo classification, offline translation, anomaly detection on sensors.
- Weak fit: large-context LLM reasoning, huge retrieval corpora, frequently-updated models, workloads needing big-batch throughput — keep in cloud or hybrid (small model local, escalate to cloud).
- **Hybrid pattern**: on-device model handles common/low-risk cases + falls back to cloud for hard ones (cascade); or on-device for privacy-sensitive preprocessing then cloud.

## Benchmarking
- Measure **on target device**, not desktop: p50/p95 **latency**, **peak memory (RSS)**, model load time, **sustained** throughput (thermal), energy (mWh/inference), accuracy on device (quant can differ from FP).
- Tools: TFLite Benchmark tool, Core ML performance report (Xcode), ONNX Runtime perf, `xcrun coremlcompiler`, platform profilers.

## Deployment & updates
- Ship model in app bundle vs **OTA download** (update model without app release; verify checksum/signature).
- **Versioning**: pin runtime+model version; feature-flag rollouts; A/B on device.
- **Compatibility**: gate on OS/HW capability; provide FP fallback for unsupported delegates.
- Monitor via aggregated/on-device telemetry (privacy-preserving); no raw data upload.
- **On-device training/personalization**: federated learning (train locally, aggregate gradients centrally, DP noise), or lightweight fine-tune/LoRA adapters on-device; keep base weights frozen.

## Conversion pipeline (typical)
- PyTorch/TF → export (`torch.export`/ExecuTorch, `tf.lite.TFLiteConverter`, `coremltools.convert`, `torch.onnx.export`) → optimize (quantize/prune/fuse) → validate numerics vs source → target-device benchmark.
- **Golden-output test**: run same inputs through source FP model and converted model; assert max abs/relative error under threshold; catch silent conversion bugs.
- Freeze/trace dynamic control flow; fixed input shapes convert best (dynamic shapes often unsupported or slow).

## Memory math (LLM sizing)
- Weights: `params × bytes_per_param` (fp16=2, int8=1, int4≈0.5).
- KV cache per token ≈ `2 × n_layers × n_kv_heads × head_dim × bytes`. Total = ×context length. This is what OOMs long chats.
- Peak = weights + KV cache + activation scratch + framework overhead. Leave headroom; OS kills apps over budget.

## Sensor/preprocessing parity
- On-device preprocessing (resize, normalize, color space, mel-spectrogram) must **exactly match training**; mismatch = silent accuracy loss with no error.
- Quantize/optimize the *whole* pipeline, not just the model; camera/audio format differences bite.

## Practical numbers (rules of thumb)
- int8 PTQ: ~4x smaller, ~2-4x faster than fp32, typically <1% top-1 drop on well-behaved CNNs; verify per model.
- NPU vs CPU: often 5-20x faster and far lower energy — but only for supported ops.
- Mobile RAM working-set budget: keep well under a few hundred MB or risk OS termination; peak matters, not average.
- On-device 1-3B LLM at 4-bit: single-digit GB RAM, tens of tokens/sec decode on a modern phone NPU/GPU; degrades with context length.

## Pitfalls -> Fix
- **Accuracy drops after quantization** → outlier activations, per-tensor scale. **Fix**: per-channel weights, better calibration set, QAT, keep first/last layers FP16, check specific class regressions not just top-1.
- **Unsupported ops** → op falls back to CPU or conversion fails. **Fix**: check runtime op coverage before designing net; replace/rewrite custom ops; use supported layers; inspect delegate partitioning logs.
- **Memory blowup on device** → activations/KV cache, not weights, dominate. **Fix**: reduce input resolution/batch, shorter context, streaming, quantize activations, reuse buffers.
- **Thermal throttling** → benchmarked cold, ships slow. **Fix**: measure sustained (30-60s) steady-state; use NPU; duty-cycle inference; cap frame rate.
- **Silent accelerator fallback** → "NPU" actually runs on CPU, 5x slower. **Fix**: verify compute unit actually used (profiler); count ops offloaded; log delegate.
- **Wrong runtime for platform** → e.g. ONNX Runtime CPU on iOS instead of Core ML/ANE. **Fix**: match runtime to HW (Core ML on Apple, QNN/NNAPI on Android, TensorRT on Jetson).
- **No on-device eval** → validated only in FP on server. **Fix**: run accuracy suite on the quantized model on real hardware; numerics differ.
- **Device fragmentation** → works on flagship, OOM/slow on low-end. **Fix**: test tiers; capability gates; multiple model sizes.
- **Binary size explosion** → multiple models/runtimes bundled. **Fix**: single runtime, OTA weights, weight sharing/palettization.
- **Ignoring load/init cost** → first inference slow (compilation/warmup). **Fix**: warm up at app start; cache compiled model (Core ML compile, ORT session).
- **KV cache OOM with long context** → LLM crashes mid-conversation. **Fix**: cap/trim context, sliding window, quantized KV cache.
- **Debugging quant on desktop only** → x86 sim ≠ ARM NPU numerics. **Fix**: reproduce on device; compare intermediate tensors.
- **Preprocessing mismatch train vs device** → silent accuracy loss, no error. **Fix**: golden-output parity test; identical normalize/resize/color/audio pipeline.
- **Dynamic input shapes** → conversion fails or de-optimizes. **Fix**: fix shapes, pad/bucket, or use runtimes with explicit dynamic-shape support.
- **No numerics validation post-conversion** → converter bug ships. **Fix**: golden-output test with error threshold on every export.
- **Bad calibration set for PTQ** → wrong activation ranges, clipped outliers. **Fix**: representative in-distribution calibration data covering edge cases.
- **Unstructured pruning without sparse kernels** → smaller file, zero speedup. **Fix**: structured/channel pruning for latency wins on dense HW.
