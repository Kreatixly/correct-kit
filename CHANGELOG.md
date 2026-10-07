# Changelog

## 0.2.0

- Copilot: `correct-policy` enforced every Copilot coding agent PR (branch `copilot/`), so ordinary
  feature PRs failed the required check. It now runs on every PR and enforces the policy only on
  PRs that close a correction issue or carry `correct-auto`.
- Weekly workflows (Claude and Copilot) assigned the report to `github.repository_owner`, which
  fails for organization repositories, and then created no issue at all. Assignee is now the
  optional repo variable `CORRECT_REPORT_ASSIGNEE`. Copilot weekly gets the fallback issue on failure.
- Runner label is a placeholder (`RUNS_ON`) in every workflow template; GitHub Models gets a
  smaller input (24 KB) than the issue.
- `correct` (after pstack by poteto): new mode `/correct log` right after a correction (first /
  repeat / relapse against the rule table); prose rules shrink once a check enforces them;
  ratchet for widespread patterns; exceptions on the line with reason, expiry and approver, never
  added by agents (policy `forbid`); hollow tests; a check must run in the verify commands;
  delivery order by frequency first.
- Copilot: prompt file `log-correction`, instructions point to it; prompt front matter `agent:`.
- Setup: enterprise checklist (allowed actions, policies, runners, data for GitHub Models).
- Skill `recall` renamed to `glean` (no clash with pstack's `/recall`, which restores working
  context). Report folder `.claude/glean/`. Existing installs: rename `.claude/skills/recall/`,
  `.claude/recall/` and the contract lines that mention it.

## 0.1.0

- Skills `correct`, `architect`, `recall` (from LernSnap, project-neutral) and `correct-setup`.
- Claude templates: `correct-weekly`, `correct-act`, `claude-code-review`; policy script with config.
- Copilot templates: weekly evidence digest (optional GitHub Models), `correct-policy` check,
  prompt files, instructions, `copilot-setup-steps`.
- ADR, docs and guard templates; LernSnap example; self-test.
