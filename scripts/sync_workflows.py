#!/usr/bin/env python3
"""Sync launch-workflows to tf-* repos in the launchbynttdata org.

Migrates legacy repos from actions-lcaf workflows to launch-workflows reusable
workflows, and keeps already-migrated repos on the latest version.

Usage:
    python scripts/sync_workflows.py --repo tf-aws-module_primitive-sqs_queue --dry-run
    python scripts/sync_workflows.py --repo tf-aws-module_primitive-sqs_queue
    python scripts/sync_workflows.py --all --dry-run
    python scripts/sync_workflows.py --all --version 0.14.0
"""

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Legacy files to delete
# ---------------------------------------------------------------------------

LEGACY_FILES = [
    ".github/workflows/increment_tagged_version.yaml",
    ".github/workflows/increment-tagged-version.yaml",
    ".github/workflows/lint-terraform.yaml",
    ".github/workflows/validate-branch-name.yaml",
]

OLD_NAMING_FILES = [
    ".github/workflows/pull-request-terraform-check.yml",
]

# ---------------------------------------------------------------------------
# Template constants — {version} is replaced at runtime via str.replace()
# ---------------------------------------------------------------------------

TEMPLATE_PR_LABEL = """\
name: Label Pull Request

on:
  pull_request:
    types: [opened, reopened, synchronize]

jobs:
  check:
    name: "Label Pull Request"
    permissions:
      contents: read
      issues: write
      pull-requests: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-pr-label-by-branch.yml@{version}
    secrets: inherit # pragma: allowlist secret
"""

TEMPLATE_TF_CHECK_AWS = """\
name: Check AWS Terraform Code

on:
  pull_request:
    types: [opened, reopened, synchronize, ready_for_review]
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  check:
    name: "Check AWS Terraform Code"
    permissions:
      contents: read
      id-token: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check-aws.yml@{version}
    with:
      assume_role_arn: ${{ vars.TERRAFORM_CHECK_AWS_ASSUME_ROLE_ARN }}
      region: ${{ vars.TERRAFORM_CHECK_AWS_REGION }}
    secrets: inherit # pragma: allowlist secret
"""

TEMPLATE_TF_CHECK_AZURE = """\
name: Check Azure Terraform Code

on:
  pull_request:
    types: [opened, reopened, synchronize, ready_for_review]
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  check:
    name: "Check Azure Terraform Code"
    permissions:
      contents: read
      id-token: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-terraform-check-azure.yml@{version}
    secrets: inherit # pragma: allowlist secret
"""

TEMPLATE_RELEASE_PUBLISH = """\
name: Publish Release

on:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  release-on-merge:
    name: "Create and Publish Release on Merge"
    permissions:
      contents: write
      pull-requests: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-release-on-merge.yml@{version}
    secrets: inherit # pragma: allowlist secret
"""

TEMPLATE_RELEASE_DRAFTER = """\
---
name-template: "$RESOLVED_VERSION"
tag-template: "$RESOLVED_VERSION"
template: |
  # Changelog

  $CHANGES

  ---

  See details of [all code changes](https://github.com/$OWNER/$REPOSITORY/compare/$PREVIOUS_TAG...$RESOLVED_VERSION) since previous release.

categories:
  - title: ":warning: Breaking Changes"
    labels:
      - "major"
  - title: "\U0001f680 Features"
    labels:
      - "minor"
  - title: "\U0001f527 Fixes"
    collapse-after: 3
    labels:
      - "patch"

autolabeler:
  - label: "major"
    branch:
      - '/(patch|bug|fix|feature|feat|chore)!\\/.+/'
  - label: "minor"
    branch:
      - '/(feature|feat)\\/.+/'
  - label: "patch"
    branch:
      - '/(patch|bug|fix|chore)\\/.+/'

change-template: "- $TITLE @$AUTHOR (#$NUMBER)"

version-resolver:
  major:
    labels:
      - "major"
  minor:
    labels:
      - "minor"
  patch:
    labels:
      - "patch"
      - "dependencies"
  default: patch
"""

