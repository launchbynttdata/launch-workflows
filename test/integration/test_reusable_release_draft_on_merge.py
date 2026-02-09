import os

import pytest

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
PR_WORKFLOW_CONTENTS = f"""
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
RELEASE_WORKFLOW_CONTENTS = f"""
name: Draft Release

on:
  push:
    branches:
      - main

permissions:
  contents: read

jobs:
  draft-release:
    name: "Draft Release on Merge"
    permissions:
      contents: write
      pull-requests: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-release-draft-on-merge.yml@{LAUNCH_WORKFLOWS_REF_TO_TEST}
    secrets: inherit # pragma: allowlist secret
"""


@pytest.mark.parametrize(
    "branch_name, expected_tag",
    [
        ("fix/patch", "0.1.0"),
        ("feature/minor", "0.1.0"),
        ("patch!/major", "0.1.0"),
    ],
)
def test_reusable_release_draft_empty_repository(
    temporary_repository, branch_name, expected_tag
):
    """In a brand new repository without any releases, the first release
    _always_ has a zero major version per the SemVer spec.

    For more info:
        - https://semver.org/spec/v2.0.0.html
        - https://github.com/release-drafter/release-drafter/issues/1391
    """

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
            content=PR_WORKFLOW_CONTENTS,
            branch=main.name,
            commit_message="Add reusable PR label workflow file",
        )
        populate_file(
            repository=temporary_repository,
            path=".github/workflows/release-draft.yml",
            content=RELEASE_WORKFLOW_CONTENTS,
            branch=main.name,
            commit_message="Add reusable release draft workflow file",
        )

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
                body=f"This is a test pull request to validate the workflow drafts a release for {expected_tag}.",
            )
            label_workflow = temporary_repository.get_workflow(
                id_or_file_name="pull-request-label.yml"
            )

            with workflow_run_created(label_workflow, branch=branch.name) as label_run:
                with workflow_run_completed(label_run) as status:
                    if status != WorkflowRunStatus.COMPLETED:
                        raise AssertionError(
                            f"Workflow run for {branch_name} did not complete successfully: {status}"
                        )
                    if label_run.conclusion != WorkflowRunConclusion.SUCCESS:
                        logs = get_workflow_run_logs(
                            label_run, drop_log_timestamps=True
                        )
                        raise AssertionError(
                            f"Workflow run for {branch_name} did not succeed as expected: {label_run.conclusion}\nLogs:\n{logs}"
                        )
                    pr_labels = [label.name for label in pull_request.get_labels()]
                    assert (
                        pr_labels
                    ), "Expected at least one label to be applied to the pull request!"

            pull_request.merge()

            release_workflow = temporary_repository.get_workflow(
                id_or_file_name="release-draft.yml"
            )

            with workflow_run_created(
                release_workflow, branch=main.name
            ) as drafter_run:
                with workflow_run_completed(drafter_run) as status:
                    if status != WorkflowRunStatus.COMPLETED:
                        raise AssertionError(
                            f"Release drafter workflow run did not complete successfully: {status}"
                        )
                    if drafter_run.conclusion != WorkflowRunConclusion.SUCCESS:
                        logs = get_workflow_run_logs(
                            drafter_run, drop_log_timestamps=True
                        )
                        raise AssertionError(
                            f"Release drafter workflow run did not succeed as expected: {drafter_run.conclusion}\nLogs:\n{logs}"
                        )
                    release = [
                        release for release in temporary_repository.get_releases()
                    ][0]
                    assert release.title == expected_tag
                    # Perform the release
                    release.update_release(
                        name=release.title, message=release.body, draft=False
                    )
                    tags = [tag for tag in temporary_repository.get_tags()]
                    assert tags[0].name == expected_tag


@pytest.mark.parametrize(
    "branch_name, expected_tag",
    [
        ("fix/patch", "0.1.0"),
        ("feature/minor", "0.1.0"),
        ("patch!/major", "0.1.0"),
    ],
)
@pytest.mark.parametrize("tag_already_exists", [True, False])
def test_reusable_release_draft_repo_without_exising_release(
    temporary_repository, branch_name, expected_tag, tag_already_exists
):
    """
    When a release is drafted into a repository without an existing release,
    the first release drafted will always reflect 0.1.0. If a tag 0.1.0 exists,
    the release will attempt to point at that existing tag and will not create
    a new tag. This behavior is slightly counterintuitive, but is documented
    here and in the markdown files for our release workflows, and users are
    encouraged to edit the drafted release in the case of the draft workflow,
    or encouraged to create a release before running the release-on-merge
    workflow.
    """

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
            content=PR_WORKFLOW_CONTENTS,
            branch=main.name,
            commit_message="Add reusable PR label workflow file",
        )
        populate_file(
            repository=temporary_repository,
            path=".github/workflows/release-draft.yml",
            content=RELEASE_WORKFLOW_CONTENTS,
            branch=main.name,
            commit_message="Add reusable release draft workflow file",
            skip_ci=True,
        )

        if tag_already_exists:
            temporary_repository.create_git_ref(
                ref="refs/tags/0.1.0", sha=main.commit.sha
            )

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
                body=f"This is a test pull request to validate the workflow drafts a release for {expected_tag}.",
            )
            label_workflow = temporary_repository.get_workflow(
                id_or_file_name="pull-request-label.yml"
            )

            with workflow_run_created(label_workflow, branch=branch.name) as label_run:
                with workflow_run_completed(label_run) as status:
                    if status != WorkflowRunStatus.COMPLETED:
                        raise AssertionError(
                            f"Workflow run for {branch_name} did not complete successfully: {status}"
                        )
                    if label_run.conclusion != WorkflowRunConclusion.SUCCESS:
                        logs = get_workflow_run_logs(
                            label_run, drop_log_timestamps=True
                        )
                        raise AssertionError(
                            f"Workflow run for {branch_name} did not succeed as expected: {label_run.conclusion}\nLogs:\n{logs}"
                        )
                    pr_labels = [label.name for label in pull_request.get_labels()]
                    assert (
                        pr_labels
                    ), "Expected at least one label to be applied to the pull request!"

            pull_request.merge()

            release_workflow = temporary_repository.get_workflow(
                id_or_file_name="release-draft.yml"
            )

            with workflow_run_created(
                release_workflow, branch=main.name
            ) as drafter_run:
                with workflow_run_completed(drafter_run) as status:
                    if status != WorkflowRunStatus.COMPLETED:
                        raise AssertionError(
                            f"Release drafter workflow run did not complete successfully: {status}"
                        )
                    if drafter_run.conclusion != WorkflowRunConclusion.SUCCESS:
                        logs = get_workflow_run_logs(
                            drafter_run, drop_log_timestamps=True
                        )
                        raise AssertionError(
                            f"Release drafter workflow run did not succeed as expected: {drafter_run.conclusion}\nLogs:\n{logs}"
                        )
                    release = [
                        release for release in temporary_repository.get_releases()
                    ][0]
                    assert release.title == expected_tag
                    # Perform the release
                    release.update_release(
                        name=release.title, message=release.body, draft=False
                    )
                    tags = [tag for tag in temporary_repository.get_tags()]
                    assert tags[0].name == expected_tag


@pytest.mark.parametrize(
    "branch_name, expected_tag",
    [
        ("fix/patch", "0.1.1"),
        ("feature/minor", "0.2.0"),
        ("patch!/major", "1.0.0"),
    ],
)
def test_reusable_release_draft_repo_with_exising_release(
    temporary_repository, branch_name, expected_tag
):
    """
    First PR tag defaults to major, so this isn't working the way I'd originally hoped.

    Maybe we change up the testing strategy for the release workflows entirely. Set
    up repositories in states where they're likely to need release-drafter workflows installed:

    - Brand new repo, no existing pull requests, tags, or releases
    - Existing repo with pull requests and tags -> go through draft/update/publish and then merge another PR
    - Existing repo with pull requests, tags, and releases
    """

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
            content=PR_WORKFLOW_CONTENTS,
            branch=main.name,
            commit_message="Add reusable PR label workflow file",
        )
        populate_file(
            repository=temporary_repository,
            path=".github/workflows/release-draft.yml",
            content=RELEASE_WORKFLOW_CONTENTS,
            branch=main.name,
            commit_message="Add reusable release draft workflow file",
            skip_ci=True,
        )

        # Create the 0.1.0 release ahead of time
        temporary_repository.create_git_release(
            tag="0.1.0",
            name="Release 0.1.0",
            message="This is the first release.",
            draft=False,
            prerelease=False,
            generate_release_notes=True,
            target_commitish=main,
        )

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
                body=f"This is a test pull request to validate the workflow drafts a release for {expected_tag}.",
            )
            label_workflow = temporary_repository.get_workflow(
                id_or_file_name="pull-request-label.yml"
            )

            with workflow_run_created(label_workflow, branch=branch.name) as label_run:
                with workflow_run_completed(label_run) as status:
                    if status != WorkflowRunStatus.COMPLETED:
                        raise AssertionError(
                            f"Workflow run for {branch_name} did not complete successfully: {status}"
                        )
                    if label_run.conclusion != WorkflowRunConclusion.SUCCESS:
                        logs = get_workflow_run_logs(
                            label_run, drop_log_timestamps=True
                        )
                        raise AssertionError(
                            f"Workflow run for {branch_name} did not succeed as expected: {label_run.conclusion}\nLogs:\n{logs}"
                        )
                    pr_labels = [label.name for label in pull_request.get_labels()]
                    assert (
                        pr_labels
                    ), "Expected at least one label to be applied to the pull request!"

            pull_request.merge()

            release_workflow = temporary_repository.get_workflow(
                id_or_file_name="release-draft.yml"
            )

            with workflow_run_created(
                release_workflow, branch=main.name
            ) as drafter_run:
                with workflow_run_completed(drafter_run) as status:
                    if status != WorkflowRunStatus.COMPLETED:
                        raise AssertionError(
                            f"Release drafter workflow run did not complete successfully: {status}"
                        )
                    if drafter_run.conclusion != WorkflowRunConclusion.SUCCESS:
                        logs = get_workflow_run_logs(
                            drafter_run, drop_log_timestamps=True
                        )
                        raise AssertionError(
                            f"Release drafter workflow run did not succeed as expected: {drafter_run.conclusion}\nLogs:\n{logs}"
                        )
                    release = [
                        release for release in temporary_repository.get_releases()
                    ][0]
                    assert release.title == expected_tag or breakpoint()
                    # Perform the release
                    release.update_release(
                        name=release.title, message=release.body, draft=False
                    )
                    tags = [tag for tag in temporary_repository.get_tags()]
                    assert tags[0].name == expected_tag


@pytest.mark.parametrize(
    "branch_name, initial_release_target_tag, update_to_tag",
    [
        ("fix/patch", "0.1.0", "1.0.2"),
        ("feature/minor", "0.1.0", "1.1.0"),
        ("patch!/major", "0.1.0", "2.0.0"),
    ],
)
def test_reusable_release_draft_existing_repo_with_prs_and_tags(
    temporary_repository, branch_name, initial_release_target_tag, update_to_tag
):
    """
    Test the reusable release drafter workflow on an existing repository with pull requests and tags.

    There have been no releases made to this repository, so the drafted release will be created with the "wrong"
    tag associated to it. The release will need to be updated by someone (in this case, the test code but typically a human)
    to reflect the next desired version before the release is published.
    """

    with branch_created(temporary_repository, "main") as main:
        temporary_repository.create_git_ref(ref="refs/tags/1.0.0", sha=main.commit.sha)

        with branch_created(temporary_repository, "branch-one", "main") as branch_one:
            populate_file(
                repository=temporary_repository,
                path="test_one.txt",
                content="Test file one",
                branch=branch_one.name,
            )
            pull_request_one = temporary_repository.create_pull(
                base="main",
                head=branch_one.name,
                title="Test PR One",
                body="This is a test pull request for branch one.",
            )
            pull_request_one.merge()
            temporary_repository.create_git_ref(
                ref="refs/tags/1.0.1",
                sha=temporary_repository.get_branch(  # get the latest sha off main
                    "main"
                ).commit.sha,
            )

        temporary_repository.get_git_ref("heads/branch-one").delete()

        # Install the workflows

        with branch_created(temporary_repository, branch_name, "main") as branch_two:
            populate_file(
                repository=temporary_repository,
                path=".github/release-drafter.yml",
                content=RELEASE_DRAFTER_CONFIG_CONTENTS,
                branch=branch_two.name,
                commit_message="Add release drafter configuration file",
            )
            populate_file(
                repository=temporary_repository,
                path=".github/workflows/pull-request-label.yml",
                content=PR_WORKFLOW_CONTENTS,
                branch=branch_two.name,
                commit_message="Add reusable PR label workflow file",
            )
            populate_file(
                repository=temporary_repository,
                path=".github/workflows/release-draft.yml",
                content=RELEASE_WORKFLOW_CONTENTS,
                branch=branch_two.name,
                commit_message="Add reusable release draft workflow file",
            )
            pull_request_two = temporary_repository.create_pull(
                base="main",
                head=branch_two.name,
                title="Install workflows",
                body="Install release workflows",
            )
            pull_request_two.merge()

            temporary_repository.get_git_ref(f"heads/{branch_name}").delete()

        # Confirm the release target
        release_workflow = temporary_repository.get_workflow(
            id_or_file_name="release-draft.yml"
        )

        with workflow_run_created(release_workflow, branch=main.name) as release_run:
            with workflow_run_completed(release_run) as status:
                if status != WorkflowRunStatus.COMPLETED:
                    raise AssertionError(
                        f"Release workflow run did not complete successfully: {status}"
                    )
                if release_run.conclusion != WorkflowRunConclusion.SUCCESS:
                    logs = get_workflow_run_logs(release_run, drop_log_timestamps=True)
                    raise AssertionError(
                        f"Release workflow run did not succeed as expected: {label_run.conclusion}\nLogs:\n{logs}"
                    )

        release = [release for release in temporary_repository.get_releases()][0]
        assert release.tag_name == initial_release_target_tag

        # Human (or computer) updates the release to the next expected tag
        release.update_release(
            name=update_to_tag,
            tag_name=update_to_tag,
            message=release.body,
            draft=False,
        )

        # Tag should have been created
        expected_tag_names = ["1.0.0", "1.0.1", update_to_tag]
        found_tag_names = [tag.name for tag in temporary_repository.get_tags()]

        assert all(tag in found_tag_names for tag in expected_tag_names) or breakpoint()
