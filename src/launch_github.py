import logging
import os
import tempfile
import zipfile
from contextlib import contextmanager
from enum import StrEnum
from pathlib import Path
from time import sleep, time
from typing import Generator

import requests
from github import Auth, Consts, Github, GithubException
from github.Branch import Branch
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


def populate_file(
    repository: Repository,
    path: str,
    content: str,
    branch: str = "main",
    commit_message: str | None = None,
    skip_ci: bool = False,
):
    """
    Populate a file in the repository.
    """
    commit_message = f"Add {path}" if commit_message is None else commit_message
    commit_message = f"{commit_message} [skip ci]" if skip_ci else commit_message
    repository.create_file(
        path=path,
        message=commit_message,
        content=content,
        branch=branch,
    )


@contextmanager
def workflow_run_created(
    workflow: Workflow, branch: str, timeout: int = 60
) -> Generator[WorkflowRun, None, None]:
    """
    Context manager to wait for a workflow run to be created.
    """
    run = None
    found = False
    start_time = time()
    while time() - start_time < timeout and not found:
        try:
            workflow_runs = list(workflow.get_runs(branch=branch))
            if workflow_runs:
                logger.debug(f"Workflow run found for branch '{branch}'.")
                found = True
                run = workflow_runs[0]
            else:
                sleep(1)
        except GithubException as ghe:
            logger.error(f"Error while checking for workflow runs: {ghe}")
    if found:
        yield run
    else:
        raise TimeoutError(
            f"Workflow run did not appear for branch '{branch}' within the timeout period."
        )


@contextmanager
def workflow_run_completed(
    workflow_run: WorkflowRun, timeout: int = 120
) -> Generator[WorkflowRunStatus, None, None]:
    """
    Context manager to wait for a workflow run to complete.
    """
    status = None
    found = False
    start_time = time()
    while time() - start_time < timeout and not found:
        workflow_run.update()
        if workflow_run.status in (
            WorkflowRunStatus.COMPLETED,
            WorkflowRunStatus.FAILED,
        ):
            found = True
            status = workflow_run.status
        else:
            sleep(1)
    if found:
        yield status
    else:
        raise TimeoutError("Workflow run did not complete within the timeout period.")


@contextmanager
def branch_created(
    github_repo: Repository,
    branch_name: str,
    origin_branch: str | None = None,
    timeout: int = 60,
) -> Generator[Branch, None, None]:
    """
    Context manager to create a branch and wait for it to be usable.
    """
    start_time = time()
    if origin_branch is None:
        # We're creating main, which has to have a file in it, so create a README.md
        populate_file(
            repository=github_repo,
            path="README.md",
            content=f"# README for {github_repo.name}\n\nThis is the main branch.",
        )
    else:
        # Create the branch from the specified origin branch
        origin_found = False
        while not origin_found and time() - start_time < timeout:
            try:
                origin_branch = github_repo.get_branch(origin_branch)
                origin_found = True
            except GithubException as ghe:
                if ghe.status == 404:
                    sleep(1)
                else:
                    raise ghe
        if not origin_found:
            raise TimeoutError(
                f"Origin branch '{origin_branch}' not found in repository '{github_repo.name}'."
            )

        github_repo.create_git_ref(
            f"refs/heads/{branch_name}", origin_branch.commit.sha
        )
    found = False
    while time() - start_time < timeout and not found:
        try:
            branch = github_repo.get_branch(branch_name)
            found = True
        except GithubException as ghe:
            if ghe.status == 404:
                continue
            else:
                raise ghe
    if found:
        yield branch
    else:
        raise TimeoutError(
            f"Branch '{branch_name}' did not appear within the timeout period."
        )
