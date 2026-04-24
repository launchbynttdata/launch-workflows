#!/bin/bash
# Clone the current repo to a test organization for testing in a clean environment.
# Usage: bash scripts/clone_to_test_organization.sh REPOSITORY_NAME

# https://github.com/nttdtest/tf-azurerm-module_primitive-storage_account.git

PRIMARY_ORG="launchbynttdata"
TEST_ORG="nttdtest"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 REPOSITORY_NAME"
  exit 1
fi

REPOSITORY_NAME="$1"

PRIMARY_REPO_URL="https://github.com/$PRIMARY_ORG/$REPOSITORY_NAME.git"
TEST_REPO_URL="https://github.com/$TEST_ORG/$REPOSITORY_NAME.git"

echo "Cloning $PRIMARY_ORG/$REPOSITORY_NAME to $TEST_ORG/$REPOSITORY_NAME..."

# Delete the test repo if it already exists, then create a fresh empty one.
if GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo view "$TEST_ORG/$REPOSITORY_NAME" &>/dev/null; then
  echo "Deleting existing repo $TEST_ORG/$REPOSITORY_NAME..."
  GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo delete "$TEST_ORG/$REPOSITORY_NAME" --yes
fi

echo "Creating fresh repo $TEST_ORG/$REPOSITORY_NAME..."
GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo create "$TEST_ORG/$REPOSITORY_NAME" --private

echo "Configuring repo settings for $TEST_ORG/$REPOSITORY_NAME..."
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

# Sort tags by their commit date (oldest first) so releases are created in order.
SORTED_TAGS=()
while IFS= read -r t; do
  SORTED_TAGS+=("$t")
done < <(git tag --sort=creatordate)

if [[ ${#SORTED_TAGS[@]} -eq 0 ]]; then
  echo "No tags found — skipping release copy."
else
  # Copy all releases except the last one; the final release will be handled by workflows.
  LAST_INDEX=$(( ${#SORTED_TAGS[@]} - 1 ))

  # Push all tags except the last one to the test repo before creating releases.
  echo "Pushing tags to $TEST_ORG/$REPOSITORY_NAME..."
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
      echo "Creating release $tag (${i+1}/${#SORTED_TAGS[@]})..."
      GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh release create "$tag" \
        --repo "$TEST_ORG/$REPOSITORY_NAME" \
        --target "$TAG_COMMIT" \
        --title "$RELEASE_TITLE" \
        --notes "$RELEASE_BODY" \
        --verify-tag
    else
      echo "Skipping final release $tag — will be handled by workflows after .github/ is restored."
    fi
  done

  # Restore .github/ and force-push to main so workflows can create the final release.
  echo "Restoring .github/ folder..."
  git checkout HEAD~1 -- .github/
  rm -fr .github/dependabot.yml # Remove dependabot config, will be overlaid by copier
  git add .github/
  git commit -m "chore: restore .github/ for workflow-managed releases"
  git push origin main -f || git push origin main -f
fi

echo "Repository cloned to $TEST_ORG/$REPOSITORY_NAME. Cleaning up local temp files..."
cd /
rm -rf "$TEMP_PATH"
echo "Done!"
