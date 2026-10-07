---
applyTo: "**"
---

# Correction loop (correct-kit)

- Project rules, verify commands and limits live in `.github/agent-contract.md`. Read it before
  changing code that other modules call, and run its verify commands before calling work done.
- When the user corrects you (rejects what you did and says what was wrong), fix it, then run
  `/log-correction`: it checks the rule table and records the episode in the class issue. A rule
  that already existed without anything enforcing it is a repeat; propose a check, not more text.
- When the same mistake comes back, fix the environment, not the instructions: prefer, in this
  order, architecture, types, a lint/CI check, a test; docs only for judgement calls.
- Never weaken, skip or delete a test or a baseline to get green, and never add an exception to
  a check on your own.
- A pull request that implements a correction class links its issue (`Closes #<n>`); the
  required `correct-policy` check then keeps it inside `.github/correct/correct_policy.conf`.
