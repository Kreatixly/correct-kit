<!-- correct-kit template: merge into the repo's existing agent/automation docs if there are
     any (check first); create this file only when there is no fitting place. -->

## Correction loop (correct-kit)

When agents repeat a mistake, the environment is corrected, not the agent: the highest level
that prevents it — architecture, types, lint/CI check, test, docs last — with proof (red on the
historical mistake, green today, no false alarms).

| When | What | Result |
|---|---|---|
| ongoing | automatic review on PRs; label `{{CORRECTION_LABEL}}` when you correct an agent | evidence |
| {{CRON_HUMAN}} | `correct-weekly` (read-only) | report issue `correct-report` |
| right after | `correct-act` (only with `CORRECT_ACT_ENABLED=true`) | selection as comment, draft PRs labelled `correct-auto` |
| you | merge or close | merge = approval, close = rejected |

- Contract (commands, rules, evidence, limits): `{{CONTRACT}}`
- Policy for automatic PRs: `.github/correct/correct_policy.conf`
- Decisions: {{ADR_WEEKLY_REF}}, {{ADR_AUTO_REF}}
