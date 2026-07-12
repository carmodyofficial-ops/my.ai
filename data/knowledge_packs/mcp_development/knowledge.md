# MCP Development (Model Context Protocol)

## What it is
- **Open protocol** (Anthropic, 2024) that standardizes how LLM apps connect to external **tools, data, and prompts** via **servers**. "USB-C for AI" — write a server once, any MCP-compatible host can use it.
- JSON-RPC 2.0 message format. Replaces bespoke per-app integrations with one interface.
- Spec is versioned by date (e.g. `2025-06-18`); capabilities negotiated per session.

## Architecture
- **Host**: the LLM application (Claude Desktop, IDE, custom agent) that wants context/tools.
- **Client**: lives inside host; maintains a **1:1 connection** to one server; handles protocol.
- **Server**: exposes capabilities (tools/resources/prompts). Runs locally (subprocess) or remote.
- Host runs many clients → many servers. Server never sees other servers.

## Primitives (server exposes)
- **Tools** (model-controlled): functions the LLM can invoke; have side effects / compute. `name`, `description`, `inputSchema` (JSON Schema), optional `outputSchema`, `annotations` (readOnlyHint, destructiveHint). Discovered via `tools/list`, called via `tools/call`.
- **Resources** (app/host-controlled): read-only data addressed by URI (`file://`, `db://…`), for context (files, records). `resources/list`, `resources/read`; support subscriptions/updates. Not meant to trigger actions.
- **Prompts** (user-controlled): reusable templated messages / slash commands; `prompts/list`, `prompts/get` with arguments.
- (Client can also offer **sampling** — server asks host to run an LLM completion — and **roots** and **elicitation**.)

## Transports
- **stdio**: server is a subprocess; JSON-RPC over stdin/stdout. Local, simple, default for local tools. **Never write logs to stdout** — corrupts the stream; use stderr.
- **Streamable HTTP** (current remote transport): single HTTP endpoint, POST for requests, optional SSE stream for server→client; supports sessions, resumability. Replaces the old **HTTP+SSE** transport (deprecated).
- Remote servers need **auth** (OAuth 2.1 for HTTP transport in recent spec).

## Building a server (Python — FastMCP)
```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("weather")

@mcp.tool()
def get_forecast(city: str, days: int = 3) -> str:
    """Get weather forecast. Args auto-become JSON schema from type hints."""
    return fetch(city, days)

@mcp.resource("config://app")
def config() -> str: ...

if __name__ == "__main__":
    mcp.run()  # stdio by default; mcp.run(transport="streamable-http")
```
- Tool **description + schema quality drives model accuracy** — this is prompt engineering. Be explicit about params, units, enums, when to use.
- Return concise, structured results; include only what the model needs.

## Building a server (TypeScript)
```ts
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
const server = new McpServer({ name: "demo", version: "1.0.0" });
server.registerTool("add", {
  inputSchema: { a: z.number(), b: z.number() }
}, async ({ a, b }) => ({ content: [{ type: "text", text: String(a+b) }] }));
```

## Building a client (basics)
- Spawn/connect transport → `initialize` handshake (exchange protocolVersion + **capabilities**) → `tools/list` → feed tool schemas to the LLM → on tool_use, call `tools/call` → return result to LLM.
- Capabilities negotiation: each side advertises what it supports (tools, resources, sampling, roots); don't call unsupported features.

## SDKs & tooling
- Official SDKs: **Python** (`mcp`, FastMCP), **TypeScript**, plus Java/Kotlin/C#/Go/Rust/Swift.
- **MCP Inspector** (`npx @modelcontextprotocol/inspector`): interactive UI to list/call tools, inspect schemas, debug — use before wiring into an agent.
- Config: hosts register servers in JSON (command + args + env for stdio; url for HTTP).

## Design principles for good tools
- **One tool = one clear capability**; avoid god-tools with a `mode` enum. Name for the model's mental model, not your internal API.
- Descriptions are the contract: state purpose, when to use vs not, param semantics, units, return shape, side effects. Include a short example in the description.
- Constrain inputs with JSON Schema (`enum`, `minimum`, `pattern`, `required`) so bad calls fail fast with a clear message.
- Make tools **idempotent** and **read-only where possible**; mark side effects with annotations.
- Return the minimum useful data; support a "detail" follow-up tool instead of dumping everything.

