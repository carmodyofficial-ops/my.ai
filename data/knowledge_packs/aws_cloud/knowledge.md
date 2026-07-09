# AWS Cloud

## Compute
- **EC2**: VMs. Instance families: `t` (burstable, CPU credits), `m` (general), `c` (compute), `r`/`x` (memory), `g`/`p` (GPU). AMI = image; user-data script runs at boot. Purchasing: On-Demand, Spot (up to ~90% off, can be reclaimed w/ 2-min notice), Reserved/Savings Plans (1-3yr commit). Instance store = ephemeral (lost on stop); EBS = persistent.
- **Lambda**: serverless functions. Triggers: API Gateway, S3, SQS/SNS, EventBridge, DynamoDB Streams. Limits: 15-min max timeout, 10 GB RAM (CPU scales with RAM), 512 MB–10 GB `/tmp`, 6 MB sync payload / 256 KB async, 250 MB unzipped deploy (or container image up to 10 GB). Concurrency default 1000/region (soft). Cold starts; mitigate w/ Provisioned Concurrency. Pay per ms.
- **ECS**: container orchestration. Launch types: **Fargate** (serverless, no nodes to manage) or EC2. Task definition = container spec; Service keeps N tasks running behind a load balancer.
- **EKS**: managed Kubernetes control plane; nodes via managed node groups or Fargate profiles. You pay hourly per cluster.

## Storage
- **S3**: object store. Bucket names globally unique. 11 nines durability. Classes: Standard, Intelligent-Tiering (auto), Standard-IA / One Zone-IA (infrequent), Glacier Instant/Flexible/Deep Archive (retrieval mins–hrs). Lifecycle rules transition/expire objects. Versioning + MFA delete. **Block Public Access on by default.** Encryption: SSE-S3, SSE-KMS, SSE-C. Static hosting, presigned URLs, event notifications. Strong read-after-write consistency.
- **EBS**: block volumes attached to one EC2 (io2/gp3 support multi-attach on Nitro). Types: gp3 (general SSD, baseline 3000 IOPS), io1/io2 (provisioned IOPS), st1/sc1 (HDD throughput/cold). Snapshots -> S3; AZ-scoped (must snapshot to move AZ).
- **EFS**: NFS, multi-AZ, mount from many instances/Lambda. **FSx** for Windows/Lustre/NetApp.

## Networking
- **VPC**: isolated network, pick CIDR (e.g. `10.0.0.0/16`). Subnets are AZ-scoped: **public** (route to Internet Gateway) vs **private** (egress via **NAT Gateway**). Route tables per subnet.
- **Security Groups**: stateful, instance-level, allow-only. **NACLs**: stateless, subnet-level, allow+deny (need explicit return rule).
- **ALB** (L7, HTTP host/path routing, target groups), **NLB** (L4, static IP, ultra-low latency), **GWLB** (appliances). **Route 53**: DNS + health-checked routing (weighted, latency, geo, failover). **CloudFront**: CDN + edge; origin S3/ALB; OAC for private S3. **VPC Endpoints** (Gateway for S3/DynamoDB, Interface/PrivateLink) keep traffic off the internet. **VPC Peering** / **Transit Gateway** for inter-VPC.

## IAM
- **Users** (long-lived, humans/legacy), **Groups**, **Roles** (assumable, temporary STS creds — prefer for services/EC2/Lambda/cross-account), **Policies** (JSON: Effect/Action/Resource/Condition). Identity vs resource policies (S3 bucket policy, KMS key policy).
- **Least privilege**: start deny-all, grant specific actions. Explicit Deny always wins. Use **instance profiles** / Lambda execution roles instead of embedding keys. **AssumeRole** for cross-account. Guardrails: SCPs (Organizations), Permission Boundaries. Enable MFA, rotate keys, use IAM Identity Center (SSO) for humans.

## Databases
- **RDS**: managed relational (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server). Multi-AZ = sync standby failover (HA, not read scaling); Read Replicas = async read scaling. Automated backups + PITR; snapshots.
- **Aurora**: MySQL/Postgres-compatible, storage auto-grows to 128 TB, 6-way replicated across 3 AZs, up to 15 read replicas, fast failover. **Aurora Serverless v2** autoscales ACUs.
- **DynamoDB**: managed NoSQL key-value/doc. Single-digit-ms. Partition key (+optional sort key); design access patterns first. Capacity: on-demand or provisioned (+auto scaling). GSI/LSI for alt queries. Streams -> Lambda. TTL auto-expire. Single-table design common.
- **ElastiCache**: managed Redis / Memcached. **MemoryDB** = durable Redis. **Redshift** = data warehouse; **Athena** = serverless SQL over S3.

## Scaling & edge
- **Auto Scaling Groups (ASG)**: maintain min/desired/max EC2 across AZs; scaling policies (target-tracking on CPU/req-count, step, scheduled); replaces unhealthy instances via ELB/EC2 health checks. **Launch Templates** define the instance config.
- **Application Auto Scaling** covers ECS tasks, DynamoDB, Aurora replicas, Lambda provisioned concurrency.
- **API Gateway**: REST (feature-rich, usage plans/API keys), HTTP API (cheaper, faster, JWT authz), WebSocket. Throttling, stages, custom authorizers (Lambda/Cognito). **AppSync** = managed GraphQL. **Cognito** = user pools (auth) + identity pools (federated AWS creds).

