# Upstream replay conflicts: v2.12 at 9063cdd21b3e

## helpers/extract_tools.py.dox.md
```
diff --cc helpers/extract_tools.py.dox.md
index 2c2af34d,0a8fc648..00000000
--- a/helpers/extract_tools.py.dox.md
+++ b/helpers/extract_tools.py.dox.md
@@@ -29,7 -29,7 +29,12 @@@
  - Dirty parsing scans complete JSON object roots in prose and prefers the first object that normalizes as a valid tool request for permissive repair and legacy callers.
    Normalization accepts canonical `tool_name`/`tool_args`, legacy `tool`/`args`, native `type="function"` `name`/`parameters`, and a single-item `actions` wrapper; malformed or multi-action wrappers are rejected.
  - `extract_tool_request` is the execution boundary: it accepts a request only when the complete trimmed content is one valid tool object. Plain text, ordinary JSON, and tool-shaped JSON embedded in prose remain final text.
++<<<<<<< HEAD
 +- `extract_tool_request` rejects content that does not have complete object boundaries before invoking the dirty root scanner. This keeps incomplete streaming prefixes cheap without changing which complete canonical tool objects are accepted.
++||||||| parent of 9063cdd2 (fix: recover tool requests when JSON root slicing fails)
++=======
+ - When regex root slicing fails on a message starting with `{` (for example invalid JSON with raw control characters inside string values), `extract_tool_request` recovers the request with the tolerant DirtyJson parser over the whole message; the complete-message contract for valid JSON with trailing or leading prose is unchanged.
++>>>>>>> 9063cdd2 (fix: recover tool requests when JSON root slicing fails)
  - Native-Responses turns may emit tool calls as OpenAI-style text XML (`<invoke name="..."><parameter name="...">`); `extract_tool_request` parses those via `extract_xml_tool_request` when the whole trimmed message is invoke markup. Nested or sibling invokes become a `parallel` request with a `calls` list; prose before or after the markup, or an unterminated block, stays final text.
  - `is_misformatted_tool_request` identifies a tool request wrapped in a JSON code fence, concatenated complete roots containing tool intent, or a complete Agent Zero envelope that starts with `thoughts` and whose dirty parser has absorbed `headline`, `tool_name`, and `tool_args` into that list. It routes that output to the existing repair prompt without executing it.
  - Streaming tool snapshots use `extract_tool_request`; the permissive root helpers remain available for repair and legacy callers, not tool execution.
```
