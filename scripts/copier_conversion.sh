#!/usr/bin/env bash
# Convert an existing Launch Terraform module repo to the copier-managed
# skeleton layout.
#
# Usage:
#   bash scripts/copier_conversion.sh REPOSITORY_NAME

set -euo pipefail

ORG="nttdtest"

info()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$@"; exit 1; }

if [[ $# -ne 1 ]]; then
  die "Usage: $0 REPOSITORY_NAME"
fi

REPOSITORY_NAME="$1"
REPO_URL="https://github.com/$ORG/$REPOSITORY_NAME.git"

if ! command -v uv &>/dev/null; then
  die "uv is not installed. Install it with:

  curl -LsSf https://astral.sh/uv/install.sh | sh

See the installation docs: https://docs.astral.sh/uv/getting-started/installation/"
fi

info "uv found: $(uv --version)"

if ! uv tool list 2>/dev/null | grep -q '^copier '; then
  info "copier not found in uv tools — installing…"
  uv tool install copier
fi

info "copier is available"

TEMP_PATH=$(mktemp -d)
info "Cloning $ORG/$REPOSITORY_NAME to $TEMP_PATH..."
git clone "$REPO_URL" "$TEMP_PATH" || git clone "$REPO_URL" "$TEMP_PATH"

cd "$TEMP_PATH"

missing=()
[[ -d .git ]]      || missing+=(".git/")
[[ -d examples ]]  || missing+=("examples/")
[[ -d tests ]]     || missing+=("tests/")
[[ -f main.tf ]]   || missing+=("main.tf")

if [[ ${#missing[@]} -gt 0 ]]; then
  die "$REPOSITORY_NAME does not look like a Launch Terraform module.
Missing: ${missing[*]}"
fi

info "Running copier copy (--trust --force) from $ORG/poc-skeleton..."
uv tool run copier copy --trust --force gh:$ORG/poc-skeleton .

info "copier copy complete"

# info "Checking changed files for deletion-only diffs..."

# # Get the list of modified (tracked) files that have a diff vs HEAD.
# # Untracked (new) files are additions-only by definition, so skip them.
# while IFS= read -r file; do
#   [[ -z "$file" ]] && continue

#   additions=$(git diff HEAD -- "$file" | grep -c '^+[^+]' || true)
#   deletions=$(git diff HEAD -- "$file" | grep -c '^-[^-]' || true)

#   if [[ "$deletions" -gt 0 && "$additions" -eq 0 ]]; then
#     info "Restoring $file (deletion-only change)"
#     git restore "$file"
#   fi
# done < <(git diff --name-only HEAD)

# info "Deletion-only files restored"

BRANCH="feat!/copier-conversion"

git checkout -b "$BRANCH"
git add -A
git commit -m "feat!: convert to copier-managed skeleton"
git push -u origin "$BRANCH" || git push -u origin "$BRANCH" # Retry once to kick secrets-helper over in case of an auth failure.

if ! command -v gh &>/dev/null; then
  warn "gh CLI not found — skipping pull request creation. Push complete."
  exit 0
fi

info "Opening pull request..."
GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh pr create \
  --repo "$ORG/$REPOSITORY_NAME" \
  --title "feat!: convert to copier-managed skeleton" \
  --body "Automated copier conversion via \`copier_conversion.sh\`." \
  --base main \
  --head "$BRANCH"

info "Pull request opened for branch $BRANCH."

info "Cleaning up temp files..."
cd /
rm -rf "$TEMP_PATH"
info "Done!"