## Secrets, keys, config
- **KMS**: managed encryption keys (AWS-managed, customer-managed CMK, imported). Envelope encryption; key policies + grants; automatic rotation. Most services integrate (S3/EBS/RDS/Secrets Manager).
- **Secrets Manager**: rotatable secrets (auto-rotate RDS creds via Lambda), $/secret/mo. **SSM Parameter Store**: config + SecureString params (free standard tier) — cheaper for non-rotating config. **Systems Manager**: Session Manager (SSH-less shell via IAM, no bastion), Run Command, Patch Manager, inventory.

## Multi-account & governance
- **AWS Organizations**: consolidated billing, OUs, **SCPs** (max-permission guardrails, don't grant). **Control Tower** = landing zone. **IAM Identity Center** for SSO across accounts. Best practice: separate accounts per env (prod/dev/security/logging).

## Messaging & Events
- **SQS**: queue, decouple producers/consumers. Standard (at-least-once, best-effort order) vs FIFO (exactly-once, ordered, 300 TPS/3000 batched). Visibility timeout, DLQ after `maxReceiveCount`, long polling.
- **SNS**: pub/sub fan-out to SQS/Lambda/HTTP/email/SMS. Common: SNS -> multiple SQS.
- **EventBridge**: event bus w/ rules + schemas; SaaS/AWS-service events; cron/rate schedules (replaces CloudWatch Events). **Step Functions**: state-machine orchestration. **Kinesis**: streaming; **MSK**: managed Kafka.

## IaC & Deploy
- **CloudFormation**: declarative YAML/JSON stacks; drift detection, change sets, `!Ref`/`!GetAtt`, nested stacks. **CDK**: define infra in TS/Python -> synthesizes CloudFormation. **SAM** for serverless. Terraform widely used as multi-cloud alt.

## Observability
- **CloudWatch**: Metrics (1-min standard, 1-sec detailed), Logs (log groups/streams, retention default = never expire), Alarms, Dashboards, Logs Insights queries. **X-Ray** distributed tracing. **CloudTrail**: API audit log (management events free, 90-day history). **Config** = resource compliance.

## Cost & Well-Architected
- **Well-Architected** 6 pillars: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability.
- Cost levers: right-size, Savings Plans/RIs for steady load, Spot for fault-tolerant, S3 lifecycle/Intelligent-Tiering, delete idle EBS/EIPs, gp2->gp3. **Cost Explorer** + **Budgets** + tag allocation. Region price varies (us-east-1 cheapest/first for new features).

## CLI quick-reference
```bash
aws sts get-caller-identity                      # who am I / which account
aws s3 cp ./file s3://bucket/key --sse aws:kms   # upload encrypted
aws ec2 describe-instances --filters Name=instance-state-name,Values=running
aws logs tail /aws/lambda/fn --follow            # stream logs
aws ec2 describe-instances --query 'Reservations[].Instances[].InstanceId' --output text
```
- `--profile` selects creds (`~/.aws/credentials` / SSO); `--region` overrides; `--query` uses JMESPath; `--dry-run` on mutating EC2 calls.

## Gotchas -> Fix
- **Public S3 bucket / data leak** -> keep Block Public Access on; use CloudFront + OAC or presigned URLs; never `s3:GetObject` w/ `Principal:*`.
- **`iam:*` / `Resource:*` wildcards** -> scope actions+resources; use Access Analyzer to find unused perms; prefer roles over access keys.
- **Hard-coded access keys in code/EC2** -> use instance profile / task role / Lambda exec role; never commit keys; rotate + use Secrets Manager/SSM Parameter Store.
- **NAT Gateway surprise bill** -> ~$0.045/hr + per-GB data processing per AZ; use VPC Gateway Endpoints for S3/DynamoDB (free), consolidate, or NAT instance for dev.
- **Cross-AZ/region data transfer charges** -> keep chatty traffic in one AZ; inter-AZ and internet egress cost per GB; egress to internet is the pricey direction.
- **Lambda in VPC cold starts / no internet** -> ENI attach adds latency (much improved); private-subnet Lambda needs NAT for internet or VPC endpoints for AWS APIs.
- **Security group can't span VPCs** -> SGs are VPC-scoped; reference SG-to-SG within a VPC; use peering/TGW + CIDR rules across.
- **Deleting a stack orphans/keeps data** -> `DeletionPolicy: Retain` on stateful resources; RDS/S3 may block or snapshot; empty S3 buckets before delete.
- **EBS volume wrong AZ** -> volume must be in same AZ as instance; snapshot then create in target AZ to move.
- **DynamoDB hot partition / throttling** -> high-cardinality partition key; use on-demand or auto scaling; avoid scans (use Query on keys/GSI).
- **RDS Multi-AZ ≠ read scaling** -> standby isn't readable; add Read Replicas for read load.
- **CloudWatch Logs bill from infinite retention** -> set retention on every log group; sample/structure logs.
- **`root` account daily use** -> lock it (MFA, no keys), use IAM Identity Center users; root only for a few account-level tasks.
- **Region confusion** -> IAM/Route53/CloudFront/S3-namespace are global; most services regional; check console region before "resource missing" panic.
- **ALB idle timeout drops long connections** -> default 60s; raise idle timeout for slow backends/streaming; enable keep-alive; NLB for very long-lived.
- **Deleting an IAM role in use breaks services** -> check where a role/policy is referenced (Lambda, EC2 profile) before deleting; use Access Analyzer.
- **KMS key deletion is irreversible + scheduled** -> 7–30 day waiting period; disable instead of delete; losing the key = losing all data encrypted with it.
- **Free-tier expiry surprise** -> 12-month free tier ends; NAT/EIP/idle ALB/EBS still bill; set a Budget alert on day one.
