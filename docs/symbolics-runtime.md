# A0 Symbolics Runtime

This page documents the repository-native runtime for `a0-symbolics`. Use it
when you cloned this repository and want the bundled Symbolics stack rather
than a stock upstream Agent Zero image.

The authoritative launcher is `scripts/symbolics`. The small wrapper scripts
under `scripts/` delegate to it.

## Start The Runtime

From the repository root:

```bash
./scripts/up
```

That is equivalent to:

```bash
./scripts/symbolics up
```

The launcher:

1. checks Docker and the Compose configuration;
2. uses `docker/symbolics/compose.yml` when present, otherwise falls back to
   `docker/symbolics/compose.yml.example`;
3. creates the default external Nix and user-data volumes when the example
   compose file is used;
4. builds the local `a0-symbolics` image with a bounded build-memory setting;
5. preserves a conflicting pre-Compose `agent-zero` container by stopping and
   renaming it instead of deleting it;
6. starts the Compose service and waits for it to become healthy;
7. runs the Symbolics verification suite before reporting success.

The example compose file publishes the Web UI on host port `50080`, but local
`compose.yml` overrides may choose another port. Use `./scripts/status` rather
than assuming a fixed URL.

## Runtime Commands

| Command | Purpose |
| --- | --- |
| `./scripts/up` | Build, start, wait for health, and verify. |
| `./scripts/down` | Stop and remove the Compose containers. |
| `./scripts/logs` | Follow the Agent Zero container logs. |
| `./scripts/status` | Show Compose state and the currently published URL. |
| `./scripts/update` | Rebuild with pulled base layers, start, and verify. |
| `./scripts/verify` | Run the current health and Symbolics smoke checks. |

You can call the dispatcher directly as `./scripts/symbolics <command>` if you
prefer one entry point.

## Configuration

The launcher recognizes these repository-level controls:

| Setting | Default | Meaning |
| --- | --- | --- |
| `A0_SYMBOLICS_COMPOSE_FILE` | local `compose.yml`, else `compose.yml.example` | Explicit Compose file. |
| `A0_SYMBOLICS_PROJECT` | `a0-symbolics` | Docker Compose project name. |
| `A0_SYMBOLICS_BUILD_MEMORY` | `8g` | Memory limit passed to `docker compose build`. |
| `.env` | optional | Loaded by Docker Compose when present at the repository root. |

The example Compose configuration also exposes runtime settings including
`PROLOG_RLM_ENABLED`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and
`EXTENSIONS_LOG`. Put host-specific ports, mounts, devices, and environment
changes in `docker/symbolics/compose.yml`; that file is intentionally local.

With the example configuration, persistent volumes are:

- `a0-symbolics-nix` mounted at `/nix`;
- `a0-symbolics-usr` mounted at `/a0/usr`.

Important runtime paths under the user-data root include:

- `/a0/usr/projects`;
- `/a0/usr/workdir`;
- `/a0/usr/chats`;
- `/a0/usr/uploads`.

## What `verify` Proves

`./scripts/verify` checks the current Compose configuration and running
container, then verifies:

- the container reports healthy;
- the Web UI root responds;
- `GET /api/health` responds;
- `/a0/usr/projects` and `/a0/usr/workdir` exist;
- SWI-Prolog is installed and executable;
- `/opt/a0-symbolics/smoke.sh /a0` succeeds;
- the smoke result exists at `/run/a0-symbolics/smoke.json`.

The container healthcheck independently verifies the smoke result, SWI-Prolog,
the Web UI, `/api/health`, and Supervisor-managed processes.

## External API Route Shape

`helpers/api.py` registers a single dispatcher at:

```text
/api/<path>
```

For built-in handlers, the filename below `api/` becomes `<path>`. Examples:

| Source handler | HTTP route |
| --- | --- |
| `api/health.py` | `GET/POST /api/health` |
| `api/api_message.py` | `POST /api/api_message` |
| `api/api_log_get.py` | `GET/POST /api/api_log_get` |
| `api/api_terminate_chat.py` | `POST /api/api_terminate_chat` |
| `api/api_reset_chat.py` | `POST /api/api_reset_chat` |
| `api/api_files_get.py` | `POST /api/api_files_get` |

The external chat/file endpoints require `X-API-KEY`; `/api/health` does not.
Do not infer a root-level route such as `/api_message` from a handler filename.

Plugin handlers use the same dispatcher. A plugin handler at
`plugins/<name>/api/<handler>.py` is addressed as
`/api/plugins/<name>/<handler>`.

## Prolog Components

The Symbolics image includes SWI-Prolog and verifies it during startup. The two
main bundled symbolic integration surfaces are:

- [Prolog-RLM Runtime](../plugins/_prolog_rlm/README.md), the typed bridge to
  the Prolog-RLM runtime;
- [Prolog Context Compiler](../plugins/_prolog_context_compiler/README.md),
  which compiles the per-turn visible tool, MCP, and skill projection.

## Lower-Level Launcher

The repository root also contains `launch.sh` with `build`, `up`, and `down`
commands. Unlike `scripts/symbolics`, it requires
`docker/symbolics/compose.yml` to exist before it runs and does not provide the
same `status`, `logs`, `update`, or `verify` workflow.

For normal local operation, prefer `scripts/symbolics` or its wrapper scripts.

## Source Of Truth

When this page and the implementation disagree, follow the implementation and
update this page in the same change. The relevant source files are:

- `scripts/symbolics` for lifecycle and verification behavior;
- `docker/symbolics/compose.yml.example` for the default local Compose shape;
- `docker/symbolics/healthcheck.sh` for container health;
- `helpers/api.py` for HTTP dispatch;
- the individual files under `api/` for endpoint methods, payloads, and
  authentication requirements.
