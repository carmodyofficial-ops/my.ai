# Computer Networks Deep Dive

## Models
- OSI (7): Physical, Data Link, Network, Transport, Session, Presentation, Application. Reference/teaching model.
- TCP/IP (4-5): Link (Ethernet/Wi-Fi, MAC, ARP), Internet (IP, ICMP, routing), Transport (TCP/UDP), Application (HTTP/DNS/TLS). What the internet actually runs.
- Encapsulation: each layer prepends header; L2 frame ⊃ L3 packet ⊃ L4 segment ⊃ app data. MTU limits frame payload.

## IP & Routing
- IPv4 32-bit dotted-quad; IPv6 128-bit hex. Private ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, loopback `127.0.0.0/8`, link-local `169.254/16`.
- CIDR: `/n` = n network bits; host bits = 32−n → `2^(32-n)` addresses (−2 for network+broadcast in IPv4). `/24`=256 addrs, `/30`=4 (2 usable, point-to-point). Subnet mask e.g. `/26` = `255.255.255.192`.
- Routing: longest-prefix match in routing table picks next hop. Interior (OSPF link-state, RIP distance-vector) vs exterior (BGP — path-vector, AS paths, policy, glues the internet). Default route `0.0.0.0/0`.
- ARP resolves IP→MAC on a LAN; ICMP for diagnostics (echo/ping, time-exceeded drives traceroute, dest-unreachable incl. fragmentation-needed).
- TTL decremented per hop; hits 0 → dropped + ICMP time-exceeded (prevents routing loops).

## TCP vs UDP
- TCP: connection-oriented, reliable, ordered, byte-stream, full-duplex; flow + congestion control. Header: seq/ack numbers, window, flags (SYN/ACK/FIN/RST/PSH/URG), checksum.
- Handshake (3-way): SYN → SYN-ACK → ACK; exchanges ISNs, MSS, window scale, SACK-permitted. Data can piggyback (TCP Fast Open).
- Teardown (4-way): FIN/ACK each direction; active closer enters TIME_WAIT (2×MSL) to absorb stray segments and ensure final ACK delivery. RST = abrupt abort.
- Reliability: cumulative ACKs, retransmission on timeout (RTO, from RTT via smoothed RTT + variance) or 3 duplicate ACKs (fast retransmit). SACK acks non-contiguous ranges.
- Flow control: receiver advertises window (rwnd) → prevents overrunning receiver buffer; zero-window probes.
- Congestion control: slow start (cwnd doubles per RTT, exponential) → congestion avoidance (linear +1 MSS/RTT after ssthresh) → on loss: fast recovery (Reno halves) or timeout (back to slow start). CUBIC (default Linux, window ∝ cubic of time since loss). BBR models bandwidth×RTT instead of loss. Effective rate ≈ min(cwnd, rwnd)/RTT.
- UDP: connectionless, unreliable, unordered, message-oriented, tiny 8-byte header. For DNS, VoIP, games, QUIC — app handles reliability if needed. Lower latency, no HOL blocking.

## DNS
- Hierarchical: root → TLD (`.com`) → authoritative. Recursive resolver queries iteratively on client's behalf; caches per TTL.
- Records: A (IPv4), AAAA (IPv6), CNAME (alias — cannot coexist with other records at same name, not at zone apex), MX (mail + priority), NS (delegation), TXT (SPF/DKIM/verification), SOA (zone params), PTR (reverse), SRV, CAA.
- Resolution: stub → recursive resolver → root/TLD/authoritative → answer cached down the chain. UDP/53 (fallback TCP/53 for large/zone transfer); DoT/DoH encrypt.
- TTL controls cache lifetime — low TTL = agile but more queries; stale caches delay propagation.

## HTTP & TLS
- HTTP/1.1: text, one request/response per connection at a time; keep-alive reuses TCP; pipelining rarely usable (server HOL blocking). Multiple parallel connections to parallelize.
- HTTP/2: binary framing, multiplexed streams over one TCP connection, header compression (HPACK), server push (deprecated), stream prioritization. Solves HTTP-level HOL — but TCP-level HOL remains (one lost segment stalls all streams).
- HTTP/3 over QUIC (UDP): independent streams with per-stream loss recovery → no transport HOL blocking; 0-/1-RTT handshake (TLS 1.3 built in); connection migration via connection IDs (survives IP change). QPACK headers.
- TLS handshake (1.2): ClientHello/ServerHello (cipher negotiation), certificate + key exchange (ECDHE for forward secrecy), Finished — 2 RTT. TLS 1.3: 1-RTT (0-RTT resumption), removes legacy ciphers, always forward-secret. Certificate chain validated to trusted root; SNI selects vhost.

## NAT, Sockets, Load Balancing
- NAT: rewrites private↔public IP:port, keeps translation table (NAPT/PAT — many hosts share one public IP by port). Breaks inbound-initiated flows → port forwarding, STUN/TURN/ICE for hole punching. CGNAT adds another layer.
- Socket: `(src IP, src port, dst IP, dst port, proto)` 5-tuple uniquely identifies a connection. `socket/bind/listen/accept` (server), `socket/connect` (client); ephemeral source ports.
- Load balancing: L4 (transport — routes by IP/port, fast, opaque to content, DSR possible) vs L7 (application — routes by URL/host/cookie, TLS termination, richer). Algorithms: round-robin, least-connections, consistent hashing (minimal remap on scale). Health checks eject bad backends.
- CDN: edge caches near users; anycast advertises same IP from many sites — BGP routes to nearest → low latency, DDoS absorption.

