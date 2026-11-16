#!/usr/bin/env bash
# Tests the "Check Pull Request" and "Revoke Approvals" run blocks of
# reusable-pr-automated-approvals.yml, as written in the workflow, against a
# stub `gh` that pages the way the GitHub API does (30 items per page without
# --paginate, and at most 250 commits for a pull request) and applies --jq the
# way gh does, printing null as an empty line.
# Needs yq (mikefarah, v4) and jq.
#
#   .github/tests/reusable-pr-automated-approvals.test.sh [<workflow file>]
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workflow="${1:-${here}/../workflows/reusable-pr-automated-approvals.yml}"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

yq '.jobs.approvals.steps[] | select(.id == "check-pull-request") | .run' "$workflow" > "${tmp}/check.sh"
yq '.jobs.approvals.steps[] | select(.name == "Revoke Approvals") | .run' "$workflow" > "${tmp}/revoke.sh"
for script in check revoke; do
  if [[ ! -s "${tmp}/${script}.sh" ]] || [[ "$(cat "${tmp}/${script}.sh")" == "null" ]]; then
    echo "FAIL: could not extract the ${script} run block from ${workflow}"
    exit 1
  fi
done

mkdir "${tmp}/bin"
cat > "${tmp}/bin/gh" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$GH_STUB_CALLS"
paginate=false method=GET path="" filter=""
args=("$@")
for ((i = 0; i < ${#args[@]}; i++)); do
  case "${args[i]}" in
    --paginate) paginate=true ;;
    --method) method="${args[i + 1]}"; i=$((i + 1)) ;;
    --jq) filter="${args[i + 1]}"; i=$((i + 1)) ;;
    -f) i=$((i + 1)) ;;
    /repos/*) path="${args[i]}" ;;
  esac
done
# Applies --jq to each page the way gh does, including printing null as an empty line.
emit() {
  if [[ -n "$filter" ]]; then
    jq -r "(${filter}) | if . == null then \"\" else . end"
  else
    cat
  fi
}
case "${method} ${path}" in
  "GET "*/pulls/*/commits)
    limit=30
    if $paginate; then limit=250; fi
    # GH_STUB_AUTHORS has one login per commit; "null" is a commit with no linked account.
    head -n "$limit" "$GH_STUB_AUTHORS" \
      | jq -R '{author: (if . == "null" then null else {login: .} end)}' \
      | jq -c -s '[range(0; length; 30) as $i | .[$i:$i + 30]] | .[]' \
      | while read -r page; do printf '%s\n' "$page" | emit; done ;;
  "GET "*/pulls/*/reviews)
    if $paginate; then emit < "$GH_STUB_REVIEWS"; else head -n 1 "$GH_STUB_REVIEWS" | emit; fi ;;
  "GET "*/pulls/[0-9]*)
    jq -n --argjson commits "$GH_STUB_EXPECTED" '{commits: $commits}' | emit ;;
  "PUT "*/dismissals) ;;
  *)
    echo "unexpected gh call: $*" >&2
    exit 99 ;;
esac
STUB
chmod +x "${tmp}/bin/gh"
PATH="${tmp}/bin:${PATH}"
export GH_STUB_CALLS="${tmp}/calls" GH_STUB_AUTHORS="${tmp}/authors" GH_STUB_REVIEWS="${tmp}/reviews"
export GITHUB_REPOSITORY="launchbynttdata/example" PR_NUMBER="7"

bot="dependabot[bot]"
updater="launch-skeleton-auto-updater[bot]"
failures=0

repeat() {
  local n="$1" line="$2"
  for ((i = 0; i < n; i++)); do printf '%s\n' "$line"; done
}

