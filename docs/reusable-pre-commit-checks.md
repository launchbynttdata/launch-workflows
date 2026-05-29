# Pre-Commit Checks

Runs the repository's [`pre-commit`](https://pre-commit.com/) hooks against all files in CI. This is useful for enforcing linting, formatting, and other repository-defined checks on every pull request without relying on contributors to have a working local `pre-commit` install.

The workflow uses [`uv`](https://docs.astral.sh/uv/) (via [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv)) to install and run `pre-commit` with the [`pre-commit-uv`](https://github.com/tox-dev/pre-commit-uv) plugin, and [`asdf`](https://asdf-vm.com/) (via [`asdf-vm/actions`](https://github.com/asdf-vm/actions)) to provision any additional tools declared in a `.tool-versions` file at the repository root. Both the `pre-commit` environment and `asdf`-installed tools are cached between runs to keep execution fast.

On completion, the workflow publishes a `Pre-Commit Checks` commit status to the head SHA via the [`update-status-check`](../.github/actions/update-status-check) action so the result is visible on the pull request even when the underlying job is skipped or re-run.

## Usage

Add the following workflow to your repository (suggested name: `.github/workflows/pull-request-precommit-checks.yml`):

```yaml
name: Pre-Commit Checks

on:
  pull_request:
    types: [opened, reopened, synchronize, ready_for_review]
    branches: [main]

jobs:
  pre-commit:
    name: Pre-Commit Checks
    permissions:
      contents: read
      pull-requests: read
      statuses: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-pre-commit-checks.yml@ref
```

Be sure you replace `ref` with an appropriate ref to this repository.

Your repository must contain a valid `.pre-commit-config.yaml` at the root. If additional CLI tooling is required by your hooks (e.g. `terraform`, `tflint`, `terragrunt`), declare it in a `.tool-versions` file at the repository root and `asdf` will install it before the hooks run.

> [!CAUTION]
> By default, we are not enforcing pre-commit as a required quality gate to merge PRs into _most_ repositories. This will change as we finish migrating to the new workflows and pre-commit runs in more places.
>
> If you need to enforce this on a particular repository in the meantime, reach out to an Organization Admin (generally via Slack) and have them add your repository to the [pre-commit-checks-validation](https://github.com/organizations/launchbynttdata/settings/rules/15529245) branch protection rule.

To make this workflow required, visit your repository's settings and create a new Ruleset with a required status check pointing at `Pre-Commit Checks`.

## Inputs

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `_placeholder` | `string` | No | `""` | Unused. Reserved for future use; do not set. |

## Secrets

This workflow does not consume any secrets.

## Required Permissions

The calling workflow must grant the following permissions:

| Permission | Level | Reason |
|------------|-------|--------|
| `contents` | `read` | Check out the repository at the PR head. |
| `pull-requests` | `read` | Read PR metadata when invoked from a `pull_request` event. |
| `statuses` | `write` | Publish the `Pre-Commit Checks` commit status to the head SHA. |
