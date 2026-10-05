# Guard: headless agent steps run sub-agents in the foreground

**Why:** in headless mode a sub-agent started in the background ends the run: the model says
it will wait, its turn ends, the job is green and nothing was produced. Seen twice in the
project this kit comes from (architecture survey; code review).

**Rule:** every step that `uses: anthropics/claude-code-action` and allows the `Task` tool —
explicitly in `--allowedTools`, or implicitly by having no `--allowedTools` — sets
`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS: '1'` in its step, job or workflow `env`.

**Implement** it as a test in the repo's own test framework (correct-setup generates it), so
it runs with the normal verify commands. It must:

1. parse every `.github/workflows/*.yml` with a YAML parser (not regex over the file);
2. report `file: job / step name` for each violation with a message that names the fix;
3. carry a matcher self-test with at least: Task allowed without the switch (red), no
   `--allowedTools` (red), switch `'0'` (red), switch on the step (green), switch at workflow
   level (green), allowlist without `Task` (green), a tool merely containing "Task" such as
   `TaskList` (green).

Reference implementation (Dart, flutter_test + package:yaml): `examples/lernsnap/workflow_rules_test.dart`.
Copilot-only repos do not need this guard.
