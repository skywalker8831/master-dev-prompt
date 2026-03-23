# Branch Protection Checklist

Use this checklist on the default branch (and any release branches).

## Required Settings
- [ ] Require a pull request before merging
- [ ] Require approvals: minimum **3**
- [ ] Require review from Code Owners
- [ ] Dismiss stale approvals when new commits are pushed
- [ ] Require conversation resolution before merge
- [ ] Require status checks to pass before merging
- [ ] Restrict who can push to matching branches
- [ ] Block force pushes
- [ ] Block branch deletion
- [ ] Apply protections to administrators

## Required Status Checks
- [ ] Approval Chain Gate (Strict)
- [ ] CI / tests
- [ ] Lint / formatting
- [ ] Security scan (if enabled)
- [ ] Schema/config validation (if enabled)

## Approval Chain Policy
Must pass in order:
1. Analyst A approval
2. Analyst B approval
3. Final Owner approval

If missing or wrong order:
- [ ] Block merge
- [ ] Add `needs-escalation` label
- [ ] Remove `ready-to-execute` label

## Recommended Extras
- [ ] Require signed commits
- [ ] Require linear history
- [ ] Auto-delete head branches after merge
- [ ] Lock branch during incident response windows if needed