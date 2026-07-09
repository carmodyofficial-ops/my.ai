# Deep Learning

## Neurons, layers, activations
- Neuron: `a = φ(wᵀx + b)`. Layer stacks neurons; depth = number of layers. MLP = fully connected layers.
- **ReLU** `max(0,x)`: default hidden activation; cheap, sparse, no upper saturation. Dead-ReLU if inputs stay negative → LeakyReLU `max(αx,x)` (α≈0.01), PReLU, ELU.
- **GELU** `x·Φ(x)`: smooth, standard in Transformers (BERT/GPT). **SiLU/Swish** `x·σ(x)` similar.
- **Sigmoid** `1/(1+e⁻ˣ)`: binary output only; saturates → vanishing grads in hidden layers.
- **Tanh** `[-1,1]`: zero-centered, still saturates.
- **Softmax** `e^{zᵢ}/Σe^{zⱼ}`: multi-class output → probability simplex. Use logits + combined loss for stability.

## Forward / backprop / autodiff
- Forward: compute activations layer by layer, cache intermediates.
- Backprop: reverse-mode autodiff applies chain rule from loss back to params; `∂L/∂w` per parameter in one backward pass. Frameworks build a computation graph and traverse it.
- Gradient of layer = local Jacobian × upstream gradient.

## Loss functions
- **Cross-entropy** (classification): `-Σ yᵢ log ŷᵢ`. Binary CE for 2-class. Pair softmax/sigmoid with logits (`nn.CrossEntropyLoss` / `BCEWithLogitsLoss`) for numerical stability.
- **MSE** `(ŷ-y)²` / **MAE** / **Huber** (robust) for regression.
- Label smoothing (ε≈0.1) regularizes overconfident classifiers. Focal loss down-weights easy examples (imbalance/detection).

## Optimizers
- **SGD** `θ ← θ - η∇L`. **+Momentum** `v ← βv - η∇L; θ ← θ+v` (β≈0.9): accelerates, dampens oscillation. Nesterov looks ahead.
- **Adam**: per-param adaptive LR from 1st/2nd moment estimates (`β₁=0.9, β₂=0.999, ε=1e-8`); fast, robust default; can generalize slightly worse than tuned SGD+momentum.
- **AdamW**: decouples weight decay from gradient — correct L2 regularization; default for Transformers.
- **LR schedules**: step decay, cosine annealing, **warmup** (ramp LR first ~1–5% steps — critical for Transformers/large batch), 1cycle, ReduceLROnPlateau.
- Typical LR: Adam 1e-3 to 3e-4; SGD 0.1 (with warmup/decay).

## Initialization
- **Xavier/Glorot** (`var=2/(fan_in+fan_out)`) for tanh/sigmoid. **He/Kaiming** (`var=2/fan_in`) for ReLU. Bad init → vanishing/exploding activations. Never init all weights to same constant (symmetry). Biases usually 0.

## Normalization
- **BatchNorm**: normalize per-feature over batch, learn `γ,β`; speeds training, mild regularization; depends on batch stats — unstable for small batches / RNNs; different train vs eval (running stats). Put before or after activation (both used).
- **LayerNorm**: normalize over features per sample; batch-independent; standard in Transformers/RNNs.
- Others: GroupNorm (small-batch vision), InstanceNorm (style transfer), RMSNorm (LLMs).

## Regularization
- **Dropout** `p` (0.1–0.5): zeros units in train, scales at inference (inverted dropout); disable in eval. Don't stack heavily with BatchNorm.
- **Weight decay** (AdamW) ≈ 1e-2 to 1e-4.
- **Early stopping** on val loss (patience). **Data augmentation**. **Gradient/mixup/label smoothing**.

## Architectures
- **MLP**: dense layers; tabular, heads.
- **CNN**: conv filters share weights, local receptive field, translation equivariance; pooling downsamples; params ≪ dense. Vision, audio.
- **RNN / LSTM / GRU**: sequential hidden state; LSTM gates (input/forget/output) mitigate vanishing grads over long sequences; slow (no parallelism over time), largely superseded by Transformers.
- **Transformer**: **self-attention** `softmax(QKᵀ/√dₖ)V` — every token attends to all tokens, `O(n²)` in sequence length; multi-head; positional encodings (no recurrence); parallelizable; residual + LayerNorm + FFN blocks. Backbone of LLMs + ViT.
- **Attention**: `Q=XWq, K=XWk, V=XWv`; scale by `√dₖ` to keep softmax gradients healthy; causal mask for autoregressive.
- Residual/skip connections (`x + F(x)`) enable very deep nets by easing gradient flow.

## Vanishing / exploding gradients
- Vanishing: grads →0 through many saturating layers → early layers don't learn. Fix: ReLU/GELU, residual connections, Batch/LayerNorm, He init, LSTM/GRU for sequences.
- Exploding: grads blow up (deep/RNN). Fix: **gradient clipping** (`clip_grad_norm_`, max-norm 1.0–5.0), smaller LR, normalization.

## Batch size / epochs
- **Batch size** 32–512; larger = more stable gradient, better GPU utilization, but needs LR warmup + scaling (linear scaling rule) and may generalize worse. Small batch = noisier, regularizing.
- **Epoch** = one full pass. Train until val loss plateaus; use early stopping. Steps = `epochs · (N/batch)`.

