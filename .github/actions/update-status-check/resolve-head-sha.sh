# shellcheck shell=bash
#
# Sourced by action.yml and resolve-head-sha.test.sh.
#
# resolve_head_sha <repository> <pr-number>
#   Sets SHA to the pull request's current head when the lookup succeeds and
#   returns a full commit SHA; otherwise leaves SHA as it was. On pull request
#   events github.sha is a temporary merge commit that doesn't appear on the
#   PR, so a status set on it is invisible. The lookup needs
#   `pull-requests: read`; without it the API answers 403, and `gh api` writes
#   that error body to stdout.

resolve_head_sha() {
  local repository="$1" pr_number="$2" head_sha
  [[ -n "$pr_number" ]] || return 0
  if head_sha=$(gh api "repos/${repository}/pulls/${pr_number}" --jq '.head.sha' 2>/dev/null) \
     && [[ "$head_sha" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Resolved PR #${pr_number} head SHA: ${head_sha} (input was: ${SHA})"
    SHA="$head_sha"
  else
    echo "::warning::Could not resolve PR #${pr_number}'s head SHA; using ${SHA}"
  fi
}