TEMPLATE_DEPENDABOT = """\
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "gomod"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "terraform"
    directory: "/"
    schedule:
      interval: "weekly"
"""

# ---------------------------------------------------------------------------
# Skeleton repo SHA validation
#
# These are the git blob SHAs of the files in lcaf-skeleton-terraform that the
# templates above were derived from.  If the skeleton changes, these SHAs will
# no longer match and the script will refuse to run until a developer updates
# the templates and records the new SHAs here.
#
# To get current SHAs:
#   gh api 'repos/launchbynttdata/lcaf-skeleton-terraform/git/trees/HEAD?recursive=1' \
#     --jq '.tree[] | select(.path | test("^\\.github/(workflows/pull-request|workflows/release-publish|release-drafter|dependabot)")) | "\(.path) \(.sha)"'
# ---------------------------------------------------------------------------

SKELETON_REPO = "lcaf-skeleton-terraform"

SKELETON_SHAS = {
    ".github/dependabot.yml": "7fa88bc19905c8f7f91e4e1dde16907704698d26",
    ".github/release-drafter.yml": "6ab7d45d7386af7b9bdde2672abb1b0a251036d8",
    ".github/workflows/pull-request-label.yml": "419a624fe4ca505fb4ed9ea345be0f67281b90c3",
    ".github/workflows/pull-request-terraform-check-aws.yml": "ca7bde6a9ad9dde8b917519691f6bb02f7f2f075",
    ".github/workflows/pull-request-terraform-check-azure.yml": "9eba6b22d9ca2c9a77b4b01fa85c925735b72c3d",
    ".github/workflows/release-publish.yml": "ce5037ca825c595ce7d151949ba2c966a7b8af3b",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_cmd(cmd, cwd=None, capture=True, check=True):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\nstderr: {result.stderr.strip()}"
        )
    return result.stdout if capture else result


def validate_skeleton(org):
    """Check that the skeleton repo files haven't changed since templates were last synced.

    Fetches the current blob SHAs from lcaf-skeleton-terraform and compares
    them against SKELETON_SHAS.  Returns normally if everything matches.
    Exits with an error message listing the changed files if any differ.
    """
    try:
        out = run_cmd([
            "gh", "api",
            f"repos/{org}/{SKELETON_REPO}/git/trees/HEAD?recursive=1",
        ])
    except RuntimeError as exc:
        print(f"ERROR: Could not fetch skeleton repo tree: {exc}", file=sys.stderr)
        sys.exit(1)

    tree = json.loads(out)
    current = {item["path"]: item["sha"] for item in tree.get("tree", [])}

    changed = []
    missing = []
    for path, expected_sha in SKELETON_SHAS.items():
        actual_sha = current.get(path)
        if actual_sha is None:
            missing.append(path)
        elif actual_sha != expected_sha:
            changed.append(path)

    if not changed and not missing:
        return  # all good

    print(
        "ERROR: The skeleton repo (lcaf-skeleton-terraform) has changed since the\n"
        "templates in this script were last updated.  The hardcoded templates may\n"
        "be stale and must be reviewed before applying to other repos.\n",
        file=sys.stderr,
    )
    for path in changed:
        print(f"  CHANGED: {path}", file=sys.stderr)
    for path in missing:
        print(f"  MISSING: {path}", file=sys.stderr)
    print(
        "\nTo fix:\n"
        "  1. Review the changes in the skeleton repo\n"
        "  2. Update the TEMPLATE_* constants in this script\n"
        "  3. Update SKELETON_SHAS with the new blob SHAs (see comment above the dict)\n",
        file=sys.stderr,
    )
    sys.exit(1)


