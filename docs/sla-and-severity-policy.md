# SLA and Severity Policy

## Purpose
Define response and resolution times for repository tasks based on business impact.

---

## Severity Levels

| Level | Name | Description | Example |
|-------|------|-------------|---------|
| **P1** | Critical | Core flow broken, security breach, or total system outage. | Workflow failing for all users, leaked API key. |
| **P2** | High | Significant feature broken, no workaround, or high-risk dependency. | Main integration failing, high-severity CVE. |
| **P3** | Medium | Minor feature issue or major documentation gap. | Incorrect UI label, missing setup step in INSTALL.md. |
| **P4** | Low | Cosmetic improvements, non-breaking suggestions, or routine cleanup. | Typo in comments, refactoring for better readability. |

---

## Target Response & Resolution Times (SLAs)

| Severity | Response (Triage) | Resolution (Fix) |
|----------|-------------------|------------------|
| **P1** | < 15 minutes | < 2 hours |
| **P2** | < 1 hour | < 8 hours |
| **P3** | < 4 hours | < 24 hours |
| **P4** | < 24 hours | < 72 hours |

---

## Escalation Policy

- **P1/P2 Breach:** Notify Flow Integrator and Final Owner immediately via alert labels.
- **P3/P4 Stale:** If P3/P4 exceeds resolution time, auto-tag with `needs-escalation`.

---

## Triage Workflow

1.  Identify new issue.
2.  Assign Severity Label (`severity-p1`, `severity-p2`, etc.).
3.  Assign Owner.
4.  Set Deadline based on SLA.
5.  Move to `wip-analysis`.

---

## Review Cadence

- Review SLA performance in **Weekly Ops Review**.
- Adjust targets monthly based on system maturity.
