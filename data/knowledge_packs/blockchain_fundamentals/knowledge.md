# Blockchain Fundamentals

*(Technical/educational reference — not financial advice.)*

## Blocks, chains, hashing
- A **block** = header (prev-block hash, Merkle root, timestamp, nonce, height) + list of transactions. Each block references the previous block's hash → an append-only linked chain; changing any past block changes its hash and breaks every subsequent link.
- **Cryptographic hash** (SHA-256 Bitcoin, Keccak-256 Ethereum): deterministic, fixed-length, one-way (preimage-resistant), avalanche effect (1-bit change → totally different output), collision-resistant. Content-addressing = the hash IS the identity.
- Immutability is economic/probabilistic, not absolute — rewriting history requires redoing all subsequent work/stake and out-pacing the honest network.

## Merkle trees
- Transactions hashed pairwise up to a single **Merkle root** in the block header. Enables **Merkle proofs**: prove a tx is in a block with `log2(n)` hashes without the full block (SPV / light clients).
- Ethereum uses **Merkle-Patricia tries** for state (accounts, storage) — the state root commits to the entire world state.

## Keys, signatures, addresses
- **Asymmetric crypto** (ECDSA, secp256k1): private key (secret, 256-bit) → public key → address. Sign a tx hash with the private key; anyone verifies with the public key. Private key = full control; there is no password reset.
- **Address**: Ethereum = last 20 bytes of Keccak-256(pubkey), `0x…` hex, EIP-55 mixed-case checksum (guards against typos). Bitcoin derives from hash of pubkey (Base58/Bech32). Sending to a wrong-but-valid address = permanent loss.
- **Signature ≠ encryption**: signing proves authorship/authorization; it does not hide data. A signature over a tx authorizes exactly that tx's effects.
- **Seed phrase** (BIP-39, 12/24 words) → HD wallet (BIP-32/44) deriving many keypairs deterministically. Lose it = lose funds; leak it = stolen funds.

## Transactions, nonces, gas
- Tx fields (Ethereum): `nonce`, `to`, `value`, `data`, `gasLimit`, `maxFeePerGas`/`maxPriorityFeePerGas` (EIP-1559), signature (v,r,s).
- **Nonce** = per-account sequential counter; enforces ordering and prevents replay. Tx with nonce N waits until N-1 is mined; a stuck low-fee tx blocks higher nonces.
- **Gas** = compute units; fee = gas used × gas price. EIP-1559: **base fee** (burned, adjusts per block via congestion) + **priority fee/tip** (to validator). Out-of-gas → reverts, but gas is still consumed.
- Mempool = pending txns; validators order them (source of MEV / front-running). Higher tip = faster inclusion; dropped if it lingers or is replaced.
- **Confirmations**: 1 = included in the latest block; each subsequent block deepens it and lowers reorg probability. Exchanges require N confirmations before crediting deposits.

## UTXO vs account model
- **UTXO** (Bitcoin): balance = sum of unspent transaction outputs; a tx consumes whole UTXOs and creates new ones (incl. change). Stateless-ish, parallelizable, better privacy, but no native rich state.
- **Account model** (Ethereum): global state of balances + contract storage; txns mutate account state directly. Simpler for smart contracts; needs nonces to prevent replay.

## Consensus
- **Proof of Work** (Bitcoin): miners brute-force a nonce so `hash(block) < target`; longest/heaviest chain wins. Sybil-resistant via energy cost; **probabilistic finality** (deeper = safer, ~6 confirmations). 51% hash-power enables double-spend/censorship.
- **Proof of Stake** (Ethereum post-Merge): validators bond stake (32 ETH), pseudo-randomly proposed/attested blocks; misbehavior is **slashed**. Cheaper energy, **economic finality** via checkpoints (Casper FFG — a block is finalized when 2/3 of stake attests, ~2 epochs / ~12.8 min; reverting costs ≥1/3 of total stake).
- Others: PBFT/Tendermint (instant BFT finality, ≤1/3 faulty), DPoS, PoA (permissioned). BFT tolerates up to f faulty of 3f+1.

## Nodes & validators
- **Full node**: validates + stores all blocks/state, enforces rules independently (trustless). **Light client**: headers + Merkle proofs. **Archive node**: full historical state. **Validator/miner**: produces blocks + earns rewards.
- Decentralization security = many independent full nodes rejecting invalid blocks; you don't have to trust miners if you run a full node.

## Smart contract platforms (EVM)
- **EVM** = stack-based virtual machine executing bytecode (opcodes); every full node re-runs each tx deterministically. Gas meters each opcode to bound computation and prevent halting-problem DoS.
- **EVM-compatible** chains (Polygon, BNB, Avalanche C-chain, Arbitrum, Optimism, Base) reuse EVM bytecode + tooling (Solidity, MetaMask, ethers) → easy portability. Non-EVM: Solana (SVM, parallel, Rust), Cosmos (CosmWasm), Sui/Aptos (Move).
- Contract accounts have code + storage; EOAs (externally owned accounts) have a keypair, no code. Contracts can't initiate txns — an EOA must trigger the first call.
- Chains identified by **chainId** (Ethereum=1); replay protection (EIP-155) binds a signed tx to its chainId.

