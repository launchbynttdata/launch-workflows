# Dependabot Auto-Merge

Automatically enables GitHub's auto-merge (squash strategy) on pull requests created by Dependabot. Once all required status checks pass and any required approvals are in place, the PR will be merged automatically.

This workflow only runs when the PR actor is `dependabot[bot]`. For all other actors, the job is skipped.

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
    secrets: inherit
```

Be sure you replace `ref` with an appropriate ref to this repository.

> [!TIP]
> This workflow pairs well with the [Automated Approvals](reusable-pr-automated-approvals.md) workflow. When both are active, Dependabot PRs receive automated approvals and are then auto-merged once all status checks pass.

## Inputs

This workflow has no configurable inputs.

## Required Permissions

The calling workflow must grant `contents: write` and `pull-requests: write` permissions so that the `GITHUB_TOKEN` can enable auto-merge on the pull request.
