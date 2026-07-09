# Cryptography

## Pick-the-primitive cheat sheet
- Encrypt data (symmetric): **AES-256-GCM** or **ChaCha20-Poly1305** (AEAD — confidentiality + integrity in one). Never plain CBC/CTR without a separate MAC.
- Encrypt to a public key: **hybrid** — random AES key, then wrap it with RSA-OAEP or ECIES/X25519. Never RSA-encrypt bulk data.
- Sign: **Ed25519** (fast, misuse-resistant) or **ECDSA P-256**; RSA-PSS if RSA required. Never RSASSA-PKCS1-v1_5 for new designs.
- Key agreement: **X25519** (ECDH) or ECDH P-256. Static-static leaks nothing forward — prefer **ephemeral** (forward secrecy).
- Hash (integrity, fingerprints): **SHA-256 / SHA-512 / SHA-3**. Never MD5 or SHA-1 (both collision-broken).
- Keyed integrity / auth tag: **HMAC-SHA256**. Password storage: **Argon2id** (or scrypt/bcrypt) — NOT a plain hash.
- Random: OS CSPRNG only (`/dev/urandom`, `getrandom(2)`, `crypto.randomBytes`, `secrets`). Never `rand()`/`Math.random()`/`mt19937` for keys/nonces/tokens.

## Symmetric encryption
- AES block cipher, 128-bit block, keys 128/192/256-bit. Modes matter more than key size.
- **AES-GCM**: AEAD. 96-bit (12-byte) nonce is optimal. Output = ciphertext + 16-byte tag. Also authenticates AAD (associated data — headers, IDs). **Nonce MUST be unique per key** — reuse under GCM leaks the auth key (XOR of plaintexts + forgery). Use random 96-bit nonce (safe to ~2^32 msgs/key) or a counter.
- **ChaCha20-Poly1305**: AEAD, constant-time in software, no AES-NI needed — preferred on mobile/embedded. Same nonce-uniqueness rule.
- **XChaCha20-Poly1305 / AES-GCM-SIV**: 192-bit / misuse-resistant nonces — use when you can't guarantee nonce uniqueness (random nonce w/o coordination).
- **ECB is broken**: encrypts identical blocks identically → leaks structure (the "ECB penguin"). Never use.
- CBC needs random IV + separate MAC (encrypt-then-MAC) and is padding-oracle prone (Lucky13, POODLE) — avoid for new code.
- Key size guidance: AES-256 for long-term/defense-in-depth; AES-128 is fine cryptographically. Rotate keys; never derive multiple purposes from one raw key — use HKDF to split.

