# Solidity Smart Contracts

## Contract structure
- `// SPDX-License-Identifier: MIT` then `pragma solidity ^0.8.24;` — pin compiler; 0.8+ has built-in overflow checks.
- Layout: state variables, events, errors, modifiers, constructor, functions. `contract C is Base { ... }` for inheritance (C3-linearized; `super.f()` calls next in chain).
- State variables live in **storage** (persistent, expensive). `constructor()` runs once at deploy; `immutable` set once in constructor and cheaper than storage; `constant` fixed at compile time.
- Events: `event Transfer(address indexed from, address indexed to, uint256 value);` emit with `emit Transfer(a,b,v);`. Up to 3 `indexed` params become filterable topics; non-indexed go in data. Events are the only way off-chain code observes state changes cheaply.
- Custom errors (cheaper than `require` strings): `error Unauthorized(address caller);` then `revert Unauthorized(msg.sender);`. `require(cond, "msg")`, `revert()`, `assert(cond)` (assert = invariant, consumes all gas pre-0.8 / Panic post).
- Modifiers: `modifier onlyOwner() { require(msg.sender == owner, "not owner"); _; }` — `_;` marks where the body runs; put checks before `_`.

## Types
- Value types: `bool`, `uint8..uint256` (`uint`=uint256), `int`, `address` / `address payable` (only payable can `.transfer`/`.send`), `bytes1..bytes32`, `enum`.
- `mapping(address => uint256) balances;` — not iterable, no length, default value for any key is zero; nested `mapping(address => mapping(address => uint256))` for allowances.
- `struct Point { uint x; uint y; }`; dynamic arrays `uint[]`, fixed `uint[10]`, `bytes`, `string` (UTF-8, no indexing). `address(this).balance`, `msg.sender`, `msg.value`, `block.timestamp`, `tx.origin`.
- `msg.sender` = immediate caller; `tx.origin` = original EOA (NEVER use for auth).

## Data location: storage vs memory vs calldata
- **storage** = persistent contract state (SLOAD/SSTORE, costly). **memory** = temporary, mutable, wiped after call. **calldata** = read-only input, cheapest — use for external function array/struct params.
- `Point storage p = points[id];` is a reference — writes persist. `Point memory p = points[id];` copies — writes don't persist.
- Function params default: value types copied; reference types need explicit location. `function f(uint[] calldata a) external`.

## Visibility & function types
- `public` (callable externally + internally, auto-getter for state vars), `external` (only from outside; cheaper for large calldata args), `internal` (this + derived), `private` (this contract only — still readable on-chain, not secret).
- `view` (reads state, no writes), `pure` (no state access), `payable` (accepts ETH). Non-payable functions reject ETH.
- Everything on-chain is public — `private` only restricts Solidity access, not visibility of the data.

## Gas & optimization
- Cost drivers: SSTORE (20k for zero→nonzero, 5k for update, refund on nonzero→zero), SLOAD (~2100 cold/100 warm), contract creation, calldata bytes.
- **Storage packing**: multiple vars < 32 bytes in same slot if declared consecutively — `uint128 a; uint128 b;` share one slot. Order struct/state fields to pack; a `bool`+`uint248` fit one slot; `uint256` after a `bool` wastes the rest of the slot.
- Cache storage in memory inside loops: read `arr.length`/mapping once into a local. Use `unchecked { ++i; }` for loop counters that can't overflow (0.8+).
- Prefer `calldata` over `memory` for external args; `constant`/`immutable` over storage reads; custom errors over require strings; short-circuit conditions; avoid unbounded loops (can exceed block gas limit → DoS).
- `++i` cheaper than `i++`; batch storage writes; delete storage to reclaim gas refund.

## ERC standards
- **ERC-20** (fungible): `totalSupply()`, `balanceOf(address)`, `transfer(to,amount)`, `approve(spender,amount)`, `allowance(owner,spender)`, `transferFrom(from,to,amount)`; events `Transfer`, `Approval`. Use OpenZeppelin `ERC20`. Beware fee-on-transfer/rebasing tokens breaking accounting; `approve` race — prefer `increaseAllowance` or set to 0 first.
- **ERC-721** (NFT, unique): `ownerOf(tokenId)`, `balanceOf`, `safeTransferFrom`, `approve`, `setApprovalForAll`, `tokenURI(id)` (often IPFS). `safeTransferFrom` calls `onERC721Received` on contract recipients (reentrancy surface).
- **ERC-1155** (multi-token): single contract, both fungible + non-fungible, batch ops `balanceOfBatch`, `safeBatchTransferFrom` — gas-efficient for many token types.

## Security patterns
- **Checks-Effects-Interactions**: validate → update state → external call, in that order. Prevents reentrancy by updating balances before sending.
- **Reentrancy guard**: OpenZeppelin `ReentrancyGuard` + `nonReentrant` modifier (a mutex flag) on functions doing external calls/transfers.
- **Access control**: OZ `Ownable` (`onlyOwner`, `transferOwnership`, use `Ownable2Step` to avoid transferring to wrong address); `AccessControl` for role-based (`hasRole`, `grantRole`, `DEFAULT_ADMIN_ROLE`, `bytes32 MINTER_ROLE`).
- **Pull over push**: don't loop-send funds (one revert blocks all); record owed amounts and let users `withdraw()`.
- ETH sending: `(bool ok, ) = to.call{value: amt}(""); require(ok);` — `.transfer`/`.send` capped at 2300 gas and can break with proxy recipients. Always check return of low-level `.call`.