# check <name> <expected should_approve> <actor> <title> <expected commit count>
# with the PR's commit authors, one per line, on stdin.
check() {
  local name="$1" want="$2" out rc=0
  export GITHUB_ACTOR="$3" PR_TITLE="$4" GH_STUB_EXPECTED="$5"
  cat > "$GH_STUB_AUTHORS"
  : > "$GH_STUB_CALLS"
  export GITHUB_OUTPUT="${tmp}/output"
  : > "$GITHUB_OUTPUT"
  out="$(bash --noprofile --norc -eo pipefail "${tmp}/check.sh" 2>&1)" || rc=$?
  local got
  got="$(sed -n 's/^should_approve=//p' "$GITHUB_OUTPUT")"
  if [[ $rc -ne 0 || "$got" != "$want" ]]; then
    echo "FAIL: ${name}: expected should_approve=${want}, got '${got}' (exit ${rc})"
    printf '    %s\n' "$out"
    failures=$((failures + 1))
  else
    echo "ok: ${name}"
  fi
}

check "bot-only PR is approved" true "$bot" "chore(deps): bump x" 2 <<<"$(repeat 2 "$bot")"
check "updater PR titled chore is approved" true "$updater" "chore: update from skeleton" 1 <<<"$updater"
check "updater PR not titled chore is refused" false "$updater" "feat: update from skeleton" 1 <<<"$updater"
check "human commit is refused" false "$bot" "chore(deps): bump x" 2 <<<"$(printf '%s\n' "$bot" "octocat")"
check "commit with no linked account is refused" false "$bot" "chore(deps): bump x" 2 <<<"$(printf '%s\n' "$bot" "null")"
check "commit with no linked account first is refused" false "$bot" "chore(deps): bump x" 2 <<<"$(printf '%s\n' "null" "$bot")"
check "human commit after the first 30 is refused" false "$bot" "chore(deps): bump x" 31 \
  <<<"$(repeat 30 "$bot"; echo "octocat")"
check "bot-only PR with 40 commits is approved" true "$bot" "chore(deps): bump x" 40 <<<"$(repeat 40 "$bot")"
check "PR with more than 250 commits is refused" false "$bot" "chore(deps): bump x" 260 <<<"$(repeat 260 "$bot")"
check "more commits listed than the PR reports is refused" false "$bot" "chore(deps): bump x" 2 <<<"$(repeat 3 "$bot")"
check "unreadable commit count is refused" false "$bot" "chore(deps): bump x" "null" <<<"$bot"
check "PR with no commits listed is refused" false "$bot" "chore(deps): bump x" 1 < /dev/null

# An approval on the second page of reviews must still be dismissed.
{
  printf '['
  for ((i = 1; i <= 30; i++)); do
    [[ $i -gt 1 ]] && printf ','
    printf '{"id":%d,"user":{"login":"octocat"},"state":"COMMENTED"}' "$i"
  done
  printf ']\n'
  echo '[{"id":31,"user":{"login":"alpha-approver[bot]"},"state":"APPROVED"},{"id":32,"user":{"login":"bravo-approver[bot]"},"state":"APPROVED"}]'
} > "$GH_STUB_REVIEWS"
: > "$GH_STUB_CALLS"
rc=0
out="$(GH_TOKEN=x ALPHA_SLUG=alpha-approver BRAVO_SLUG=bravo-approver ALPHA_TOKEN=a BRAVO_TOKEN=b \
  bash --noprofile --norc -eo pipefail "${tmp}/revoke.sh" 2>&1)" || rc=$?
if [[ $rc -ne 0 ]] || ! grep -q 'reviews/31/dismissals' "$GH_STUB_CALLS" || ! grep -q 'reviews/32/dismissals' "$GH_STUB_CALLS"; then
  echo "FAIL: approvals on the second page of reviews are dismissed (exit ${rc})"
  printf '    %s\n' "$out"
  failures=$((failures + 1))
else
  echo "ok: approvals on the second page of reviews are dismissed"
fi

if [[ $failures -gt 0 ]]; then
  echo "${failures} test(s) failed."
  exit 1
fi
echo "All tests passed."
