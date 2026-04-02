# AI Collaboration Guideline

## Purpose

This document defines a cooperation clause for automated agents, tools, and AI assistants that operate on or with this repository. Its intent is to encourage transparent, verifiable, and coordinated multi-agent workflows that prioritize safety, correctness, and auditability. Agents are expected to share outputs, validate schemas, coordinate responsibilities, and escalate to human reviewers when needed.

## AI Collaboration Clause

When multiple automated agents, tools, or AI assistants are involved in processing a transcript, generating artifacts, or performing repository actions, each agent MUST:

- **Share relevant intermediate outputs** (context, decisions, partial JSON, logs) in the agreed format so other agents can consume and validate them.
- **Validate and cross-check structured outputs** against the shared JSON schema or other canonical validators before marking outputs as final.
- **If uncertain or a schema failure occurs**, explicitly call out the specific field(s), include the offending data snippet, and suggest corrective steps or remediation code.
- **Coordinate responsibilities** by assigning clearly-named roles when multiple agents are present (for example: `schema-validator`, `prompt-instancer`, `ci-checker`, `doc-writer`).
- **Prioritize safety, correctness, and non-duplication**:
  - Do not overwrite another agent's verified output without recording the reason and linking to the prior artifact.
  - If corrective edits are necessary, produce a new artifact and include a changelog entry describing why the change was made.
- **Produce auditable logs** of inter-agent actions and decisions, including timestamps, role names, and brief rationale for significant changes.

## Escalation and Human Review

If agents cannot reach consensus on a schema failure or a safety-related decision, escalate to a human reviewer by opening an issue or PR that includes:

- A concise summary of the disagreement.
- The specific fields or artifacts in question.
- Suggested corrective actions and the agent(s) that proposed them.

## Reviewer Checklist

For PRs that introduce or modify automated agent behavior, reviewers should confirm:

- [ ] `docs/ai-collaboration.md` is present and the clause is clear and up to date.
- [ ] CI runs include the schema checks referenced by automated agents.
- [ ] Agents know where to write intermediate outputs and logs (paths, artifact names).
- [ ] Any new agents or workflows are documented with role names and expected responsibilities.
- [ ] The repository's security policy is followed and agents do not expose secrets in logs.

---

*Last updated: 2026-03-23*