def get_latest_version(org):
    """Query the latest release tag from launch-workflows."""
    out = run_cmd(
        ["gh", "api", f"repos/{org}/launch-workflows/releases/latest", "--jq", ".tag_name"]
    )
    return out.strip()


def list_tf_repos(org):
    """List all public tf-* repos in the org via gh api with pagination."""
    out = run_cmd(
        [
            "gh", "api", "--paginate",
            f"/orgs/{org}/repos?type=public&per_page=100",
            "--jq", ".[].name",
        ]
    )
    names = sorted(
        n.strip() for n in out.strip().split("\n")
        if n.strip().startswith("tf-")
    )
    return names


def detect_provider(repo_name, provider_override=None):
    """Return 'aws' or 'azure' from the repo name prefix, or raise."""
    if provider_override:
        return provider_override
    if repo_name.startswith("tf-aws-"):
        return "aws"
    if repo_name.startswith("tf-azurerm-") or repo_name.startswith("tf-azureado-"):
        return "azure"
    raise ValueError(
        f"Cannot detect cloud provider for '{repo_name}'. "
        "Use --provider aws|azure to override."
    )


def get_expected_files(provider, version):
    """Return dict of {relative_path: content} for the target state."""
    tf_check_template = TEMPLATE_TF_CHECK_AWS if provider == "aws" else TEMPLATE_TF_CHECK_AZURE
    tf_check_filename = (
        "pull-request-terraform-check-aws.yml"
        if provider == "aws"
        else "pull-request-terraform-check-azure.yml"
    )

    files = {
        ".github/workflows/pull-request-label.yml": TEMPLATE_PR_LABEL.replace("{version}", version),
        f".github/workflows/{tf_check_filename}": tf_check_template.replace("{version}", version),
        ".github/workflows/release-publish.yml": TEMPLATE_RELEASE_PUBLISH.replace("{version}", version),
        ".github/release-drafter.yml": TEMPLATE_RELEASE_DRAFTER,
        ".github/dependabot.yml": TEMPLATE_DEPENDABOT,
    }
    return files


# ---------------------------------------------------------------------------
# API helpers for dry-run mode
# ---------------------------------------------------------------------------


def fetch_tree(org, repo_name):
    """Fetch the repo's full file tree via the Git Trees API. Returns a list of tree entries."""
    try:
        out = run_cmd(
            ["gh", "api", f"repos/{org}/{repo_name}/git/trees/HEAD?recursive=1"]
        )
        data = json.loads(out)
        return data.get("tree", [])
    except RuntimeError:
        return None


def fetch_file_content(org, repo_name, path):
    """Fetch a single file's content via the Contents API. Returns string or None."""
    try:
        out = run_cmd(
            ["gh", "api", f"repos/{org}/{repo_name}/contents/{path}", "--jq", ".content"]
        )
        raw = out.strip()
        if not raw or raw == "null":
            return None
        return base64.b64decode(raw).decode("utf-8")
    except (RuntimeError, Exception):
        return None


def extract_versions(content):
    """Extract launch-workflows version refs from file content."""
    return re.findall(r"launch-workflows/[^@]+@(\d+\.\d+\.\d+)", content)


# ---------------------------------------------------------------------------
# Dry-run logic
# ---------------------------------------------------------------------------


