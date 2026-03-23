# AI Collaboration Guideline

This document defines how automated agents and AI assistants operating in this repository should work together. The goal is to encourage agents to share outputs, validate schemas, coordinate responsibilities, and escalate unresolved issues to human reviewers when needed.

## Cooperation Clause

When multiple automated agents, tools, or AI assistants are involved in processing a transcript or producing artifacts, each agent **MUST**:

- **Share relevant intermediate outputs** (context, decisions, partial JSON) in the agreed format so that downstream agents have the context they need.
- **Validate and cross-check structured outputs** against the shared JSON schema before passing results to the next stage or committing artifacts.
- **Call out schema failures explicitly**: if uncertain or a schema validation failure occurs, identify the specific field that failed and suggest corrective steps before proceeding.
- **Coordinate responsibilities clearly** when multiple agents are present — assign well-named roles (e.g., `schema-validator`, `prompt-instancer`, `ci-checker`) so there is no ambiguity about which agent owns which step.
- **Prioritize safety, correctness, and non-duplication**: do not overwrite another agent's verified output without recording the reason in a log or commit message.
- **Produce auditable logs** of inter-agent actions and decisions so that human reviewers can reconstruct what happened and why.

If an issue cannot be resolved between agents (e.g., conflicting schema interpretations, unrecoverable validation errors), agents **must escalate to a human reviewer** rather than silently continuing or discarding work.

## PR Reviewer Checklist

Before merging any PR that involves automated agent output or inter-agent coordination, reviewers should confirm:

- [ ] The new or modified output files pass `make ci` (schema validation and test suite).
- [ ] All structured JSON outputs are validated against the shared schema in `master_dev_runtime.py`.
- [ ] Agent responsibilities are clearly named in commit messages or PR descriptions when multiple agents contributed.
- [ ] Any schema failures discovered during the PR are documented and resolved (not silently skipped).
- [ ] No previously verified agent output has been overwritten without an explanation in the commit history.
- [ ] Auditable logs or notes are present if inter-agent coordination occurred.

---

*Last updated: 2026-03-23*
