#!/usr/bin/env bash
# correct-kit: a correction class PR carries its proof in the description.
#
#   check_proof.sh <pr-body-file> '<Heading>|<term>|<term>...'
#
# Mechanical only: a section with that heading exists and names every term (e.g.
# 'Nachweis|rot|grün|Fehlalarm'). Whether the proof is right is for the review.
# Exit 1 with one reason per line on stderr.

set -u
export LC_ALL=C.UTF-8  # tolower() folds Ü to ü only in a UTF-8 locale
body="${1:?pr body file}"
terms="${2:?terms}"
heading="${terms%%|*}"
[ -f "$body" ] || { echo "PROOF: no PR description" >&2; exit 1; }

# The section runs from the heading to the next heading of the same or a higher level.
section=$(H="$heading" awk '
  BEGIN { h = tolower(ENVIRON["H"]) }
  { sub(/\r$/, "") }
  /^#+[ \t]/ {
    match($0, /^#+/)
    if (on && RLENGTH <= lvl) exit
    if (!on && index(tolower($0), h)) { on = 1; lvl = RLENGTH; next }
  }
  on { print }' "$body")

if [ -z "${section//[[:space:]]/}" ]; then
  echo "PROOF: the PR description has no section '## $heading' (red on the past, green today, no false alarms)" >&2
  exit 1
fi
fail=0
IFS='|' read -r -a list <<< "$terms"
for term in "${list[@]:1}"; do
  # awk instead of `grep -i`: case folding of non-ASCII terms (grün) differs between greps.
  if ! S="$section" T="$term" awk 'BEGIN { exit !index(tolower(ENVIRON["S"]), tolower(ENVIRON["T"])) }'; then
    echo "PROOF: section '$heading' does not mention '$term'" >&2
    fail=1
  fi
done
exit $fail
