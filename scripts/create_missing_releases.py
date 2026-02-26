#!/usr/bin/env python3
"""Create missing GitHub releases for tf-* repos in the launchbynttdata org.

The old increment_tagged_version workflow created semver tags on merge but never
created GitHub releases.  The new launch-workflows release pipeline requires a
GitHub release to trigger publishing.  This script backfills the missing release
by finding repos that have semver tags but no releases and creating a release at
the latest tag.

Usage:
    python scripts/create_missing_releases.py --repo tf-aws-module_primitive-s3 --dry-run
    python scripts/create_missing_releases.py --all --dry-run
    python scripts/create_missing_releases.py --all
"""

import argparse
import re
import subprocess
import sys

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


# ---------------------------------------------------------------------------
# Semver helpers
# ---------------------------------------------------------------------------

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_semver(tag):
    """Parse a semver tag (vX.Y.Z or X.Y.Z) into a (major, minor, patch) tuple.

    Returns None if the tag is not valid semver.
    """
    m = SEMVER_RE.match(tag.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def get_latest_semver_tag(org, repo):
    """Fetch all tags for a repo, filter to semver, and return the highest.

    Returns the tag name string (e.g. 'v1.2.3') or None if no semver tags exist.
    """
    out = run_cmd(
        [
            "gh", "api", "--paginate",
            f"repos/{org}/{repo}/tags",
            "--jq", ".[].name",
        ]
    )
    if not out.strip():
        return None

    tags = []
    for line in out.strip().split("\n"):
        tag = line.strip()
        version = parse_semver(tag)
        if version is not None:
            tags.append((version, tag))

    if not tags:
        return None

    # Sort by semver tuple and return the tag name of the highest
    tags.sort(key=lambda t: t[0])
    return tags[-1][1]


# ---------------------------------------------------------------------------
# Release helpers
# ---------------------------------------------------------------------------


def has_releases(org, repo):
    """Return True if the repo already has at least one GitHub release."""
    out = run_cmd(
        [
            "gh", "api",
            f"repos/{org}/{repo}/releases",
            "--jq", "length",
        ]
    )
    return int(out.strip()) > 0


def create_release(org, repo, tag):
    """Create a GitHub release at the given tag."""
    run_cmd(
        [
            "gh", "release", "create", tag,
            "--repo", f"{org}/{repo}",
            "--title", tag,
            "--generate-notes",
        ]
    )


# ---------------------------------------------------------------------------
# Per-repo logic
# ---------------------------------------------------------------------------


def process_repo(repo_name, org, dry_run):
    """Orchestrate release creation for one repo. Returns a status string."""
    print(f"\n=== {repo_name} ===")

    try:
        # 1. Find the latest semver tag
        latest_tag = get_latest_semver_tag(org, repo_name)
        if latest_tag is None:
            print("  No semver tags found — skipping")
            return "no_tags"

        print(f"  Latest semver tag: {latest_tag}")

        # 2. Check if releases already exist
        if has_releases(org, repo_name):
            print("  Already has releases — skipping")
            return "has_releases"

        # 3. Create the release (or report what would happen)
        if dry_run:
            print(f"  WOULD CREATE release at {latest_tag}")
            return "would_create"
        else:
            print(f"  Creating release at {latest_tag}...")
            create_release(org, repo_name, latest_tag)
            print(f"  Release created: {latest_tag}")
            return "created"

    except RuntimeError as exc:
        print(f"  ERROR: {exc}")
        return "error"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(results, dry_run):
    """Print a summary of all processed repos."""
    created = results.count("created") + results.count("would_create")
    no_tags = results.count("no_tags")
    has_rel = results.count("has_releases")
    errors = results.count("error")

    print()
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"  Repos processed:        {len(results)}")
    if dry_run:
        print(f"  Would create releases:  {created}")
    else:
        print(f"  Created releases:       {created}")
    print(f"  Skipped (no tags):      {no_tags}")
    print(f"  Skipped (has releases): {has_rel}")
    print(f"  Errors:                 {errors}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Create missing GitHub releases for tf-* repos."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--repo", help="Target a single repo (short name, no org prefix)")
    group.add_argument("--all", action="store_true", help="Target all tf-* repos in the org")

    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without creating releases")
    parser.add_argument("--org", default="launchbynttdata", help="GitHub org (default: launchbynttdata)")

    args = parser.parse_args()

    # Build repo list
    if args.all:
        print("Listing tf-* repos...")
        repos = list_tf_repos(args.org)
        print(f"Found {len(repos)} repos")
    else:
        repos = [args.repo]

    # Process each repo
    results = []
    for repo_name in repos:
        status = process_repo(repo_name, args.org, args.dry_run)
        results.append(status)

    print_summary(results, args.dry_run)


if __name__ == "__main__":
    main()
