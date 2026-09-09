# Dependabot Auto-Merge

Automatically enables GitHub's auto-merge (squash strategy) on pull requests created by Dependabot. Once all required status checks pass and any required approvals are in place, the PR will be merged automatically.

This workflow only runs when the PR actor is `dependabot[bot]`. For all other actors, the job is skipped.

A GitHub App token is used to perform the merge rather than `GITHUB_TOKEN`. This ensures that the resulting push to the default branch is attributed to the GitHub App rather than `dependabot[bot]`, which allows downstream workflows (such as a release process) to be triggered as expected. When Dependabot performs the merge directly, GitHub suppresses re-triggering of actions to prevent infinite loops.

## Prerequisite

GitHub auto-merge must be enabled on the repository using this workflow.

Go to:

`Settings > General > Pull Requests > Allow auto-merge`

If auto-merge is disabled, the workflow stops before attempting the merge and reports a clear configuration error.

## Usage

Add the following workflow to your repository (suggested name: `.github/workflows/pr-dependabot-automerge.yml`):

```yaml
name: Dependabot Auto-Merge

on:
  pull_request:
    types: [opened, reopened, synchronize]

permissions:
  contents: write
  pull-requests: write

jobs:
  dependabot-automerge:
    name: Dependabot Auto-Merge
    permissions:
      contents: write
      pull-requests: write
    uses: launchbynttdata/launch-workflows/.github/workflows/reusable-pr-dependabot-automerge.yml@ref
    with:
      skeleton_update_app_id: ${{ vars.LAUNCH_SKELETON_UPDATE_APP_ID }}
    secrets: inherit
```

Be sure you replace `ref` with an appropriate ref to this repository.

> [!TIP]
> This workflow pairs well with the [Automated Approvals](reusable-pr-automated-approvals.md) workflow. When both are active, Dependabot PRs receive automated approvals and are then auto-merged once all status checks pass.

## Inputs

| Input | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `skeleton_update_app_id` | `string` | No | `vars.LAUNCH_SKELETON_UPDATE_APP_ID` | The GitHub App ID to use for authentication when enabling auto-merge. The app must be installed on the repository with permissions to read and write code and create pull requests. |

## Secrets

| Secret | Required | Description |
|--------|----------|-------------|
| `LAUNCH_SKELETON_UPDATE_KEY` | Yes | The private key for the GitHub App used for authentication. |

## Required Permissions

The calling workflow must grant `contents: write` and `pull-requests: write` permissions. The GitHub App identified by `skeleton_update_app_id` and `LAUNCH_SKELETON_UPDATE_KEY` must be installed on the repository with permissions to read and write code and to read and write pull requests.
