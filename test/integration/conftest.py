import os
import pathlib
import random
import string
from time import sleep
from typing import Generator

import pytest
from git.repo import Repo
from github.Organization import Organization
from github.Repository import Repository

from src.launch_github import get_github_instance


@pytest.fixture(scope="session")
def test_organization_name():
    yield os.environ.get("TESTING_ORGANIZATION_NAME", "nttdtest")


@pytest.fixture(scope="session")
def github_instance():
    return get_github_instance()


@pytest.fixture(scope="function")
def organization(
    github_instance, test_organization_name
) -> Generator[Organization, None, None]:
    return github_instance.get_organization(test_organization_name)


@pytest.fixture(scope="function")
def repo_name() -> Generator[str, None, None]:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    yield f"test-repo-{suffix}"


@pytest.fixture(scope="function")
def local_repo(tmp_path) -> Generator[pathlib.Path, None, None]:
    """
    Fixture to provide a local repository path for testing.
    This creates a temporary directory that can be used as a local repository.
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize a git repository in the temporary directory
    os.system(f"git init {repo_path}")

    yield repo_path

    # Cleanup: remove the temporary directory after the test
    if repo_path.exists():
        os.system(f"rm -rf {repo_path}")


@pytest.fixture(scope="function")
def temporary_repository(
    request, test_organization_name, organization, repo_name, tmp_path
) -> Generator[tuple[Repository, Repo], None, None]:
    """
    Fixture to create a temporary GitHub repository for testing.
    This repository will be created in the test organization and deleted after the test.
    """
    github_repo = organization.create_repo(
        name=repo_name,
        description=f"Test Repository for Integration Test: {request.node.name}",
        private=False,
        visibility="public",
        auto_init=False,
    )

    max_tries = 10
    found = False
    attempt = 0
    while not found and attempt < max_tries:
        for repo in organization.get_repos():
            if repo.name == repo_name:
                found = True
                break
        sleep(1)
        attempt += 1

    if not found:
        raise RuntimeError(
            f"Repository {repo_name} not found on GitHub after {max_tries} attempts!"
        )

    yield github_repo
    github_repo.delete()
