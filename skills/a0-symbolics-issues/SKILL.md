---
name: a0-symbolics-issues
description: Report, triage, or cross-link a0-symbolics and prolog-rlm bugs in the correct GitHub issue tracker.
triggers:
  - "file an issue"
  - "report a bug"
  - "report regression"
  - "github issue"
  - "a0-symbolics issue"
  - "prolog-rlm issue"
allowed_tools:
  - code_execution_tool
---

# a0-symbolics Issue Reporting

File issues for the a0-symbolics integration project and the prolog-rlm runtime
in the correct repository, with reproducible evidence. Both repositories use
GitHub issues; `gh` must be authenticated in the runtime environment.

## Routing

| Defect domain | Repository |
| --- | --- |
| Agent Zero plugin (`plugins/_prolog_rlm`), prompt budgets, bridge glue, tool adapters, WebUI, nix packaging, flake pin, a0 tests, docker | `lost-rob0t/a0-symbolics` |
| Prolog runtime itself (`prolog/*.pl`, `rlm_direct/4`, context compilation, provider turns, preflight faults, worker protocol, runtime tests) reproducible without Agent Zero | `lost-rob0t/prolog-rlm` |

Rules:

- Reproduce against the standalone runtime checkout when the defect is inside
  prolog-rlm; otherwise file in a0-symbolics.
- If ownership is unclear, file in a0-symbolics and cross-reference the
  prolog-rlm issue after it exists.
- Never split one defect across both trackers; pick one and link from the other
  only as context.

## Preconditions

- Search existing issues before filing (see examples).
- Verify the a0-symbolics checkout is current; the flake pins an exact
  prolog-rlm revision in `flake.nix`/`flake.lock`. Record that revision as part
  of the environment. In the container the application root is `/a0`.
- prolog-rlm checkouts may carry remotes for the GitHub upstream and a private
  Forgejo mirror; issues always go to the GitHub upstream, never the mirror.

## Workflow

1. Search existing issues before filing:

   ```sh
   gh issue list -R lost-rob0t/a0-symbolics --state open --search "<keywords>"
   gh issue list -R lost-rob0t/prolog-rlm --state open --search "<keywords>"
   ```

2. Reproduce with the narrowest meaningful verification. For pytest under the
   nix devshell, export `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1`; without
   them OpenBLAS aborts silently under the 4 GB `ulimit -v` cap and exits 1
   with no output.
3. Record evidence: repository, branch, commit SHA, flake-pinned prolog-rlm
   revision, exact command, and the red/green result.
4. File the issue with `gh issue create -R <repo>` using the template below.
5. Cross-link related issues or PRs, then report the issue URL.

## Issue template

```markdown
## Summary
<one paragraph: what is broken and the impact>

## Environment
- Repo: <owner/repo>@<branch> <commit-sha>
- prolog-rlm pin (a0-symbolics flake): <rev or "not applicable">
- Command: <exact command>

## Repro
<numbered steps that an agent can run autonomously>

## Expected / Actual
<expected behavior> / <actual behavior, include exact error text>

## Evidence
<test output, assertion diff, or log excerpt>
```

## Examples

```sh
# a0-symbolics integration defect (prompt budget assertion)
gh issue create -R lost-rob0t/a0-symbolics \
  --title "test_default_prompt_budget: '### exec' assertion fails on main" \
  --body-file issue.md

# prolog-rlm runtime defect (rlm_direct preflight fault handling)
gh issue create -R lost-rob0t/prolog-rlm \
  --title "rlm_direct/4 drops resolved bindings on recoverable preflight fault" \
  --body-file issue.md
```