## Link Layer & Switching
- Ethernet frame: dest/src MAC, EtherType, payload, FCS (CRC32). Switches learn MAC→port (CAM table), forward by MAC; unknown/broadcast flooded. VLANs (802.1Q tag) segment L2 broadcast domains.
- Collision domains eliminated by full-duplex switching; STP prevents L2 loops. LAG/bonding aggregates links. Jumbo frames (MTU 9000) cut per-packet overhead on controlled networks.
- DHCP leases IP/gateway/DNS (DISCOVER/OFFER/REQUEST/ACK). ARP cache poisoning is an L2 attack vector.

## IPv6 & Transition
- No broadcast (uses multicast); NDP replaces ARP; SLAAC autoconfig via router advertisements. No NAT needed (huge address space) though NAT66 exists. Dual-stack, 6to4/Teredo tunneling, `::ffff:0:0/96` IPv4-mapped.

## Performance
- Latency (RTT, propagation-bound, ~speed of light) vs bandwidth (throughput). Adding bandwidth won't fix latency-bound workloads; RTT dominates short transfers and handshakes.
- Bandwidth-delay product = capacity of the pipe; TCP window must ≥ BDP to fill it (window scaling for high BDP links).
- MTU 1500 typical Ethernet; PMTUD discovers path min via DF bit + ICMP frag-needed. MSS = MTU − IP − TCP headers. IP fragmentation (when DF clear) is fragile — reassembly at receiver, any lost fragment drops the whole datagram; avoid by keeping ≤ path MTU.
- Connection setup cost: DNS (1 RTT) + TCP handshake (1 RTT) + TLS (1-2 RTT) before first byte → connection reuse, TLS session resumption, and 0-RTT (QUIC/TLS 1.3) matter for tail latency.
- Throughput per flow ≈ MSS/(RTT·√loss) (Mathis) — high-RTT or lossy paths cap single-flow speed regardless of link capacity → parallelism or better congestion control (BBR).
- Observability: `ping`/`traceroute`/`mtr` (path/latency), `ss`/`netstat` (socket states), `tcpdump`/Wireshark (capture), `dig`/`nslookup` (DNS), `iperf` (throughput).

## Security & Middleboxes
- Firewalls (stateless ACL vs stateful connection-tracking); proxies (forward vs reverse); WAF inspects L7. Deep packet inspection and TLS interception break end-to-end encryption assumptions.
- Common attacks: DDoS (volumetric/SYN-flood/amplification via DNS/NTP reflection), ARP/DNS spoofing, on-path MITM, BGP hijack/route leaks. Defenses: rate limiting, RPKI for BGP origin validation, DNSSEC (signed records prevent forgery), TLS + HSTS.
- Ports: well-known <1024 (80 HTTP, 443 HTTPS, 53 DNS, 22 SSH, 25 SMTP), registered 1024-49151, ephemeral 49152-65535.

## Gotchas -> Fix
- Nagle + delayed-ACK interaction (40ms+ stalls on small writes) -> set `TCP_NODELAY` for latency-sensitive request/response; or batch writes.
- TIME_WAIT exhaustion on busy clients (ephemeral ports/ports used up) -> reuse connections (keep-alive/pooling), `SO_REUSEADDR`; let the peer be active closer; tune `tcp_tw_reuse`.
- PMTUD black hole (ICMP frag-needed filtered → large packets silently dropped, connection hangs after handshake) -> allow ICMP type 3 code 4, or clamp MSS at the router (`--clamp-mss-to-pmtu`).
- Stale DNS after failover due to long TTL -> lower TTL ahead of planned changes; don't rely on instant propagation.
- CNAME at zone apex -> illegal; use A/AAAA or provider ALIAS/ANAME/flattening.
- HTTP/2 over lossy links still HOL-blocks at TCP -> use HTTP/3/QUIC where loss is significant.
- Assuming TCP preserves message boundaries -> it's a byte stream; frame your own messages (length prefix/delimiter).
- Ignoring `write()` partial sends / TCP backpressure -> loop until all bytes sent; handle EAGAIN on non-blocking sockets.
- Trusting `Connection: keep-alive` without idle timeout handling -> handle server-closed idle connections (retry idempotent requests only; non-idempotent POSTs risk duplication).
- Blocking on a single DNS resolver / no fallback -> configure multiple resolvers and sane timeouts; a stalled resolver hangs every connection.
- Ephemeral-port reuse with lingering old connections -> tune `SO_LINGER`, rely on TIME_WAIT to protect against delayed duplicates rather than disabling it.
- SYN flood / half-open exhaustion -> enable SYN cookies.
- Sticky-session LB + backend scaling -> use consistent hashing or externalize session state so rebalancing doesn't drop sessions.
- Bufferbloat (huge queues inflate latency under load) -> AQM (fq_codel/CAKE), BBR congestion control.
