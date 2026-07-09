# Azure Cloud (Microsoft Azure)

## Hierarchy & identity basics
- **Management Groups -> Subscriptions -> Resource Groups -> Resources.** A **resource group (RG)** is a logical container; every resource lives in exactly one RG + one region. Billing/quota boundary = subscription. **Azure Policy** enforces rules; **Blueprints/landing zones** for governance.
- Two identity planes: **Microsoft Entra ID** (formerly Azure AD) = who you are (users/groups/apps/managed identities); **Azure RBAC** = what you can do on Azure resources. Distinct from **Entra roles** (directory admin roles).

## Compute
- **Virtual Machines (VMs)**: series `B` (burstable), `D` (general), `F` (compute), `E`/`M` (memory), `N` (GPU). **Scale Sets (VMSS)** = autoscaling identical VMs. **Availability Zones** (spread across zones) + Availability Sets (fault/update domains). Managed Disks attach to VMs. Spot VMs (cheap, evictable); Reserved Instances / Savings Plans for commit.
- **App Service**: managed PaaS web apps/APIs (code or container). App Service Plan = compute tier (F1/B/S/P). Deployment slots (staging + swap), autoscale, easy auth. **Azure Functions**: serverless; plans: Consumption (scale-to-zero, pay-per-exec), Premium (no cold start, VNet), Dedicated. Triggers/bindings: HTTP, Timer, Queue/Service Bus, Blob, Event Grid/Hub, Cosmos DB.
- **AKS**: managed Kubernetes; free control plane, pay for nodes; node pools, cluster autoscaler, Entra + Azure RBAC integration. **Container Apps**: serverless containers on Kubernetes/Dapr/KEDA (scale to zero, microservices) — the Cloud Run analog. **Container Instances (ACI)** = single quick containers.

## Storage
- **Storage Account** = namespace for Blob/File/Queue/Table (name globally unique -> `*.blob.core.windows.net`). Redundancy: **LRS** (3 copies 1 DC), **ZRS** (across zones), **GRS/GZRS** (cross-region), **RA-GRS** (read replica).
- **Blob Storage**: object store. Tiers: **Hot / Cool / Cold / Archive** (offline, hours to rehydrate). Block/append/page blobs. Lifecycle mgmt, versioning, soft delete, SAS tokens, `$web` static site. **Data Lake Gen2** = hierarchical-namespace blob for analytics.
- **Azure Files**: managed SMB/NFS shares. **Managed Disks**: Standard HDD/SSD, Premium SSD, Ultra Disk; attach to one VM (shared disks option). **Azure NetApp Files** for high-perf.

## Networking
- **VNet**: regional private network + subnets. **NSG** (Network Security Group): stateful allow/deny rules on subnet/NIC (priority-ordered, default rules). **ASG** groups NICs for rule targeting. **NAT Gateway** for outbound. **VNet Peering** (regional/global), **VPN/ExpressRoute** for hybrid.
- **Load Balancer** (L4, regional), **Application Gateway** (L7, WAF, path/host routing, regional), **Front Door** (global L7, CDN, anycast, WAF), **Traffic Manager** (DNS-based global routing). **Azure DNS**. **Private Endpoint / Private Link** = private IP to a PaaS service (keeps traffic off internet). **Service Endpoints** extend VNet identity to PaaS.

## Databases
- **Azure SQL**: managed SQL Server. Flavors: **SQL Database** (single DB / elastic pool, DTU or vCore), **SQL Managed Instance** (near-100% SQL Server compat, VNet). Geo-replication, failover groups, PITR.
- **Cosmos DB**: globally-distributed multi-model NoSQL. APIs: **NoSQL (Core)**, MongoDB, Cassandra, Gremlin, Table. Provisioned or **serverless/autoscale RU/s**. 5 tunable consistency levels (Strong -> Eventual). Partition key choice is critical. Turnkey multi-region writes.
- **Azure Database for PostgreSQL / MySQL** (Flexible Server): managed OSS DBs, zone-redundant HA, burstable/general/memory tiers. **Azure Cache for Redis** (managed Redis, tiers Basic/Standard/Premium/Enterprise). **Synapse Analytics** = data warehouse; **Fabric** newer analytics platform.

## Identity & access
- **Entra ID**: tenants, users, groups, **app registrations** (client id/secret/cert, OAuth2/OIDC), enterprise apps, Conditional Access, MFA, PIM (just-in-time roles).
- **RBAC**: role assignment = principal + role definition + scope (MG/sub/RG/resource); inherits down. Built-in roles (Owner/Contributor/Reader + service-specific); custom roles. **Managed identities** (system-assigned = tied to resource lifecycle; user-assigned = reusable) — the credential-less way for a resource to call Azure/Key Vault. **Key Vault** for secrets/keys/certs.

## Messaging & Events
- **Service Bus**: enterprise queues + topics/subscriptions (pub/sub), sessions, dedup, DLQ, transactions, FIFO. **Storage Queues** = simple/cheap. **Event Grid**: reactive event routing (discrete events, low-latency, pub/sub w/ filters). **Event Hubs**: high-throughput streaming ingestion (Kafka-compatible, partitions, capture).

