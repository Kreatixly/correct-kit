#!/usr/bin/env bash
# correct-kit: policy check for patches that an unattended agent run wants to publish.
#
#   correct_policy.sh <patch-file> [<config-file>]
#
# The limits live here and in the config, not in a prompt: the model cannot
# reinterpret them. Exit 1 on any violation, one reason per line on stderr.
# Run from the repository root. Config format: see correct_policy.conf.
#
# Patterns are bash patterns where `*` also matches `/` (lib/*.dart matches
# lib/a/b.dart). First matching `deny` wins over any `allow`.

set -u

patch="${1:?patch file}"
conf="${2:-$(dirname "$0")/correct_policy.conf}"
[ -f "$conf" ] || { echo "POLICY: config not found: $conf" >&2; exit 1; }

allow=(); deny=(); check=(); tests=(); baseline=(); forbid=()
max_files=10; max_lines=600; test_marker=''
while IFS= read -r line || [ -n "$line" ]; do
  line="${line%%#*}"; line="${line%"${line##*[![:space:]]}"}"
  [ -n "$line" ] || continue
  key="${line%%:*}"; val="${line#*:}"; val="${val#"${val%%[![:space:]]*}"}"
  case "$key" in
    allow) allow+=("$val") ;;
    deny) deny+=("$val") ;;
    check) check+=("$val") ;;
    tests) tests+=("$val") ;;
    baseline) baseline+=("$val") ;;
    forbid) forbid+=("$val") ;;          # <regex> | <reason>
    max_files) max_files="$val" ;;
    max_lines) max_lines="$val" ;;
    test_marker) test_marker="$val" ;;   # regex for a test case or assertion
    *) echo "POLICY: unknown config key '$key'" >&2; exit 1 ;;
  esac
done < "$conf"

fail=0
violation() { echo "POLICY: $*" >&2; fail=1; }
matches() { local p="$1"; shift; local g; for g in "$@"; do [[ "$p" == $g ]] && return 0; done; return 1; }

[ -s "$patch" ] || { echo "POLICY: empty patch" >&2; exit 1; }

if git apply --summary "$patch" | grep -E "^ (delete|rename|copy|mode change)" >/dev/null; then
  violation "deleting, renaming or changing the mode of files is not allowed"
fi
if git apply --numstat "$patch" | grep -E "^-	-	" >/dev/null; then
  violation "binary file in patch"
fi

files=0; lines=0; checks=0; test_paths=()
while IFS=$'\t' read -r added deleted path; do
  [ -n "$path" ] || continue
  if matches "$path" "${deny[@]}"; then violation "path is excluded: $path"; continue; fi
  if ! matches "$path" "${allow[@]}"; then violation "path outside the allowed scope: $path"; continue; fi
  files=$((files + 1)); lines=$((lines + added + deleted))
  matches "$path" "${check[@]}" && checks=$((checks + 1))
  matches "$path" "${tests[@]}" && test_paths+=("$path")
  if matches "$path" "${baseline[@]}" && [ "$added" != "0" ]; then
    violation "baseline grows (it may only shrink): $path"
  fi
done < <(git apply --numstat "$patch")

[ "$files" -le "$max_files" ] || violation "$files files (max $max_files)"
[ "$lines" -le "$max_lines" ] || violation "$lines changed lines (max $max_lines)"
[ "$checks" -ge 1 ] || violation "no check added or extended (docs alone are not a fix)"

# Tests are never weakened: per test file, no fewer test/assert lines than before, no skips.
if [ -n "$test_marker" ] && [ "${#test_paths[@]}" -gt 0 ]; then
  # The marker goes in through ENVIRON, not `awk -v`: -v expands backslash escapes, which turns
  # `\(` into `(`, an invalid regex, and awk dies without reporting anything.
  if ! weakened=$(MARKER="$test_marker" FILES="$(printf '%s\n' "${test_paths[@]}")" awk '
    BEGIN { marker = ENVIRON["MARKER"]; n = split(ENVIRON["FILES"], arr, "\n"); for (i = 1; i <= n; i++) if (arr[i] != "") t[arr[i]] = 1 }
    /^\+\+\+ b\// { f = substr($0, 7); next }
    /^--- / { next }
    (f in t) && /^-/ && $0 ~ marker { rem[f]++ }
    (f in t) && /^\+/ { if ($0 ~ marker) add[f]++; if ($0 ~ /(skip:|\.skip\(|@skip|xit\(|xdescribe\(|pytest\.mark\.skip)/) skip[f] = 1 }
    END {
      for (k in rem) if (rem[k] > add[k]) print k ": " rem[k] " test lines removed, " (add[k] + 0) " added"
      for (k in skip) print k ": test skipped"
    }' "$patch"); then
    violation "test check failed to run (test_marker: $test_marker)"
  elif [ -n "$weakened" ]; then
    while IFS= read -r w; do violation "test weakened: $w"; done <<< "$weakened"
  fi
fi

# Forbidden patterns in added lines outside test files (tests may contain them as probes).
added_lines=$(awk -v files="$(printf '%s\n' "${test_paths[@]}")" '
  BEGIN { n = split(files, arr, "\n"); for (i = 1; i <= n; i++) if (arr[i] != "") t[arr[i]] = 1 }
  /^\+\+\+ b\// { f = substr($0, 7); next }
  /^\+/ && !(f in t) { print }' "$patch")
for entry in "${forbid[@]}"; do
  regex="${entry%% | *}"; reason="${entry#* | }"
  if printf '%s\n' "$added_lines" | grep -E -i -- "$regex" >/dev/null; then violation "$reason"; fi
done

exit $fail
