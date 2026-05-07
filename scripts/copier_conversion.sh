#!/usr/bin/env bash
# Convert an existing Launch Terraform module repo to the copier-managed
# skeleton layout.
#
# Usage:
#   bash scripts/copier_conversion.sh [--force] [--pr] REPOSITORY_NAME

set -euo pipefail

ORG="launchbynttdata"

info()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$@"; exit 1; }

FORCE=false
PR=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=true; shift ;;
    --pr)    PR=true;    shift ;;
    -*) die "Unknown option: $1" ;;
    *) break ;;
  esac
done

if [[ $# -ne 1 ]]; then
  die "Usage: $0 [--force] [--pr] REPOSITORY_NAME"
fi

REPOSITORY_NAME="$1"
REPO_URL="ssh://git@github.com/$ORG/$REPOSITORY_NAME.git"

if ! command -v uv &>/dev/null; then
  die "uv is not installed. Install it with:

  curl -LsSf https://astral.sh/uv/install.sh | sh

See the installation docs: https://docs.astral.sh/uv/getting-started/installation/"
fi

info "uv found: $(uv --version)"

if ! command -v gh &>/dev/null; then
  die "gh CLI is not installed. Install it with:

  brew install gh

See the installation docs: https://cli.github.com/"
fi

info "gh found: $(gh --version | head -1)"

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

if [[ -f .lcafenv ]]; then
  if grep -qvE '^\s*(#|$)' .lcafenv; then
    if [[ "$FORCE" == true ]]; then
      warn ".lcafenv contains uncommented lines -- proceeding anyway due to --force."
    else
      die ".lcafenv contains uncommented lines. This is an indication something weird is going on and this repo needs further examination. Comment them out and commit to main or re-run this script with --force to skip this check."
    fi
  fi
fi

copier_flags=(--trust --force)
PRERELEASE_PROP=$(gh api "/repos/$ORG/$REPOSITORY_NAME/properties/values" \
  --jq '.[] | select(.property_name == "prerelease") | .value' 2>/dev/null || true)
if [[ "$PRERELEASE_PROP" == "true" ]]; then
  info "Repository custom property prerelease=true — adding --prereleases flag to copier."
  copier_flags+=(--prereleases)
fi

info "Running copier copy (${copier_flags[*]}) from $ORG/launch-terraform-skeleton..."
uv tool run copier copy "${copier_flags[@]}" gh:$ORG/launch-terraform-skeleton .

info "copier copy complete"

BRANCH="feat!/copier-conversion"

git checkout -b "$BRANCH"
make configure
pre-commit run --all-files || true # Fix in place, these should have already been fixed but someone has neglected to install the hook on the last change.
git add -A

make check || die "Make check failed after copier conversion. Please fix the issues and commit the changes manually from $TEMP_PATH."
git commit -m "feat!: convert to copier-managed skeleton" || (git add -A && git commit -m "feat!: convert to copier-managed skeleton")

git push --force -u origin "$BRANCH" || git push --force -u origin "$BRANCH" # Retry once to kick secrets-helper over in case of an auth failure.
info "Branch $BRANCH pushed to origin."

if [[ "$PR" == true ]]; then
  EXISTING_PR=$(gh pr list \
    --repo "$ORG/$REPOSITORY_NAME" \
    --head "$BRANCH" \
    --state open \
    --json url \
    --jq '.[0].url' 2>/dev/null || true)
  if [[ -n "$EXISTING_PR" ]]; then
    info "Open PR already exists for $BRANCH — skipping creation: $EXISTING_PR"
  else
    info "Opening pull request..."
    GITHUB_TOKEN=$GITHUB_TOKEN gh pr create \
      --repo "$ORG/$REPOSITORY_NAME" \
      --title "feat!: convert to copier-managed skeleton" \
      --body "Automated copier conversion via \`copier_conversion.sh\`." \
      --base main \
      --head "$BRANCH" \
      --label "major"
    info "Pull request opened for branch $BRANCH."
  fi
else
  info "Skipping PR creation (pass --pr to open a pull request)."
fi

info "Cleaning up temp files..."
cd /
rm -rf "$TEMP_PATH"
info "Done!"