## GPU / mixed precision
- Move model + data to GPU. **Mixed precision** (fp16/bf16 via autocast + loss scaling): ~2× speed, ~half memory; bf16 needs no loss scaling (Ampere+).
- **Gradient accumulation** simulates large batch on limited VRAM (accumulate over k steps, step once).
- Multi-GPU: DDP (data parallel), FSDP/ZeRO (shard params for huge models), pipeline/tensor parallel.

## CNN specifics
- Conv layer: filters share weights, local receptive field; output `⌊(H+2p−k)/s⌋+1`. Stacking small 3×3 convs > one large kernel (fewer params, more nonlinearity).
- Pooling / strided conv downsamples; 1×1 conv mixes channels; global average pooling replaces bulky FC heads.
- Residual `x+F(x)` and dense connections train very deep nets. Depthwise-separable convs cut compute (MobileNet).

## RNN / sequence specifics
- Hidden state carries context; **BPTT** unrolls over time. Vanilla RNN vanishing/exploding → use LSTM (input/forget/output gates + cell state) or GRU (reset/update, fewer params).
- Bidirectional RNN sees full context (non-causal tasks). Teacher forcing during seq2seq training. Largely replaced by Transformers except tiny/streaming cases.

## Attention / Transformer detail
- Scaled dot-product: `Attn(Q,K,V)=softmax(QKᵀ/√dₖ)V`; `√dₖ` scaling prevents softmax saturation.
- Multi-head: `h` parallel projections, concat → learns different relations. Self-attention `O(n²·d)` in sequence length.
- Block: `x → LN → MHA → +residual → LN → FFN(GELU) → +residual`. Positional encoding (sinusoidal or learned/RoPE) injects order. Causal mask for autoregressive decoding.
- Encoder-only (BERT), decoder-only (GPT/LLaMA), encoder-decoder (T5).

## Hyperparameters that matter most
- Learning rate (dominant), batch size, optimizer + weight decay, LR schedule/warmup, architecture depth/width, dropout, init, augmentation strength.
- Sensible defaults: AdamW `lr=3e-4`, `wd=1e-2`, warmup 2–5%, cosine decay, batch 32–256, dropout 0.1, grad-clip 1.0.

## Training diagnostics
- **Overfit a tiny batch first** — if loss can't reach ~0, there's a bug (data/labels/graph).
- Monitor train vs val loss curves, gradient norms, weight/activation histograms, LR.
- Signs: loss plateau early → LR/capacity/init; loss spikes → LR too high or bad batch; val diverges from train → overfit.
- Checkpoint best val; use early stopping (patience). Track a fixed val set + fixed seed for comparability.

## Compute + efficiency
- Mixed precision (autocast + GradScaler for fp16; bf16 needs none) ~2× speed + less memory.
- Gradient accumulation simulates large batch; gradient checkpointing trades compute for memory.
- Multi-GPU: DDP (data parallel, all-reduce grads) > DataParallel; FSDP/ZeRO shard params/optimizer state for huge models; tensor/pipeline parallel for very large.
- `torch.compile`/fused kernels, FlashAttention reduce memory + speed up attention.

## Transfer / self-supervision
- Pretrain on large unlabeled data (masked/contrastive/next-token) → fine-tune on downstream with small LR. Feature extraction (freeze) vs full fine-tune vs PEFT/LoRA.
- Self-supervised: SimCLR/MoCo (contrastive), MAE (masked autoencoder), BYOL — learn representations without labels.

## Data pipeline + generalization
- Shuffle training data each epoch (not time series). Normalize inputs to zero mean / unit variance or `[0,1]`; use train statistics only.
- Augment to enlarge the effective dataset (crops/flips/noise for vision; back-translation/token dropout for text). More data beats more tuning for reducing variance.
- Split train/val/test with no leakage across correlated groups; keep a frozen test set touched once. Track a fixed val set + seed so runs are comparable.

## Metrics + monitoring in training
- Track the task metric (accuracy/F1/mAP/BLEU) alongside loss — loss can improve while the metric stalls.
- Watch for train/val divergence (overfit), plateaus (LR/capacity), and instability (LR too high, bad init, exploding grads).
- Save the best-val checkpoint, not the last; use EMA of weights for smoother, often-better final models.

## Pitfalls -> Fix
- **Loss NaN/Inf** -> lower LR, clip grads, check for log(0)/div0, use `*WithLogits` loss, bf16 over fp16.
- **Applying softmax then CrossEntropyLoss** (double softmax) -> pass raw logits.
- **Not zeroing grads** -> `optimizer.zero_grad()` every step (grads accumulate).
- **Dropout/BatchNorm active at inference** -> `model.eval()` + `torch.no_grad()`.
- **BatchNorm with batch size 1 / tiny batch** -> use GroupNorm/LayerNorm or larger batch.
- **Learning rate too high** (diverge) / **too low** (no learning) -> LR range test; warmup + cosine.
- **No warmup on Transformers/large batch** -> add linear warmup.
- **Vanishing grads in deep net** -> residuals, ReLU/GELU, normalization, He init.
- **Exploding grads in RNN** -> gradient clipping.
- **Train loss ↓ but val loss ↑** (overfit) -> dropout, weight decay, augmentation, more data, early stop.
- **Train loss flat** (underfit/bug) -> verify data/labels, raise LR/capacity, overfit a tiny batch first as a sanity check.
- **Data not on same device as model** -> `.to(device)` for both.
- **Wrong weight init** (all zeros/large) -> He/Xavier.
- **Forgetting to shuffle training data** -> `shuffle=True` (not for time series).
- **Comparing runs without fixed seed** -> seed torch/numpy/cuda; note nondeterminism from cuDNN.