## Fallback, receive, low-level calls
- `receive() external payable {}` handles plain ETH transfers (empty calldata); `fallback() external [payable] {}` handles unknown selectors or ETH with data. Keep them minimal — they run under 2300 gas from `.transfer`.
- Function **selector** = first 4 bytes of `keccak256("transfer(address,uint256)")`; calldata = selector + ABI-encoded args. Selector clashes possible in proxies.
- Low-level: `addr.call(abi.encodeWithSelector(...))`, `staticcall` (view), `delegatecall` (borrow logic, keep own storage/`msg.sender`/`msg.value`). All return `(bool success, bytes memory data)` and do NOT auto-revert — check success.

## Libraries & inheritance
- `library L { function f(uint x) internal ... }` + `using L for uint;` attaches methods; internal library funcs inline, external ones `delegatecall`. Common: OZ `SafeERC20` (`safeTransfer` handles non-standard tokens returning no bool).
- Inheritance is linearized (C3); `virtual`/`override` required to redefine; `abstract contract`/`interface` (only function signatures, all external, no state/constructor). Diamond inheritance resolved right-to-left in `is` list.
- Function overloading by param types; interface IDs via ERC-165 `supportsInterface(bytes4)`.

## Events, logs, revert semantics
- Reverts roll back ALL state changes in the call (and bubble up unless caught with `try/catch`); gas up to the revert point is spent. `try extContract.f() returns (...) { } catch { }` isolates external-call failures.
- Logs are cheaper than storage and unreadable by contracts — use for off-chain state, not on-chain logic. Anonymous events save a topic but lose the event signature.

## Testing & tooling
- **Foundry**: tests in Solidity. `forge test`, `forge build`, `forge fmt`. `contract T is Test { function testX() public { ... } }`, cheatcodes `vm.prank(addr)`, `vm.expectRevert()`, `vm.deal`, `vm.warp`. Fuzzing: `function testFuzz(uint256 x) public`. `forge coverage`, invariant tests.
- **Hardhat**: JS/TS, `npx hardhat test` with ethers + chai, `hardhat-network` forking mainnet, console.log debugging.
- Static analysis: **Slither** (`slither .`), Mythril; run before deploy. Fork-test against real mainnet state.

## Upgradeability (proxy patterns)
- Contracts are immutable; upgrade via proxy delegating logic. **Transparent proxy** (admin vs user routing), **UUPS** (upgrade logic in implementation, `_authorizeUpgrade`, cheaper), **Beacon** (many proxies, one upgrade point).
- `delegatecall` runs logic code against the proxy's storage — storage layout MUST stay compatible across versions (append only, never reorder/remove; use storage gaps `uint256[50] __gap`).
- Use OZ `@openzeppelin/contracts-upgradeable` + Upgrades plugin; no constructors — use `initializer`/`__X_init` with `initializer` modifier; guard against uninitialized implementation.

## Security Pitfalls -> Fix
- **Reentrancy** (external call before state update, e.g. withdraw sends then zeroes balance): apply checks-effects-interactions AND `nonReentrant`.
- **`tx.origin` for auth**: phishable via intermediary contract — use `msg.sender`.
- **Integer overflow pre-0.8**: use 0.8+ (checked math) or SafeMath on old code; only wrap in `unchecked` when provably safe.
- **Unchecked low-level call return**: `.call`/`.send` return false on failure without reverting — `require` the bool.
- **`approve` front-running / double-spend**: use `increaseAllowance`/`decreaseAllowance` or approve-to-zero-then-set.
- **Oracle/price manipulation** (spot price from a DEX pool): use TWAP or Chainlink; a flash loan can skew a single-block reserve read.
- **Front-running / MEV**: sensitive txns are public in the mempool — use commit-reveal, slippage limits (`minAmountOut`), private relays.
- **Unbounded loop / gas griefing**: iterating a user-growable array can brick the function — pull pattern, pagination, caps.
- **Missing access control on `init`/`mint`/`selfdestruct`**: restrict with modifiers; guard proxy initializers against re-call and front-run initialization.
- **`delegatecall` to untrusted/upgradable target or storage-layout drift**: only delegatecall audited logic; append-only storage + gaps.
- **Default-visible "private" secrets on-chain**: never store secrets or seeds in contract storage — all readable via `eth_getStorageAt`.
- **Floating pragma / outdated compiler**: pin exact version; track known compiler bugs.
- **Rounding / precision loss in division**: multiply before dividing; use fixed-point scaling (1e18).
- **Signature replay**: same signed message accepted twice or on another chain — include a nonce + `chainid` + contract address in the signed payload (EIP-712 domain separator); use OZ `ECDSA.recover` and reject `address(0)`.
- **`block.timestamp` manipulation**: validators can nudge it a few seconds — don't use for randomness or tight timing; `block.timestamp` acceptable for coarse deadlines.
- **On-chain randomness from block data**: `keccak256(block.timestamp, ...)` is predictable/manipulable — use Chainlink VRF.
- **Force-fed ETH via `selfdestruct`**: `address(this).balance` can exceed tracked deposits — never assume balance equals internal accounting; track deposits in a variable.
- **DoS via revert in a callback / unexpected revert**: an external recipient that always reverts can block a shared function — pull pattern + isolate with `try/catch`.
- **Uninitialized storage pointer / shadowed variables**: enable compiler warnings, use `memory`/`storage` explicitly, avoid name shadowing.
