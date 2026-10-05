import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:yaml/yaml.dart';

/// Source guard: a headless Claude run that may start sub-agents runs them in
/// the foreground.
///
/// In `claude -p` (what `anthropics/claude-code-action` runs) a sub-agent
/// started in the background ends the run: the model says "I'll wait for it",
/// its turn ends, the job is green and nothing was produced. It happened in the
/// architecture survey (8a2b74c, fixed only as prose in the skill) and again in
/// the code review (#134 log: 2 turns, sub-agent started in background,
/// completed 0; fixed in #135). The YAML shows `Task` in the tool list but
/// nothing about this trap, so the next workflow repeats it.
///
/// Every claude-code-action step that allows `Task` — explicitly, or by having
/// no `--allowedTools` at all — must set
/// `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS: '1'` (step, job or workflow env).
/// Rule table: docs/enforcement.md.
void main() {
  const action = 'anthropics/claude-code-action';
  const envVar = 'CLAUDE_CODE_DISABLE_BACKGROUND_TASKS';

  /// The `--allowedTools` list of [claudeArgs], or null when there is none
  /// (then every tool, `Task` included, is allowed).
  List<String>? allowedTools(String claudeArgs) {
    final m =
        RegExp(r'''--allowed-?[tT]ools[\s=]+["']([^"']*)["']''').firstMatch(claudeArgs);
    if (m == null) return null;
    return m.group(1)!.split(',').map((t) => t.trim()).toList();
  }

  bool allowsTask(String claudeArgs) {
    final tools = allowedTools(claudeArgs);
    return tools == null ||
        tools.any((t) => t == 'Task' || t.startsWith('Task('));
  }

  String? envValue(Object? env) =>
      env is YamlMap ? env[envVar]?.toString() : null;

  /// One finding per claude-code-action step in [source] that allows `Task`
  /// without the foreground switch: `<job> / <step name>`.
  List<String> findings(String source) {
    final hits = <String>[];
    final doc = loadYaml(source);
    if (doc is! YamlMap || doc['jobs'] is! YamlMap) return hits;
    final workflowEnv = envValue(doc['env']);
    final jobs = doc['jobs'] as YamlMap;
    for (final jobEntry in jobs.entries) {
      final job = jobEntry.value;
      if (job is! YamlMap || job['steps'] is! YamlList) continue;
      final jobEnv = envValue(job['env']);
      for (final step in job['steps'] as YamlList) {
        if (step is! YamlMap) continue;
        final uses = step['uses']?.toString() ?? '';
        if (!uses.startsWith(action)) continue;
        final withArgs = step['with'];
        final claudeArgs = withArgs is YamlMap
            ? withArgs['claude_args']?.toString() ?? ''
            : '';
        if (!allowsTask(claudeArgs)) continue;
        final value = envValue(step['env']) ?? jobEnv ?? workflowEnv;
        if (value != '1') {
          hits.add('${jobEntry.key} / ${step['name'] ?? uses}');
        }
      }
    }
    return hits;
  }

  test('headless Claude steps that may start sub-agents run them in the '
      'foreground', () {
    final hits = <String>[];
    final workflows = Directory('.github/workflows')
        .listSync()
        .whereType<File>()
        .where((f) => f.path.endsWith('.yml') || f.path.endsWith('.yaml'))
        .toList()
      ..sort((a, b) => a.path.compareTo(b.path));
    for (final file in workflows) {
      for (final hit in findings(file.readAsStringSync())) {
        hits.add('${file.path.replaceAll(r'\', '/')}: $hit');
      }
    }
    expect(hits, isEmpty,
        reason: 'These claude-code-action steps allow Task (or set no '
            '--allowedTools) but do not set $envVar. A sub-agent started in '
            'the background ends a headless run without a result while the '
            "job stays green (#134/#135). Add to the step:\n"
            "  env:\n    $envVar: '1'\n${hits.join('\n')}");
  });

  test('matcher self-test', () {
    String workflow({String? stepEnv, String? args, String? workflowEnv}) => '''
${workflowEnv == null ? '' : 'env:\n  $envVar: $workflowEnv\n'}jobs:
  review:
    steps:
      - uses: actions/checkout@v4
      - name: Run
        uses: $action@v1
${stepEnv == null ? '' : '        env:\n          $envVar: $stepEnv\n'}        with:
          prompt: x
${args == null ? '' : "          claude_args: '$args'\n"}''';

    // claude-code-review.yml before #135: Task allowed, no switch.
    expect(findings(workflow(args: '--allowedTools "Read,Grep,Glob,Task"')),
        ['review / Run']);
    // claude.yml today: no --allowedTools, so Task is allowed by default.
    expect(findings(workflow()), ['review / Run']);
    // Folded multi-line args as in architecture-survey.yml.
    expect(
        findings(workflow(
            args: '--model x --allowedTools "Read,Task,Bash(git log:*)"')),
        ['review / Run']);
    // Switch set but not to 1.
    expect(findings(workflow(stepEnv: "'0'")), ['review / Run']);

    expect(findings(workflow(stepEnv: "'1'")), isEmpty);
    expect(findings(workflow(workflowEnv: "'1'")), isEmpty);
    // Fix step of architecture-survey-act: no Task, nothing to switch off.
    expect(
        findings(workflow(args: '--allowedTools "Read,Grep,Glob,Edit,Write"')),
        isEmpty);
    // A tool whose name only contains "Task" is not the Task tool.
    expect(findings(workflow(args: '--allowedTools "Read,TaskList"')),
        isEmpty);
  });
}
