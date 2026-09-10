# Upstream replay conflicts: v2.12 at 0b62cccbe750

## helpers/state_snapshot.py.dox.md
```
diff --cc helpers/state_snapshot.py.dox.md
index e0c4190a,97f1458b..00000000
--- a/helpers/state_snapshot.py.dox.md
+++ b/helpers/state_snapshot.py.dox.md
@@@ -42,7 -42,7 +42,12 @@@
  - Important called helpers/classes observed in the source: `dataclass`, `_build_schema_from_typeddict`, `get_origin`, `timezone.strip`, `StateRequestV1`, `localization.get_timezone`, `localization.set_timezone`, `ctxid.strip`, `_coerce_non_negative_int`, `AgentContext.get_notification_manager`, `notification_manager.output`, `_get_agent_profile_labels`, `ctxs.sort`, `tasks.sort`, `validate_snapshot_schema_v1`, `_coerce_state_request_inputs`, `super.__init__`, `get_args`, `_annotation_to_isinstance_types`, `TypeError`.
  - Snapshot building prunes non-running in-memory contexts that were previously saved but no longer have a `chat.json`, preventing stale sidebar rows after chat files are deleted outside `/chat_remove`.
  - Notification payloads use the manager's matching GUID and cursor from the same atomic read, preventing a concurrent notification from being skipped by the WebUI.
++<<<<<<< HEAD
 +- `StateRequestV1.collections_delta` is an optional, false-by-default capability. Negotiated state pushes may use `null` for both `contexts` and `tasks` when those collections are unchanged; HTTP polling and legacy WebSocket clients always receive full lists.
++||||||| parent of 0b62cccb (fix: isolate scheduler run contexts)
++=======
+ - Scheduler task rows bind only to the current or last per-occurrence run context and expose its selectable `id` separately from the durable task `uuid`, run status, and bounded last-successful-output metadata. Older successful run contexts remain ordinary inspectable chats, and legacy task contexts remain the row source until a first run exists.
++>>>>>>> 0b62cccb (fix: isolate scheduler run contexts)
  - Keep request/response, tool, or helper semantics documented here at the same time as source changes.
  
  ## Work Guidance
```