def dry_run_repo(repo_name, org, version, provider_override):
    """Analyse a single repo and print what would change."""
    try:
        provider = detect_provider(repo_name, provider_override)
    except ValueError as exc:
        print(f"\n=== {repo_name} ===")
        print(f"  SKIP ({exc})")
        return

    expected = get_expected_files(provider, version)
    tree = fetch_tree(org, repo_name)

    if tree is None:
        print(f"\n=== {repo_name} ===")
        print("  SKIP (empty or inaccessible repo)")
        return

    tree_paths = {item["path"] for item in tree}

    # Check for legacy files
    legacy_present = [f for f in LEGACY_FILES if f in tree_paths]
    old_naming = [f for f in OLD_NAMING_FILES if f in tree_paths]
    files_to_delete = legacy_present + old_naming
    is_legacy = bool(legacy_present)

    changes = []          # list of (action, path, detail)
    up_to_date_count = 0
    current_versions = set()

    for f in files_to_delete:
        changes.append(("DELETE", f, None))

    for path, expected_content in expected.items():
        if path not in tree_paths or is_legacy:
            changes.append(("CREATE", path, None))
        else:
            # Migrated repo — fetch content and compare
            current_content = fetch_file_content(org, repo_name, path)
            if current_content is None:
                changes.append(("CREATE", path, None))
                continue

            vers = extract_versions(current_content)
            current_versions.update(vers)

            if current_content == expected_content:
                up_to_date_count += 1
            else:
                old_ver = vers[0] if vers else None
                changes.append(("UPDATE", path, old_ver))

    # Determine state label
    if is_legacy:
        state_label = f"legacy \u2192 {provider}"
    elif not changes:
        state_label = "up to date"
    else:
        ver_str = "/".join(sorted(current_versions)) if current_versions else "unknown"
        state_label = f"update {ver_str} \u2192 {version}"

    # Print
    print(f"\n=== {repo_name} ({state_label}) ===")
    if not changes:
        print(f"  SKIP (all files match version {version})")
    else:
        for action, path, detail in changes:
            if action == "UPDATE" and detail:
                print(f"  {action} {path} ({detail} \u2192 {version})")
            else:
                print(f"  {action} {path}")
        if up_to_date_count > 0:
            print(f"  ({up_to_date_count} files already up to date)")


# ---------------------------------------------------------------------------
# Apply logic
# ---------------------------------------------------------------------------


