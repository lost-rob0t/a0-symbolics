### patch
stale-safe text patch
Input schema for tool_args: {"type":"object","required":["path"],"additionalProperties":false,"properties":{"path":{"type":"string"},"patch_text":{"type":"string"},"old_text":{"type":"string"},"new_text":{"type":"string"},"edits":{"type":"array","items":{"type":"object"}},"open_in_canvas":{"type":"boolean"}}}
provide one patch form: `patch_text`, `old_text` plus `new_text`, or line `edits`
reuses canonical context matching stale-read checks and readback
