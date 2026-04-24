#!/usr/bin/env bash
# Migrate a Launch Terraform module repo to the copier-managed skeleton layout.
#
# This script consolidates clone_to_test_organization.sh and copier_conversion.sh
# into a single workflow:
#   1. Copies the repo to the test organization (deleting it if it exists).
#   2. Configures merge settings (squash-only, auto-merge, delete branch on merge).
#   3. Copies tags and releases (oldest-first), leaving the final release for workflows.
#   4. Restores .github/ (minus dependabot) and pushes main.
#   5. Runs copier conversion, pushes the branch, and opens a PR.
#
# Usage:
#   bash scripts/migrate.sh REPOSITORY_NAME

set -euo pipefail

PRIMARY_ORG="launchbynttdata"
TEST_ORG="nttdtest"

info()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$@"; exit 1; }

if [[ $# -ne 1 ]]; then
  die "Usage: $0 REPOSITORY_NAME"
fi

REPOSITORY_NAME="$1"
PRIMARY_REPO_URL="https://github.com/$PRIMARY_ORG/$REPOSITORY_NAME.git"
TEST_REPO_URL="https://x-access-token:${GITHUB_TOKEN_nttdtest}@github.com/$TEST_ORG/$REPOSITORY_NAME.git"

# ── Prerequisites ───────────────────────────────────────────────────────────

if ! command -v gh &>/dev/null; then
  die "gh CLI is not installed."
fi

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

# ── Phase 1: Clone to test organization ─────────────────────────────────────

info "Cloning $PRIMARY_ORG/$REPOSITORY_NAME to $TEST_ORG/$REPOSITORY_NAME..."

# Delete the test repo if it already exists, then create a fresh empty one.
if GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo view "$TEST_ORG/$REPOSITORY_NAME" &>/dev/null; then
  info "Deleting existing repo $TEST_ORG/$REPOSITORY_NAME..."
  GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo delete "$TEST_ORG/$REPOSITORY_NAME" --yes
fi

info "Creating fresh repo $TEST_ORG/$REPOSITORY_NAME..."
GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo create "$TEST_ORG/$REPOSITORY_NAME" --private

info "Configuring repo settings for $TEST_ORG/$REPOSITORY_NAME..."
GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo edit "$TEST_ORG/$REPOSITORY_NAME" \
  --enable-rebase-merge=false \
  --enable-merge-commit=false \
  --enable-squash-merge \
  --enable-auto-merge \
  --delete-branch-on-merge

TEMP_PATH=$(mktemp -d)
git clone "$PRIMARY_REPO_URL" "$TEMP_PATH"

cd "$TEMP_PATH"
git fetch --tags origin

# Remove .github/ from the initial push so workflows don't fire during release setup.
git rm -r --quiet .github/ 2>/dev/null || true
git commit -m "chore: temporarily remove .github/ for clean clone" --allow-empty

git remote remove origin
git remote add origin "$TEST_REPO_URL"
git push -u origin main -f || git push -u origin main -f

# ── Phase 2: Copy tags and releases ─────────────────────────────────────────

# Sort tags by their commit date (oldest first) so releases are created in order.
SORTED_TAGS=()
while IFS= read -r t; do
  SORTED_TAGS+=("$t")
done < <(git tag --sort=creatordate)

if [[ ${#SORTED_TAGS[@]} -eq 0 ]]; then
  info "No tags found — skipping release copy."
else
  # Copy all releases except the last one; the final release will be handled by workflows.
  LAST_INDEX=$(( ${#SORTED_TAGS[@]} - 1 ))

  # Push all tags except the last one to the test repo before creating releases.
  info "Pushing tags to $TEST_ORG/$REPOSITORY_NAME..."
  for i in "${!SORTED_TAGS[@]}"; do
    if [[ "$i" -lt "$LAST_INDEX" ]]; then
      git push origin "refs/tags/${SORTED_TAGS[$i]}"
    fi
  done

  for i in "${!SORTED_TAGS[@]}"; do
    tag="${SORTED_TAGS[$i]}"
    TAG_COMMIT=$(git rev-list -n 1 "$tag")

    # Fetch the release title and body from the primary repo.
    RELEASE_TITLE=$(gh release view "$tag" --repo "$PRIMARY_ORG/$REPOSITORY_NAME" --json name --jq '.name' 2>/dev/null || echo "$tag")
    RELEASE_BODY=$(gh release view "$tag" --repo "$PRIMARY_ORG/$REPOSITORY_NAME" --json body --jq '.body' 2>/dev/null || echo "")

    if [[ "$i" -lt "$LAST_INDEX" ]]; then
      info "Creating release $tag ($((i + 1))/${#SORTED_TAGS[@]})..."
      GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh release create "$tag" \
        --repo "$TEST_ORG/$REPOSITORY_NAME" \
        --target "$TAG_COMMIT" \
        --title "$RELEASE_TITLE" \
        --notes "$RELEASE_BODY" \
        --verify-tag
    else
      info "Skipping final release $tag — will be handled by workflows after .github/ is restored."
    fi
  done

  # Restore .github/ and force-push to main so workflows can create the final release.
  info "Restoring .github/ folder..."
  git checkout HEAD~1 -- .github/
  rm -fr .github/dependabot.yml # Remove dependabot config, will be overlaid by copier
  git add .github/
  git commit -m "chore: restore .github/ for workflow-managed releases"
  git push origin main -f || git push origin main -f
fi

info "Test repository ready at $TEST_ORG/$REPOSITORY_NAME."

# ── Phase 3: Copier conversion ──────────────────────────────────────────────

# We already have the repo checked out in TEMP_PATH with origin pointing at the
# test org, so we can run copier directly without re-cloning.

missing=()
[[ -d .git ]]      || missing+=(".git/")
[[ -d examples ]]  || missing+=("examples/")
[[ -d tests ]]     || missing+=("tests/")
[[ -f main.tf ]]   || missing+=("main.tf")

if [[ ${#missing[@]} -gt 0 ]]; then
  die "$REPOSITORY_NAME does not look like a Launch Terraform module.
Missing: ${missing[*]}"
fi

info "Running copier copy (--trust --force) from $TEST_ORG/poc-skeleton..."
uv tool run copier copy --trust --force "gh:$TEST_ORG/poc-skeleton" .

info "copier copy complete"

BRANCH="feat!/copier-conversion"

git checkout -b "$BRANCH"
git add -A
git commit -m "feat!: convert to copier-managed skeleton"
git push -u origin "$BRANCH" || git push -u origin "$BRANCH"

info "Opening pull request..."
GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh pr create \
  --repo "$TEST_ORG/$REPOSITORY_NAME" \
  --title "feat!: convert to copier-managed skeleton" \
  --body "Automated copier conversion via \`migrate.sh\`." \
  --base main \
  --head "$BRANCH"

info "Pull request opened for branch $BRANCH."

# ── Cleanup ──────────────────────────────────────────────────────────────────

info "Cleaning up temp files..."
cd /
rm -rf "$TEMP_PATH"
info "Done!"
