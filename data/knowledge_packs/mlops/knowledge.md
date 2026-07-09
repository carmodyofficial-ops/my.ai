# MLOps

## ML lifecycle
`problem framing -> data collection/labeling -> feature eng -> train/experiment -> evaluate -> package -> deploy/serve -> monitor -> retrain` (a loop, not a line).
- Treat data, code, config, AND model as versioned artifacts. Reproducibility = same data + code + config + seed -> same model.
- The model is ~5% of a production ML system; data pipelines, serving, and monitoring are the rest. Invest there.
- Automate the path from commit -> tested -> deployed; manual handoffs are where drift and errors enter.

## Experiment tracking
- Log every run: hyperparameters, dataset version, code/git SHA, metrics, artifacts, environment. Tools: **MLflow**, **Weights & Biases**, Neptune, Comet.
- Enables comparison, leaderboard, reproduction, and "why did metric drop" forensics. Tag the run that became a production model.
- Log evaluation on a FIXED validation set so runs are comparable across time.

## Data + model versioning
- **Data versioning**: DVC, LakeFS, Delta Lake, or dataset snapshots/hashes. A model is meaningless without knowing which data trained it.
- **Model versioning**: store weights + metadata (metrics, data version, code SHA, framework version) as immutable versioned artifacts.
- Pin dependency versions (lockfiles, container images) — framework/CUDA version changes silently alter results.
- Reproducibility checklist: seed, data version, code SHA, env/container, config all captured.

## Model registry
- Central store of model versions with **stage/alias** lifecycle: `dev -> staging -> production -> archived`. Tools: MLflow Registry, SageMaker/Vertex registries.
- Registry holds lineage (which run/data produced it), approval status, and the pointer serving uses. Promotion is a gated, auditable action.
- Enables instant **rollback**: repoint the production alias to the previous version.

## Serving
- **Batch/offline**: score a dataset on a schedule; simplest, high throughput, tolerant of latency. Use when predictions aren't needed instantly (e.g. nightly scores).
- **Online/real-time**: low-latency request/response via **REST** (simple, ubiquitous) or **gRPC** (faster, streaming, typed). Add autoscaling, timeouts, health checks.
- **Streaming**: score events off a queue (Kafka) as they arrive.
- Serving runtimes: **Triton Inference Server** (multi-framework, dynamic batching, GPU), **TorchServe**, **BentoML**, ONNX Runtime; for LLMs **vLLM** / **TGI** / **TensorRT-LLM** (paged attention, continuous batching, high throughput).
- Optimize: **dynamic/continuous batching**, quantization, ONNX/TensorRT compilation, caching, GPU sharing. Separate model-serving from business logic behind an API gateway.

## Feature stores
- Central, versioned feature definitions with **offline** (training, historical) and **online** (serving, low-latency) stores kept consistent. Tools: Feast, Tecton.
- Solves **training-serving skew**: the SAME feature logic computes training and serving features. Supports **point-in-time correctness** (no label leakage from future data) and feature reuse across teams.

## CI/CD for ML
- **CI**: on commit — lint, unit tests, data validation (schema/stats), train on a sample, run eval gate. Fail the build if metrics regress below a threshold.
- **CD**: build a container/artifact, register the model, deploy to staging, run integration + shadow tests, gate on eval, then promote to prod.
- **CT (continuous training)**: pipelines (Kubeflow, Airflow, SageMaker/Vertex Pipelines) that retrain, evaluate, and conditionally deploy on new data or triggers.
- Validate DATA in the pipeline (Great Expectations, TFDV): schema, ranges, nulls, cardinality, distribution — bad data is the top failure source.

## Monitoring
- **Operational**: latency (p50/p95/p99), throughput, error rate, resource use, uptime.
- **Data drift**: input feature distribution shifts from training (PSI, KL-divergence, KS test per feature). Model still runs but on unfamiliar inputs.
- **Concept drift**: the input->output relationship changes (world changed); accuracy decays even if inputs look stable.
- **Prediction drift**: output distribution shifts — an early proxy when labels are delayed.
- **Performance**: real accuracy/AUC/etc. once ground-truth labels arrive (often delayed). Track vs training baseline.
- **Training-serving skew**: feature values differ between training and serving pipelines — monitor by logging serving features and comparing to training stats.
- Alert on threshold breaches; dashboard drift + performance; log inputs/outputs for audit and future retraining data.

