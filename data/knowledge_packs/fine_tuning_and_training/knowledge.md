# Fine-Tuning and Training

## When to fine-tune vs RAG vs prompt
- **Prompt/few-shot first**: fastest, no training, no infra. Solves most tasks. Try before anything else.
- **RAG**: when the model needs *knowledge/facts* it lacks (private docs, fresh data). Fine-tuning does NOT reliably teach new facts and can't stay current — RAG does.
- **Fine-tune**: when you need *behavior/format/style/tone*, consistent structured output, a narrow task done reliably, latency/cost reduction (smaller model matching a bigger one via distillation), or to bake in a skill prompting can't hold.
- Combine: fine-tune for behavior + RAG for knowledge is common and strong.
- Fine-tuning trades flexibility and effort for consistency; needs a good dataset, eval, and retraining discipline. Don't fine-tune to fix a prompt you haven't optimized.

## Dataset preparation
- Quality >> quantity. A few hundred to a few thousand clean, on-distribution examples often beat tens of thousands of noisy ones.
- Format matches the objective: SFT = `{prompt/messages, completion}` chat pairs in the model's chat template; preference = `{prompt, chosen, rejected}`.
- Match the exact chat template / special tokens the base model expects — mismatched templates silently wreck results.
- Curate: dedup (exact + near-dup via embeddings/minhash to avoid memorization and eval leakage), filter low-quality/toxic, balance classes/intents, ensure diversity and coverage of edge cases.
- Splits: train / validation / test, split BEFORE dedup-across-sets. Never let train and test share/near-share examples (leakage inflates metrics).
- Include the desired output format and refusals/negative examples so the model learns boundaries, not just happy paths.
- Label consistency: inconsistent labels cap achievable quality; audit a sample.

## SFT (supervised fine-tuning)
- Teach input->output mapping on curated pairs; loss usually only on the completion tokens (mask the prompt).
- Standard first step for instruction/behavior tuning. Watch train vs val loss — val loss rising = overfitting.

## Parameter-efficient (PEFT)
- **LoRA**: freeze base weights, train small low-rank adapter matrices (A,B) injected into attention/MLP layers. ~<1% of params trained; small checkpoints; swappable adapters; near full-FT quality for many tasks.
  - Key knobs: `r` (rank, 8-64; higher = more capacity), `lora_alpha` (scaling, often 2×r), `target_modules` (q,k,v,o + MLP proj), `dropout`.
- **QLoRA**: base model quantized to 4-bit (NF4) + LoRA adapters trained on top. Fits large models on a single GPU with minimal quality loss — default for consumer/single-GPU fine-tuning.
- **Adapters/prefix/prompt tuning**: other PEFT variants; LoRA/QLoRA dominate in practice.
- **Full fine-tune**: updates all weights — max capacity, needs most memory (optimizer states ~2-4× params), best for large domain shifts or when you own serving. Higher forgetting risk.
- Rule of thumb: PEFT/LoRA for most tasks; full FT for big distribution shifts or foundation-scale work with the compute for it.

## Hyperparameters
- **Learning rate**: the highest-leverage knob. LoRA: ~1e-4 to 3e-4. Full FT: ~1e-5 to 5e-5 (much lower). Too high -> divergence/forgetting; too low -> underfit.
- **Epochs**: 1-3 typical. LLMs overfit fast on small sets; more epochs memorize. Watch val loss, early-stop.
- **Batch size**: as large as memory allows; use **gradient accumulation** to simulate large effective batch. Larger batch = more stable, needs slightly higher LR.
- **Warmup**: 3-10% of steps ramp LR from 0 to avoid early instability; then cosine or linear decay.
- **Weight decay**, `max_seq_len` (cap to your data; longer = more memory), gradient clipping (~1.0), mixed precision (bf16).
- Tune LR first, then epochs/early-stop, then rank/batch. Log everything.

## Preference tuning (alignment)
- **RLHF**: SFT -> train a reward model on human preference pairs -> optimize policy with PPO against the reward model. Powerful, complex, unstable, expensive.
- **DPO** (Direct Preference Optimization): skips the reward model/RL; optimizes directly on `{chosen, rejected}` pairs with a simple classification-style loss against a frozen reference model. Much simpler/stabler — the practical default for preference tuning. (Variants: IPO, KTO, ORPO.)
- Order: pretrain -> SFT -> preference tuning. Preference tuning refines *how* it answers (helpfulness, safety, style), not raw knowledge.

