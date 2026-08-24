### git
read-only Git inspection
Input schema for tool_args: {"type":"object","required":["action"],"additionalProperties":false,"properties":{"action":{"type":"string","enum":["status","branch","diff","show","log","grep"]},"revision":{"type":"string"},"path":{"type":"string"},"query":{"type":"string"},"staged":{"type":"boolean"},"limit":{"type":"integer","minimum":1,"maximum":200},"session":{"type":"integer","minimum":0}}}
`diff` accepts staged revision and path; `show` defaults to HEAD; `grep` requires query
