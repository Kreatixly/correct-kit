---
description: Find mistakes agents keep making here and fix the environment (correct-kit). Modes - analyse (plan only), apply <class>, or log.
agent: agent
---

Read `.github/correct-kit/skills/correct/SKILL.md` and `.github/agent-contract.md` and follow
them. Mode: ${input:mode:analyse, apply <class-slug> or log}.

- For `analyse`: use the newest open issue labelled `correct-report` as the evidence digest
  (and everything the contract lists under Evidence sources). Write the plan into a comment on
  that issue only if the owner asks; otherwise answer here.
- For `apply <class>`: implement exactly one class as a draft pull request, within
  `.github/correct/correct_policy.conf`, with the proof from step 4 of the skill (red on the
  past, green today, no noise, runs in the verify commands) in the PR description, and
  `Closes #<n>` for the class issue. Never weaken a test.
- For `log`: as `.github/prompts/log-correction.prompt.md`.
