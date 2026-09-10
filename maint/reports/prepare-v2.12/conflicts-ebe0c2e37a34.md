# Upstream replay conflicts: v2.12 at ebe0c2e37a34

## helpers/extract_tools.py.dox.md
```
diff --cc helpers/extract_tools.py.dox.md
index ad3333ea,64287624..00000000
--- a/helpers/extract_tools.py.dox.md
+++ b/helpers/extract_tools.py.dox.md
@@@ -29,7 -29,7 +29,12 @@@
  - Dirty parsing scans complete JSON object roots in prose and prefers the first object that normalizes as a valid tool request for permissive repair and legacy callers.
    Normalization accepts canonical `tool_name`/`tool_args`, legacy `tool`/`args`, native `type="function"` `name`/`parameters`, and a single-item `actions` wrapper; malformed or multi-action wrappers are rejected.
  - `extract_tool_request` is the execution boundary: it accepts a request only when the complete trimmed content is one valid tool object. Plain text, ordinary JSON, and tool-shaped JSON embedded in prose remain final text.
++<<<<<<< HEAD
 +- `extract_tool_request` rejects content that does not have complete object boundaries before invoking the dirty root scanner. This keeps incomplete streaming prefixes cheap without changing which complete canonical tool objects are accepted.
++||||||| parent of ebe0c2e3 (fix: extract XML tool calls from native-responses text turns)
++=======
+ - Native-Responses turns may emit tool calls as OpenAI-style text XML (`<invoke name="..."><parameter name="...">`); `extract_tool_request` parses those via `extract_xml_tool_request` when the whole trimmed message is invoke markup. Nested or sibling invokes become a `parallel` request with a `calls` list; prose before or after the markup, or an unterminated block, stays final text.
++>>>>>>> ebe0c2e3 (fix: extract XML tool calls from native-responses text turns)
  - `is_misformatted_tool_request` identifies a tool request wrapped in a JSON code fence, concatenated complete roots containing tool intent, or a complete Agent Zero envelope that starts with `thoughts` and whose dirty parser has absorbed `headline`, `tool_name`, and `tool_args` into that list. It routes that output to the existing repair prompt without executing it.
  - Streaming tool snapshots use `extract_tool_request`; the permissive root helpers remain available for repair and legacy callers, not tool execution.
  - Root extraction ignores objects nested inside an open parent object, so streamed wrapper tools such as `parallel` cannot stop early on the first nested `tool_calls` item.
```
