# Upstream replay conflicts: v2.12 at 936713bcecd6

## extensions/python/_functions/AGENTS.md
```
diff --cc extensions/python/_functions/AGENTS.md
index 5ba2a7f5,d3485ff9..00000000
--- a/extensions/python/_functions/AGENTS.md
+++ b/extensions/python/_functions/AGENTS.md
@@@ -15,10 -15,9 +15,15 @@@
  - Do not flatten nested qualname paths into retired legacy folder names.
  - Extension functions must match the implicit hook's supplied arguments.
  - Preserve ordering prefixes where exception handling, watchdog registration, or cleanup depends on them.
 -- Hooks that mirror persisted AI responses into UI logs must reuse existing stream log items and avoid duplicating live response-tool logs.
 +- Hooks that mirror persisted AI responses into UI logs must reuse existing stream log items and avoid duplicating live response-tool logs. Native-call commentary must not be finalized as a plain response; canonical calls keep their tool-step log ownership.
 +- The `AgentContext.run_task/end` hook attaches integration callbacks to the returned `DeferredTask`; keep terminal side effects out of `agent.py`.
  - Recovery-loop circuit breakers must stop at the General Settings limit and render their user-visible cost warning from a core framework prompt.
++<<<<<<< HEAD
 +- Prompt settings snapshots must be task-local, accessed through `get_settings_for_prompt()`, and end with the matching `Agent.prepare_prompt` call, including exceptional exits.
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++=======
+ - The local-tool prompt post-hook removes complete fenced JSON examples only after availability plugins have added or removed their tool stubs. Keep callable prose, argument contracts, non-JSON fences, and incomplete fences intact.
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
  
  ## Work Guidance
```

## helpers/defer.py.dox.md
```
diff --cc helpers/defer.py.dox.md
index 449e9ac6,afbf2cb8..00000000
--- a/helpers/defer.py.dox.md
+++ b/helpers/defer.py.dox.md
@@@ -17,8 -17,8 +17,9 @@@
  - `ChildTask` (no explicit base class)
  - `DeferredTask` (no explicit base class)
    - `start_task(self, func: Callable[..., Coroutine[Any, Any, Any]], *args, **kwargs)`
 +  - `add_done_callback(self, callback: Callable[[Future], Any]) -> None`
    - `is_ready(self) -> bool`
+   - `wait_finished(self, timeout: Optional[float]=...) -> bool`
    - `result_sync(self, timeout: Optional[float]=...) -> Any`
    - `async result(self, timeout: Optional[float]=...) -> Any`
    - `kill(self, terminate_thread: bool=...) -> None`
@@@ -29,11 -29,10 +30,18 @@@
  
  ## Runtime Contracts
  
 +- Named event-loop instances serialize loop and thread creation under the registry lock, including concurrent first use and lazy starts through `run_coroutine`. Cancelling a consumer task must not terminate its shared loop.
  - Helper modules own reusable framework APIs and must preserve public callers unless all callers, tests, and docs are updated together.
  - `DeferredTask` retains its callable and arguments only while an invocation is active; completion and `kill()` clear those references after the running coroutine has taken its own snapshot.
++<<<<<<< HEAD
 +- `add_done_callback()` forwards to the current invocation's concurrent future and rejects calls before `start_task()`; callbacks observe `is_alive() == False` and must remain lightweight.
 +- Task results remain available after completion. `restart()` can restart an active invocation, but a completed invocation has no retained call recipe and must be started again explicitly.
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++- Task results remain available after completion. `restart()` can restart an active invocation, but a completed invocation has no retained call recipe and must be started again explicitly.
++=======
+ - Task results remain available after ordinary completion. A killed invocation drops its completed future after cancellation cleanup so coroutine frames cannot retain arguments. `restart()` can restart an active invocation, but a completed invocation has no retained call recipe and must be started again explicitly.
+ - Cross-thread future cancellation is only a request; `wait_finished()` observes generation-fenced event-loop settlement after the coroutine and its completion callback have exited. The coroutine clears its self-reference before settlement; Python may still leave an unreachable cancellation-traceback cycle for normal cyclic garbage collection, but the task must retain no reachable argument reference. An older cancelled generation must never clear or settle a restarted invocation.
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
  - Update this file whenever public functions, classes, persistence behavior, path/security assumptions, side effects, or cross-module contracts change.
  - Observed side-effect areas: scheduler state.
  - Imported dependency areas include: `asyncio`, `concurrent.futures`, `dataclasses`, `threading`, `typing`.
```

