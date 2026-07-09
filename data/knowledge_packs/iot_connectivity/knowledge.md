# IoT Connectivity

## Architecture
- Tiers: **device (sensor/actuator) -> gateway/edge -> cloud/broker -> app/dashboard**. Edge aggregates, filters, and buffers; cloud stores, analyzes, and controls; app visualizes and commands.
- Constrained devices (battery, KB RAM, intermittent link) push lightweight protocols and store-and-forward. Assume the network is unreliable and eventually-connected, not always-on.
- Ingest pipeline: device -> broker/ingest -> stream (Kafka/Kinesis) -> time-series DB / lake -> rules/ML -> alerts + control loop back to device.

## MQTT (dominant IoT protocol)
- Lightweight **pub/sub** over TCP (default port 1883, TLS 8883). Broker (Mosquitto, EMQX, HiveMQ, AWS IoT Core) decouples publishers from subscribers.
- **Topics** are hierarchical strings: `home/kitchen/temp`. Wildcards on subscribe only: `+` (single level), `#` (multi-level, must be last). Publishers use exact topics.
- **QoS**: `0` at-most-once (fire-and-forget, may lose); `1` at-least-once (acked, may duplicate — handle idempotently); `2` exactly-once (4-way handshake, slowest). Pick per message; most telemetry is QoS 0/1.
- **Retained message**: broker keeps the last message on a topic and delivers it instantly to new subscribers (`retain=true`) — good for "current state".
- **Last Will & Testament (LWT)**: broker publishes a predefined message if the client drops uncleanly — the standard "device offline" detector.
- **Keep-alive** + PINGREQ detects dead connections. **Clean session / persistent session** controls whether the broker queues QoS1/2 messages for an offline subscriber.
- Best practice: structured topic hierarchy, per-device credentials, ACLs restricting each device to its own subtree.

## Other protocols
- **CoAP**: REST-like (GET/POST/PUT/DELETE) over **UDP** (port 5683, DTLS 5684); tiny, for very constrained nodes; observe option = subscribe. No broker; request/response.
- **HTTP(S)/REST**: simple, universal, but heavy headers, request/response only, no server push — poor for battery/real-time. Fine for provisioning and firmware download.
- **WebSocket**: full-duplex over 80/443 — MQTT-over-WS punches through web proxies/firewalls to browsers.
- **AMQP**: heavier, enterprise messaging with routing/queues.

## Wireless technologies (range / power / rate tradeoffs)
- **WiFi (2.4/5GHz)**: high bandwidth, ~30-100m, **high power** (mains/large battery), needs AP + IP. Good for cameras/hubs, poor for coin-cell sensors.
- **BLE**: ~10-50m, **very low power**, ~1-2 Mbps, phone-friendly. **GATT** model: server (device) exposes Services -> Characteristics (read/write/notify/indicate) identified by UUIDs; central (phone/hub) reads/subscribes. Great for wearables, beacons, provisioning.
- **Zigbee / Thread** (802.15.4, 2.4GHz): low power **mesh**, ~10-100m per hop, self-healing, hundreds of nodes. Home automation (Matter runs over Thread/WiFi).
- **LoRaWAN**: **long range** (2-15km), **ultra-low power**, tiny payloads (<256B), very low data rate, unlicensed sub-GHz. Star-of-stars via gateways to a network server. Metering, agriculture, asset tracking. Duty-cycle limited.
- **Cellular NB-IoT / LTE-M**: km-scale, licensed, no gateway needed, carrier SIM/cost. NB-IoT = low rate, deep indoor, static; LTE-M = higher rate, mobility, voice. 5G RedCap emerging.
- Rule of thumb: more range + lower power => lower data rate. Match to payload size, latency need, battery, and site.

## Edge vs cloud
- **Edge/fog** compute: filter, aggregate, run inference near the device -> less bandwidth, lower latency, offline resilience, privacy. Send only summaries/anomalies upstream.
- **Cloud**: durable storage, fleet-wide analytics, ML training, dashboards, OTA orchestration.
- Control loops needing tight latency (safety, motor control) stay at the edge; anything tolerant goes cloud.

