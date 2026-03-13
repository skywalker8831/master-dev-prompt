# Repository Inventory

This file is the source of truth for repository roles in the Master Developer Prompt Kit family.

## Current classification

| Repository | Role | Visibility | Recommended description | Notes |
|---|---|---|---|---|
| `skywalker8831/master-dev-prompt` | template | public | Canonical template/source for the Master Developer Prompt Kit repository family. | This repo is marked as a GitHub template repository and should remain the upstream source for shared prompt, validator, and baseline workflow changes. |
| `skywalker8831/master` | primary working repo | public or internal-to-owner | Primary active working derivative built from `master-dev-prompt`. | Use this repo for ongoing product/workflow development that intentionally diverges from the base template. |
| `skywalker8831/op2` | variant | public or internal-to-owner | Named variant of `master-dev-prompt` for a specific workflow or operational branch. | Keep only if it serves a distinct purpose. Future variants should use purpose-based names instead of vague labels like `op2`. |
| `skywalker8888/effective-journey` | experiment | private | Private experiment derived from the `master-dev-prompt` template family. | Treat as a private clone/experiment unless it graduates into a maintained variant or archive. |
| `skywalker8888/master888` | experiment | private | Private experiment derived from the `master-dev-prompt` template family. | Treat as a private clone/experiment unless it graduates into a maintained variant or archive. |
| `skywalker8888/effective-umbrella` | experiment | private | Private experiment derived from the `master-dev-prompt` template family. | Treat as a private clone/experiment unless it graduates into a maintained variant or archive. |

## Role definitions

- **template** — the canonical source repository used to generate or seed related repos.
- **primary working repo** — the main actively developed derivative where day-to-day product or workflow evolution happens.
- **variant** — a maintained repo that intentionally differs from the primary working repo for a specific use case.
- **experiment** — a private clone, prototype, or short-lived branch repo that should not be treated as canonical.
- **archive** — an inactive repo retained only for reference or historical traceability.

There are currently **no known archive repos** in this repository family. If a repo becomes inactive, update this file and its GitHub description to classify it as an archive.

## Naming and ownership guidance

1. Keep exactly one canonical template/source repo for this family: `skywalker8831/master-dev-prompt`.
2. Keep exactly one primary working repo at a time. Today that role belongs to `skywalker8831/master`.
3. Use the `skywalker8831` namespace for canonical, shared, or team-owned repositories.
4. Use personal namespaces such as `skywalker8888` only for private experiments, evaluation clones, or short-lived sandboxes.
5. Name variants by purpose, not by vague labels. Prefer names like `master-ops-variant` or `master-<use-case>` instead of opaque names like `op2`.
6. When a repo changes role, update both this file and the repo’s GitHub description in the same change.

## Maintenance rules

- Shared prompt/schema/baseline validation changes should start in `skywalker8831/master-dev-prompt`.
- Productized or fast-moving operational changes can land first in `skywalker8831/master` when they are intentionally derivative-specific.
- Experimental repos should either be promoted to `variant`, folded back into the canonical/primary repos, or marked as `archive` once inactive.