## helpers/litellm_transport.py
```
diff --cc helpers/litellm_transport.py
index 9cedac2a,463fb8d0..00000000
--- a/helpers/litellm_transport.py
+++ b/helpers/litellm_transport.py
@@@ -1860,17 -1733,12 +1894,28 @@@ def _object_to_dict(obj: Any) -> dict[s
      return {}
  
  
++<<<<<<< HEAD
 +def _reported_usage(response: Any) -> dict[str, Any]:
 +    usage = _object_to_dict(_get_value(response, "usage"))
 +    hidden = _object_to_dict(_get_value(response, "_hidden_params"))
 +    if usage.get("cost") is None:
 +        usage.pop("cost", None)
 +        if hidden.get("response_cost") is not None:
 +            usage["cost"] = hidden["response_cost"]
 +    return usage
 +
 +
 +def _normalize_reasoning_effort(effort: Any) -> str | None:
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++def _normalize_reasoning_effort(effort: Any) -> str | None:
++=======
+ def _normalize_reasoning_effort(
+     effort: Any,
+     *,
+     supported_efforts: Any = None,
+     none_is_effort: bool = False,
+ ) -> str | None:
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
      if isinstance(effort, str):
          normalized = effort.strip().lower()
      else:
```

## helpers/ws.py.dox.md
```
diff --cc helpers/ws.py.dox.md
index 692a817c,a38b5e47..00000000
--- a/helpers/ws.py.dox.md
+++ b/helpers/ws.py.dox.md
@@@ -43,11 -43,7 +43,16 @@@
  - `WsHandler` defines `requires_csrf(...)`.
  - `WsHandler` defines `requires_api_key(...)`.
  - `WsHandler` defines `requires_loopback(...)`.
++<<<<<<< HEAD
 +- `WsHandler.emit_to(..., max_payload_bytes=...)` delegates optional serialized-size enforcement to `WsManager` so protocol handlers can apply negotiated peer ceilings without duplicating envelope logic.
 +- The namespace wildcard dispatcher sends manager-produced handler responses
 +  through `WsManager.constrain_ack_response(...)` after security results are
 +  merged, so acknowledgements obey the same negotiated per-peer ceiling as
 +  ordinary emitted events.
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++=======
+ - Directly invoked handlers may be constructed without a manager; acknowledgement-returning operations still work and unsolicited emit helpers become no-ops until `bind_manager(...)` is called.
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
  - Observed side-effect areas: filesystem reads, filesystem deletion, network calls, WebSocket state, plugin state, settings/state persistence, secret handling.
  - Imported dependency areas include: `abc`, `dataclasses`, `flask`, `helpers`, `helpers.errors`, `helpers.network`, `helpers.print_style`, `os`, `pathlib`, `socketio`, `threading`, `typing`, `urllib.parse`, `uuid`.
```

## tests/email_parser_test.py
```
* Unmerged path tests/email_parser_test.py
```

## tests/rate_limiter_test.py
```
diff --cc tests/rate_limiter_test.py
index 630a45e7,e7f69651..00000000
--- a/tests/rate_limiter_test.py
+++ b/tests/rate_limiter_test.py
@@@ -3,23 -3,21 +3,59 @@@ import sys, o
  sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
  import models
  
++<<<<<<< HEAD
  async def run():
      provider = "openrouter"
      name = "deepseek/deepseek-r1"
 +
      model = models.get_chat_model(
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++provider = "openrouter"
++name = "deepseek/deepseek-r1"
++
++model = models.get_chat_model(
++    provider=provider,
++    name=name,
++    model_config=models.ModelConfig(
++        type=models.ModelType.CHAT,
++=======
++async def run():
++    provider = "openrouter"
++    name = "deepseek/deepseek-r1"
++    model = models.get_chat_model(
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
          provider=provider,
          name=name,
++<<<<<<< HEAD
 +        model_config=models.ModelConfig(
 +            type=models.ModelType.CHAT,
 +            provider=provider,
 +            name=name,
 +            limit_requests = 5,
 +            limit_input = 15000,
 +            limit_output = 1000,
 +        )
 +        )
 +
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++        limit_requests = 5,
++        limit_input = 15000,
++        limit_output = 1000,
++    )
++    )
++
++async def run():
++=======
+         model_config=models.ModelConfig(
+             type=models.ModelType.CHAT,
+             provider=provider,
+             name=name,
+             limit_requests=5,
+             limit_input=15000,
+             limit_output=1000,
+         ),
+     )
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
      response, reasoning = await model.unified_call(
          user_message="Tell me a joke"
      )
@@@ -27,6 -25,7 +63,16 @@@
      print("Reasoning: ", reasoning)
  
  
++<<<<<<< HEAD
 +import asyncio
 +if __name__ == "__main__":
 +    asyncio.run(run())
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++import asyncio
++asyncio.run(run())
++=======
+ if __name__ == "__main__":
+     import asyncio
+ 
+     asyncio.run(run())
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
```

