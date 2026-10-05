# {{ADR_TITLE_WEEKLY}}

<!-- correct-kit template. Adapt to the repo's ADR format and language before committing;
     keep the decision, drop what does not apply. -->

**Status:** accepted ({{DATE}})

**Context:** Agents working in this repository repeat some mistakes. Each correction by a
human is evidence, but it is spread over review comments, reverts, fix-up commits and
correction issues, and nobody reads it as a whole. A rule added as prose to the agent
instructions decays; a check in the repository holds.

**Decision:**

- A scheduled workflow (`correct-weekly`, {{CRON_HUMAN}}) runs the `correct` method in
  analysis mode and publishes one report issue (label `correct-report`). The previous report
  is closed, so one is open at a time.
- The run is **read-only**, enforced by rights, not by the prompt: workflow permissions
  `contents`/`pull-requests: read`, `issues: write`; the model cannot write files or call
  GitHub; a workflow step collects the evidence and another publishes the report.
- Each class gets the highest enforcement level that prevents it — architecture, types,
  lint/CI check, test, docs last — and counts as fixed only with proof: red on the historical
  mistake, green today, no false alarms.
- A failed or empty run creates an issue; a green run without a report is a failure.

**Consequences:** Actions minutes for one short run per week. The report is a plan; changes
still need the owner's approval (see {{ADR_AUTO_REF}} for the exception, if adopted).
