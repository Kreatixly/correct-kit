---
description: Record the correction that just happened in this chat as evidence for its mistake class (correct-kit).
agent: agent
---

Read `.github/correct-kit/skills/correct/SKILL.md` and `.github/agent-contract.md` and follow the
mode `/correct log` for the correction the user just made in this chat. ${input:note:optional - what was wrong, in your words}

Use the GitHub tools to find, update or create the class issue. If they are not available,
print the ready `gh issue comment` / `gh issue create` command instead. Never copy chat text,
file contents or secrets into the issue; paraphrase.
