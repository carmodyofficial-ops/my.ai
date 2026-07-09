# gRPC & Protocol Buffers

## Protobuf basics
- Binary, schema-first serialization. Define messages in `.proto`; generate typed code per language.
```proto
syntax = "proto3";
package acme.orders.v1;
message Order {
  string id = 1;
  int64 total_cents = 2;
  repeated LineItem items = 3;
  Status status = 4;
}
enum Status { STATUS_UNSPECIFIED = 0; PLACED = 1; SHIPPED = 2; }
```
- **Field numbers (tags)** are the wire identity, not the field name. 1–15 encode in 1 byte (use for hot/frequent fields); 16–2047 take 2 bytes. Range up to 2^29-1; **19000–19999 reserved**.
- Scalars: `int32/int64` (varint, inefficient for negatives), `sint32/sint64` (zigzag, use for signed), `uint32/64`, `fixed32/64` (better for large/random values), `float/double`, `bool`, `string` (UTF-8), `bytes`.
- **proto3 defaults**: missing scalar = type default (0/""/false), indistinguishable from "explicitly set to default" unless you use `optional` (adds presence/has-bit) or wrapper types.
- **Composite**: `repeated` (list), `map<k,v>` (keys are scalar/string only), `oneof` (exactly one of a set is set — mutually exclusive union, saves space), nested messages, `enum` (must have a `0` value = UNSPECIFIED).

