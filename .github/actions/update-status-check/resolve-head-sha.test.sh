#!/usr/bin/env bash
# Tests resolve_head_sha, and the action's run block as written in action.yml,
# against a stub `gh` on PATH. Needs yq (mikefarah, v4) and jq.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source-path=SCRIPTDIR
source "${here}/resolve-head-sha.sh"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "${tmp}/gh" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$GH_STUB_CALLS"
if [[ " $* " == *" --input "* ]]; then
  cat > "$GH_STUB_PAYLOAD"
  exit 0
fi
printf '%s' "$GH_STUB_STDOUT"
printf '%s' "$GH_STUB_STDERR" >&2
exit "$GH_STUB_EXIT"
STUB
chmod +x "${tmp}/gh"
PATH="${tmp}:${PATH}"
export GH_STUB_CALLS="${tmp}/calls" GH_STUB_PAYLOAD="${tmp}/payload"

input_sha="1111111111111111111111111111111111111111"
head_sha="2222222222222222222222222222222222222222"
failures=0

fail() {
  echo "FAIL: $1"
  shift
  printf '    %s\n' "$@"
  failures=$((failures + 1))
}

# check <name> <pr-number> <stub stdout> <stub stderr> <stub exit> <expected stdout> <expected stderr>
check() {
  local name="$1" pr_number="$2" expected_out="$6" expected_err="$7" out err rc=0
  export GH_STUB_STDOUT="$3" GH_STUB_STDERR="$4" GH_STUB_EXIT="$5"
  : > "$GH_STUB_CALLS"
  out="$(resolve_head_sha "launchbynttdata/example" "$pr_number" "$input_sha" 2> "${tmp}/err")" || rc=$?
  err="$(cat "${tmp}/err")"
  if ((rc != 0)) || [[ "$out" != "$expected_out" || "$err" != "$expected_err" ]]; then
    fail "$name" "exit:   ${rc} (expected 0)" \
      "stdout: ${out}" "expected: ${expected_out}" \
      "stderr: ${err}" "expected: ${expected_err}"
  else
    echo "ok: ${name}"
  fi
}

# warning_for <pr-number> <input sha> <cause>: the warning line resolve_head_sha prints
warning_for() {
  printf "::warning::Could not resolve PR #%s's head SHA; using %s. Cause: %s" "$1" "$2" "$3"
}
# w <cause>: the warning for PR #7 and the usual input SHA
w() { warning_for 7 "$input_sha" "$1"; }

check "head SHA resolved" 7 "$head_sha" "" 0 \
  "$head_sha" "Resolved PR #7 head SHA: ${head_sha} (input was: ${input_sha})"
hint="(the token needs pull-requests: read)"
body_403='{"message":"Resource not accessible by integration","status":"403"}'
err_403="gh: Resource not accessible by integration (HTTP 403)"
long="$(printf 'x%.0s' {1..300})"
long_cause="gh api exited 1: ${long} (HTTP 403)"

check "403 keeps the input SHA and names the permission" 7 "$body_403" "$err_403" 1 \
  "$input_sha" "$(w "gh api exited 1: ${err_403} ${hint}")"
check "403 on a later stderr line still names the permission" 7 "" \
  $'gh: first line\n'"$err_403" 1 \
  "$input_sha" "$(w "gh api exited 1: gh: first line ${err_403} ${hint}")"
check "403 past the display limit still names the permission" 7 "" \
  "${long} (HTTP 403)" 1 \
  "$input_sha" "$(w "${long_cause:0:RESOLVE_HEAD_SHA_CAUSE_MAX} ${hint}")"
check "403 body on stdout only names the permission" 7 "$body_403" "" 1 \
  "$input_sha" "$(w "gh api exited 1: ${body_403} ${hint}")"
check "other API error keeps the input SHA" 7 '{"message":"Not Found","status":"404"}' \
  $'gh: Not Found (HTTP 404)\nsecond line' 1 \
  "$input_sha" "$(w "gh api exited 1: gh: Not Found (HTTP 404) second line")"