## Forks
- **Soft fork**: backward-compatible rule tightening (old nodes still accept new blocks). **Hard fork**: rule change old nodes reject → chain splits if not universally adopted (ETH/ETC, BTC/BCH).
- **Reorg**: shorter competing chain replaced by a longer/heavier one; recent blocks can revert (why you wait for confirmations).

## Scalability: L1 vs L2
- **Trilemma**: decentralization, security, scalability — hard to maximize all three; L1s trade off.
- **Rollups** (L2): execute txns off-chain, post data/proofs to L1 for security.
  - **Optimistic** (Arbitrum, Optimism): assume valid, **fraud proofs** during a challenge window (~7-day withdrawal delay); cheaper, EVM-equivalent.
  - **ZK-rollups** (zkSync, StarkNet): **validity proofs** (SNARK/STARK) verify every batch cryptographically; fast finality, no challenge delay, heavier proving.
- **Data availability**: rollups need tx data published (EIP-4844 blobs cut L2 costs). **Sharding / danksharding**: split data across the network. Sidechains (Polygon PoS) have own consensus — not inheriting L1 security.
- State/payment channels (Lightning) and Plasma are older scaling approaches.

## Bridges & risks
- **Bridges** move assets across chains: lock-and-mint (lock on A, mint wrapped on B) or burn-and-mint. Trust models: trusted/multisig custodian vs trust-minimized (light-client/ZK).
- Bridges hold huge pooled value and are top hack targets (validator key compromise, mint bug, signature forgery — e.g. hundreds of millions lost). Wrapped assets carry bridge counterparty risk.

## Wallets & custody
- **Non-custodial** (MetaMask, hardware): you hold keys, full control + full responsibility. **Custodial** (exchange): third party holds keys ("not your keys, not your coins"), reversible support but counterparty/insolvency risk.
- **Hardware wallets** keep keys in a secure element, sign offline. **Smart-contract wallets / account abstraction** (ERC-4337): social recovery, multisig, gas sponsorship, batched txns.

## Common misconceptions -> Correction
- **"Blockchain is anonymous"**: it's **pseudonymous** — all txns are public and traceable; chain analysis deanonymizes.
- **"Data is encrypted on-chain"**: public ledger data is plaintext/hashed, not encrypted; anyone can read it.
- **"Transactions are instant/free"**: subject to block times, congestion, gas fees, and confirmation depth.
- **"Immutable = can't be wrong/reversed"**: bad code is permanent, but consensus can reorg recent blocks or hard-fork.
- **"Smart contracts are legally binding contracts"**: they're autonomous code; bugs execute exactly as written (no intent).
- **"More decentralized always"**: many chains have concentrated validators/clients; measure client + stake diversity.
- **"Lost password recoverable"**: no central authority; lost seed = permanently lost funds.
- **"51% attack lets you steal anyone's coins"**: it enables double-spend/censorship, not stealing keyed funds or minting arbitrary balances.
- **"Confirmation = final"**: on PoW it's probabilistic; wait for depth or PoS finality.

## Economics & security model
- **Double-spend** = spending the same funds twice; consensus prevents it by agreeing on one canonical order. PoW cost = hardware+energy; PoS cost = slashable stake.
- **MEV** (maximal extractable value): block producers reorder/insert/censor txns to extract value (front-run, sandwich, back-run arb/liquidations). Mitigations: private mempools (Flashbots), proposer-builder separation (PBS), encrypted mempools.
- **Attack surfaces**: 51% (rewrite/censor), long-range (PoS, mitigated by weak subjectivity checkpoints), eclipse (isolate a node), Sybil (fake identities — countered by PoW/PoS cost), selfish mining.
- Validators earn issuance + fees + tips; fee burning (EIP-1559) can make issuance net-deflationary under load.

## Key tradeoffs
- Trustlessness costs redundancy (every node re-executes) → low throughput vs centralized DBs; L2s recover throughput while inheriting L1 security.
- Finality speed vs decentralization; on-chain storage is expensive → store hashes on-chain, data off-chain (IPFS/Arweave).
- Permissionless/public (open validators, censorship-resistant) vs permissioned/private (known validators, faster, no native token, but a trusted consortium — often a distributed DB with extra steps).
- Reversibility: no chargebacks/undo — errors and thefts are final absent a hard fork; UX must prevent mistakes (address checksums, simulation, confirmations).
- Cost vs security: more confirmations / higher finality = safer but slower; choose depth by value at risk.