## Security (critical)
- **Untrusted servers = untrusted code**: a malicious server can exfiltrate data or return **prompt-injection** payloads in tool results that hijack the agent. Only install trusted servers.
- **Tool results are untrusted content**: treat as data, not instructions; the model may obey injected instructions. Sandbox/limit what the agent can do after.
- **Confused deputy / token passthrough**: don't blindly forward the user's tokens; scope credentials per server.
- **Tool permissions / human-in-loop**: gate destructive tools (annotations `destructiveHint`); require confirmation.
- **Auth** for remote: OAuth 2.1, validate audience, short-lived tokens.
- **Rug-pull**: a server can change tool definitions after approval — pin/verify.
- **Combined-server exfil**: benign tool + malicious tool → data flows out; limit trust surface.

## Lifecycle & message types
- **Initialization**: client sends `initialize` (protocolVersion, capabilities, clientInfo) → server responds → client sends `initialized` notification. Only then normal ops.
- Message types: **requests** (expect response, have `id`), **responses** (result or error), **notifications** (no `id`, no reply — e.g. `notifications/tools/list_changed`, progress, cancellation).
- **Dynamic capabilities**: server can notify `list_changed` so client refetches tools/resources; support if tools change at runtime.
- **Pagination**: `list` methods use opaque `cursor` — implement for large tool/resource sets.

## Tool result shape
- Content blocks: `text`, `image`, `audio`, **embedded resource**, **resource_link**. Set `isError: true` for tool-level failures (vs protocol errors). Optional `structuredContent` matching `outputSchema`.
- Return structured, minimal data; prefer links/IDs over dumping large payloads.

## Use in agent systems
- Servers give agents reusable, composable capabilities; one server usable across Claude Desktop, IDEs, custom agents.
- Keep tool set small and relevant per agent — too many tools bloat context and confuse selection.
- **Tool namespacing**: with multiple servers, prefix/qualify names to avoid collisions; document overlap.
- Combine with sampling (server → host LLM) and elicitation (server → user input) for interactive flows; but each expands trust surface.

## Local server config example (stdio)
```json
{ "mcpServers": {
  "weather": { "command": "python", "args": ["-m", "weather_server"],
    "env": { "API_KEY": "..." } } } }
```
- Remote: `{ "url": "https://host/mcp", "headers": { "Authorization": "Bearer ..." } }`.

## Testing & debugging
- **Inspector** first: verify `tools/list`, call each tool, check schemas + error paths before host integration.
- Log to stderr/file; capture raw JSON-RPC frames when debugging framing/buffering.
- Unit-test handlers directly (pure functions); integration-test over the transport.

## Gotchas -> Fix
- **Poor tool schema/description** → model calls wrong tool or bad args. **Fix**: precise descriptions, enums, examples, units, `required` fields; test in Inspector; iterate like prompts.
- **Oversized tool results / context bloat** → dumping huge JSON blows context window and cost. **Fix**: paginate, filter, summarize, return IDs + a fetch-detail tool; cap response size.
- **Logging to stdout on stdio** → corrupts JSON-RPC, cryptic client failures. **Fix**: log to **stderr** / file only.
- **Unhandled errors / crashes** → server dies, whole session breaks. **Fix**: return structured tool errors (`isError`), catch exceptions, validate inputs against schema.
- **Trusting tool output as safe** → prompt injection via returned content. **Fix**: treat outputs as untrusted; don't auto-execute embedded instructions; sandbox side effects; sanitize.
- **stdio buffering / not flushing** → hangs. **Fix**: line-buffered, flush after each message; correct framing.
- **Protocol version / capability mismatch** → calling features the peer lacks. **Fix**: honor negotiated capabilities; check `protocolVersion`; degrade gracefully.
- **Long-running tools block** → client timeout. **Fix**: async handlers, progress notifications, keep tools fast/idempotent.
- **Secrets in server env leaking** → tool returns credentials. **Fix**: never echo secrets; scope env; least privilege.
- **Too many tools registered** → poor tool selection, token waste. **Fix**: expose only needed tools per host/agent; group servers.
- **No versioning on server** → breaking changes silently. **Fix**: version the server, keep tool contracts stable, deprecate gracefully.
- **Deprecated HTTP+SSE transport** used for new remote server. **Fix**: use Streamable HTTP.
- **Tool name collisions across servers** → wrong tool invoked. **Fix**: namespace/prefix tool names; document.
- **No pagination on large list** → truncated/oversized `tools/list`. **Fix**: implement cursor pagination.
- **Blocking on `initialize`d before ready** → race calling tools pre-handshake. **Fix**: wait for `initialized` before ops.
- **Non-idempotent tools retried** → duplicate side effects on client retry. **Fix**: idempotency keys, annotate destructive tools, confirm.
- **Server holds unbounded state / connections** → resource leak. **Fix**: clean up per-session; bound concurrency.
