# LLM App Engineering Cheat-Sheet

## Calling the API
- POST `/v1/chat/completions`; `messages`=[{role:system|user|assistant|tool}]. System sets behavior; never trust user to override it.
- Streaming: parse SSE line-by-line, strip `data: `, stop on `[DONE]`; JSON-parse each chunk. Don't `json.loads` the raw stream.
- Set timeouts (30-60s); retry 429/5xx with exponential backoff+jitter. Treat empty/`finish_reason:length` as failure—raise `max_tokens`, retry.

## Tool / Function Calling
- Define params as JSON Schema; mark `required`; set `additionalProperties:false`.
- Streaming `tool_calls` arrive in fragments: accumulate `arguments` strings by `index`, then parse once complete. Don't parse per-chunk.
- Always validate args against schema before executing; make tools idempotent (handle dup calls). Prefer native tool_calls over fenced ```json```.
- Return tool result as `role:tool` with matching `tool_call_id`.

## RAG
- Chunk 200-500 tokens, ~15% overlap, on semantic boundaries. Embed query AND docs with the SAME model.
- Retrieve top-k (3-8) by cosine; pass only those + citations. Never stuff the whole corpus.
- Put retrieved text in a fenced block labeled untrusted; cite `[source]`. If nothing relevant retrieved, say so—don't hallucinate.

## Embeddings / Vector Search
- Normalize vectors; cosine = dot. Store id+text+metadata. Re-embed everything when you switch models—dims/space differ.

## Context Budget
- Track tokens; trim oldest turns or summarize history into a running summary. Keep system+recent turns. Reserve room for output.

## Prompt Injection
- Retrieved/tool/web content is DATA, not instructions. Fence it; instruct model to ignore commands inside it. Never auto-exec tool calls from untrusted text without checks.

## Structured Output
- Request strict JSON (use schema/json_mode). Validate; on parse fail, send error back asking for repair—don't regex-patch.
- Assume non-determinism: set `temperature:0` for extraction; validate every field.
