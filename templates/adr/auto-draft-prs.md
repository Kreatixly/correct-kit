# {{ADR_TITLE_AUTO}}

<!-- correct-kit template. Adapt to the repo's ADR format and language before committing. -->

**Status:** trial until {{TRIAL_END}}. Extends {{ADR_WEEKLY_REF}}.

**Context:** The weekly report proposes checks (architecture tests, lint rules, doc checks).
Most touch no product behaviour. The owner does not want to handle each one by hand: an agent
should decide whether a class is worth it and present it as a draft pull request.

**Decision:**

- A follow-up workflow (`correct-act`) starts after the report, only when the repository
  variable `CORRECT_ACT_ENABLED` is `true` (kill switch), or by hand.
- **Select** (model, read-only): per class `auto`, `owner` or `skip`, posted on the report
  issue. At most {{MAX_AUTO}} `auto` per run.
- **Implement** (model, read token, toolchain available): `/correct apply` with its proof.
  It does not commit, push or open anything.
- **Limits enforced by the workflow** (`.github/correct/correct_policy.sh` with
  `correct_policy.conf`; gate job with `contents: read`, publish job with write rights but
  without running repository code):
  - only allowed paths ({{ALLOWED_SUMMARY}}); never {{DENIED_SUMMARY}};
  - a check must be added or extended; docs alone are not a fix;
  - no deleted or renamed files; tests never weakened; baselines only shrink;
  - size limits; patterns of the hard rules rejected outside tests;
  - all verify commands green in the workflow.
- **Always a draft PR**, label `correct-auto`. No auto-merge. **Merging is the approval.**
  Closing without merge means rejected; the next report does not propose the same fix
  without new evidence.
- Workflow files are out of scope (the workflow token cannot push them); such classes go to
  the owner.

**Consequences:** A false alarm now costs a PR instead of a line in a report; hence the
selection step, the proof in every PR and the limit per run. At the end of the trial the owner
counts merged, rejected and broken PRs; without a clear majority of merged PRs the workflow is
removed and this decision withdrawn.
