import os

from src.launch_github import (
    WorkflowRunConclusion,
    WorkflowRunStatus,
    branch_created,
    get_workflow_run_logs,
    populate_file,
    workflow_run_completed,
    workflow_run_created,
)

LAUNCH_WORKFLOWS_REF_TO_TEST = os.environ.get("LAUNCH_WORKFLOWS_REF_TO_TEST", "main")
RELEASE_DRAFTER_CONFIG_CONTENTS = """
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
WORKFLOW_CONTENTS = f"""
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


def test_reusable_pr_label_by_branch(temporary_repository):
    branch_name_label_map = {
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

    with branch_created(temporary_repository, "main") as main:
        populate_file(
            repository=temporary_repository,
            path=".github/release-drafter.yml",
            content=RELEASE_DRAFTER_CONFIG_CONTENTS,
            branch=main.name,
            commit_message="Add release drafter configuration file",
        )
        populate_file(
            repository=temporary_repository,
            path=".github/workflows/pull-request-label.yml",
            content=WORKFLOW_CONTENTS,
            branch=main.name,
            commit_message="Add reusable PR label workflow file",
        )
        for branch_name, expected_labels in branch_name_label_map.items():
            with branch_created(
                temporary_repository, branch_name, origin_branch=main.name
            ) as branch:
                populate_file(
                    repository=temporary_repository,
                    path="test.txt",
                    content="Test file",
                    branch=branch.name,
                )

                pull_request = temporary_repository.create_pull(
                    base="main",
                    head=branch_name,
                    title=f"Test PR Label for {branch_name}",
                    body=f"This is a test pull request to validate the autolabeler applies the {expected_labels} label to the branch name {branch_name}.",
                )
                workflow = temporary_repository.get_workflow(
                    id_or_file_name="pull-request-label.yml"
                )

                with workflow_run_created(workflow, branch=branch.name) as run:
                    with workflow_run_completed(run) as status:
                        if status != WorkflowRunStatus.COMPLETED:
                            raise AssertionError(
                                f"Workflow run for {branch_name} did not complete successfully: {status}"
                            )
                        if run.conclusion != WorkflowRunConclusion.SUCCESS:
                            logs = get_workflow_run_logs(run, drop_log_timestamps=True)
                            raise AssertionError(
                                f"Workflow run for {branch_name} did not succeed as expected: {run.conclusion}\nLogs:\n{logs}"
                            )
                        pr_labels = [label.name for label in pull_request.get_labels()]
                        if expected_labels != pr_labels:
                            raise AssertionError(
                                f"Expected labels '{expected_labels}' didn't match pull request: {pr_labels} for branch {branch_name}"
                            )