## Provisioning, fleet, OTA
- **Provisioning**: get a new device onboarded with unique identity + credentials + config. Methods: pre-provisioned certs at manufacture, BLE/SoftAP onboarding app, claim-and-register, QR/zero-touch. Never ship identical default creds.
- **Device identity**: per-device X.509 cert or key stored in secure element/TPM; broker maps cert -> device -> permissions.
- **Fleet management**: registry, grouping, config/shadow (desired vs reported state), health monitoring, remote command, decommissioning/cert revocation.
- **OTA firmware update**: signed image, A/B (dual) partitions, download-verify-flash-reboot, automatic rollback on boot failure, staged/canary rollout. A fleet with no OTA path is unpatchable = a liability.

## Security
- **TLS/DTLS** everywhere (mutual TLS for device auth). Never plaintext MQTT/HTTP in production.
- **Device identity**: unique per-device keys/certs; secure element for key storage. **Secure boot** + signed firmware chain of trust so only authentic code runs. Encrypt flash where supported.
- **Least privilege**: per-device ACLs (its own topics only), short-lived tokens, revocation.
- Attack surface: default passwords, open ports/UPnP, unencrypted OTA, no rollback, exposed debug (UART/JTAG) — all classic botnet (Mirai) vectors.

## Data & power
- **Formats**: JSON (readable, verbose), **CBOR/MessagePack** (binary, compact — save bandwidth/battery), Protobuf (schema, efficient). Batch small readings; delta/compress.
- **Power budget**: dominated by **radio TX** and wake time, not compute. Duty-cycle: sleep deep, wake briefly, send batched, sleep again. Fewer/larger transmissions beat many tiny ones. Model coin-cell life from avg current = sleep + wake/TX bursts.
- Payload discipline: include device id + timestamp + schema/version; keep telemetry small and self-describing; version your message format so old firmware stays parseable.

## Device shadow / digital twin
- **Shadow** = a cloud-side JSON doc mirroring device state with `desired` (app wants) and `reported` (device confirms) sections; delta drives the device to converge. Lets apps command offline devices — the change applies on reconnect.
- Command patterns: request/response over a dedicated MQTT topic pair (`.../cmd`, `.../resp`) with a correlation id; ack every command; make commands idempotent.

## Time-series & telemetry pipeline
- Sensor streams land in a **time-series database** (InfluxDB, TimescaleDB, Timestream): timestamp + tags (device, location) + fields (metrics). Downsample/retention policies keep storage bounded.
- Rules engine / stream processor evaluates thresholds and triggers alerts or control actions; ML/anomaly detection runs on the aggregated stream, not raw device data.

## Standards & interop
- **Matter** (over Thread/WiFi) unifies smart-home device interop across ecosystems. **Home Assistant / MQTT discovery** auto-registers devices. **OPC-UA / Modbus** dominate industrial IoT.
- Prefer open, documented schemas and standard transports over proprietary clouds to avoid lock-in and ease fleet integration.

## Gotchas -> Fix
- **Unsecured devices** (default creds, plaintext, open ports). Fix: per-device certs, mTLS, close ports, disable debug, secure boot.
- **MQTT topic sprawl / no naming convention**. Fix: designed hierarchy `tenant/site/device/metric`, ACLs per subtree, document it.
- **No OTA mechanism**. Fix: signed A/B OTA with rollback before first field deployment — retrofitting is painful.
- **Assuming always-connected**. Fix: local buffering/store-and-forward, idempotent handlers, reconnect with backoff + jitter, LWT for presence.
- **Power drain surprises**: chatty polling, keeping radio on, HTTP overhead. Fix: MQTT/CoAP + deep sleep + batching; measure real average current.
- **QoS/dup mishandling**: QoS1 duplicates cause double-actuation. Fix: idempotent commands, message IDs/dedup.
- **Retained-message staleness**: old retained value read as current after device died. Fix: LWT + retained "offline"; timestamp payloads.
- **Wrong radio for the job**: WiFi sensor on coin cell (dies in days) or LoRa for a video feed. Fix: pick by range/power/rate; prototype the power budget early.
- **No time sync**: readings can't be correlated. Fix: NTP/SNTP or gateway-stamped timestamps; include monotonic + wall-clock.
- **Cert expiry / no revocation plan**: fleet locked out or compromised device can't be cut off. Fix: rotation strategy, revocation lists, monitor expiry.
- **Firewall/NAT blocks broker**. Fix: device-initiated outbound TLS to broker (443/MQTT-over-WSS); never require inbound to the device.
