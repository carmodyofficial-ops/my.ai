# Threat Model — my.ai Glasses

Assets: (1) the Odysseus host and its data, (2) device credentials,
(3) private conversation/audio/image content, (4) the glasses channel itself
(potential command injection into a tool-using agent).

## Adversaries & scenarios

| # | Threat | Mitigation | Status |
|---|---|---|---|
| T1 | Attacker on the LAN calls the gateway | Every route except `/pair` requires a session or scoped bearer token; `/pair` needs a single-use 5-min code and is rate-limited 5/min/IP | tested + live-verified |
| T2 | Pairing code interception / replay | Code is useless after first redemption (atomic consume); sha256 at rest; TTL 300 s; QR contains no long-lived secret | tested + live-verified |
| T3 | Stolen phone / extracted credential | Token lives in Android Keystore; scope `wearables` blocks the general API; instant admin revocation (Settings → API tokens or DELETE /devices/{id}) | tested + live-verified (see per-process cache caveat, PAIRING_AND_AUTH.md) |
| T4 | Glasses channel as a remote shell (voice-prompt injection, hostile web content during web_fetch) | Read-only toolset + hard deny-set; `trusted_execution=False` keeps the safe-abstention anti-injection layer active; max 6 agent rounds; no workspace bound | tested (unit) — deny-set asserted |
| T5 | Secrets read aloud | System prompt forbids; spoken transform strips code/URLs; gateway never surfaces env/config; tools that could read secrets are disabled | tested (spoken transform) |
| T6 | DoS: huge payloads / request floods | Byte caps enforced mid-stream (413), per-owner and per-IP sliding-window rate limits (429), bounded sessions per owner, bounded pending codes | tested |
| T7 | Cross-user data access (multi-user host) | All session/cancel/delete lookups owner-scoped; hostile session-id collision mints a fresh id; devices listing is admin-only | tested |
| T8 | CSRF minting of pairing codes | Mint is POST + admin cookie (SameSite=Lax) — same posture as existing token routes | tested |
| T9 | Exposure of internal model ports to the phone | Phone only ever talks to the gateway; 11434/8787/8100/8080 stay loopback-bound; compose unchanged | verified (compose config) |
| T10 | Log exfiltration of content | Gateway logs metadata only (verified live); pre-existing agent-loop INFO line documented as a host-level finding | partially mitigated — see SECURITY_AND_PRIVACY.md |
| T11 | Malicious/compromised Meta transport | Out of our control; scope limited to pairing/BT transport; disclosed honestly; no firmware modification attempted | accepted + disclosed |
| T12 | Rogue second app in Developer Mode | Meta allows one registered third-party app at a time; user-visible in Meta AI app "connected apps" | accepted (platform control) |
| T13 | Downgrade to cleartext on LAN | Client policy: TLS by default; cleartext only to RFC1918 after explicit user confirmation at setup; server-side operator guidance (reverse proxy / overlay VPN) | client policy defined; TLS termination is an operator step (runbook) |
| T14 | Reasoning/thinking leakage to voice | Thinking deltas excluded from spoken text + session history (regression-tested after live discovery) | tested + fixed |

## Residual risks (explicit)

1. **TLS is operator-provisioned** (reverse proxy or overlay network). Until
   configured, LAN traffic is cleartext HTTP on a trusted home network — the
   default bind is loopback-only precisely so exposure is a conscious step.
2. Per-process token-cache revocation caveat (single-process deployments
   unaffected).
3. Host-level `[agent-intent]` prompt logging (pre-existing, documented).
4. Meta-side data practices are outside this project's boundary.
5. Guest account: unrelated to this feature, but note the host has a
   known-password guest account with elevated privileges (operator decision,
   2026-06-29); the wearables scope gate is independent of it — guest is not
   an admin, so it cannot mint pairing codes.
