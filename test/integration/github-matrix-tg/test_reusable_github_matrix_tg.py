import os

from github.Repository import Repository

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
WORKFLOW_FILE_CONTENTS = f"""
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


def populate_platform_folder(
    repository: Repository,
    environment: str,
    region: str,
    instance: str,
    branch: str = "main",
):
    populate_file(
        repository=repository,
        path=f"platform/{environment}/{region}/{instance}/test.txt",
        content="Test Environment File",
        branch=branch,
        commit_message=f"Add test environment file for {environment} in {region}/{instance}",
    )


def test_reusable_github_matrix_tg(temporary_repository):
    """
    Test the reusable GitHub matrix template with a temporary repository.
    """
    with branch_created(temporary_repository, "main") as main:
        populate_file(
            repository=temporary_repository,
            path=".github/workflows/github_matrix.yml",
            content=WORKFLOW_FILE_CONTENTS,
            branch=main.name,
            commit_message="Add reusable GitHub matrix workflow file",
        )
        with branch_created(
            temporary_repository, "test/matrix-happy-path", origin_branch=main.name
        ) as pr_branch:
            populate_platform_folder(
                repository=temporary_repository,
                environment="sandbox",
                region="us-east-1",
                instance="000",
                branch=pr_branch.name,
            )

        temporary_repository.create_pull(
            base=main.name,
            head=pr_branch.name,
            title="Test Reusable GitHub Matrix Template",
            body="This is a test pull request to validate the reusable GitHub matrix template with a happy path scenario.",
        )

        workflow = temporary_repository.get_workflow(
            id_or_file_name="github_matrix.yml"
        )

        with workflow_run_created(workflow, branch=pr_branch.name) as run:
            with workflow_run_completed(run) as status:
                if status != WorkflowRunStatus.COMPLETED:
                    raise AssertionError(
                        f"Workflow run for happy path did not complete successfully: {status}"
                    )
                if run.conclusion != WorkflowRunConclusion.SUCCESS:
                    logs = get_workflow_run_logs(run, drop_log_timestamps=True)
                    raise AssertionError(
                        f"Workflow run for happy path did not succeed as expected: {run.conclusion}\nLogs:\n{logs}"
                    )
                run_logs = get_workflow_run_logs(run, drop_log_timestamps=True)
                expected_lines = [
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
                assert all(line in run_logs for line in expected_lines)


def test_reusable_github_matrix_tg_no_platform_folder(temporary_repository):
    """
    Test the reusable GitHub matrix template with a temporary repository that has no platform folder.
    """

    with branch_created(temporary_repository, "main") as main:
        populate_file(
            repository=temporary_repository,
            path=".github/workflows/github_matrix.yml",
            content=WORKFLOW_FILE_CONTENTS,
            branch=main.name,
            commit_message="Add reusable GitHub matrix workflow file",
        )
        with branch_created(
            temporary_repository,
            "test/matrix-no-platform-folder",
            origin_branch=main.name,
        ) as pr_branch:
            populate_file(
                repository=temporary_repository,
                path="test.txt",
                content="Nothing to see here.",
                branch=pr_branch.name,
            )

        temporary_repository.create_pull(
            base=main.name,
            head=pr_branch.name,
            title="Test Reusable GitHub Matrix Template - No Platform Folder",
            body="This is a test pull request to validate the reusable GitHub matrix template with no platform folder. A failure is expected.",
        )

        workflow = temporary_repository.get_workflow(
            id_or_file_name="github_matrix.yml"
        )

        with workflow_run_created(workflow, branch=pr_branch.name, timeout=180) as run:
            with workflow_run_completed(run) as status:
                if status != WorkflowRunStatus.COMPLETED:
                    raise AssertionError(
                        f"Workflow run for no platform folder did not complete as expected: {status}"
                    )

                if run.conclusion != WorkflowRunConclusion.FAILURE:
                    raise AssertionError(
                        f"Workflow run for no platform folder did not fail as expected: {run.conclusion}"
                    )

            run_logs = get_workflow_run_logs(run, drop_log_timestamps=True)
            assert "FileNotFoundError" in run_logs
