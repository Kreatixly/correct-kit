# {{ADR_TITLE_TRIAGE}}

<!-- correct-kit template (GitHub Copilot). Adapt to the repo's ADR format and language before
     committing; keep the decision, drop what does not apply. -->

**Status:** accepted ({{DATE}}). Stage 2 (below) is not adopted.

**Context:** Several developers work with coding agents in this repository and correct the same
mistakes independently. A rule added as prose to the agent instructions decays; a check in the
repository holds. Each correction is evidence, but it is scattered over chats, reviews and
reverts, and no single developer sees the pattern across the team.

**Decision:**

- **Locally, right away:** after correcting an agent, the developer runs `/log-correction`. It
  records the episode on the class issue (one issue per class) and says whether it is a first
  occurrence, a repeat (a rule exists, nothing enforces it) or a relapse (a check missed it).
  Rules and checks it proposes go through a reviewed pull request, never a direct commit.
- **Weekly QA run** (`correct-weekly`, {{CRON_HUMAN}}): collects evidence across all developers,
  GitHub Models groups it into classes as JSON fields, and a script renders short class issues
  and one agenda issue from fixed templates. At most 3 new class issues per run; known classes
  get one comment; relapses are reopened; classes quiet for 90 days are closed. The run writes
  issues only, never code.
- **The team decides** on the agenda: `correct:umsetzen` (then assign to the Copilot coding agent
  or apply locally) or `correct:verworfen` (closed as not planned; not proposed again without new
  evidence).
- **Proof in the pull request:** red on the historical mistake, green today, no false alarms,
  in a section of the PR description. The required check `correct-policy` holds class PRs to
  `.github/correct/correct_policy.conf` and to that section. Merging is the approval.

**Consequences:** One short team slot per week. Evidence before the decision is "the problem is
real" (two occurrences, a reproducible test case); proof that the fix holds comes with the PR.
Without `CORRECT_MODELS_ENABLED`, new classes come only from local logs.

**Stage 2 (not adopted):** the weekly run starts a Copilot coding agent task through the agent
tasks API (user token, public preview) that selects and implements the best class itself, behind
the kill switch `CORRECT_ACT_ENABLED`. Revisit when the team has merged most of the class issues
it accepted over several weeks — the selection is then shown to be trustworthy.