## Retraining triggers
- Options: **scheduled** (cadence), **performance-based** (metric drops below threshold), **drift-based** (data/concept drift detected), **data-volume** (enough new labels).
- Automate the retrain->evaluate->gate->deploy loop; require the new model to BEAT the current one on a frozen eval before promotion. Never auto-deploy without a gate.

## Deployment strategies
- **Shadow (dark launch)**: new model receives real traffic, predictions logged but NOT served — compare to prod with zero user risk. Best first step.
- **Canary**: route a small % of traffic to the new model, watch metrics, ramp up.
- **A/B test**: split traffic, measure business KPI (not just offline metric) with significance.
- **Blue/green**: full parallel environment, switch over, instant rollback.
- Always keep the previous version deployable for **rollback**. Define rollback criteria before launch.

## Scaling / cost
- Autoscale on load; scale-to-zero for spiky/batch; right-size GPU vs CPU. Batch and quantize to raise throughput/$.
- Cache frequent predictions; use spot/preemptible for training. Track cost per prediction and per training run.
- Set SLOs (latency, availability, freshness) per model and alert on breach; degrade gracefully (fallback model / cached default) when the primary is down.
- Separate GPU inference pools from CPU pre/post-processing; batch requests to raise GPU utilization without blowing tail latency.

## Packaging + reproducible environments
- Package model + preprocessing + dependencies together (container image, or a serialized bundle like MLflow model / BentoML). The serving env must match training for feature parity.
- Pin everything: base image, framework, CUDA/cuDNN, library versions via lockfiles. "Works on my machine" is a production outage waiting to happen.
- Standardize the model interface (predict signature, input/output schema) so serving and clients are decoupled from the framework.
- Store artifacts in object storage with immutable versioned keys; never overwrite a released model.

## Pipelines + orchestration
- Orchestrators run multi-step DAGs (ingest -> validate -> feature -> train -> eval -> register -> deploy): Airflow, Kubeflow, Dagster, Prefect, SageMaker/Vertex Pipelines.
- Make steps idempotent and cacheable; parameterize by data version so a pipeline re-run is reproducible.
- Gate deployment steps on eval results and data-validation passing — no green, no promote.
- Separate the training pipeline (produces a registered model) from the serving deployment (consumes a registered model).

## Drift detection specifics
- Univariate tests per feature: **PSI** (>0.1 warn, >0.25 significant), **KS test** (continuous), **chi-square** (categorical), KL/JS divergence.
- Multivariate/embedding drift: monitor a domain-classifier or distance between reference and live distributions for high-dim/unstructured inputs.
- Set a reference window (training or a stable prod period) and compare rolling live windows; alert on sustained breach, not single spikes.
- Drift is a warning, not proof of harm — confirm with performance metrics once labels arrive before retraining.

## Metadata, lineage, governance
- Capture end-to-end lineage: which data version + code SHA + config produced which model, deployed where, serving which requests.
- For regulated/high-stakes models: model cards, approval sign-off, audit logs of predictions, explainability (SHAP), and bias/fairness checks.
- Log inputs+outputs (privacy-permitting) — this is both your audit trail and your next training set.

## Pitfalls -> Fix
- Training-serving skew (works offline, fails in prod) -> shared feature logic / feature store, log+compare serving vs training features.
- Silent drift, accuracy quietly decays -> monitor data/concept/prediction drift + delayed labels; alert on thresholds.
- No rollback path -> model registry with staged aliases + keep previous version live; define rollback criteria.
- Can't reproduce a model -> version data+code+config+env+seed; log with the run.
- Data leakage / non-point-in-time features -> point-in-time joins, split before feature computation, feature store correctness.
- Bad data reaches training/serving -> data validation gates (schema/stats) in CI and pipeline.
- Deploy blindly, users hit a bad model -> shadow -> canary -> A/B with metric gates before full rollout.
- Metrics look great offline, fail on business KPI -> A/B on the real KPI, not just offline accuracy.
- Latency spikes under load -> dynamic batching, autoscaling, quantization/compilation, load test before launch.
- Model gets stale -> automated retraining triggers (drift/performance/schedule) with eval gate.
- Untracked experiments, "which run is prod?" -> experiment tracking + registry lineage + tag the prod run.
- New model deployed without beating old -> require champion/challenger eval gate before promotion.
