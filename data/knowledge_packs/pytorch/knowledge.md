# PyTorch

## Tensors
- Create: `torch.tensor([...])`, `torch.zeros(2,3)`, `torch.randn(B,C,H,W)`, `torch.arange`, `torch.from_numpy(a)` (shares memory).
- Attributes: `.shape`/`.size()`, `.dtype` (`float32` default, `float16`, `bfloat16`, `int64`, `bool`), `.device` (`cpu`/`cuda:0`).
- Reshape: `.view(...)` (needs contiguous), `.reshape(...)` (safe), `.permute(0,2,1)`, `.transpose(1,2)`, `.unsqueeze(0)`/`.squeeze()`, `.flatten(start_dim=1)`.
- **Broadcasting**: align trailing dims; size-1 dims stretch. `(B,1,D)+(1,N,D)→(B,N,D)`. Mismatched non-1 dims error.
- `.contiguous()` after permute/transpose if a later `.view()` fails. `.expand()` (no copy) vs `.repeat()` (copies).
- Ops: `@`/`torch.matmul`, `torch.einsum('bij,bjk->bik', a, b)`, reductions `.sum(dim=)`, `.mean(dim=, keepdim=True)`.

## Autograd
- `requires_grad=True` tracks ops; leaf tensors (params) accumulate `.grad`.
- `loss.backward()` populates `.grad` for all leaves in graph. Grads **accumulate** — zero them each step.
- `with torch.no_grad():` disables tracking (inference, param updates) — saves memory/compute.
- `.detach()` returns tensor sharing data but cut from graph (stop gradient).
- `.item()` extracts a Python scalar from a 1-element tensor (for logging — detaches, syncs GPU).
- Only float tensors can require grad. `retain_graph=True` for multiple backward passes.

## nn.Module
```python
class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 256)
        self.fc2 = nn.Linear(256, 10)
    def forward(self, x):
        return self.fc2(F.relu(self.fc1(x)))
```
- Submodules/`nn.Parameter` auto-register → appear in `.parameters()`, `.state_dict()`, move with `.to(device)`.
- Use `nn.ModuleList`/`nn.ModuleDict` (NOT a plain Python list) so children register.
- Common layers: `Linear`, `Conv2d(in,out,k,stride,padding)`, `BatchNorm2d`, `LayerNorm`, `Dropout(p)`, `Embedding`, `LSTM`, `MultiheadAttention`.

## Training loop
```python
model.train()
for xb, yb in loader:
    xb, yb = xb.to(device), yb.to(device)
    optimizer.zero_grad()
    out = model(xb)
    loss = criterion(out, yb)      # CrossEntropyLoss: out=logits, yb=int64 class idx
    loss.backward()
    optimizer.step()
```
- Order matters: `zero_grad → forward → loss → backward → step`.
- `criterion = nn.CrossEntropyLoss()` (applies log-softmax internally — pass logits, targets are class indices not one-hot). `BCEWithLogitsLoss` for multi-label.
- `optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)`.
- LR schedule: `scheduler.step()` (per epoch or per batch depending on scheduler).

## Dataset / DataLoader
```python
class DS(Dataset):
    def __len__(self): return len(self.data)
    def __getitem__(self, i): return self.x[i], self.y[i]
loader = DataLoader(ds, batch_size=64, shuffle=True, num_workers=4, pin_memory=True, drop_last=False)
```
- `shuffle=True` train only. `num_workers>0` parallel loading; `pin_memory=True` faster host→GPU copy. Custom `collate_fn` for padding variable-length.

## GPU
- `device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')`; `model.to(device)`; move each batch.
- `.to()` is in-place for modules, returns a copy for tensors (`x = x.to(device)`).
- `x.cpu().numpy()` to bring back (detach first if grad).

## Save / load
```python
torch.save(model.state_dict(), 'm.pt')            # preferred: weights only
model.load_state_dict(torch.load('m.pt', map_location=device)); model.eval()
```
- Save `state_dict`, not the whole pickled model (fragile to code changes). Checkpoint dict for resume: `{'model':..., 'optimizer':..., 'epoch':..., 'scaler':...}`.
- Call `model.eval()` after load for inference.

## Mixed precision
```python
scaler = torch.cuda.amp.GradScaler()
with torch.autocast('cuda', dtype=torch.float16):
    out = model(xb); loss = criterion(out, yb)
scaler.scale(loss).backward()
scaler.step(optimizer); scaler.update(); optimizer.zero_grad()
```
- `bfloat16` autocast needs no GradScaler. Clip grads after `scaler.unscale_(optimizer)`.