def apply_repo(repo_name, org, version, provider_override, branch):
    """Clone, branch, edit, commit, push, and open a PR for a single repo."""
    try:
        provider = detect_provider(repo_name, provider_override)
    except ValueError as exc:
        print(f"\n=== {repo_name} ===")
        print(f"  SKIP ({exc})")
        return

    expected = get_expected_files(provider, version)

    tmpdir = tempfile.mkdtemp(prefix="sync_wf_")
    clone_dir = os.path.join(tmpdir, repo_name)

    try:
        print(f"\n=== {repo_name} ===")

        # Clone
        print(f"  Cloning {org}/{repo_name}...")
        run_cmd(["gh", "repo", "clone", f"{org}/{repo_name}", clone_dir, "--", "--depth=1"])

        # Detect state before changes
        legacy_files = [f for f in LEGACY_FILES if os.path.exists(os.path.join(clone_dir, f))]
        old_naming = [f for f in OLD_NAMING_FILES if os.path.exists(os.path.join(clone_dir, f))]
        is_legacy = bool(legacy_files)

        # Check if branch already exists on remote
        ls_out = run_cmd(
            ["git", "ls-remote", "--heads", "origin", branch],
            cwd=clone_dir,
        )
        if ls_out.strip():
            print(f"  SKIP (branch '{branch}' already exists on remote — PR may already be open)")
            return

        # Create branch
        run_cmd(["git", "checkout", "-b", branch], cwd=clone_dir)

        # Delete legacy and old-naming files
        for f in legacy_files + old_naming:
            fpath = os.path.join(clone_dir, f)
            os.remove(fpath)
            print(f"  DELETE {f}")

        # Write expected files
        for path, content in expected.items():
            fpath = os.path.join(clone_dir, path)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)

            action = "CREATE"
            if os.path.exists(fpath):
                with open(fpath, "r") as fh:
                    if fh.read() == content:
                        continue  # already correct
                action = "UPDATE"

            with open(fpath, "w") as fh:
                fh.write(content)
            print(f"  {action} {path}")

        # Stage and check for changes
        run_cmd(["git", "add", "-A"], cwd=clone_dir)
        status_out = run_cmd(["git", "status", "--porcelain"], cwd=clone_dir)
        if not status_out.strip():
            print("  SKIP (no changes needed)")
            return

        # Commit
        if is_legacy:
            title = f"chore: migrate to launch-workflows {version}"
        else:
            title = f"chore: update launch-workflows to {version}"

        run_cmd(["git", "commit", "-m", title], cwd=clone_dir)

        # Push
        print(f"  Pushing branch '{branch}'...")
        run_cmd(["git", "push", "-u", "origin", branch], cwd=clone_dir)

        # Build PR body
        status_lines = status_out.strip().split("\n")
        file_list = "\n".join(f"- `{line.strip()}`" for line in status_lines)

        legacy_line = ""
        if is_legacy:
            legacy_line = "- Removed legacy `actions-lcaf` workflow files\n"

        body = (
            "## Summary\n"
            f"- {'Migrated CI workflows to use' if is_legacy else 'Updated'} "
            f"`launch-workflows` reusable workflows at version `{version}`\n"
            f"{legacy_line}"
            "- Added/updated `release-drafter.yml` and `dependabot.yml`\n"
            "\n"
            "## Files changed\n"
            f"{file_list}\n"
            "\n"
            "---\n"
            f"Generated by `sync_workflows.py` from "
            f"[launch-workflows](https://github.com/{org}/launch-workflows)\n"
        )

        # Create PR
        print("  Creating PR...")
        pr_out = run_cmd(
            [
                "gh", "pr", "create",
                "--repo", f"{org}/{repo_name}",
                "--title", title,
                "--body", body,
                "--head", branch,
            ],
            cwd=clone_dir,
        )
        pr_url = pr_out.strip()
        print(f"  PR created: {pr_url}")

        # Ensure the "patch" label exists (legacy repos may not have it)
        run_cmd(
            ["gh", "label", "create", "patch", "--color", "006b75", "--force",
             "--repo", f"{org}/{repo_name}"],
            check=False,
        )

        # Apply the "patch" label to the PR
        run_cmd(
            ["gh", "pr", "edit", pr_url, "--add-label", "patch",
             "--repo", f"{org}/{repo_name}"],
        )
        print("  Label 'patch' applied")

    except RuntimeError as exc:
        print(f"  ERROR: {exc}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Sync launch-workflows to tf-* repos in a GitHub org."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", help="Target a single repo (short name, no org prefix)")
    group.add_argument("--all", action="store_true", help="Target all tf-* repos in the org")

    parser.add_argument("--dry-run", action="store_true", help="Show what would change without pushing")
    parser.add_argument("--version", help="launch-workflows version to pin (default: latest release tag)")
    parser.add_argument("--provider", choices=["aws", "azure"], help="Override cloud provider auto-detection")
    parser.add_argument("--org", default="launchbynttdata", help="GitHub org (default: launchbynttdata)")
    parser.add_argument("--branch", default="chore/sync-workflows", help="PR branch name (default: chore/sync-workflows)")

    parser.add_argument(
        "--skip-skeleton-check", action="store_true",
        help="Skip validation that templates match the skeleton repo (use with caution)",
    )

    args = parser.parse_args()

    # Validate templates against skeleton repo
    if not args.skip_skeleton_check:
        print("Validating templates against skeleton repo...")
        validate_skeleton(args.org)

    # Resolve version
    if args.version:
        version = args.version
    else:
        print("Fetching latest launch-workflows version...")
        version = get_latest_version(args.org)

    print(f"Target version: {version}")

    # Build repo list
    if args.all:
        print("Listing tf-* repos...")
        repos = list_tf_repos(args.org)
        print(f"Found {len(repos)} repos")
    else:
        repos = [args.repo]

    # Process each repo
    for repo_name in repos:
        if args.dry_run:
            dry_run_repo(repo_name, args.org, version, args.provider)
        else:
            apply_repo(repo_name, args.org, version, args.provider, args.branch)

    print()


if __name__ == "__main__":
    main()
