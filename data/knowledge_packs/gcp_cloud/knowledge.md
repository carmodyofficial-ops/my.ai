# GCP Cloud (Google Cloud Platform)

## Resource hierarchy & identity basics
- **Organization -> Folders -> Projects -> Resources.** Everything lives in a **project** (billing + APIs + quota boundary). IAM policies inherit down; deny-by-default, most-permissive union wins (no explicit deny except Deny Policies).
- Enable a service's API before use (`gcloud services enable run.googleapis.com`).

## Compute
- **Compute Engine (GCE)**: VMs. Machine families: `e2` (cost), `n2`/`n2d` (general), `c2`/`c3` (compute), `m` (memory), `a2`/`g2` (GPU/TPU-adjacent). **Custom machine types** (pick vCPU+RAM). Preemptible/**Spot VMs** (cheap, reclaimable). **Sustained-use discounts** auto-apply; **Committed-use discounts** (1/3yr). **Managed Instance Groups (MIG)** = autoscaling + auto-healing + rolling updates. Zonal resource.
- **Cloud Run**: serverless containers (any language, listens on `$PORT`). Scales to zero, request or CPU-always billing, concurrency per instance (default 80), 60-min max request. Fully managed; deploy from image or source. Best default for stateless HTTP/gRPC/jobs.
- **Cloud Functions**: event/HTTP functions (2nd gen runs on Cloud Run/Eventarc). Triggers: HTTP, Pub/Sub, Cloud Storage, Firestore, Eventarc.
- **GKE**: managed Kubernetes. **Autopilot** (per-pod billing, Google manages nodes) vs **Standard** (manage node pools). Regional clusters for HA control plane.

## Storage
- **Cloud Storage (GCS)**: object store, globally-unique bucket names. Classes: Standard, Nearline (30d), Coldline (90d), Archive (365d) — same API/ms latency, differ on storage vs retrieval price + min duration. Location: region / dual-region / multi-region. Uniform bucket-level access (recommended) vs fine-grained ACLs. Object lifecycle, versioning, signed URLs, CMEK.
- **Persistent Disk (PD)**: block storage for GCE (pd-standard/balanced/ssd, zonal or regional-replicated). **Hyperdisk** (newer, tunable IOPS/throughput). **Local SSD** = ephemeral. **Filestore** = managed NFS.

## Networking
- **VPC** is **global**; **subnets are regional** (a subnet spans zones in its region). Auto vs custom mode. Firewall rules are VPC-global, target by tag/service-account, stateful. **Private Google Access** for private-IP VMs to reach Google APIs. **Cloud NAT** for egress from private VMs. **Shared VPC** (host project shares subnets) and **VPC Peering**.
- **Cloud Load Balancing**: global external Application LB (L7, anycast IP, one IP worldwide), regional LBs, internal LB, Network LB (L4). **Cloud CDN** rides on the external ALB. **Cloud Armor** = WAF/DDoS. **Cloud DNS** managed DNS.

## IAM
- **Members**: Google accounts, groups, **service accounts (SA)**, domains, allUsers/allAuthenticatedUsers. **Roles**: basic (Owner/Editor/Viewer — avoid), **predefined** (per-service, granular), **custom**. Bind role+member on a resource/project.
- **Service accounts** are the identity for workloads. **Workload Identity Federation** (federate external/AWS/OIDC ids — no keys) and **Workload Identity** on GKE (map K8s SA -> GCP SA). **Prefer attaching a SA to the resource over downloading JSON keys.** Impersonation (`--impersonate-service-account`) for short-lived creds.

## Databases & Data
- **Cloud SQL**: managed MySQL/PostgreSQL/SQL Server. HA = regional (sync standby failover); read replicas for scaling. Connect via Cloud SQL Auth Proxy / connectors (IAM auth).
- **Spanner**: horizontally-scalable, strongly-consistent relational SQL, global, 99.999% multi-region. Pricey; for large scale + global consistency.
- **Firestore**: serverless document DB (Native or Datastore mode), realtime listeners, offline; strong consistency.
- **Bigtable**: wide-column NoSQL, low-latency, huge throughput (time-series, IoT). **Memorystore**: managed Redis/Memcached.
- **BigQuery**: serverless columnar data warehouse. Separates storage + compute. Pricing: **on-demand per bytes scanned** (~$5/TB) or capacity **slots** (editions). Partition + cluster tables; `SELECT` only needed columns (never `SELECT *`). Streaming inserts, BQ ML, federated queries.
- **Dataflow** (managed Apache Beam, batch+stream), **Pub/Sub** (global async messaging, at-least-once, ordering keys, push/pull, dead-letter), **Dataproc** (managed Spark/Hadoop).

## Secrets, config, scheduling, edge
- **Secret Manager**: versioned secrets, IAM-controlled, auto-replication or user-managed regions; rotation via Pub/Sub notifications. Prefer over env vars/keys.
- **Cloud KMS**: managed keys (symmetric/asymmetric), CMEK for GCS/BQ/PD/Cloud SQL, HSM/external key options, auto-rotation.
- **Cloud Scheduler** (managed cron -> HTTP/Pub/Sub), **Cloud Tasks** (deferred/rate-limited task queues), **Eventarc** (unified event routing from Google/Cloud Audit Logs/Pub/Sub to Cloud Run/Functions).
- **API Gateway** / **Apigee** (full API management). **Identity-Aware Proxy (IAP)** = zero-trust auth in front of apps/SSH without a VPN. **reCAPTCHA/Cloud Armor** for edge protection.

## Governance & quotas
- **VPC Service Controls**: perimeter around services (BQ/GCS) to stop data exfiltration. **Organization Policy Service**: constraints (e.g. disable SA key creation, restrict public IPs). **Resource Manager** labels for cost/attribution. Quotas are per-project + per-region — request increases before scaling.

## IaC & Deploy
- **Terraform** (Google-recommended, `google` provider) is the de facto IaC. **Deployment Manager** (legacy, YAML/Jinja) being deprecated in favor of **Infrastructure Manager** (managed Terraform). **Cloud Build** CI/CD; **Artifact Registry** for images/packages (replaces Container Registry).

## Observability
- **Cloud Logging** (log buckets, sinks -> BigQuery/GCS/Pub/Sub, Logs Explorer, log-based metrics; `_Default`/`_Required` buckets), **Cloud Monitoring** (metrics, dashboards, alerting policies, uptime checks), **Cloud Trace**, **Cloud Profiler**, **Error Reporting**. **Cloud Audit Logs**: Admin Activity (always on), Data Access (opt-in, can be large/costly).

## Build & registry
- **Cloud Build**: managed CI/CD, `cloudbuild.yaml` steps run in containers; triggers on repo push. **Artifact Registry**: Docker + Maven/npm/Python repos (replaces Container Registry/`gcr.io`); regional, IAM-scoped. **Binary Authorization** enforces signed/attested images to GKE/Cloud Run.
- Cloud Run/GKE deploy pattern: build image (`gcloud builds submit` or buildpacks) -> push to Artifact Registry -> deploy referencing the immutable digest.

## Cost
- Levers: Spot VMs, committed-use + sustained-use discounts, Cloud Run scale-to-zero, GCS lifecycle + right class, BigQuery partitioning + slot reservations, Autopilot GKE. **Budgets + alerts**, billing export to BigQuery, per-label cost breakdown. `gcloud` region/zone affects price.

## CLI quick-reference
```bash
gcloud config set project MY_PROJECT             # set active project
gcloud auth application-default login            # ADC for local dev
gcloud run deploy svc --source . --region us-central1 --allow-unauthenticated
gcloud compute instances list                    # list VMs across zones
bq query --use_legacy_sql=false 'SELECT ...'     # run BigQuery SQL
gsutil ls gs://bucket   # (gcloud storage ls also)  object listing
```
- **ADC** (Application Default Credentials) resolves creds automatically: env var `GOOGLE_APPLICATION_CREDENTIALS`, `gcloud auth application-default login`, or attached SA. `--impersonate-service-account` for short-lived creds without keys.

## Gotchas -> Fix
- **Basic roles (Owner/Editor) over-grant** -> use predefined/custom roles; Editor can modify almost everything. Audit with Policy Analyzer / Recommender.
- **Service-account JSON key sprawl** -> keys are long-lived secrets that leak; use attached SAs, Workload Identity (GKE), or Workload Identity Federation; disable key creation via org policy.
- **BigQuery `SELECT *` scans whole table = surprise bill** -> select needed columns, partition/cluster, use `--dry-run` / preview bytes, set max-bytes-billed, use BI Engine/materialized views.
- **VPC is global but subnet is regional** -> a workload can only use a subnet in its region; plan CIDR per region; firewall rules are global though.
- **allUsers on a bucket = public data** -> use uniform bucket-level access, remove `allUsers`/`allAuthenticatedUsers`, enable Public Access Prevention org policy.
- **Forgot to enable the API** -> `gcloud services enable ...`; "API not enabled" errors are common on new projects.
- **Cloud Run/Functions cold start + scale-to-zero latency** -> set min-instances; keep container small; CPU-always for background work.
- **Cloud SQL public IP exposure** -> use private IP + Auth Proxy/connectors + IAM auth; don't `0.0.0.0/0` authorized networks.
- **Data Access audit logs blow up logging cost** -> enable selectively; route via sinks; set log bucket retention.
- **Wrong billing account / project quota** -> resources need an active linked billing account; quotas are per-project-per-region (request increases early).
- **Firestore Native vs Datastore mode is permanent** -> chosen once per project; pick Native for new apps.
- **Preemptible/Spot VM reclaimed mid-job** -> only for fault-tolerant/batch; use MIG auto-healing + checkpointing.
- **Default network + wide firewall rules** -> auto-mode VPC opens broad rules (e.g. SSH from anywhere); tighten to source ranges/tags, use IAP for SSH.
- **IAM changes take time / wrong scope** -> bindings are set at project/folder/org/resource level and inherit down; propagation can lag; grant at the narrowest scope.
- **Cloud Run allowUnauthenticated makes it public** -> omit the flag and require IAM invoker role, or front with IAP/API Gateway; check `--ingress` (all vs internal).
- **BigQuery streaming inserts cost + can't be deleted immediately** -> streamed rows have a buffer; prefer batch load (free) for bulk; watch streaming insert pricing.
- **Deleting a project is reversible ~30 days then permanent** -> deletion schedules; shut down unused projects to stop billing; org policy can restrict.
- **KMS/CMEK region must match resource** -> the key ring region must align with the encrypted resource's location.
