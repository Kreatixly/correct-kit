#!/usr/bin/env bash
# correct-kit self-test: renders the templates with the LernSnap example values, checks that
# every workflow is valid YAML with shell-valid run blocks, and that the policy script accepts
# an allowed patch and rejects the three kinds of violation. Needs bash, python3 (PyYAML), git.
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
cp templates/copilot/workflows/correct-policy.yml "$out/copilot-correct-policy.yml"
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

rm -rf "$out"
exit $fail
