#!/usr/bin/env bash
# Audition Dependabot configurations by creating a test-org copy of a source
# repo for each config file in dependabot-configs/.
#
# For every YAML file in dependabot-configs/ the script:
#   1. Creates a fresh private repo in the test organization.
#   2. Pushes the main branch of the source repo (without .github/).
#   3. Populates .github/dependabot.yml from the config file.
#   4. Sets the repo description to the test-case description (line 2 of the config).
#
# Usage:
#   bash scripts/dependabot_config_audition.sh

set -euo pipefail

PRIMARY_ORG="launchbynttdata"
TEST_ORG="nttdtest"
SOURCE_REPOS=(
  "tf-azurerm-module_primitive-dns_zone"
  "tf-aws-module_primitive-iam_role"
)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGS_DIR="$SCRIPT_DIR/dependabot-configs"

info()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*"; }
error() { printf '\033[1;31m[ERROR]\033[0m %s\n' "$*" >&2; }
die()   { error "$@"; exit 1; }

# ── Prerequisites ───────────────────────────────────────────────────────────

if ! command -v gh &>/dev/null; then
  die "gh CLI is not installed."
fi

# Verify config directory has YAML files.
shopt -s nullglob
CONFIG_FILES=("$CONFIGS_DIR"/*.yaml "$CONFIGS_DIR"/*.yml)
shopt -u nullglob

if [[ ${#CONFIG_FILES[@]} -eq 0 ]]; then
  die "No YAML config files found in $CONFIGS_DIR"
fi

info "Found ${#CONFIG_FILES[@]} config file(s) to audition across ${#SOURCE_REPOS[@]} source repo(s)."

# ── Clone source repos once ─────────────────────────────────────────────────

TEMP_PATH=$(mktemp -d)
for SOURCE_REPO in "${SOURCE_REPOS[@]}"; do
  info "Cloning source repo $PRIMARY_ORG/$SOURCE_REPO..."
  git clone "https://github.com/$PRIMARY_ORG/$SOURCE_REPO.git" "$TEMP_PATH/$SOURCE_REPO"
done

# ── Process each source repo × config combination ───────────────────────────

for SOURCE_REPO in "${SOURCE_REPOS[@]}"; do
for CONFIG_FILE in "${CONFIG_FILES[@]}"; do
  CONFIG_NAME="$(basename "$CONFIG_FILE" .yaml)"
  CONFIG_NAME="$(basename "$CONFIG_NAME" .yml)"

  TEST_REPO_NAME="${SOURCE_REPO}-dependabot-${CONFIG_NAME}"
  TEST_REPO_URL="https://github.com/$TEST_ORG/$TEST_REPO_NAME.git"

  # Extract the description from the second line of the config file.
  DESCRIPTION="$(sed -n '2p' "$CONFIG_FILE" | sed 's/^#\s*//')"

  info "──────────────────────────────────────────────────────────────"
  info "Config: $(basename "$CONFIG_FILE")  →  $TEST_ORG/$TEST_REPO_NAME"
  info "Description: $DESCRIPTION"

  # ── Create test repo ────────────────────────────────────────────────────

  if GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo view "$TEST_ORG/$TEST_REPO_NAME" &>/dev/null; then
    info "Deleting existing repo $TEST_ORG/$TEST_REPO_NAME..."
    GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo delete "$TEST_ORG/$TEST_REPO_NAME" --yes
  fi

  info "Creating fresh repo $TEST_ORG/$TEST_REPO_NAME..."
  GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo create "$TEST_ORG/$TEST_REPO_NAME" --private

  sleep 2 # Wait a moment for GitHub to be ready to accept pushes to the new repo.

  info "Configuring repo settings..."
  GITHUB_TOKEN=$GITHUB_TOKEN_nttdtest gh repo edit "$TEST_ORG/$TEST_REPO_NAME" \
    --description "$DESCRIPTION" \
    --enable-rebase-merge=false \
    --enable-merge-commit=false \
    --enable-squash-merge \
    --enable-auto-merge \
    --delete-branch-on-merge

  # ── Prepare and push main branch ───────────────────────────────────────

  WORK_PATH=$(mktemp -d)
  cp -a "$TEMP_PATH/$SOURCE_REPO" "$WORK_PATH/repo"
  cd "$WORK_PATH/repo"

  # Wipe .github/ entirely.
  git rm -r --quiet .github/ 2>/dev/null || true

  # Populate .github/dependabot.yml from the config file.
  mkdir -p .github
  cp "$CONFIG_FILE" .github/dependabot.yml
  git add .github/dependabot.yml

  git commit -m "chore: set up dependabot audition ($CONFIG_NAME)"

  git remote remove origin
  git remote add origin "https://x-access-token:${GITHUB_TOKEN_nttdtest}@github.com/$TEST_ORG/$TEST_REPO_NAME.git"
  git push -u origin main -f || git push -u origin main -f

  info "Test repo ready: $TEST_ORG/$TEST_REPO_NAME"

  # ── Clean up working copy ──────────────────────────────────────────────

  cd /
  rm -rf "$WORK_PATH"
done
done

# ── Final cleanup ────────────────────────────────────────────────────────────

rm -rf "$TEMP_PATH"
info "All dependabot audition repos created. Done!"