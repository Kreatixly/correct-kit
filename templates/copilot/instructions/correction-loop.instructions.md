---
applyTo: "**"
---

# Correction loop (correct-kit)

- Project rules, verify commands and limits live in `.github/agent-contract.md`. Read it before
  changing code that other modules call, and run its verify commands before calling work done.
- When the same mistake comes back, fix the environment, not the instructions: prefer, in this
  order, architecture, types, a lint/CI check, a test; docs only for judgement calls.
- Never weaken, skip or delete a test or a baseline to get green.
- Pull requests that implement a correction class carry the label `correct-auto` and must pass
  the `correct-policy` check.