check "whitespace-only stderr falls back to the response body" 7 '{"message":"Not Found","status":"404"}' \
  $' \n\t' 1 \
  "$input_sha" "$(w 'gh api exited 1: {"message":"Not Found","status":"404"}')"
check "failure without output keeps the input SHA" 7 "" "" 2 \
  "$input_sha" "$(w "gh api exited 2: no output")"
check "empty output keeps the input SHA" 7 "" "" 0 \
  "$input_sha" "$(w "empty response")"
check "non-SHA output keeps the input SHA" 7 "null" "" 0 \
  "$input_sha" "$(w "unexpected response: null")"
check "stderr noise on success doesn't hide the response" 7 "null" "gh: a notice" 0 \
  "$input_sha" "$(w "unexpected response: null")"
check "abbreviated SHA keeps the input SHA" 7 "2222222" "" 0 \
  "$input_sha" "$(w "unexpected response: 2222222")"
check "multi-line output stays on one line" 7 $'a\n::error::b' "" 0 \
  "$input_sha" "$(w "unexpected response: a ::error::b")"
check "carriage return in output stays on one line" 7 $'a\r::error::b' "" 0 \
  "$input_sha" "$(w "unexpected response: a ::error::b")"
check "carriage return in stderr stays on one line" 7 "" $'gh: a\r::error::b' 1 \
  "$input_sha" "$(w "gh api exited 1: gh: a ::error::b")"
check "percent signs are escaped" 7 "100%0A" "" 0 \
  "$input_sha" "$(w "unexpected response: 100%250A")"
long_response="unexpected response: ${long}"
check "long output is truncated" 7 "$long" "" 0 \
  "$input_sha" "$(w "${long_response:0:RESOLVE_HEAD_SHA_CAUSE_MAX}")"

export GH_STUB_STDOUT="$head_sha" GH_STUB_STDERR="" GH_STUB_EXIT=0
multi_line_input=$'1111111\n::error::injected'
rc=0
out="$(resolve_head_sha "launchbynttdata/example" 7 "$multi_line_input" 2> "${tmp}/err")" || rc=$?
if ((rc != 0)) || [[ "$out" != "$head_sha" \
      || "$(cat "${tmp}/err")" != "Resolved PR #7 head SHA: ${head_sha} (input was: 1111111 ::error::injected)" ]]; then
  fail "a multi-line input SHA stays on one line when resolved" "exit: ${rc}" "stdout: ${out}" "stderr: $(cat "${tmp}/err")"
else
  echo "ok: a multi-line input SHA stays on one line when resolved"
fi

check "no PR number keeps the input SHA without a lookup" "" "$head_sha" "" 0 "$input_sha" ""
if [[ -s "$GH_STUB_CALLS" ]]; then
  fail "no PR number: gh was called" "$(cat "$GH_STUB_CALLS")"
fi

check "lookup targets the PR" 42 "$head_sha" "" 0 \
  "$head_sha" "Resolved PR #42 head SHA: ${head_sha} (input was: ${input_sha})"
if [[ "$(cat "$GH_STUB_CALLS")" != "api repos/launchbynttdata/example/pulls/42 --jq .head.sha" ]]; then
  fail "lookup targets the PR: wrong gh call" "$(cat "$GH_STUB_CALLS")"
fi

# The action's run block, as written in action.yml, with the step's env and
# the shell options GitHub uses for `shell: bash`.
run_block="$(yq '.runs.steps[] | select(.name == "Update Status Check") | .run' "${here}/action.yml")"
# shellcheck disable=SC2016 # a literal, unevaluated GitHub expression
if [[ -z "$run_block" || "$run_block" == *'${{'* ]]; then
  fail "action run block: missing, or contains an expression this test can't evaluate" "$run_block"
fi