## Asymmetric / public-key
- **RSA**: security from integer factorization. Min 2048-bit (3072 for long-term). Encrypt with **OAEP** (not PKCS#1v1.5 — Bleichenbacher padding oracle). Sign with **PSS**. Slow; large keys/signatures.
- **ECC**: equivalent security at far smaller keys (256-bit ECC ≈ 3072-bit RSA). Curves: P-256/P-384 (NIST), Curve25519/448 (Bernstein — rigid, side-channel friendly).
- **ECDSA**: signature. **Fatal flaw: per-signature nonce `k` must be unique + secret** — reuse or bias recovers the private key (PS3, Sony). Use RFC 6979 deterministic `k` or Ed25519.
- **Ed25519**: EdDSA over Curve25519 — deterministic nonces, no `k` footgun, fast verify. Default for new signing.
- Public key = distribute freely; private key = never leaves its boundary (HSM/KMS/TPM ideal).

## Key exchange
- **Diffie-Hellman**: parties derive shared secret over public channel. Finite-field DH needs ≥2048-bit groups (use named groups, RFC 7919 `ffdhe`) — small/unknown groups enable Logjam.
- **ECDH / X25519**: DH on curves; far cheaper. **Ephemeral (ECDHE) → forward secrecy**: past traffic stays safe if long-term key later leaks.
- Never use the raw DH output as a key — run it through a **KDF (HKDF-Extract+Expand)** to get uniform key material and bind context (labels, transcript).

## Hashing, MACs, passwords
- Cryptographic hash props: preimage, 2nd-preimage, collision resistance. SHA-256/512, SHA-3/SHAKE. BLAKE2/BLAKE3 fast + secure.
- **MD5, SHA-1 = collision-broken** (Flame, SHAttered). Never for signatures/certs/integrity vs adversary. (Non-security dedup only, grudgingly.)
- **MAC**: authenticity + integrity with shared key. **HMAC-SHA256** (HMAC construction immune to length-extension, unlike raw SHA-2). Verify tags in **constant time**. Prefer AEAD over encrypt+separate-MAC when possible.
- **Passwords ≠ hashes**: use a slow, memory-hard KDF: **Argon2id** (memory ~64MB+, iterations tuned), **scrypt**, or **bcrypt** (≤72 bytes, cost ≥12). Never SHA-256(password) — GPU-crackable at billions/sec.
- **Salt**: unique random per password (defeats rainbow tables); stored alongside hash. **Pepper**: optional secret key kept separate (HMAC before hashing). Argon2/bcrypt embed salt in the output string.

## TLS, certificates, PKI
- **TLS 1.3 handshake** (1-RTT): ClientHello (offers key shares, cipher suites) → ServerHello (picks suite, its key share) → both derive shared secret via **ECDHE** → server sends Certificate + CertificateVerify (signs transcript) + Finished. Only AEAD suites; static-RSA key exchange removed → **forward secrecy always**. 0-RTT resumption exists but is replayable — don't use for non-idempotent requests.
- **Certificate** = public key + identity (SAN/CN) signed by a CA. Client validates: signature chain up to a trusted root, `notBefore/notAfter`, hostname vs **SAN** (CN is legacy), key usage/EKU, and **revocation** (OCSP stapling; CRL). Basic Constraints `CA:TRUE` gates who can sign.
- **PKI**: root CA (offline) → intermediates → leaf. Trust anchored in OS/browser root store. **Certificate Transparency** logs catch mis-issuance. **HPKP is dead**; pin at the CA/SPKI level in apps cautiously.
- mTLS: client also presents a cert — service-to-service auth.

## Key derivation & formats
- **KDF from a shared secret** (DH output, X25519): **HKDF** = Extract (concentrate entropy w/ optional salt) + Expand (stretch to N bytes, bind an `info` label per context/purpose). Derive distinct keys for each direction/role from one master secret.
- **KDF from a password**: PBKDF2 (legacy, many iterations) or, better, Argon2id/scrypt (memory-hard). Password KDF ≠ HKDF — different threat (offline brute force).
- Key/cert encodings: **PEM** (base64 text, `-----BEGIN …-----`) vs **DER** (binary). **PKCS#8** private keys, **SPKI/X.509** public keys/certs, **PKCS#12/.pfx** (key+cert bundle, password-protected). JWK/JWKS = JSON key format for web.
- Fingerprints: identify a key/cert by SHA-256 of its DER SPKI — used in cert pinning.

## Side channels & constant-time
- **Timing attacks**: branch/lookup time leaks secrets. Compare MACs/tokens/passwords in **constant time** (`hmac.compare_digest`, `crypto.timingSafeEqual`) — never `==`/early-exit `memcmp`.
- **Padding oracles**: any observable difference between "bad padding" and "bad MAC" leaks plaintext (CBC). AEAD sidesteps this (single auth failure). Return uniform errors.
- Cache/branch side channels in modular exponentiation/scalar mult → use libraries with constant-time implementations; Curve25519/Ed25519 are designed for this. Prefer AES-NI hardware or constant-time ChaCha20.
- Don't leak via error messages, logs, or differential responses (username enumeration, "wrong password" vs "no such user").

## Post-quantum (awareness)
- A large quantum computer would break RSA/ECC/DH (Shor's algorithm); symmetric/hash only lose ~half security (Grover) → AES-256 and SHA-384/512 stay safe.
- NIST PQC standards (2024): **ML-KEM/Kyber** (key encapsulation), **ML-DSA/Dilithium** + **SLH-DSA/SPHINCS+** (signatures). Deploy as **hybrid** (classical + PQC) for "harvest-now-decrypt-later" protection of long-lived secrets; don't drop classical yet.

## Randomness & key management
- CSPRNG for all keys, IVs/nonces, tokens, salts. Seed from OS entropy; never a timestamp/PID/PRNG. Watch VM-clone / early-boot low-entropy.
- Keys: generate in and keep inside a KMS/HSM where possible; separate keys per purpose/environment; enforce **rotation** (define crypto-period) and **versioned key IDs** so you can decrypt old data during rollover.
- **Envelope encryption**: DEK encrypts data; KEK (in KMS) encrypts the DEK — rotate KEK cheaply without re-encrypting data.

## Gotchas -> Fix
- **Roll-your-own crypto** -> use vetted libs (libsodium/NaCl, `cryptography`, ring, Tink, WebCrypto); never invent modes/protocols.
- **ECB mode** -> AES-GCM/ChaCha20-Poly1305 (AEAD).
- **GCM/CTR nonce reuse** -> unique nonce per key (counter or random 96-bit); or AES-GCM-SIV/XChaCha20 for misuse resistance.
- **ECDSA nonce reuse/bias** -> RFC 6979 deterministic k, or switch to Ed25519.
- **Hardcoded/committed keys** -> KMS/secret manager + env injection; rotate anything ever in git history (scan with gitleaks/trufflehog).
- **SHA-256(password)** -> Argon2id/bcrypt/scrypt with per-user salt.
- **Non-constant-time compare** of MACs/tokens -> `hmac.compare_digest`/`crypto.timingSafeEqual`.
- **RSA PKCS#1v1.5 encrypt/sign** -> OAEP for encrypt, PSS for sign.
- **Encrypt without authenticate** (CBC only) -> AEAD, or encrypt-then-MAC with HMAC.
- **`Math.random()`/`rand()` for tokens** -> CSPRNG (`crypto.randomBytes`, `secrets.token_bytes`).
- **Reusing one key for encrypt + MAC + KDF** -> derive distinct subkeys via HKDF with context labels.
- **`alg:none`/algorithm confusion** (JWT/JWS) -> pin expected algorithm server-side; verify, don't just decode.
- **Trusting CN for hostname** -> validate SAN; reject on chain/expiry/revocation failure (don't disable verification to "make it work").
- **Encrypting huge data with RSA** -> hybrid encryption (RSA/ECIES wraps a symmetric key).
- **No forward secrecy** -> ECDHE key exchange; ephemeral keys, TLS 1.3.
