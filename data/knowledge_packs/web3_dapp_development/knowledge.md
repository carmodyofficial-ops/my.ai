# Web3 dApp Development

*(Technical/educational reference — not financial advice.)*

## dApp architecture
- Layers: **frontend** (React/Next) ↔ **wallet** (signs txns, holds keys) ↔ **library** (ethers/viem) ↔ **RPC node/provider** (Alchemy, Infura, public RPC) ↔ **smart contracts** (on-chain state/logic). Off-chain: **indexer** (The Graph) for querying history, **storage** (IPFS/Arweave) for large assets.
- Two connection roles: a **provider** (read-only, connects to a node) and a **signer** (an account that can sign/send txns, from the wallet). Reads hit the RPC; writes go through the wallet.
- Frontend never holds private keys — the wallet does; frontend requests signatures.

## Libraries
- **ethers.js** (v6): `new ethers.BrowserProvider(window.ethereum)`, `provider.getSigner()`, `new ethers.Contract(addr, abi, signerOrProvider)`. `ethers.parseEther("1.0")` / `formatEther(wei)`, `parseUnits(amt, decimals)`.
- **viem**: typed, modular; `createPublicClient`/`createWalletClient` with `http()` transport; `readContract`/`writeContract`/`simulateContract`. Lighter, tree-shakeable, TS-first.
- **wagmi** (React hooks over viem): `useAccount`, `useConnect`, `useReadContract`, `useWriteContract`, `useWaitForTransactionReceipt`, `useBalance`, wrap app in `WagmiProvider` + `QueryClientProvider`. **RainbowKit/ConnectKit** = prebuilt connect UI.
- **web3.js** = older alternative (`new Web3(provider)`).

## Wallet connection
- **EIP-1193** standard provider interface: `window.ethereum.request({ method, params })`. Connect: `eth_requestAccounts` (prompts user). Events: `accountsChanged`, `chainChanged` (recommended: reload or re-init on chain change), `disconnect`.
- **MetaMask** injects `window.ethereum`; multiple wallets → use **EIP-6963** (multi-injected provider discovery) to avoid conflicts.
- **WalletConnect** (v2): QR/deeplink to mobile wallets via relay; wagmi/RainbowKit bundle connectors.
- Switch/add network: `wallet_switchEthereumChain` (`{chainId:"0x1"}`), `wallet_addEthereumChain`. Always verify `chainId` — user may be on the wrong network.

## Reading vs writing
- **Read (call)**: `eth_call`, free, instant, no wallet/gas, no state change — `await contract.balanceOf(addr)`, view/pure functions.
- **Write (transaction)**: `eth_sendTransaction`, costs gas, needs signature, async (mine → confirm), can revert. `const tx = await contract.transfer(to, amt); const receipt = await tx.wait();`.
- **Signing messages** (no gas, off-chain auth): `signer.signMessage("...")` (EIP-191) or `signTypedData` (**EIP-712** structured, human-readable in wallet) — used for logins (Sign-In With Ethereum, EIP-4361), permits, gasless approvals (`permit`).

## Events & indexing
- Contract events are logs; listen: `contract.on("Transfer", (from,to,value,event)=>{})`; query past: `contract.queryFilter(contract.filters.Transfer(null, myAddr), fromBlock, toBlock)`.
- Indexed params are filterable topics. Raw `getLogs` is limited (block range caps, no aggregation/joins).
- **The Graph**: define a subgraph (`schema.graphql` entities + `subgraph.yaml` + AssemblyScript mappings that handle events) → query historical/aggregated data via GraphQL. Alternatives: Ponder, self-indexing into Postgres, Alchemy/Covalent APIs.

## Transaction lifecycle
- Build → estimate gas → user signs in wallet → broadcast → **pending** in mempool → included in block (**1 confirmation**) → more blocks (deeper confirmations) → possibly reorged/dropped.
- `tx.wait(n)` resolves after n confirmations. Receipt has `status` (1 success / 0 revert), `gasUsed`, `logs`, `blockNumber`.
- **Stuck tx** (fee too low): resubmit **same nonce** with higher `maxFeePerGas` to replace; send-to-self same nonce to cancel.
- EIP-1559: set `maxFeePerGas` and `maxPriorityFeePerGas`; provider can estimate via `getFeeData()`.

## Gas estimation & errors
- `contract.estimateGas.fn(args)` or `provider.estimateGas`; estimation itself reverts if the call would revert — surface that as a pre-flight check. Add a buffer (~20%) for state that changes between estimate and mine.
- **Simulate first** (`simulateContract` in viem, or `callStatic`/staticCall in ethers) to catch reverts and decode custom errors before spending gas.
- Decode revert reasons: parse `error.data` against the ABI (custom errors `error Insufficient(uint have,uint want)`); `require` strings appear in the revert.

## ABIs
- **ABI** = JSON describing functions/events/errors (name, inputs, outputs, type, stateMutability) — how the frontend encodes calls and decodes results. Get from compiler artifact (Foundry `out/`, Hardhat `artifacts/`) or a verified contract on the explorer.
- Only include the fragments you use (human-readable ABI: `["function balanceOf(address) view returns (uint256)"]`). ABI mismatch with deployed bytecode → decode errors/wrong data.

