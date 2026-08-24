### exec
run source with `exec(lang, source_code)`
Input schema for tool_args: {"type":"object","required":["lang","source_code"],"additionalProperties":false,"properties":{"lang":{"type":"string","enum":["shell","python","javascript","terminal","bash","sh","py","js","node","nodejs"]},"source_code":{"type":"string"},"session":{"type":"integer","minimum":0},"reset":{"type":"boolean"},"allow_running":{"type":"boolean"}}}
uses protected shell Python or Node.js sessions; never expose credentials
