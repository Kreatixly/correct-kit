<!-- correct-kit template: merge into the repo's existing agent/automation docs if there are
     any (check first); create this file only when there is no fitting place. Keep the table
     of the variant this repository uses and drop the other. -->

## Correction loop (correct-kit)

When agents repeat a mistake, the environment is corrected, not the agent: the highest level
that prevents it — architecture, types, lint/CI check, test, docs last — with proof (red on the
historical mistake, green today, no false alarms).

**Claude Code**

| When | What | Result |
|---|---|---|
| ongoing | automatic review on PRs; label `{{CORRECTION_LABEL}}` when you correct an agent | evidence |
| {{CRON_HUMAN}} | `correct-weekly` (read-only) | report issue `correct-report` |
| right after | `correct-act` (only with `CORRECT_ACT_ENABLED=true`) | selection as comment, draft PRs labelled `correct-auto` |
| you | merge or close | merge = approval, close = rejected |

**GitHub Copilot (team triage)**

| When | Who | What | Result |
|---|---|---|---|
| after each correction | developer | `/log-correction` in Copilot Chat | episode on the class issue |
| {{CRON_HUMAN}} | Actions | `correct-weekly` | class issues (label `correct:triage`) and one agenda (`correct-report`) |
| weekly slot | team | go through the agenda | `correct:umsetzen` or `correct:verworfen` |
| after the decision | developer | assign the class issue to Copilot, or `/correct apply <slug>` | draft PR with `Closes #n` and a proof section |
| on every PR | Actions | `correct-policy` (required) | class PRs inside the policy and with proof |
| review | team | merge or close | merge = approval; the class issue closes |

- Contract (commands, rules, evidence, limits): `{{CONTRACT}}`
- Policy: `.github/correct/correct_policy.conf`
- Decisions: {{ADR_WEEKLY_REF}}, {{ADR_AUTO_REF}}