## tests/test_default_prompt_budget.py
```
diff --cc tests/test_default_prompt_budget.py
index 6e4db595,e3acdd55..00000000
--- a/tests/test_default_prompt_budget.py
+++ b/tests/test_default_prompt_budget.py
@@@ -1,4 -1,4 +1,9 @@@
++<<<<<<< HEAD
 +import re
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++=======
+ import os
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
  import sys
  from pathlib import Path
  
@@@ -81,18 -65,25 +97,58 @@@ async def test_default_agent0_prompt_co
          PROJECT_ROOT / "prompts" / "agent.system.main.communication.md"
      ).read_text(encoding="utf-8")
  
++<<<<<<< HEAD
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++    # The default prompt now intentionally includes the compact always-on tool
++    # surface plus skill metadata. Keep the guardrail close to the observed
++    # budget so prompt creep remains visible without pretending this surface is
++    # a tiny single-tool prompt.
++    assert tokens.approximate_tokens(system_text) <= 10000
++=======
+     # The default prompt now intentionally includes the compact always-on tool
+     # surface plus skill metadata. Keep the guardrail close to the observed
+     # budget so prompt creep remains visible without pretending this surface is
+     # a tiny single-tool prompt.
+     assert tokens.approximate_tokens(system_text) <= 8500
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
      assert "`tool_name` must be one listed tool name" in system_text
      assert "- tool_args: key value pairs tool arguments" in system_text
++<<<<<<< HEAD
 +    assert '"*.promptinclude.md" files in workdir auto-injected' in system_text
 +    assert '"tool_name": "call_subordinate"' in system_text
 +    assert "always use specialized subordinate agents" in system_text
 +    assert "delegate them to separate subordinates" in system_text
 +    assert '"tool_name": "parallel"' in system_text
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++    assert '"tool_name": "call_subordinate"' in system_text
++    assert '"tool_name": "parallel"' in system_text
++=======
+     assert "### call_subordinate" in system_text
+     assert "### parallel" in system_text
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
      assert "Each `tool_calls` item is a normal tool request object" in system_text
++<<<<<<< HEAD
 +    assert '"reset": true' in system_text
 +    assert '"tool_name": "text_editor"' in system_text
 +    assert '"action": "read"' in system_text
 +    assert '"tool_name": "code_execution_tool"' in system_text
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++    assert '"reset": true' in system_text
++    assert '"tool_name": "text_editor"' in system_text
++    assert '"action": "read"' in system_text
++    assert '"tool_name": "code_execution_tool"' in system_text
++    assert '"tool_name": "memory_load"' in system_text
++=======
+     assert "`reset`: use json boolean `true`" in system_text
+     assert "### text_editor" in system_text
+     assert "actions: read write patch" in system_text
+     assert "### code_execution_tool" in system_text
+     assert "### exec" in system_text
+     assert "### git" in system_text
+     assert "### patch" in system_text
+     assert "Input schema for tool_args:" not in system_text
+     assert "`memory_load`: search stored memories" in system_text
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
      assert "informative but tight" in system_text
      assert "Your actual output starts with `{` and ends with `}`" in system_text
      assert "~~~json" in communication_prompt
```

## tests/test_defer_lifecycle.py
```
diff --cc tests/test_defer_lifecycle.py
index de793646,bb6b3af0..00000000
--- a/tests/test_defer_lifecycle.py
+++ b/tests/test_defer_lifecycle.py
@@@ -1,7 -1,5 +1,12 @@@
  import asyncio
++<<<<<<< HEAD
 +from pathlib import Path
 +import subprocess
 +import sys
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++=======
+ import gc
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
  import threading
  import uuid
  import weakref
```

## tests/test_docker_release_plan.py
```
diff --cc tests/test_docker_release_plan.py
index 801323fb,24cd4533..00000000
--- a/tests/test_docker_release_plan.py
+++ b/tests/test_docker_release_plan.py
@@@ -49,6 -49,7 +49,12 @@@ def test_docker_publish_workflow_tracks
      assert "workflow_dispatch:" in content
      assert "inputs:" in content
      assert "tag:" in content
++<<<<<<< HEAD
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++    assert 'ref: ${{ matrix.source_tag }}' in content
++=======
+     assert 'TARGET_TAG: ${{ matrix.source_tag }}' in content
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
      assert "SOURCE_REF_TYPE: ${{ github.ref_type }}" in content
      assert "BEFORE_SHA: ${{ github.event_name == 'push' && github.event.before || '' }}" in content
```

## tests/test_welcome_composer_static.py
```
diff --cc tests/test_welcome_composer_static.py
index e40fcb28,4480a997..00000000
--- a/tests/test_welcome_composer_static.py
+++ b/tests/test_welcome_composer_static.py
@@@ -82,6 -83,9 +83,14 @@@ def test_welcome_screen_embeds_shared_n
      assert "discovery-account-card" in discovery_cards
      assert "topHeroCards" not in discovery_cards
      assert "bottomHeroCards" not in discovery_cards
++<<<<<<< HEAD
++||||||| parent of 936713bc (feat: integrate Prolog-RLM symbolic context)
++    assert "background: var(--color-background);" in welcome
++=======
+     container_style = re.search(r"\.welcome-container\s*\{(?P<body>[^}]*)\}", welcome)
+     assert container_style is not None
+     assert "background:" not in container_style.group("body")
++>>>>>>> 936713bc (feat: integrate Prolog-RLM symbolic context)
      assert "radial-gradient" not in welcome
```
