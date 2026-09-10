# Upstream replay conflicts: v2.12 at 7c057880f037

## skills/AGENTS.md
```
diff --cc skills/AGENTS.md
index 4113f9a0,cea374b9..00000000
--- a/skills/AGENTS.md
+++ b/skills/AGENTS.md
@@@ -37,9 -35,15 +37,21 @@@ Direct child DOX files
  
  | Child | Scope |
  | --- | --- |
 -| [a0-contribute-plugin/AGENTS.md](a0-contribute-plugin/AGENTS.md) | Publishing plugins to the community Plugin Index. |
  | [a0-create-agent/AGENTS.md](a0-create-agent/AGENTS.md) | Creating Agent Zero agent profiles. |
 -| [a0-create-plugin/AGENTS.md](a0-create-plugin/AGENTS.md) | Creating or extending Agent Zero plugins. |
 -| [a0-debug-plugin/AGENTS.md](a0-debug-plugin/AGENTS.md) | Diagnosing plugin loading, API, frontend, and extension issues. |
 +| [a0-create-plugin/AGENTS.md](a0-create-plugin/AGENTS.md) | Plugin authoring entrypoint with implementation, UI, review, and contribution references. |
  | [a0-development/AGENTS.md](a0-development/AGENTS.md) | Broad Agent Zero framework development guidance. |
++<<<<<<< HEAD
 +| [a0-manage-plugin/AGENTS.md](a0-manage-plugin/AGENTS.md) | Plugin Index discovery/recommendations and lifecycle operations. |
++||||||| parent of 7c057880 (fix: route harness direct/complete through the context compiler)
++| [a0-manage-plugin/AGENTS.md](a0-manage-plugin/AGENTS.md) | Plugin install, update, scan, enable, disable, and removal workflows. |
++| [a0-plugin-router/AGENTS.md](a0-plugin-router/AGENTS.md) | Routing plugin-related user requests to specialist skills. |
++| [a0-review-plugin/AGENTS.md](a0-review-plugin/AGENTS.md) | Full plugin audit workflow and checklists. |
++=======
+ | [a0-manage-plugin/AGENTS.md](a0-manage-plugin/AGENTS.md) | Plugin install, update, scan, enable, disable, and removal workflows. |
+ | [a0-plugin-router/AGENTS.md](a0-plugin-router/AGENTS.md) | Routing plugin-related user requests to specialist skills. |
+ | [a0-review-plugin/AGENTS.md](a0-review-plugin/AGENTS.md) | Full plugin audit workflow and checklists. |
+ | [a0-symbolics-issues/](a0-symbolics-issues) | Issue routing and filing for a0-symbolics and prolog-rlm trackers. |
++>>>>>>> 7c057880 (fix: route harness direct/complete through the context compiler)
  | [build-skill/AGENTS.md](build-skill/AGENTS.md) | Building and improving Agent Zero skills. |
+ | [debug-io/](debug-io) | Debugging Prolog-RLM provider HTTP IO, attribution, and OpenRouter generation data. |
  | [scheduled-tasks/AGENTS.md](scheduled-tasks/AGENTS.md) | Managing scheduled, planned, and adhoc tasks. |
```
