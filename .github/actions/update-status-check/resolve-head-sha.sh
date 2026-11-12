# shellcheck shell=bash
#
# Sourced by action.yml and resolve-head-sha.test.sh.
#
# resolve_head_sha <repository> <pr-number> <input-sha>
#   Prints the pull request's current head SHA when the lookup succeeds and
#   returns a full commit SHA; otherwise prints <input-sha> unchanged.
#   Messages, including a warning with the lookup's cause on failure, go to
#   stderr, each on one line. Always returns 0, so a failed lookup never fails
#   the step.
#   On pull request events github.sha is a temporary merge commit that doesn't
#   appear on the PR, so a status set on it is invisible. The lookup needs
#   `pull-requests: read`; without it the API answers 403, and `gh api` exits
#   non-zero, writes that error body to stdout and the HTTP status to stderr.
#
#   The warning's cause depends on gh's exit status, so stderr noise on a
#   successful call can't hide a bad response:
#   - non-zero exit: "gh api exited <code>: " and gh's stderr, or its stdout
#     when stderr is blank, or "no output";
#   - exit 0 with a response that isn't a full SHA: "unexpected response: "
#     and the response, or "empty response".
#   The 403 hint is decided from the full stderr and stdout, before the cause
#   is cut to RESOLVE_HEAD_SHA_CAUSE_MAX characters for display.

# Longest cause shown in the warning, in characters.
RESOLVE_HEAD_SHA_CAUSE_MAX=200

# Joins text onto one line, so it can't start another workflow command.
_resolve_head_sha_one_line() {
  local text="$1"
  text="${text//$'\r'/ }"
  printf '%s\n' "${text//$'\n'/ }"
}

resolve_head_sha() {
  local repository="$1" pr_number="$2" input_sha="$3" head_sha="" rc=0 err_file err cause message
  local status_403='"status":[[:space:]]*"?403'
  if [[ -z "$pr_number" ]]; then
    printf '%s\n' "$input_sha"
    return 0
  fi

  err_file="$(mktemp)"
  head_sha=$(gh api "repos/${repository}/pulls/${pr_number}" --jq '.head.sha' 2>"$err_file") || rc=$?
  err="$(cat "$err_file")"
  rm -f "$err_file"
  [[ -n "${err//[[:space:]]/}" ]] || err=""
  if ((rc == 0)) && [[ "$head_sha" =~ ^[0-9a-f]{40}$ ]]; then
    _resolve_head_sha_one_line "Resolved PR #${pr_number} head SHA: ${head_sha} (input was: ${input_sha})" >&2
    printf '%s\n' "$head_sha"
    return 0
  fi

  if ((rc != 0)); then
    cause="gh api exited ${rc}: ${err:-${head_sha:-no output}}"
  elif [[ -n "$head_sha" ]]; then
    cause="unexpected response: ${head_sha}"
  else
    cause="empty response"
  fi
  message="Could not resolve PR #${pr_number}'s head SHA; using ${input_sha}. Cause: ${cause:0:RESOLVE_HEAD_SHA_CAUSE_MAX}"
  if [[ "$err" == *"HTTP 403"* || "$head_sha" =~ $status_403 ]]; then
    message+=" (the token needs pull-requests: read)"
  fi
  # `%` is escaped too, so response text can't be decoded as one of the
  # annotation's escapes.
  echo "::warning::$(_resolve_head_sha_one_line "${message//%/%25}")" >&2
  printf '%s\n' "$input_sha"
}
