# WIP (Work-In-Progress) Limit Policy

## Purpose
Improve flow speed and reduce mistakes by limiting parallel work.

---

## Global WIP Limits

| Stage | WIP Limit |
|-------|----------|
| Intake/Triage | 10 |
| In Analysis | 3 |
| In Execution | 5 |
| In Review/Approval | 4 |
| In Verification | 3 |
| Awaiting Release | 2 |

---

## Per-Agent WIP Limits

- Each agent: max **3 active tasks** at once
- Idle agents must assist blocked high-priority tasks before taking new ones
- No agent may start a new task while holding a task in "blocked" state without escalation

---

## WIP Overflow Rules

If WIP limit is reached:
1. Stop pulling new work
2. Identify and resolve the bottleneck
3. Escalate to Flow Integrator if blocked >2 hours
4. Do NOT bypass the limit without manager approval

---

## Enforcement

- WIP labels tracked in GitHub issues (`wip-analysis`, `wip-execution`, etc.)
- Daily ops checklist includes WIP count review
- Weekly ops review includes WIP trend analysis
- Violations flagged in `needs-escalation` label

---

## Benefits

- Reduces context switching
- Improves task completion rate
- Surfaces bottlenecks earlier
- Reduces rework from rushed execution

---

## Review Cadence

- Review WIP limits monthly or after any sprint where MTTR exceeded SLA
- Adjust limits based on team capacity and throughput data
