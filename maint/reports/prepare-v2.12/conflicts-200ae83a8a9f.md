# Upstream replay conflicts: v2.12 at 200ae83a8a9f

## webui/components/sidebar/AGENTS.md
```
diff --cc webui/components/sidebar/AGENTS.md
index 6d109865,b62c29c4..00000000
--- a/webui/components/sidebar/AGENTS.md
+++ b/webui/components/sidebar/AGENTS.md
@@@ -32,9 -32,7 +32,14 @@@
  - The utility-message preference controls both individual utility steps and utility-only process-group chrome so hidden utility runs cannot leave empty headers in the transcript.
  - Chat deletion removes the sidebar row optimistically in the same render batch as fallback selection. Keep successful local deletion tombstones for the page session so out-of-order poll or push snapshots cannot reinsert rows; restore the row and clear its tombstone if the delete request fails.
  - Chat selection must synchronize the sidebar store even when the low-level context has already switched to the requested ID.
++<<<<<<< HEAD
 +- Context snapshots preserve the Alpine contexts-array and row identities while their order is stable, updating changed row metadata in place so streaming log counters do not reconcile the whole chat list. Additions, removals, reordering, and deletion tombstones must still replace the visible list; selection and parent-expansion synchronization must not publish unchanged state.
 +
 +- Preserve `canvas:<surface-id>` visibility entries even when a plugin is absent, so later registration restores its saved choice.
++||||||| parent of 200ae83a (feat(webui): searchable chats and projects lists)
++=======
+ - The chat list owns a client-side search box (shown when more than five chats exist or while searching) that filters chat names and project labels case-insensitively; during search, matching children stay reachable and their parents remain visible.
++>>>>>>> 200ae83a (feat(webui): searchable chats and projects lists)
  
  ## Work Guidance
```