## Secrets, config, integration, edge
- **Key Vault**: secrets, keys (software/HSM), certificates. Access via RBAC (recommended) or access policies; managed-identity access; CMK for Storage/SQL/Disks; auto-rotation + versioning. Never store keys in app config — reference Key Vault.
- **App Configuration**: centralized settings + feature flags (pairs with Key Vault references).
- **API Management (APIM)**: gateway, policies, products/subscriptions, developer portal. **Logic Apps** (workflow/iPaaS connectors, low-code), **Static Web Apps** (JAMstack + Functions backend).
- **Front Door / CDN** at edge (WAF, TLS, caching, global anycast). **DDoS Protection** standard tier for VNets.

## Governance & scaling
- **VMSS + Autoscale**, **App Service autoscale**, AKS cluster autoscaler + KEDA. **Azure Policy** (audit/deny/deployIfNotExists), **Management Groups** for org-wide RBAC + policy, **Blueprints/landing zones**. Quotas (vCPU) are per-subscription-per-region — request increases early. **Resource locks** (CanNotDelete/ReadOnly) protect critical resources.

## IaC & Observability
- **Bicep** (recommended DSL) compiles to **ARM templates** (JSON, declarative, idempotent). Terraform (`azurerm`) widely used. **Azure CLI** (`az`) / PowerShell (`Az`).
- **Azure Monitor** umbrella: **Metrics**, **Log Analytics** (KQL over logs), **Application Insights** (APM, traces, live metrics), alerts + action groups, **Diagnostic Settings** route resource logs to Log Analytics/Storage/Event Hub.

## Cost
- Levers: right-size + auto-shutdown VMs, Reserved Instances/Savings Plans, Spot, Consumption/Container Apps scale-to-zero, Blob lifecycle tiering, delete orphaned disks/public IPs/NAT. **Cost Management + Budgets**, tags, Advisor recommendations. Region + redundancy tier drive price.

## CLI quick-reference
```bash
az login && az account set --subscription SUB_ID     # pick subscription
az group create -n rg-app -l eastus                  # create resource group
az webapp up --name app --resource-group rg-app      # deploy web app
az vm list -d -o table                               # VMs + power state
az role assignment create --assignee OBJ_ID --role Contributor --scope /subscriptions/SUB
```
- `az account show` = current context; `--resource-group`/`-g` scopes most commands; Bicep deploy: `az deployment group create -g rg --template-file main.bicep`.

## Gotchas -> Fix
- **Entra roles vs Azure RBAC confusion** -> Entra (directory) roles manage users/apps/tenant; Azure RBAC manages resources. Global Admin ≠ access to subscriptions (needs "Access management for Azure resources" elevation).
- **Resource group / subscription sprawl** -> group by lifecycle + region; use consistent naming + tags + Azure Policy; RG delete removes all contained resources (careful).
- **Public blob container / storage exposure** -> disable "allow public blob access" at account level; use Private Endpoint + SAS/RBAC (`Storage Blob Data Contributor`); prefer Entra auth over account keys.
- **Storage account keys / connection strings in code** -> use managed identity + RBAC data-plane roles; store secrets in Key Vault; rotate keys.
- **Deleted resource but still billed** -> orphaned Managed Disks, Public IPs, NAT Gateways, App Service Plans persist after the app is gone; hunt them via Cost Management/Advisor.
- **NSG default deny surprises / wrong priority** -> lower number = higher priority; default rules allow VNet-internal + LB, deny inbound internet; add explicit allows above defaults.
- **Cosmos DB hot partition / RU throttling (429)** -> pick high-cardinality partition key, use autoscale RU/s, implement SDK retry on 429, avoid cross-partition queries.
- **Functions Consumption cold starts / no VNet** -> use Premium plan for warm instances + VNet integration; keep deps small.
- **Region ≠ zone availability** -> not all regions have Availability Zones or every SKU/VM size; check before committing to zonal HA.
- **App Service scale limits per plan** -> autoscale is on the App Service Plan; free/shared tiers can't scale or use custom domains/SSL.
- **Private Endpoint DNS not resolving** -> must configure Private DNS Zone (e.g. `privatelink.blob.core.windows.net`) linked to the VNet or clients still hit the public IP.
- **Service Bus vs Event Grid vs Event Hubs mixup** -> Service Bus = ordered enterprise messaging; Event Grid = discrete reactive events; Event Hubs = high-volume telemetry streaming.
- **Managed identity not authorized** -> creating the identity isn't enough; assign it an RBAC role at the target scope (and Key Vault access policy/RBAC).
- **RBAC role assignment propagation delay** -> can take minutes; assignments inherit from MG/sub/RG down; use narrowest scope; "AuthorizationFailed" often just needs time or a broader scope.
- **Deleting resource group is instant + total** -> removes every resource inside with no undo; add resource locks (CanNotDelete) on prod RGs.
- **Soft-deleted Key Vault blocks name reuse** -> purge protection/soft delete keeps the name reserved; purge or recover the vault.
- **VM auto-shutdown not on by default** -> dev VMs bill 24/7; enable auto-shutdown schedule or deallocate (stopped-but-allocated still bills compute).
- **Storage account name is global + immutable** -> 3–24 lowercase alphanumerics, globally unique; can't rename — plan naming.
