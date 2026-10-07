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
- Copilot team triage: the weekly run turns evidence into class issues (one class = one wrong
  move = one PR, at most 3 new per run) and one agenda issue. GitHub Models returns JSON fields
  only; `correct_issues.py` validates, shortens and renders them from fixed templates, folds in
  local `/correct log` episodes, reopens relapses, keeps rejected classes closed, closes quiet
  ones, and reports drift (rules added to agent instructions without a check). Raw evidence goes
  to the run summary. Tests: `tests/test_correct_issues.py`.
- Proof check: `check_proof.sh` in `correct-policy` requires a proof section (red / green /
  false alarms) in the description of class PRs.
- `/correct log` writes episodes as comments with a marker and leaves the lifecycle to the
  weekly run; rules and checks only through reviewed PRs. ADR template `team-triage.md` (stage 2,
  agent task API, documented, not adopted). README with flow diagrams and who-does-what tables.
- Skill `recall` renamed to `glean` (no clash with pstack's `/recall`, which restores working
  context). Report folder `.claude/glean/`. Existing installs: rename `.claude/skills/recall/`,
  `.claude/recall/` and the contract lines that mention it.

## 0.1.0

- Skills `correct`, `architect`, `recall` (from LernSnap, project-neutral) and `correct-setup`.
- Claude templates: `correct-weekly`, `correct-act`, `claude-code-review`; policy script with config.
- Copilot templates: weekly evidence digest (optional GitHub Models), `correct-policy` check,
  prompt files, instructions, `copilot-setup-steps`.
- ADR, docs and guard templates; LernSnap example; self-test.
