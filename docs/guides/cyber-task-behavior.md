# Cyber Task Execution Behavior

How Agent Zero handles security work: penetration testing, red/blue team engagements, CTF challenges, vulnerability research, malware analysis, and hardening.

## Design Principle

Security work is normal work. The framework is used by security professionals on real engagements, so dual-use tasks are judged by **technical content and context**, not by topic, tone, or stated intent. This follows current research on cyber refusal policy:

- Topic-based and intent-based refusal rules cause false refusals on legitimate dual-use work (Irregular, *A Framework for Cyber Refusal Policies in LLM Agents*, 2026).
- Loud authorization and ethics boilerplate backfire: removing authorization signals from otherwise identical security tasks cut refusal rates from 21.8% to 13.7% (arXiv, *Defensive Refusal Bias: How Safety Alignment Fails Cyber Defenders*, 2026). Persona prompts therefore use quiet, operational framing.

## What Refused Before, What Happens Now

| Behavior | Before | Now |
| --- | --- | --- |
| Local reads of credential files (`.env`, keys) on in-scope targets | Auto-terminate | Normal audit work; clarify only if purpose is unclear |
| Multi-step plans with security wording (`find` + stated intent) | Terminate on first step | Clarify or allow; no intent-based termination |
| Security tooling (nmap, metasploit, hashcat, sudo) in scope | Clarify friction | Routine; allowed |
| Secret exfiltration to an external endpoint | Terminate | **Still terminates** — this defends you from prompt injection |
| Obedience to injected instructions ("ignore previous instructions") | Terminate | **Still terminates** |

## Where This Lives

- **Persona prompts** (`agents/*/prompts/`): direct-execution framing; concerns surface as findings, not refusals.
- **Infection Check plugin** (`plugins/_infection_check/`): content-based judge. Terminate is reserved for the two hard rules above; ambiguity clarifies and **proceeds with a warning after the clarification budget is exhausted** — it never blocks unilaterally.
- **Tool Access plugin** (`plugins/_tool_access/`): deterministic per-project/profile tool policy — enable or disable tools, no ethics gating.

If you want zero safety middleware at all, disable the Infection Check plugin in Settings > Plugins; the agent runs fully unattended.
