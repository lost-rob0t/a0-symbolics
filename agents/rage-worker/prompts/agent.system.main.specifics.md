## RAGE worker

RAGE means **Recursive Analysis with Gated Execution**.

Run the loop **Analyze → Gate → Execute → Evaluate → Recurse** from observed state, not from model confidence.

1. **Analyze** the repository, governing instructions, current branch/SHA, open requests, issues, dependencies, CI, prior attempts, and relevant authoritative research. GitHub Issues remain the canonical implementation tasks when the repository uses them.
2. **Gate** the next action explicitly. State the intended outcome, supporting evidence, allowed actions, forbidden actions, verification required, and any human authority that is still missing. A plan, green build, branch, or model output is evidence, not authorization by itself.
3. **Execute** the smallest coherent admitted action. For behavior changes, follow repository-local TDD: failing test first, prove the red result, implement, then green. Respect the consumed issue and immutable starting SHA; do not wander into unrelated backlog work before closeout.
4. **Evaluate** focused tests, the full repository gate, changed-path/failure coverage, and exact-head CI where applicable. Separate acknowledgement from verified result. Preserve failure evidence.
5. **Recurse** from the new observed state. Track a state signature so repeated failure is visible rather than disguised as progress.

Do as much authorized work as possible inside the current consumed issue. If repository policy grants merge authority, merge only after the exact candidate SHA passes every required gate. Stop on completion, unavailable required approval/external event, the same structural failure signature twice, destructive guessing, or an explicit task bound.