## Evaluation + overfitting
- Hold-out test set the model never saw; report task metrics, not just loss. Add an LLM-judge / rubric for open-ended quality.
- Overfitting signs: val loss rises while train falls; model parrots training phrasing; brittle on paraphrases. Fix: fewer epochs/early stop, more/diverse data, lower LR, more regularization, lower LoRA rank.
- **Eval leakage**: test examples (or near-dups) in training inflate scores — dedup across splits, keep test frozen and separate.
- Check for **catastrophic forgetting**: eval on general/held-out capabilities, not just the new task.

## Distributed training
- **Data parallel (DDP)**: replicate model per GPU, split the batch, all-reduce gradients. Scales when the model fits on one GPU.
- **FSDP / ZeRO**: shard params, gradients, and optimizer states across GPUs — fits models too big for one GPU (memory ~ /N). ZeRO stages 1/2/3 shard progressively more; **DeepSpeed** and PyTorch **FSDP** implement this.
- **Tensor/pipeline/model parallel**: split a single layer's compute (tensor) or layers across devices (pipeline) for very large models; add communication overhead.
- **Gradient checkpointing** trades compute for memory (recompute activations). Combine with mixed precision (bf16) and gradient accumulation.

## Quantization
- **Inference**: 8-bit / 4-bit (GPTQ, AWQ, NF4, GGUF) shrink memory ~2-4× with small quality loss — deploy big models cheaply.
- **Training**: QLoRA (4-bit base + adapters) is the main quantized-training path. Full training runs in bf16/fp16, not int4.
- More aggressive quantization = more quality loss; measure on your eval, don't assume.

## Data volume + scaling guidance
- Style/format tuning: often 100s-1,000s of examples suffice. Complex new skills/domains: 1,000s-10,000s. Diminishing returns past coverage of the task distribution.
- Distillation: generate a large clean dataset from a stronger model, SFT a smaller model to match it at lower serving cost (respect the source model's terms).
- Curriculum: order easy->hard, or upsample rare classes, when the distribution is skewed.
- Synthetic data helps coverage but audit for quality and mode collapse; don't train on your own model's uncorrected outputs at scale.

## Training workflow + monitoring
- Baseline first: measure the base model + best prompt on your eval before tuning, so you can prove FT helped.
- Log train loss, val loss, LR, grad norm, throughput; watch for divergence (loss spikes/NaN -> lower LR, check data), plateau, or overfitting (val turns up).
- Checkpoint regularly; keep the best-val checkpoint, not the last. Save adapter + config + tokenizer + base-model reference for LoRA.
- Small-scale sanity run first (few steps, tiny subset) to catch template/format/OOM bugs before a long expensive run.
- Reproducibility: fix seeds, pin library/CUDA versions, record the exact data snapshot and config.

## Serving fine-tuned models
- LoRA adapters: serve merged (fold adapter into base weights -> single model) for simplicity, or keep adapters separate to hot-swap many task adapters over one base (multi-LoRA serving) for memory efficiency.
- Quantize for inference (GPTQ/AWQ/GGUF) after tuning to cut serving cost; re-measure quality on your eval post-quantization.
- Version the model + the eval it passed; keep the ability to roll back to the base/previous adapter.

## Pitfalls -> Fix
- Fine-tuning to add knowledge -> use RAG; FT teaches behavior, not current facts.
- Catastrophic forgetting of general skills -> lower LR, fewer epochs, PEFT over full FT, mix in general data, eval broad capabilities.
- Overfitting on small data -> 1-3 epochs, early stop on val, more diverse data, lower rank.
- Eval leakage inflates metrics -> dedup across train/val/test, freeze a clean test set.
- Wrong/mismatched chat template or special tokens -> use the base model's exact template; verify a rendered sample.
- LR too high -> divergence/forgetting; too low -> no learning. Tune LR first; LoRA≈1e-4, full≈1e-5.
- OOM during training -> QLoRA/4-bit, gradient checkpointing + accumulation, FSDP/ZeRO, shorter max_seq_len, smaller batch.
- Loss on prompt tokens -> mask prompt, compute loss on completion only.
- Noisy/inconsistent labels cap quality -> audit and clean data before tuning; quality > quantity.
- Prompt not optimized first -> optimize prompt/few-shot before spending on fine-tuning.
- Unstable RLHF -> use DPO/ORPO instead of PPO for most cases.
- Skipping validation -> always hold out; watch train vs val gap; test on paraphrases and general tasks.
