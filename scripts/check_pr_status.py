#!/usr/bin/env python3
"""Check the status of sync-workflows PRs across tf-* repos.

After running sync_workflows.py --all, use this script to see which repos have
the sync branch, whether an open PR exists, and whether CI checks are passing.

Optionally generates a CSV file for tracking PR completion in a shared
spreadsheet (Google Sheets, Excel, etc.).

Usage:
    python scripts/check_pr_status.py
    python scripts/check_pr_status.py --csv pr_status.csv
    python scripts/check_pr_status.py --branch chore/sync-workflows
    python scripts/check_pr_status.py --branch nonexistent
"""

import argparse
import csv
import json
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
# Per-repo logic
# ---------------------------------------------------------------------------


def check_repo(repo_name, org, branch):
    """Check branch/PR/checks status for one repo.

    Returns (status, detail) where detail is a PR URL or None.
    Statuses: passing, failing, pending, no_checks, no_pr, no_branch, error
    """
    try:
        # 1. Check if the branch exists
        result = run_cmd(
            ["gh", "api", f"repos/{org}/{repo_name}/git/ref/heads/{branch}"],
            check=False, capture=False,
        )
        if result.returncode != 0:
            return ("no_branch", None)

        # 2. Check for an open PR from that branch
        pr_json = run_cmd(
            [
                "gh", "pr", "list",
                "--repo", f"{org}/{repo_name}",
                "--head", branch,
                "--state", "open",
                "--json", "url",
            ]
        )
        prs = json.loads(pr_json)
        if not prs:
            return ("no_pr", None)

        pr_url = prs[0]["url"]

        # 3. Check CI status on the PR
        checks_result = run_cmd(
            [
                "gh", "pr", "checks", pr_url,
                "--json", "name,state",
            ],
            check=False, capture=False,
        )
        if checks_result.returncode != 0:
            # gh pr checks exits non-zero when checks fail, but still outputs JSON
            # Try to parse whatever we got
            checks_out = checks_result.stdout
        else:
            checks_out = checks_result.stdout

        if not checks_out.strip():
            return ("no_checks", pr_url)

        checks = json.loads(checks_out)
        if not checks:
            return ("no_checks", pr_url)

        states = {c.get("state", "").upper() for c in checks}

        if "FAILURE" in states or "ERROR" in states:
            return ("failing", pr_url)
        if "PENDING" in states or "QUEUED" in states or "IN_PROGRESS" in states:
            return ("pending", pr_url)
        if states <= {"SUCCESS", "SKIPPED", "NEUTRAL"}:
            return ("passing", pr_url)

        # Unexpected states — treat as pending
        return ("pending", pr_url)

    except RuntimeError as exc:
        print(f"  ERROR: {exc}", file=sys.stderr)
        return ("error", None)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

STATUS_ORDER = ["passing", "failing", "pending", "no_checks", "no_pr", "no_branch", "error"]
STATUS_LABELS = {
    "passing": "Passing (all checks green)",
    "failing": "Failing (checks failed)",
    "pending": "Pending (checks running)",
    "no_checks": "No checks registered",
    "no_pr": "Branch exists, no open PR",
    "no_branch": "No branch",
    "error": "Error",
}


def print_summary(results, branch):
    """Print a grouped summary of all results."""
    # Group by status
    grouped = {}
    for repo, status, detail in results:
        grouped.setdefault(status, []).append((repo, detail))

    print()
    print("=" * 60)
    print(f"Summary — branch: {branch}")
    print("=" * 60)
    print(f"  Total repos checked: {len(results)}")
    for status in STATUS_ORDER:
        repos = grouped.get(status, [])
        print(f"  {STATUS_LABELS[status]:35s} {len(repos)}")

    # Detail listings for statuses with PRs (skip no_branch — too many)
    for status in ["passing", "failing", "pending", "no_checks", "no_pr"]:
        repos = grouped.get(status, [])
        if not repos:
            continue
        print()
        print(f"--- {STATUS_LABELS[status]} ({len(repos)}) ---")
        for repo, detail in sorted(repos):
            if detail:
                print(f"  {repo:50s} {detail}")
            else:
                print(f"  {repo}")

    errors = grouped.get("error", [])
    if errors:
        print()
        print(f"--- Errors ({len(errors)}) ---")
        for repo, _ in sorted(errors):
            print(f"  {repo}")


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

CSV_COLUMNS = ["Repo", "PR URL", "CI Status", "Owner", "Tracking Status", "Notes"]


def write_csv(results, path, branch):
    """Write a CSV tracking file for repos that have a branch (skip no_branch).

    Includes empty Owner / Tracking Status / Notes columns for manual use in a
    shared spreadsheet.
    """
    # Only include repos where the branch exists (actionable items)
    actionable = [(repo, status, detail) for repo, status, detail in results
                  if status != "no_branch"]

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)
        for repo, status, detail in sorted(actionable):
            writer.writerow([
                repo,
                detail or "",
                status,
                "",  # Owner — to be filled in manually
                "",  # Tracking Status — to be filled in manually
                "",  # Notes — to be filled in manually
            ])

    print(f"\nWrote {len(actionable)} rows to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Check sync-workflows PR status across tf-* repos."
    )
    parser.add_argument(
        "--branch", default="chore/sync-workflows",
        help="Branch name to check (default: chore/sync-workflows)",
    )
    parser.add_argument(
        "--org", default="launchbynttdata",
        help="GitHub org (default: launchbynttdata)",
    )
    parser.add_argument(
        "--csv", metavar="FILE",
        help="Write a CSV tracking file (for import into Google Sheets / Excel)",
    )

    args = parser.parse_args()

    print(f"Listing tf-* repos in {args.org}...")
    repos = list_tf_repos(args.org)
    print(f"Found {len(repos)} repos")

    results = []
    for i, repo_name in enumerate(repos, 1):
        print(f"  [{i}/{len(repos)}] {repo_name}...", end="", flush=True)
        status, detail = check_repo(repo_name, args.org, args.branch)
        print(f" {status}")
        results.append((repo_name, status, detail))

    print_summary(results, args.branch)

    if args.csv:
        write_csv(results, args.csv, args.branch)


if __name__ == "__main__":
    main()
