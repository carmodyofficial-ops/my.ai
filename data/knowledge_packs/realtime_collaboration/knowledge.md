# Realtime Collaboration

## CRDTs
- **Conflict-free Replicated Data Type**: concurrent edits merge deterministically to the same state without a central coordinator; merge is commutative, associative, idempotent → eventual consistency, no rollback.
- **State-based (CvRDT)**: replicas exchange full state, merge via a join (least-upper-bound on a semilattice). Simple, robust to lost/duplicate/reordered messages, but bandwidth-heavy (deltas mitigate: δ-CRDTs ship only changes).
- **Op-based (CmRDT)**: broadcast operations; requires reliable, exactly-once, causally-ordered delivery (else divergence). Lower bandwidth, more delivery burden.
- **Yjs**: highly optimized op/delta CRDT; shared types `Y.Text`, `Y.Array`, `Y.Map`, `Y.XmlFragment`. Uses a struct store + garbage-collected tombstones; document is a sequence of items with client-id + clock IDs. Encodes updates as compact binary; `Y.applyUpdate`/`Y.encodeStateAsUpdate`, state vectors for diff sync (`encodeStateVector` → request only missing). Pluggable providers: `y-websocket`, `y-webrtc`, `y-indexeddb` (offline persistence).
- **Automerge**: JSON-document CRDT with full history; columnar binary format; heavier metadata than Yjs but richer time-travel/change introspection. Better when you need auditable history; Yjs better for raw text-editing performance/memory.
- **Awareness/presence** (Yjs `awareness` protocol): ephemeral, non-persisted per-client state (cursor, selection, name, color) with heartbeat timeout → auto-remove stale peers. Kept out of the CRDT doc (don't pollute mergeable state with transient UI).

## OT vs CRDT
- **Operational Transformation**: transform incoming op against concurrent ops so intention is preserved (insert/delete index adjustment). Needs a central server to order/transform (Google Docs model); transformation functions must satisfy TP1/TP2 convergence properties — TP2 is notoriously hard, source of historical bugs.
- **Tradeoffs**: OT = compact ops, mature for text, but complex transforms + usually server-authoritative. CRDT = simpler merge reasoning, works P2P/offline, but larger metadata/memory (tombstones) and interleaving anomalies possible on concurrent same-position inserts.
- **Intention preservation**: both aim to keep each user's *intended* effect; CRDT sequence types use unique dense position IDs (fractional index / RGA-style) so concurrent inserts interleave deterministically rather than clobber.

## Ordering primitives
- **Lamport clock**: single counter, `L = max(local, received)+1`; gives total-ish order but can't detect concurrency.
- **Vector clock**: per-replica counter vector; compare component-wise → establishes happens-before vs concurrent (needed to know when to merge vs order). O(n) replicas storage. Yjs uses a compact (client→clock) state vector for the same purpose.

## WebRTC
- **Data channels**: `RTCDataChannel` over SCTP/DTLS; configurable reliability: `{ordered:false, maxRetransmits:0}` = UDP-like unreliable/unordered (good for cursors/game state), default = reliable/ordered (like TCP). Backpressure via `bufferedAmount` + `bufferedAmountLowThreshold`.
- **Signaling**: out-of-band (your WS server) exchanges SDP offer/answer + ICE candidates. WebRTC does not define signaling — you build it.
- **STUN**: discovers public IP/port (NAT reflexive candidate) for direct P2P. **TURN**: relays media when NAT/firewall blocks direct (symmetric NAT); costs bandwidth, always provision TURN for production (~10-20% of users need it).
- **Mesh** (every peer↔every peer): O(n²) connections + uplink; fine ≤4-6 peers. **SFU** (Selective Forwarding Unit): each peer sends one uplink to server which forwards; scales to dozens. **MCU** mixes server-side (heavy CPU). For collaboration data (not media), a WS/pub-sub hub usually beats WebRTC mesh past a few peers.

## WebTransport / QUIC
- **WebTransport** over HTTP/3 (QUIC): multiple independent streams + unreliable datagrams over one connection, no TCP head-of-line blocking (QUIC streams are independent), 0-RTT reconnect, built-in TLS 1.3. Bidirectional/unidirectional streams + `datagrams` API. Replaces WebSocket+WebRTC-data for many cases; still maturing, needs HTTP/3 infra.

## Offline-first sync
- Persist CRDT locally (IndexedDB/`y-indexeddb`), apply edits offline, sync deltas on reconnect via state-vector diff. Because merge is conflict-free, offline edits reconcile without prompts. Key: durable local store + idempotent update application + garbage-collect tombstones to bound growth.

## Scaling realtime
- **Fan-out**: N clients per room; broadcasting each op to all is O(N) per op. Use a pub/sub bus (Redis, NATS) so multiple stateless WS nodes share room traffic; each node subscribes to its rooms' channels.
- **Sticky sessions**: WS/room affinity to a node (consistent hashing / room→node) so in-memory doc state isn't split; or externalize state so any node serves any room.
- **Backpressure**: slow client → server send buffer grows → OOM. Monitor `bufferedAmount`/socket buffer, drop or coalesce (send latest snapshot not every op), disconnect abusers. Batch/debounce awareness updates (e.g. throttle cursor to ~20-30Hz).
- **Presence at scale**: ephemeral, TTL-based, don't persist; aggregate/heartbeat with expiry so crashed clients vanish.

## Latency compensation
- **Local echo / optimistic apply**: render local edit immediately, reconcile on server ack (CRDT makes reconcile trivial — reapply remote deltas). **Cursor prediction/interpolation**: smooth remote cursors between updates. **Debounce/coalesce** high-freq signals. Show pending vs confirmed state for slow networks.

## Gotchas -> Fix
- **Op-based CRDT with lossy transport** → divergence (op lost/duplicated/reordered) -> require causal reliable delivery, or use state/delta-based + state-vector reconciliation (Yjs).
- **Putting presence/cursors in the shared CRDT doc** → tombstone bloat + persisted junk -> use ephemeral awareness channel, never the merged document.
- **No TURN in production** → ~15% of users can't connect (symmetric NAT) -> always provision TURN with credentials rotation.
- **WebRTC mesh past ~5 peers** → uplink saturation, quality collapse -> switch to SFU or server pub/sub hub.
- **Reliable-ordered data channel for cursors** → head-of-line blocking, laggy under loss -> `{ordered:false, maxRetransmits:0}` for transient state.
- **Ignoring `bufferedAmount` backpressure** → memory blowup / stalls -> gate sends on `bufferedAmountLowThreshold`; coalesce to latest snapshot.
- **Concurrent same-index inserts interleave characters** (CRDT) → garbled text -> expected with position-ID CRDTs; acceptable vs OT; don't "fix" by forcing order — Yjs handles deterministically.
- **Sticky-session assumed but LB round-robins** → doc state split across nodes, edits lost -> room→node affinity or fully externalized state + pub/sub.
- **Unbounded CRDT growth** from tombstones/history -> enable GC (Yjs) / periodic snapshot+compaction; Automerge history is intentional but costs memory.
- **Lamport clock used to detect concurrency** → can't -> use vector clocks / state vectors to distinguish concurrent vs causal.
- **postMessage/WS with no auth on join** → anyone edits the room -> authorize per-room; sign provider tokens.
- **Optimistic UI without server as tiebreak** for non-CRDT data → conflicting divergent states -> either full CRDT or server-authoritative with reconciliation on ack.
