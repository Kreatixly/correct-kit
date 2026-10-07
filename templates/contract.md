# Project contract — {{PROJECT_NAME}}

Read by the project-neutral skills `correct`, `architect` and `glean` (correct-kit). Keep the
`##` headings; the skills look them up by name. Everything project-specific lives here.
Mark anything not verified with `(unverified)` until the owner confirms it.

## Project

{{PROJECT_NAME}} — {{ONE_LINE}}. Stack: {{STACK}}.

## Verify

All must be green before anything counts as done:

```bash
{{VERIFY_COMMANDS}}
```

{{VERIFY_NOTES}}

## Rules

- Project rules: {{RULES_SOURCE}} (e.g. the hard rules in the agent instruction file).
- Decisions not to re-litigate: {{ADR_DIR}}.
- Rule table (rule → enforcement → evidence): {{RULE_TABLE}} (best in the agent instruction
  file, where agents read it). Every delivery that moves a rule up the ladder updates it in the
  same commit and shrinks the prose rule to a pointer; a rule whose mistake can no longer happen
  leaves the table.

## Enforcement levels

| Rung | Tool here |
|---|---|
| Architecture | {{ARCH_TOOLS}} |
| Types | {{TYPE_TOOLS}} |
| Lint / CI | {{LINT_TOOLS}} |
| Architecture tests | {{ARCH_TEST_TOOLS}} — reports file, line and the rule, and self-tests its matcher |
| Tests | {{TEST_TOOLS}} |
| Docs | {{DOC_FILES}} |

## Evidence sources

- Git history of the default branch (cloud clones may be shallow: fetch full history first).
- Merged and closed PRs with review comments (humans and the automatic review).
- Correction log: issues and PR comments labelled **`{{CORRECTION_LABEL}}`**.
- Earlier reports: issues labelled `correct-report`; PRs labelled `correct-auto` closed without
  merge are rejected fixes.
- {{EXTRA_EVIDENCE}}
- Local Claude Code transcripts — only on a developer's machine, read through `/glean`.

## Correction issues

- Label: `{{CORRECTION_LABEL}}`. Title prefix: `{{CLASS_TITLE_PREFIX}}`.
- One issue per class, marked `<!-- correct-class: <slug> -->` in the body. Episodes arrive as
  comments with `<!-- correct-episode {…} -->` (`/correct log`); the weekly run renders the body.
- Team decision labels: `correct:triage` (open) → `correct:umsetzen` (implement) or
  `correct:verworfen` (closed as not planned; not proposed again without new evidence).
  `correct:ruhig`: closed after the stale period. Relapses are reopened by the weekly run.
- min occurrences: 2 · max new per run: 3 · stale after: 90 days (Copilot:
  `.github/correct/weekly.json`).
- Report folder for `/glean`: `.claude/glean/` (git-ignored).

## Limits

- Approval before implementation: {{APPROVAL_RULE}}. An analysis run never needs it.
- Nothing is merged by an agent. The owner merges.
- Unattended runs read and open issues only ({{ADR_WEEKLY_REF}}). Exception, if adopted:
  `correct-act` opens draft PRs within `.github/correct/correct_policy.conf` ({{ADR_AUTO_REF}}).
- Changes to agent instructions, the rule table or checks only through a reviewed pull request,
  never as a direct commit — also when they come from a local `/correct log`.
- Never weaken a rule or a test to make a check pass. Deleting a hollow test is the owner's call.
- Exceptions to a check sit on the offending line with reason, expiry date and approver, e.g.
  `// correct-allow(<rule>): <reason> · until YYYY-MM-DD · approved @<user>`. Agents never add
  one on their own.

## Delivery

- Prototypes: local branches `proto/<class-slug>`, never pushed.
- Changes: one mistake class per change, as a draft PR with `Closes #<class issue>`. Docs in the
  same commit.
- Proof in the PR description, section `## {{PROOF_HEADING}}`: red on the past, green today, false
  alarms, with commands and decisive output. Copilot: the required check `correct-policy` looks
  for the terms `{{PROOF_TERMS}}`.
- Commit messages and PR text in {{REPORT_LANGUAGE}}.

## Vocabulary

{{VOCABULARY}}

## Language

{{LANGUAGE_LINE}}
