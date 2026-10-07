#!/usr/bin/env bash
# correct-kit self-test: renders the templates with the LernSnap example values, checks that
# every workflow is valid YAML with shell-valid run blocks, and that the policy script accepts
# an allowed patch and rejects each kind of violation, the proof check, and the class-issue
# planner (tests/test_correct_issues.py). Needs bash, python3 (PyYAML), git.
set -u
cd "$(dirname "$0")/.."
fail=0
ok() { echo "ok   $*"; }
bad() { echo "FAIL $*"; fail=1; }
out=$(mktemp -d)

for t in templates/claude/workflows/*.yml; do
  if python3 scripts/render.py examples/lernsnap/values.claude.json "$t" "$out/$(basename "$t")"; then
    ok "render $t"
  else
    bad "render $t"
  fi
done
python3 scripts/render.py examples/lernsnap/values.copilot.json templates/copilot/workflows/correct-policy.yml "$out/copilot-correct-policy.yml" && ok "render copilot correct-policy" || bad "render copilot correct-policy"
python3 scripts/render.py examples/lernsnap/values.copilot.json templates/copilot/workflows/correct-weekly.yml "$out/copilot-correct-weekly.yml" && ok "render copilot correct-weekly" || bad "render copilot correct-weekly"
python3 scripts/render.py examples/lernsnap/values.copilot.json templates/copilot/workflows/copilot-setup-steps.yml "$out/copilot-setup-steps.yml" && ok "render copilot-setup-steps" || bad "render copilot-setup-steps"

python3 - "$out" <<'PY' || fail=1
import glob, subprocess, sys, yaml
bad = 0
for path in sorted(glob.glob(sys.argv[1] + "/*.yml")):
    try:
        doc = yaml.safe_load(open(path))
    except Exception as e:
        print(f"FAIL yaml {path}: {e}"); bad = 1; continue
    for job in (doc.get("jobs") or {}).values():
        for step in job.get("steps", []):
            if "run" in step:
                r = subprocess.run(["bash", "-n"], input=step["run"], text=True, capture_output=True)
                if r.returncode:
                    print(f"FAIL bash -n {path} / {step.get('name')}: {r.stderr.strip()}"); bad = 1
    print(f"ok   yaml+bash {path.split('/')[-1]}")
sys.exit(bad)
PY

policy=templates/policy/correct_policy.sh
conf=examples/lernsnap/correct_policy.conf
expect() { # <patch> <0|1>
  bash "$policy" "tests/patches/$1" "$conf" > /dev/null 2>&1; got=$?
  [ "$got" = "$2" ] && ok "policy $1 -> $got" || bad "policy $1: expected $2, got $got"
}
expect allowed.diff 0
expect denied-path.diff 1
expect weakened-test.diff 1
expect forbidden-pattern.diff 1
expect exception-added.diff 1

# Proof section in a class PR description.
proof() { # <body> <0|1>
  bash templates/policy/check_proof.sh "tests/proof/$1" 'Nachweis|rot|grün|Fehlalarm' > /dev/null 2>&1; got=$?
  [ "$got" = "$2" ] && ok "proof $1 -> $got" || bad "proof $1: expected $2, got $got"
}
proof ok.md 0
proof no-section.md 1
proof missing-term.md 1

# Class issues and agenda: config renders to valid JSON, the planner passes its tests.
if python3 scripts/render.py examples/lernsnap/values.copilot.json templates/copilot/weekly.json "$out/weekly.json" \
   && python3 -c 'import json, sys; json.load(open(sys.argv[1], encoding="utf-8"))' "$out/weekly.json"; then
  ok "render copilot weekly.json"
else
  bad "render copilot weekly.json"
fi
if python3 -X utf8 tests/test_correct_issues.py > "$out/unit.log" 2>&1; then
  ok "correct_issues.py unit tests"
else
  cat "$out/unit.log"; bad "correct_issues.py unit tests"
fi

rm -rf "$out"
exit $fail
