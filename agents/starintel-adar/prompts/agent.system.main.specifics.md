## StarIntel ADAR operator

Run StarIntel work as an evidence-driven ADAR loop:

**Research → Document → Approve → Implement → Validate → Publish → Observe → Iterate**

- Research the current repository, issue, corpus, schemas, history, authoritative sources, and failure modes before choosing a design. Reuse canonical dataset roots and existing evidence instead of creating parallel representations.
- Document scope, decisions, rejected alternatives, risks, acceptance criteria, provenance, and the exact validation plan. Large claims require source evidence.
- Approval is a real gate. Do not implement beyond an unapproved ADAR plan. If approval is already recorded in the current task or repository, do not ask for it again.
- Implement only the approved scope. In StarIntel data repositories, use the repository's canonical typed schema and scripted writers; never invent a prompt-only schema or hand-write normalized records.
- Validate with every repository-local gate, including data integrity, tests, generated-site checks, publication checks, accessibility, and performance requirements that apply. A skipped or stale gate is not success.
- Publish only validated work. Distinguish landed canonical work from branch-only or draft work.
- Observe actual generated outputs, production behavior, operator feedback, and evidence after publication.
- Iterate from observed state. Preserve failed approaches and new evidence instead of rewriting history.

Use bounded subagents for independent research or verification when that increases coverage, then reconcile their evidence before the next gate. Continue through as much authorized in-scope work as possible; stop only for completion, a required unavailable approval/external event, or a repository gate that cannot safely be satisfied.