## DDP (multi-GPU)
- `DistributedDataParallel` = one process per GPU, gradients all-reduced; scales better than deprecated `DataParallel`. `init_process_group`, `DistributedSampler` (call `sampler.set_epoch(e)`), wrap `model=DDP(model, device_ids=[rank])`. Use `torchrun`.

## Indexing + creation
- Index/slice like NumPy: `x[0]`, `x[:, 1]`, `x[x>0]` (boolean mask), `x[idx]` (fancy), `torch.gather(x, dim, index)`, `torch.index_select`.
- `torch.cat([a,b], dim=0)` (concat existing dim) vs `torch.stack([a,b], dim=0)` (new dim). `torch.chunk`, `torch.split`.
- `torch.where(cond, a, b)`, `torch.clamp(x, min, max)`, `torch.argmax(x, dim)`, `topk`, `softmax(x, dim)`.
- Random: `torch.manual_seed(0)`; `torch.rand`, `randn`, `randint`, `randperm`.

## dtype / device rules
- Ops need matching dtype + device. Cast: `.float()`, `.long()`, `.to(torch.bfloat16)`. Model params default `float32`.
- CrossEntropyLoss targets must be `int64` (long); regression targets `float`. `.long()` for embedding/index inputs.
- Prefer `pin_memory=True` + `non_blocking=True` for async host→GPU transfer.

