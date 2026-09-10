# Upstream replay conflicts: v2.12 at 0874c8f17b48

## AGENTS.md
```
diff --cc AGENTS.md
index a4359b4f,84f9ef1d..00000000
--- a/AGENTS.md
+++ b/AGENTS.md
@@@ -31,12 -28,8 +31,18 @@@
  - Preserve authentication and CSRF protections.
  - Use Linux paths and commands in examples.
  - When a live Dockerized Agent Zero target is explicitly named, verify that exact runtime instead of assuming a fixed localhost port.
++<<<<<<< HEAD
 +- Message-loop completion flows through a response tool with `break_loop`; plain or malformed Chat Completions text enters repair, and native Responses output text is normalized through the same response-tool path.
 +- Reuse the startup-preloaded local embedding model for matching runtime configurations; wrappers retain their own rate-limit configuration while sharing the underlying inference model.
 +- Embedding wrappers expose batch-shaped `embed(inputs)` for provider-ready inputs; keep `embed_documents` and `embed_query` as LangChain compatibility adapters.
 +- Embedding requests never forward the chat-only `a0_api_mode` control to providers.
++||||||| parent of 0874c8f1 (fix: resolve extracted tool names through the responses name map)
++- Message-loop completion flows through a response tool with `break_loop`; plain or malformed Chat Completions text enters repair, and native Responses output text is normalized through the same response-tool path.
++=======
+ - Message-loop completion flows through a response tool with `break_loop`; plain or malformed Chat Completions text enters repair, and native Responses output text is normalized through the same response-tool path, including OpenAI-style text XML tool calls whose names resolve through the responses name map.
++>>>>>>> 0874c8f1 (fix: resolve extracted tool names through the responses name map)
  - Prompt Markdown may retain fenced JSON examples for readability; final system-prompt rendering removes only their JSON fence markers before model calls and preserves non-JSON fences.
 +- System section owners register request-only alternatives with `helpers.responses_tools`; `helpers.responses_history` owns their per-build state and prepared-history capture in existing loop parameters. Responses applies them to copied input, preserving original Chat/fallback messages and stored history.
  - Copy live core-plugin changes back into tracked source under `plugins/`.
  - Develop new custom plugins under ignored `usr/plugins/`; tracked bundled plugins live under `plugins/`.
  - Use the framework runtime for backend and plugin-hook verification, not the separate agent execution runtime.
```
