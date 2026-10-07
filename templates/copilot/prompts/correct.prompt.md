---
description: Find mistakes agents keep making here and fix the environment (correct-kit). Modes - analyse (plan only), apply <class>, or log.
agent: agent
---

Read `.github/correct-kit/skills/correct/SKILL.md` and `.github/agent-contract.md` and follow
them. Mode: ${input:mode:analyse, apply <class-slug> or log}.

- For `analyse`: a deeper look than the weekly run, for when the team wants one. Use the open
  agenda (label `correct-report`), the class issues and everything the contract lists under
  Evidence sources. Answer here; write nothing to the tracker unless asked.
- For `apply <class>`: only a class issue labelled `correct:umsetzen`. Implement exactly one
  class as a draft pull request, meeting the issue's acceptance criteria, within
  `.github/correct/correct_policy.conf`, with the proof from step 4 of the skill (red on the
  past, green today, no noise, runs in the verify commands) in the PR description, and
  `Closes #<n>` for the class issue. Never weaken a test.
- For `log`: as `.github/prompts/log-correction.prompt.md`.
