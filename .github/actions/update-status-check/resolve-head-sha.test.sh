#!/usr/bin/env bash
# Tests resolve_head_sha against a stub `gh` on PATH.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
source "${here}/resolve-head-sha.sh"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "${tmp}/gh" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$GH_STUB_CALLS"
printf '%s' "$GH_STUB_STDOUT"
echo "gh stub stderr" >&2
exit "$GH_STUB_EXIT"
STUB
chmod +x "${tmp}/gh"
PATH="${tmp}:${PATH}"
export GH_STUB_CALLS="${tmp}/calls"

input_sha="1111111111111111111111111111111111111111"
head_sha="2222222222222222222222222222222222222222"
failures=0

# check <name> <pr-number> <stub stdout> <stub exit> <expected SHA> <expected output fragment>
check() {
  local name="$1" pr_number="$2" output
  export GH_STUB_STDOUT="$3" GH_STUB_EXIT="$4"
  : > "$GH_STUB_CALLS"
  SHA="$input_sha"
  output="$(resolve_head_sha "launchbynttdata/example" "$pr_number"; echo "SHA=${SHA}")"
  if [[ "$output" != *"SHA=$5"* || "$output" != *"$6"* ]]; then
    echo "FAIL: ${name}: expected SHA $5 and output containing '$6', got:"
    printf '    %s\n' "${output//$'\n'/$'\n'    }"
    failures=$((failures + 1))
  else
    echo "ok: ${name}"
  fi
}

check "head SHA resolved" 7 "$head_sha" 0 "$head_sha" "Resolved PR #7 head SHA: ${head_sha} (input was: ${input_sha})"
check "403 error body on stdout keeps the input SHA" 7 \
  '{"message":"Resource not accessible by integration","status":"403"}' 1 \
  "$input_sha" "::warning::Could not resolve PR #7's head SHA; using ${input_sha}"
check "empty output keeps the input SHA" 7 "" 0 "$input_sha" "::warning::"
check "non-SHA output keeps the input SHA" 7 "null" 0 "$input_sha" "::warning::"
check "abbreviated SHA keeps the input SHA" 7 "2222222" 0 "$input_sha" "::warning::"

check "no PR number keeps the input SHA" "" "$head_sha" 0 "$input_sha" ""
if [[ -s "$GH_STUB_CALLS" ]]; then
  echo "FAIL: no PR number: gh was called: $(cat "$GH_STUB_CALLS")"
  failures=$((failures + 1))
fi

check "lookup targets the PR" 42 "$head_sha" 0 "$head_sha" "Resolved PR #42"
if [[ "$(cat "$GH_STUB_CALLS")" != "api repos/launchbynttdata/example/pulls/42 --jq .head.sha" ]]; then
  echo "FAIL: lookup targets the PR: gh was called with: $(cat "$GH_STUB_CALLS")"
  failures=$((failures + 1))
fi

if ((failures)); then
  echo "${failures} check(s) failed"
  exit 1
fi
echo "all checks passed"