## Testnets & deployment
- Testnets: **Sepolia** (main Ethereum testnet), Holesky (staking); fund from faucets. L2 testnets: Base Sepolia, Arbitrum Sepolia, etc. Never deploy unaudited value-holding contracts to mainnet.
- Deploy: Foundry `forge create`/`forge script --broadcast --verify`, Hardhat `hardhat ignition`/deploy scripts. **Verify** source on Etherscan (`--verify` / `hardhat verify`) so users can read/trust it.
- Store RPC URLs + deployer keys in env/secrets — never commit; use a dedicated deployer key with limited funds.

## Storage (IPFS/Arweave)
- **IPFS**: content-addressed (CID = hash of content); store NFT metadata/images off-chain, put the CID on-chain (`ipfs://<cid>`). Data must be **pinned** (Pinata, web3.storage, own node) or it can disappear. `ipfs://` needs a gateway to fetch in browsers.
- **Arweave** = pay-once permanent storage. On-chain storage is far too expensive for media — store hashes/pointers, not blobs.

## Security
- **Never expose private keys or seed phrases** in frontend code, env shipped to client, or git. All client-side env (`NEXT_PUBLIC_`/`VITE_`) is public — only RPC URLs/read keys, never signing keys.
- **Validate on-chain, not just in UI**: client checks are UX only; contracts must enforce every rule (auth, amounts, limits) — a malicious client bypasses your frontend.
- Show what users sign: prefer EIP-712 typed data over blind hex; warn on unlimited `approve` (max uint256) — offer exact-amount or revocation.
- Verify `chainId` before sending; pin contract addresses per network; beware phishing dApps requesting `setApprovalForAll` or draining approvals.
- Use audited contracts (OpenZeppelin); rate-limit RPC; don't trust `eth_call` results from untrusted RPCs for security decisions.

## UX
- Reflect every tx state: idle → wallet-confirm → pending (show explorer link) → confirmed/failed. Disable buttons while pending; handle user rejection (error code `4001`).
- Decode revert messages into human copy; handle wrong-network (prompt switch), no-wallet (prompt install), and `accountsChanged`/`chainChanged` reactively.
- Optimistic UI is risky — a tx can revert or reorg; reconcile after `wait()`.

## Account abstraction & gasless UX
- **ERC-4337** (no protocol change): users are smart-contract wallets; `UserOperation`s go to a **bundler** via an alt-mempool → `EntryPoint` contract; **paymasters** can sponsor gas (gasless) or accept ERC-20 for gas. Enables batching, session keys, social recovery.
- **Meta-transactions**: user signs (EIP-712), a relayer submits + pays gas; contract recovers signer via `_msgSender()` (ERC-2771 trusted forwarder).
- **Gasless approvals**: EIP-2612 `permit` lets a user sign an approval; the spender submits it in the same tx — one signature, no separate approve tx.

## Multicall & batching
- Batch many reads in one RPC round-trip via a **Multicall3** contract (`aggregate3`) — wagmi/viem do this automatically for `useReadContracts`. Cuts latency and rate-limit pressure vs N separate `eth_call`s.
- Use `Promise.all` for independent reads; debounce on input; cache with React Query (wagmi built-in) — set sensible `staleTime`, invalidate after writes.

## Common dApp Pitfalls -> Fix
- **Sending a tx while user is on the wrong chain**: check `chainId`, prompt `wallet_switchEthereumChain` before write.
- **Not awaiting `tx.wait()`** / treating broadcast as confirmed: await receipt, check `status === 1`, then update UI.
- **Float math on token amounts**: use `BigInt`/`parseUnits` with the token's `decimals` — never JS floats (precision loss); read `decimals()` (USDC=6, not 18).
- **Hardcoding gas or ignoring EIP-1559**: use `getFeeData()`/estimation with a buffer.
- **Wrong/stale ABI or address after redeploy**: regenerate ABI, update per-network address map, verify on explorer.
- **Unhandled user rejection / no error surfacing**: catch code `4001` and revert-decode; show actionable messages.
- **Nonce collisions from parallel sends**: serialize writes or manage nonce explicitly; replace stuck tx with same nonce + higher fee.
- **Trusting a single public RPC**: they rate-limit/lag/reorg — use a reliable provider, retries, and confirmations.
- **Unpinned IPFS content**: pin via a service or run a node; assets vanish otherwise.
- **Requesting infinite `approve` by default**: default to exact amounts; expose revoke; educate users.
- **`chainChanged`/`accountsChanged` not handled**: re-init provider/signer and refetch on these events.
- **Assuming events return instantly / missing blocks**: index with The Graph; handle reorged logs (`removed` flag) and block-range caps.
- **Reading a contract before it exists on the current chain**: guard on `chainId` and address presence; getCode check before calls to avoid decoding empty returns as zero.
- **Blind signing / phishing `setApprovalForAll`**: use EIP-712 typed data, display decoded intent, warn on approvals to unknown spenders; provide a revoke flow.
- **CORS / exposing API keys in RPC URL**: proxy provider requests through your backend or use domain-allowlisted keys; rotate leaked keys.
- **Ignoring token `decimals` differences across chains** (USDC 6 vs DAI 18): read `decimals()` per token, format with `formatUnits`.
- **Not simulating writes**: a tx that will revert wastes gas and confuses users — `simulateContract`/`callStatic` first and decode the custom error.
