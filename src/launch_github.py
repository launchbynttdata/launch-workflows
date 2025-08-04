import logging
import os
import tempfile
import zipfile
from enum import StrEnum
from pathlib import Path
from time import sleep

import requests
from github import Auth, Consts, Github
from github.Repository import Repository
from github.Workflow import Workflow
from github.WorkflowRun import WorkflowRun

logger = logging.getLogger(__name__)


class WorkflowRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowRunConclusion(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"


def read_github_token() -> str:
    try:
        return os.environ["GITHUB_TOKEN"]
    except KeyError:
        raise RuntimeError(
            "ERROR: The GITHUB_TOKEN environment variable is not set. You must set this environment variable."
        )


def get_github_instance(token: str | None = None, timeout: int | None = None) -> Github:
    if timeout is None:
        timeout = Consts.DEFAULT_TIMEOUT
    if not token:
        token = read_github_token()
    auth = Auth.Token(token)
    return Github(auth=auth, timeout=timeout)


def populate_readme_file(
    repository: Repository, branch: str = "main", content: str = "# README"
):
    repository.create_file(
        path="README.md",
        message="Add README",
        content=content,
        branch=branch,
    )


def wait_for_workflow_run_create(workflow: Workflow, branch: str, timeout=60):
    """
    Wait for a workflow run to be created.
    """
    for _ in range(timeout):
        runs = list(workflow.get_runs(branch=branch))
        if runs:
            return runs[0]
        sleep(1)
    raise TimeoutError("A workflow run did not appear within the timeout period.")


def wait_for_workflow_run_completion(
    workflow_run: WorkflowRun, timeout=60
) -> WorkflowRunStatus:
    """
    Wait for a workflow run to be completed.
    """
    for _ in range(timeout):
        workflow_run.update()
        status = workflow_run.status
        if status in (
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
        ):
            return status
        sleep(1)
    breakpoint()
    raise TimeoutError("Workflow run did not complete within the timeout period.")


def get_workflow_run_logs(
    workflow_run: WorkflowRun, drop_log_timestamps: bool = False
) -> str:
    """
    Retrieve the logs of a workflow run.
    """
    logs_url = workflow_run.logs_url
    response = requests.get(
        logs_url,
        headers={"Authorization": f"Bearer {read_github_token()}"},
    )
    response.raise_for_status()

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = Path(temp_dir).joinpath("logs.zip")
        with open(zip_path, "wb") as f:
            f.write(response.content)
        extract_dir = Path(temp_dir).joinpath("logs")
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        # Return contents of the text file at the top of the extract path
        text_file = list(extract_dir.glob("*.txt"))[0]
        contents = text_file.read_text(encoding="utf-8")

        if drop_log_timestamps:
            contents = "\n".join([line[29:] for line in contents.splitlines()])

    return contents