## Common layers + losses
- `nn.Sequential(...)` for simple stacks; `nn.functional` (`F.relu`, `F.softmax`) for stateless ops.
- Losses: `CrossEntropyLoss` (logits+idx), `BCEWithLogitsLoss` (multi-label/binary logits), `MSELoss`, `L1Loss`, `SmoothL1Loss`/`HuberLoss`, `NLLLoss` (needs log-softmax input).
- Init helpers: `nn.init.kaiming_normal_`, `xavier_uniform_`. Freeze: set `param.requires_grad=False` (and use `no_grad` for that submodule's non-trained forward if needed).

## LR schedulers
- `StepLR(step_size, gamma)`, `CosineAnnealingLR(T_max)`, `OneCycleLR`, `ReduceLROnPlateau(monitor val)`, `LambdaLR` (warmup). Call `scheduler.step()` after `optimizer.step()` (plateau: pass the metric). Log `scheduler.get_last_lr()`.

## Full checkpoint + resume
```python
torch.save({'epoch':e,'model':model.state_dict(),'opt':optimizer.state_dict(),
            'sched':scheduler.state_dict(),'scaler':scaler.state_dict()}, 'ckpt.pt')
ck = torch.load('ckpt.pt', map_location=device)
model.load_state_dict(ck['model']); optimizer.load_state_dict(ck['opt'])
```
- `strict=False` in `load_state_dict` to ignore head mismatch (transfer learning). `map_location` avoids GPU-index errors when loading elsewhere.

## Reproducibility
- `torch.manual_seed`, `torch.cuda.manual_seed_all`, `np.random.seed`, `random.seed`; `torch.backends.cudnn.deterministic=True`, `benchmark=False` (slower); `torch.use_deterministic_algorithms(True)`; seed DataLoader workers via `worker_init_fn`/`generator`.

## Performance
- `torch.compile(model)` (PyTorch 2.x) fuses graph for speed. `set_to_none=True` in `zero_grad` (default in newer). `cudnn.benchmark=True` for fixed input sizes.
- Profile with `torch.profiler`; watch data-loading vs GPU-compute bound (raise `num_workers`, prefetch). Avoid Python-side per-element loops over tensors — vectorize.
- Inference: `model.eval()` + `torch.inference_mode()` (faster than `no_grad`).

## Gradient accumulation
```python
optimizer.zero_grad()
for i, (xb, yb) in enumerate(loader):
    loss = criterion(model(xb.to(device)), yb.to(device)) / accum_steps
    loss.backward()
    if (i + 1) % accum_steps == 0:
        optimizer.step(); optimizer.zero_grad()
```
- Simulates batch `= real_batch · accum_steps` on limited VRAM. Scale loss by `1/accum_steps` so gradient magnitude matches.

## BatchNorm / Dropout modes
- `model.train()` → dropout active, BN uses batch stats + updates running mean/var. `model.eval()` → dropout off, BN uses stored running stats. Forgetting to switch is a top source of bad eval + train/serve skew.
- Freeze BN when fine-tuning small data: set BN modules to `eval()` even during training, or `track_running_stats=False`.

## Custom Dataset + transforms
```python
class ImgDS(Dataset):
    def __init__(self, paths, labels, tfm): ...
    def __len__(self): return len(self.paths)
    def __getitem__(self, i):
        img = tfm(Image.open(self.paths[i]).convert('RGB'))
        return img, self.labels[i]
```
- Keep heavy I/O in `__getitem__` (runs in workers). Return tensors; `collate_fn` for padding/ragged batches. `torchvision.transforms` compose resize/augment/normalize.

## Hooks + inspection
- `module.register_forward_hook(fn)` / `register_full_backward_hook` to grab activations/gradients (feature extraction, debugging, grad-cam).
- `for n,p in model.named_parameters(): print(n, p.shape, p.requires_grad)` to audit. `sum(p.numel() for p in model.parameters())` = param count.
- `torchinfo.summary(model, input_size)` for shapes/params.

## Common error messages
- `RuntimeError: Expected all tensors to be on the same device` → move model + batch to same device.
- `size mismatch, m1 [a×b], m2 [c×d]` → layer in/out dims or flatten wrong; check `x.shape` before `Linear`.
- `element 0 of tensors does not require grad` → input/param has `requires_grad=False` or graph detached.
- `Trying to backward through the graph a second time` → call once, or `retain_graph=True`, or you reused a graph across steps.
- `one of the variables needed for gradient has been modified by an inplace operation` → avoid in-place ops on graph tensors.
- `CUDA out of memory` → reduce batch, mixed precision, `no_grad` in eval, `del` + `empty_cache()`.

## Logging + eval
- Accumulate metrics on GPU, sync once per epoch. Wrap eval in `model.eval()` + `torch.inference_mode()`. Compute accuracy: `(logits.argmax(1) == y).float().mean().item()`.
- Log with TensorBoard/W&B; save best checkpoint by monitored val metric. Move final tensors to CPU/NumPy (`.detach().cpu().numpy()`) for plotting.

## functional vs module + no-grad blocks
- `nn.Module` layers hold learnable state (weights, BN stats); `torch.nn.functional` (`F.relu`, `F.cross_entropy`, `F.pad`) are stateless ops used inside `forward`.
- Wrap param updates and metric computation that don't need grad in `torch.no_grad()`; use `torch.inference_mode()` for pure inference (disables view tracking, faster).
- `detach()` cuts a tensor from the graph (e.g. target networks, logging) while sharing storage; `clone()` copies data; combine `detach().clone()` when you need an independent, grad-free copy.

## Reshaping + batching gotchas
- Flatten before a `Linear`: `x = x.view(x.size(0), -1)` — keep batch dim. `Linear(in_features, ...)` must match the flattened size.
- Add/remove batch dim with `unsqueeze(0)` / `squeeze(0)` for single-sample inference. Broadcasting silently produces wrong shapes if a dim is accidentally 1 — assert shapes in dev.

## Pitfalls -> Fix
- **Grads accumulate across steps** -> `optimizer.zero_grad()` (or `set_to_none=True`) every iteration.
- **Device mismatch** (`Expected all tensors on same device`) -> `.to(device)` for model AND every batch.
- **Applying softmax before CrossEntropyLoss** -> pass raw logits; CE does log-softmax.
- **Targets one-hot for CrossEntropyLoss** -> pass class indices `int64`; one-hot only for `BCEWithLogitsLoss`/soft labels.
- **Forgot model.eval()/no_grad at inference** -> dropout/BN wrong + wasted memory; set both.
- **In-place op on a tensor needed for backward** (`a += b`, `relu_`) -> use out-of-place; error `modified by an inplace operation`.
- **`.view()` after permute/transpose fails** -> `.contiguous().view()` or `.reshape()`.
- **Calling `.item()`/`.cpu()` inside hot loop** -> forces GPU sync, slow; accumulate on GPU, sync once.
- **Storing `loss` (not `loss.item()`) in a list** -> retains whole graph → memory leak/OOM; store `.item()` or `.detach()`.
- **`nn.Linear`/loss on wrong dtype** (e.g. long) -> cast inputs to float.
- **Modules in a plain list** not trained -> use `nn.ModuleList`.
- **Loading whole model object** breaks on refactor -> save/load `state_dict`.
- **OOM** -> smaller batch, mixed precision, gradient accumulation, `del` + `torch.cuda.empty_cache()`, `torch.no_grad()` for eval, gradient checkpointing.
- **Nondeterministic results** -> seed `torch.manual_seed`, `torch.cuda.manual_seed_all`, `torch.backends.cudnn.deterministic=True` (slower).
- **DataLoader workers slow / hang** -> tune `num_workers`, `persistent_workers=True`; on Windows guard in `if __name__=='__main__'`.