# run_action <name> <pr-number> <input sha> <stub stdout> <stub stderr> <stub exit> <expected exit>
#            <expected status SHA, or "" for no POST> <expected warning line, or "" for none>
run_action() {
  local name="$1" pr_number="$2" sha_input="$3" stub_stdout="$4" stub_stderr="$5" stub_exit="$6"
  local expected_rc="$7" expected_sha="$8" expected_warning="$9"
  local out rc=0 lookup post payload warnings expected_lookup=""
  [[ -z "$pr_number" ]] || expected_lookup="api repos/launchbynttdata/example/pulls/${pr_number} --jq .head.sha"
  export GH_STUB_STDOUT="$stub_stdout" GH_STUB_STDERR="$stub_stderr" GH_STUB_EXIT="$stub_exit"
  : > "$GH_STUB_CALLS"
  rm -f "$GH_STUB_PAYLOAD"
  out="$(GITHUB_ACTION_PATH="$here" GITHUB_REPOSITORY="launchbynttdata/example" \
    GITHUB_TOKEN="not-a-token" CHECK_NAME="example-check" STATUS="success" SHA="$sha_input" \
    DESCRIPTION="Example description" TARGET_URL="https://example.com/run" PR_NUMBER="$pr_number" \
    bash --noprofile --norc -eo pipefail -c "$run_block" 2>&1)" || rc=$?
  lookup="$(grep -v -- '-X POST' "$GH_STUB_CALLS" || true)"
  post="$(grep -- '-X POST' "$GH_STUB_CALLS" || true)"
  payload="$(jq -c . "$GH_STUB_PAYLOAD" 2>/dev/null || true)"
  warnings="$(grep '^::warning::' <<< "$out" || true)"
  if ((rc != expected_rc)); then
    fail "$name" "exit ${rc}, expected ${expected_rc}; output:" "$out"
  elif [[ "$lookup" != "$expected_lookup" ]]; then
    fail "$name" "lookup: ${lookup:-none}" "expected: ${expected_lookup:-none}"
  elif [[ "$warnings" != "$expected_warning" ]]; then
    fail "$name" "warning: ${warnings:-none}" "expected: ${expected_warning:-none}"
  elif [[ -z "$expected_sha" ]]; then
    if [[ -n "$post" ]]; then
      fail "$name" "expected no status POST, got: ${post}"
    else
      echo "ok: ${name}"
    fi
  elif [[ "$post" != "api -X POST repos/launchbynttdata/example/statuses/${expected_sha} --input -" ]]; then
    fail "$name" "status POST: ${post:-none}" "expected statuses/${expected_sha}"
  elif [[ "$payload" != '{"state":"success","context":"example-check","description":"Example description","target_url":"https://example.com/run"}' ]]; then
    fail "$name" "payload: ${payload:-none}"
  else
    echo "ok: ${name}"
  fi
}

err_404="gh: Not Found (HTTP 404)"
run_action "action posts to the PR's resolved head" 7 "$input_sha" "$head_sha" "" 0 0 "$head_sha" ""
run_action "action posts to the input SHA when the lookup fails" 7 "$input_sha" "" "$err_404" 1 0 \
  "$input_sha" "$(w "gh api exited 1: ${err_404}")"
run_action "action warns about the permission on a 403" 7 "$input_sha" "$body_403" "$err_403" 1 0 \
  "$input_sha" "$(w "gh api exited 1: ${err_403} ${hint}")"
run_action "action posts to the input SHA without a PR" "" "$input_sha" "" "" 0 0 "$input_sha" ""
run_action "action rejects an abbreviated sha" "" "abc1234" "" "" 0 1 "" ""
run_action "action rejects an empty sha" "" "" "" "" 0 1 "" ""
run_action "action rejects an abbreviated sha when the lookup fails" 7 "abc1234" "" "$err_404" 1 1 "" \
  "$(warning_for 7 abc1234 "gh api exited 1: ${err_404}")"

if ((failures)); then
  echo "${failures} check(s) failed"
  exit 1
fi
echo "all checks passed"
