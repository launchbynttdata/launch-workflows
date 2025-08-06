import os
from time import sleep

from github.Repository import Repository

from src.launch_github import (
    WorkflowRunConclusion,
    WorkflowRunStatus,
    get_workflow_run_logs,
    populate_readme_file,
    wait_for_workflow_run_completion,
    wait_for_workflow_run_create,
)

LAUNCH_WORKFLOWS_REF_TO_TEST = os.environ.get("LAUNCH_WORKFLOWS_REF_TO_TEST", "main")


def populate_release_drafter_config(repository: Repository):
    content = """
---
name-template: "$RESOLVED_VERSION"
tag-template: "$RESOLVED_VERSION"
template: |
  # Changelog

  $CHANGES

  ---

  See details of [all code changes](https://github.com/$OWNER/$REPOSITORY/compare/$PREVIOUS_TAG...v$RESOLVED_VERSION) since previous release.

categories:
  - title: ":warning: Breaking Changes"
    labels:
      - "major"
  - title: "🚀 Features"
    labels:
      - "minor"
  - title: "🔧 Fixes"
    collapse-after: 3
    labels:
      - "patch"

autolabeler:
  - label: "major"
    branch:
      - '/(patch|bug|fix|feature)!\\/.+/'
  - label: "minor"
    branch:
      - '/feature\\/.+/'
  - label: "patch"
    branch:
      - '/(patch|bug|fix)\\/.+/'

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

    repository.create_file(
        ".github/release-drafter.yml",
        content=content,
        branch="main",
        message="Add Release Drafter configuration",
    )


def populate_workflow_file(repository: Repository):
    content = f"""
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
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-pr-label-by-branch.yml@{LAUNCH_WORKFLOWS_REF_TO_TEST}
    secrets: inherit # pragma: allowlist secret
"""

    repository.create_file(
        ".github/workflows/pull-request-label.yml",
        content=content,
        branch="main",
        message="Add workflow file for reusable PR label by branch",
    )


def test_reusable_pr_label_by_branch(temporary_repository):
    github_repo, _ = temporary_repository

    # Set up initial state on main branch
    populate_workflow_file(repository=github_repo)
    populate_release_drafter_config(repository=github_repo)

    branch_name_label_map = {
        "first_pr_always_major_regardless_of_name": ["major"],
        "bug/something": ["patch"],
        "fix/something": ["patch"],
        "patch/something": ["patch"],
        "feature/something": ["minor"],
        "bug!/breaking": ["major"],
        "fix!/breaking": ["major"],
        "patch!/breaking": ["major"],
        "feature!/breaking": ["major"],
        "unexpected/prefix": [],
    }
    sleep(1)

    main_commit_sha = github_repo.get_branch("main").commit.sha

    for branch_name, expected_labels in branch_name_label_map.items():
        github_repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_commit_sha)
        sleep(1)
        populate_readme_file(github_repo, branch=branch_name)
        pull_request = github_repo.create_pull(
            base="main",
            head=branch_name,
            title=f"Test PR Label for {branch_name} - Happy Path",
            body=f"This is a test pull request to validate the autolabeler applies the {expected_labels} label to the branch name {branch_name}.",
        )

        workflow = github_repo.get_workflow(id_or_file_name="pull-request-label.yml")
        workflow_run = wait_for_workflow_run_create(
            workflow=workflow, branch=branch_name
        )
        status = wait_for_workflow_run_completion(workflow_run=workflow_run)
        if status != WorkflowRunStatus.COMPLETED:
            raise AssertionError(
                f"Workflow run for {branch_name} did not complete successfully: {status}"
            )
        if workflow_run.conclusion != WorkflowRunConclusion.SUCCESS:
            logs = get_workflow_run_logs(workflow_run, drop_log_timestamps=True)
            raise AssertionError(
                f"Workflow run for {branch_name} did not succeed as expected: {workflow_run.conclusion}\nLogs:\n{logs}"
            )
        pr_labels = [label.name for label in pull_request.get_labels()]
        if expected_labels != pr_labels:
            sleep(90)
            raise AssertionError(
                f"Expected labels '{expected_labels}' didn't match pull request: {pr_labels} for branch {branch_name}"
            )
