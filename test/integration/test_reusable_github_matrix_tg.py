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


def populate_workflow_file(repository: Repository):
    content = f"""
name: GitHub Matrix Workflow

on:
    pull_request:

jobs:
  build-matrix:
    permissions:
      contents: read
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-github-matrix-tg.yml@{LAUNCH_WORKFLOWS_REF_TO_TEST}
    with:
      platform_environment: sandbox
"""
    repository.create_file(
        ".github/workflows/github_matrix.yml",
        content=content,
        branch="main",
        message="Add workflow file for reusable GitHub matrix",
    )


def populate_platform_folder(
    repository: Repository,
    environment: str,
    region: str,
    instance: str,
    branch: str = "main",
):
    repository.create_file(
        path=f"platform/{environment}/{region}/{instance}/test.txt",
        message=f"Add test environment file for {environment} in {region}/{instance}",
        content="Test Environment File",
        branch=branch,
    )


def test_reusable_github_matrix_tg(temporary_repository):
    """
    Test the reusable GitHub matrix template with a temporary repository.
    """
    github_repo, _ = temporary_repository

    assert github_repo.name.startswith("test-repo-")
    assert github_repo.private is False
    assert github_repo.visibility == "public"

    populate_workflow_file(repository=github_repo)

    github_repo.create_git_ref(
        "refs/heads/test/matrix-happy-path", github_repo.get_branch("main").commit.sha
    )
    sleep(1)
    populate_readme_file(github_repo, branch="test/matrix-happy-path")
    populate_platform_folder(
        repository=github_repo,
        environment="sandbox",
        region="us-east-1",
        instance="000",
        branch="test/matrix-happy-path",
    )

    github_repo.create_git_ref(
        "refs/heads/test/matrix-missing-platform-folder",
        github_repo.get_branch("main").commit.sha,
    )
    sleep(1)
    populate_readme_file(github_repo, branch="test/matrix-missing-platform-folder")

    github_repo.create_pull(
        base="main",
        head="test/matrix-happy-path",
        title="Test Reusable GitHub Matrix Template - Happy Path",
        body="This is a test pull request to validate the reusable GitHub matrix template with a happy path scenario.",
    )
    github_repo.create_pull(
        base="main",
        head="test/matrix-missing-platform-folder",
        title="Test Reusable GitHub Matrix Template - Missing Platform Folder",
        body="This is a test pull request to validate the reusable GitHub matrix template with a missing platform folder. A failure is expected.",
    )

    workflow = github_repo.get_workflow(id_or_file_name="github_matrix.yml")

    run_happy_path = wait_for_workflow_run_create(
        workflow, branch="test/matrix-happy-path"
    )
    status_happy_path = wait_for_workflow_run_completion(run_happy_path)
    if status_happy_path != WorkflowRunStatus.COMPLETED:
        raise AssertionError(
            f"Workflow run for happy path did not complete successfully: {status_happy_path}"
        )
    if run_happy_path.conclusion != WorkflowRunConclusion.SUCCESS:
        raise AssertionError(
            f"Workflow run for happy path did not succeed as expected: {run_happy_path.conclusion}"
        )

    run_missing_platform_folder = wait_for_workflow_run_create(
        workflow, branch="test/matrix-missing-platform-folder"
    )
    status_missing_platform_folder = wait_for_workflow_run_completion(
        run_missing_platform_folder
    )
    if status_missing_platform_folder != WorkflowRunStatus.COMPLETED:
        raise AssertionError(
            f"Workflow run for missing platform folder did not complete as expected: {status_missing_platform_folder}"
        )
    if run_missing_platform_folder.conclusion != WorkflowRunConclusion.FAILURE:
        raise AssertionError(
            f"Workflow run for missing platform folder did not fail as expected: {run_missing_platform_folder.conclusion}"
        )

    logs_happy_path = get_workflow_run_logs(run_happy_path, drop_log_timestamps=True)
    logs_missing_platform_folder = get_workflow_run_logs(run_missing_platform_folder)

    happy_path_expected_lines = [
        "Generated the following environment matrix:",
        "{",
        '    "terragrunt_environment": [',
        "        {",
        '            "environment": "sandbox",',
        '            "region": "us-east-1",',
        '            "instance": "000"',
        "        }",
        "    ]",
        "}",
    ]

    assert all(line in logs_happy_path for line in happy_path_expected_lines)
    assert "FileNotFoundError" in logs_missing_platform_folder