## Wire format
- Tag-length-value: each field on the wire is `(field_number << 3) | wire_type` then the value. Unknown fields are **preserved and passed through** by default (tolerant reader).
- Types not on the wire: field names, defaults, `repeated` empties. Small integers, compact. Not self-describing → you need the schema to decode.
- No field ordering guarantees; not canonical by default (don't hash serialized bytes for equality).

## Schema evolution rules
- **Never change or reuse a field number.** Changing a number = new field; reusing an old number = data corruption when old messages are decoded.
- Deleting a field: stop using it and **`reserved 3;` / `reserved "old_name";`** so the number/name can never be recycled.
- Safe: **add** new fields (old code ignores unknowns), add enum values (handle unknown/`UNSPECIFIED` on read), rename a field (name isn't on the wire — but breaks JSON mapping and codegen).
- Compatible type changes: `int32`↔`int64`↔`uint32`↔`uint64`↔`bool` (varint family) mostly interoperate but can truncate; `string`↔`bytes` compatible if bytes are valid UTF-8. Most other retype = breaking.
- Wrapping/unwrapping a `oneof`, moving fields in/out of `oneof`, or changing `repeated`↔scalar = breaking.

## gRPC RPC types
- Contract in `.proto` `service`; HTTP/2 transport, protobuf payloads by default.
```proto
service OrderService {
  rpc Get(GetReq) returns (Order);                 // unary
  rpc Watch(WatchReq) returns (stream Order);      // server streaming
  rpc Upload(stream Chunk) returns (UploadResp);   // client streaming
  rpc Chat(stream Msg) returns (stream Msg);       // bidirectional
}
```
- **Unary**: 1 req → 1 resp. **Server streaming**: 1 req → stream (feeds, tailing). **Client streaming**: stream → 1 resp (uploads, aggregation). **Bidi**: independent full-duplex streams over one connection.
- HTTP/2 multiplexes many RPCs over one TCP connection; header compression (HPACK); flow control per stream.

## Stubs / codegen
- `protoc` + language plugin (or Buf) generates message classes + client **stub** and server **base/skeleton**. Client calls the stub like a local method; it marshals + sends.
- Manage `.proto` files in a shared repo/registry; **Buf** provides linting, breaking-change detection, and dependency management. Version the package (`acme.orders.v1`).

## Deadlines, cancellation, metadata
- Set a **deadline/timeout per call** (absolute time preferred over relative). No deadline = calls can hang forever.
- **Deadline propagation**: pass the incoming context to downstream calls so the deadline flows through the chain; a server should stop work when the client's deadline expires (`context.Done()`/`CANCELLED`).
- **Cancellation**: client cancels → server context is cancelled; long-running/streaming handlers must check and bail out to free resources.
- **Metadata**: key/value headers (like HTTP headers) for auth tokens, trace context, request ids. Sent as leading/trailing (trailers carry final status).

## Interceptors, errors, LB
- **Interceptors** (unary + stream, client + server): cross-cutting middleware for auth, logging, metrics, tracing, retries. Compose in a chain.
- **Error model**: return a `status` = code + message + optional `details` (typed `google.rpc.*` messages). Codes: `OK, INVALID_ARGUMENT, NOT_FOUND, ALREADY_EXISTS, PERMISSION_DENIED, UNAUTHENTICATED, DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, FAILED_PRECONDITION, ABORTED, UNAVAILABLE, INTERNAL`. Don't stuff app errors into `INTERNAL`.
- Retry only **idempotent** RPCs and only safe codes (`UNAVAILABLE`, sometimes `RESOURCE_EXHAUSTED`); use gRPC's built-in retry/hedging policy with backoff.
- **Load balancing**: gRPC keeps **long-lived HTTP/2 connections**, so L4 LBs pin all traffic to one backend. Use **client-side LB** (round_robin/lookaside via xDS) or an L7/gRPC-aware proxy (Envoy, Linkerd) that balances per-request.

## Well-known types & options
- Standard types from `google/protobuf/`: `Timestamp` (seconds+nanos, UTC — use instead of raw int for time), `Duration`, `Empty` (RPCs with no request/response), `Any` (embed an arbitrary message + type URL), `Struct`/`Value` (dynamic JSON-like), `FieldMask` (partial update — client lists which fields to patch), wrapper types (`StringValue`, `Int32Value`) for explicit presence.
- **JSON mapping**: proto3 has a canonical JSON encoding (field names → camelCase, `Timestamp` → RFC 3339). Enables gRPC-JSON transcoding so REST clients can hit a gRPC service via a gateway.
- **Compression**: per-message gzip (`grpc-encoding`); worth it for large payloads, costs CPU.
- **Channels**: reuse one channel (connection pool) across many calls — creating a channel per call is expensive (TCP+TLS+HTTP/2 handshake). Channels are thread-safe.

## gRPC vs REST vs GraphQL
- **gRPC**: strong typed contract, binary/fast, streaming, HTTP/2, polyglot codegen. Best for **internal service-to-service**, low latency, streaming. Weaker browser support, not human-readable, needs tooling.
- **REST/JSON**: ubiquitous, human-readable, cache-friendly (HTTP caching), easy debugging. Best for **public/external** APIs and broad clients. No native streaming, no strict contract, over/under-fetching.
- **GraphQL**: client-specified queries, single endpoint, solves over/under-fetching for varied clients (esp. mobile/web aggregation). Caching + rate-limiting harder; N+1 resolver risk.
- **gRPC-Web**: browsers can't speak raw gRPC (no HTTP/2 frame access); gRPC-Web needs a proxy (Envoy) to translate; server-streaming works, client/bidi streaming limited. Or use **Connect** protocol (gRPC-compatible, browser-friendly).

## Gotchas -> Fix
- **Reusing/renumbering a field** -> silent data corruption; treat field numbers as permanent; `reserved` deleted numbers and names.
- **Enum without a 0 = UNSPECIFIED** -> proto3 requires a zero value; missing/unknown enum decodes to 0. Always reserve `0` for UNSPECIFIED and handle unknowns on read.
- **proto3 presence ambiguity** (can't tell "unset" from "zero") -> use `optional` fields or wrapper types (`google.protobuf.Int32Value`) when zero/empty is meaningful.
- **No deadline set** -> RPCs hang, threads/connections leak; set a per-call deadline and propagate the context downstream.
- **Deadline not propagated** -> downstream keeps working after the client gave up (wasted compute, cascading load); pass context through every hop.
- **L4 load balancer with gRPC** -> all requests pin to one backend (connection reuse); use client-side LB or an L7 gRPC-aware proxy.
- **Large messages / unbounded streams** -> default max message size ~4MB; big payloads blow memory and latency. Raise limits deliberately, or **stream/chunk** large data instead of one giant message.
- **Retrying non-idempotent RPCs** -> duplicate side effects; retry only idempotent methods and safe status codes; make handlers idempotent (dedup keys).
- **Errors dumped as INTERNAL/strings** -> clients can't act on them; use precise status codes + typed `details`.
- **Browser calls raw gRPC** -> won't work; use gRPC-Web/Connect behind a translating proxy.
- **Breaking change slips through** -> run automated breaking-change detection (Buf) in CI against the published schema.
- **Hashing serialized protobuf for equality** -> serialization isn't canonical (map/field order, unknown fields); compare parsed messages, not bytes.
- **Blocking event loop on unary in async runtimes** -> use the async stub; never block the reactor thread waiting on an RPC.
